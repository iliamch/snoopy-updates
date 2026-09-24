"""Download, verify, install and configure a complete Snoopy Linux installation."""
import hashlib
import io
import tarfile
import importlib.util
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

RELEASE = "https://github.com/iliamch/snoopy-updates/releases/download/v2026.09.24/"
BASE_RELEASE = "https://github.com/iliamch/snoopy-updates/releases/download/v2026.09.20.2/"
APP_NAME = "snoopy-linux_1.1.0_all.deb"
APP_SHA = "c149a46b50429512f9baf3c02b0031e12b89a22df9d9c150d723f833889242ba"
MEDIA_NAME = "SnoopyLinux-Media-1.zip"
MEDIA_SHA = "40f1c7c6d6ed61ed72afa934f85530a0605ecf605f8d9ceb594953caee5fa33f"

def digest(path):
    with Path(path).open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()

def download(name, expected, cache):
    target=cache/name
    if target.is_file() and digest(target)==expected:return target
    partial=cache/(name+".part")
    if not partial.is_file() or digest(partial)!=expected:
        print("Downloading "+name+"...",flush=True)
        subprocess.run(["curl","--fail","--location","--retry","3","--continue-at","-","--output",str(partial),(BASE_RELEASE if name==MEDIA_NAME else RELEASE)+name],check=True)
    if digest(partial)!=expected:
        partial.unlink()
        raise RuntimeError("Download checksum mismatch. Please run the installer again.")
    partial.replace(target)
    return target

def extract_media(archive, root):
    root=Path(root);target=root/"Media-1"
    if (target/"installed-archive.sha256").is_file() and (target/"installed-archive.sha256").read_text().strip()==MEDIA_SHA and (target/"scenes.json").is_file():return target
    print("Extracting and checking the animation library...",flush=True)
    with tempfile.TemporaryDirectory(prefix="media-install-",dir=root) as temp:
        stage=Path(temp)
        with zipfile.ZipFile(archive) as package:
            members=package.infolist();names=[m.filename for m in members]
            if len(names)!=len(set(names)) or len(names)>10000:raise ValueError("Invalid media entries")
            if sum(m.file_size for m in members)>3*1024**3:raise ValueError("Media archive too large")
            for member in members:
                path=PurePosixPath(member.filename)
                if path.is_absolute() or ".." in path.parts or "\\" in member.filename or path.parts[0]!="Media" or stat.S_ISLNK(member.external_attr>>16):raise ValueError("Unsafe media path")
            manifest=json.loads(package.read("Media/SHA256SUMS.json"))
            if set(names)!=set(manifest)|{"Media/SHA256SUMS.json"}:raise ValueError("Media manifest mismatch")
            for member in members:
                path=stage/member.filename;path.parent.mkdir(parents=True,exist_ok=True)
                with package.open(member) as source,path.open("wb") as output:shutil.copyfileobj(source,output,1024*1024)
                if member.filename in manifest and digest(path)!=manifest[member.filename]:raise ValueError("Media file checksum mismatch")
        ready=stage/"Media"
        if not (ready/"scenes.json").is_file() or not (ready/"IdleAssets/catalog.json").is_file():raise ValueError("Media is incomplete")
        (ready/"installed-archive.sha256").write_text(MEDIA_SHA+"\n")
        if target.exists():target=root/("Media-1-"+os.urandom(4).hex())
        ready.rename(target)
    return target

def prepare_idle_from_deb(app,media,cache):
    # The entire .deb is pinned by SHA256 before any contained Python is loaded.
    payload=Path(app).read_bytes()
    if digest(app)!=APP_SHA or payload[:8]!=b'!<arch>\n':raise ValueError('Invalid application package')
    at=8;data=None
    while at+60<=len(payload):
        header=payload[at:at+60];size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
        at+=60
        if name=='data.tar.gz':data=payload[at:at+size]
        at+=size+(size%2)
    if data is None:raise ValueError('Application payload missing')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as package:
        member=package.getmember('usr/share/snoopy-linux/snoopy/media_update.py')
        if not member.isfile() or member.size>100000:raise ValueError('Invalid media installer')
        code=package.extractfile(member).read()
    helper=cache/'verified_idle_installer.py';helper.write_bytes(code)
    spec=importlib.util.spec_from_file_location('snoopy_idle_installer',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ensure(media)

def configure(media):
    root=Path(os.environ.get("XDG_CONFIG_HOME",Path.home()/".config"))/"snoopy"
    root.mkdir(parents=True,exist_ok=True);settings=root/"settings.json"
    if settings.exists():
        data=json.loads(settings.read_text())
        if not isinstance(data,dict):raise ValueError("Existing settings are invalid; they were left unchanged")
    else:data={}
    data["MediaPath"]=str(media)
    temporary=root/("settings-"+os.urandom(4).hex()+".json")
    temporary.write_text(json.dumps(data,indent=2));os.replace(temporary,settings)

def main():
    if sys.platform!="linux":raise SystemExit("Run this installer on Ubuntu or Debian Linux.")
    if os.geteuid()==0:raise SystemExit("Run this command as your normal user, without sudo. It will ask for sudo only when needed.")
    if platform.machine() not in ("x86_64","aarch64","arm64"):raise SystemExit("Supported processors: Intel/AMD 64-bit and ARM64.")
    release=platform.freedesktop_os_release();distro=release.get("ID");release_version=tuple(int(p) for p in release.get("VERSION_ID","0").split(".") if p.isdigit())
    if not ((distro=="ubuntu" and release_version>=(24,4)) or (distro=="debian" and release_version>=(12,))):raise SystemExit("This package requires Ubuntu 24.04+ or Debian 12+.")
    if sys.version_info<(3,11):raise SystemExit("Python 3.11 or newer is required.")
    root=Path(os.environ.get("XDG_DATA_HOME",Path.home()/".local/share"))/"SnoopyLinux";root.mkdir(parents=True,exist_ok=True)
    cache=Path(os.environ.get("XDG_CACHE_HOME",Path.home()/".cache"))/"SnoopyLinuxInstaller";cache.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(root).free<8*1024**3:raise SystemExit("Free at least 8 GB of space before installing Snoopy's animation library.")
    print("Installing Snoopy for "+platform.machine()+". The animation download is about 4.2 GB (base library plus the new idle scenes).",flush=True)
    subprocess.run(["sudo","apt-get","update"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","curl","ca-certificates"],check=True)
    app=download(APP_NAME,APP_SHA,cache);archive=download(MEDIA_NAME,MEDIA_SHA,cache)
    # Extract and verify all media before changing the application or its preferences.
    media=extract_media(archive,root)
    archive.unlink()  # Verified base media is installed; free cache space before the idle upgrade.
    prepare_idle_from_deb(app,media,cache)
    # /tmp copy is readable by apt's download sandbox even with a private home directory.
    with tempfile.TemporaryDirectory(prefix="snoopy-deb-") as temp:
        os.chmod(temp,0o755);package=Path(temp)/APP_NAME;shutil.copyfile(app,package);os.chmod(package,0o644)
        subprocess.run(["sudo","apt-get","install","-y",str(package)],check=True)
    configure(media)
    print("Snoopy installed. Open Snoopy from the applications menu, or type: snoopy-linux",flush=True)
    print("Animations are configured automatically. Automatic idle startup is optional in Settings. Your screen lock is unchanged.",flush=True)
    print("Try Preview on this desktop first; automatic idle support depends on the desktop.",flush=True)

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:raise SystemExit("Installation stopped: "+str(error))

