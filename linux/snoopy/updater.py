"""Anonymous GitHub updates into a user-owned, atomically selected version directory."""
import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
from . import VERSION
from .core import data_root
from .services import fetch_json

API = "https://api.github.com/repos/iliamch/snoopy-updates"
PREFIX = "SnoopyLinuxUpdate-"

def version(value):
    if not re.fullmatch(r"\d+\.\d+\.\d+",value): raise ValueError("Invalid version")
    return tuple(map(int,value.split(".")))

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def select(releases,installed=VERSION):
    offers=[]
    for release in releases:
        if release.get("draft") or release.get("prerelease"):continue
        for asset in release.get("assets",[]):
            match=re.fullmatch(re.escape(PREFIX)+r"(\d+\.\d+\.\d+)\.tar\.gz",asset["name"])
            if not match or version(match[1])<=version(installed):continue
            if asset.get("state")!="uploaded" or not 0<asset["size"]<20*1024*1024:continue
            if not re.fullmatch(r"sha256:[0-9a-f]{64}",asset.get("digest") or ""):raise ValueError("Release checksum missing")
            if not re.fullmatch(re.escape(API)+r"/releases/assets/\d+",asset.get("url", "")):raise ValueError("Invalid asset URL")
            offers.append(dict(version=match[1],asset=asset))
    return max(offers,key=lambda x:version(x["version"])) if offers else None

def check():
    return select(fetch_json(API+"/releases?per_page=100"))

class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,url):
        target=urlparse(url)
        if target.scheme!="https" or target.hostname not in ("release-assets.githubusercontent.com","objects.githubusercontent.com") or target.username or target.port not in (None,443):
            raise ValueError("Untrusted update redirect")
        return super().redirect_request(request,fp,code,msg,headers,url)

def download(offer, destination):
    asset=offer["asset"]
    if not re.fullmatch(re.escape(API)+r"/releases/assets/\d+",asset["url"]):raise ValueError("Invalid asset URL")
    request=Request(asset["url"],headers={"Accept":"application/octet-stream","User-Agent":"SnoopyLinux/"+VERSION,"X-GitHub-Api-Version":"2022-11-28"})
    total=0
    with build_opener(SafeRedirect()).open(request,timeout=30) as response, open(destination,"wb") as output:
        while True:
            block=response.read(65536)
            if not block:break
            total+=len(block)
            if total>asset["size"] or total>20*1024*1024:raise ValueError("Update exceeds expected size")
            output.write(block)
    if total!=asset["size"] or "sha256:"+sha256(destination)!=asset["digest"]:raise ValueError("Update checksum mismatch")

def extract(archive, destination, expected):
    destination=Path(destination)
    with tarfile.open(archive,"r:gz") as package:
        members=package.getmembers()
        names=[m.name for m in members]
        if len(names)!=len(set(names)) or len(names)>100:raise ValueError("Invalid package entries")
        if sum(m.size for m in members)>20*1024*1024:raise ValueError("Expanded package too large")
        for member in members:
            path=PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or "\\" in member.name or not re.fullmatch(r"[A-Za-z0-9_./-]+",member.name):raise ValueError("Unsafe package path")
        manifest=json.load(package.extractfile("UpdatePackage.json"))
        if manifest.get("Edition")!="SnoopyLinux" or manifest.get("Version")!=expected:raise ValueError("Wrong edition or version")
        if set(names)!={"UpdatePackage.json",*manifest["Files"]}:raise ValueError("Package file list mismatch")
        for member in members:
            payload=package.extractfile(member).read()
            if member.name!="UpdatePackage.json" and hashlib.sha256(payload).hexdigest()!=manifest["Files"][member.name]:raise ValueError("Payload checksum mismatch")
            target=destination/member.name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
    source=(destination/"snoopy/__init__.py").read_text()
    if not re.search(r'VERSION\s*=\s*[\'"]'+re.escape(expected)+r'[\'"]',source):raise ValueError("Application version mismatch")

def install(offer):
    if version(offer["version"])<=version(VERSION):raise ValueError("Older version refused")
    root=data_root();root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="update-",dir=root) as temp:
        temp=Path(temp);archive=temp/"download.tar.gz";download(offer,archive)
        ready=temp/"ready";extract(archive,ready,offer["version"])
        # Execute the verified candidate media migrator before selecting the new version.
        from .core import load_settings
        media=load_settings()["MediaPath"]
        subprocess.run([sys.executable,"-c","from snoopy.media_update import ensure; import sys; ensure(sys.argv[1])",media],cwd=ready,check=True)
        versions=root/"versions";versions.mkdir(exist_ok=True)
        target=versions/offer["version"]
        if target.exists():
            # Never overwrite a running version. Select a fresh verified directory.
            target=versions/(offer["version"]+"-"+os.urandom(4).hex())
        ready.rename(target)
        link=root/("current-"+os.urandom(4).hex());link.symlink_to(target,target_is_directory=True)
        current=root/"current"
        if current.exists() and not current.is_symlink():raise ValueError("Current installation is not a managed link")
        os.replace(link,current)
    return target
