#!/usr/bin/env python3
import argparse
import hashlib
import gzip
import io
import json
import tarfile
from pathlib import Path
from snoopy import VERSION

ROOT=Path(__file__).resolve().parent
def tar_bytes(files, directories=False):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode="w",format=tarfile.USTAR_FORMAT) as tar:
        if directories:
            parents=set()
            for name,_,_ in files:
                parts=name.split('/')[:-1]
                for depth in range(1,len(parts)+1):parents.add('/'.join(parts[:depth]))
            for name in sorted(parents,key=lambda x:(x.count('/'),x)):
                info=tarfile.TarInfo(name+'/');info.type=tarfile.DIRTYPE;info.mode=0o755;info.uid=info.gid=0;info.mtime=0
                tar.addfile(info)
        for name,payload,mode in files:
            info=tarfile.TarInfo(name);info.size=len(payload);info.mode=mode;info.uid=info.gid=0;info.mtime=0
            tar.addfile(info,io.BytesIO(payload))
    return gzip.compress(stream.getvalue(),mtime=0)

def ar_write(path,files):
    with path.open("wb") as out:
        out.write(b"!<arch>\n")
        for name,payload in files:
            header=f'{name+"/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(payload):<10}`\n'.encode("ascii")
            if len(header)!=60:raise ValueError("Invalid ar header")
            out.write(header);out.write(payload)
            if len(payload)%2:out.write(b"\n")

def build(out):
    out.mkdir(parents=True,exist_ok=True)
    app=[("main.py",(ROOT/"main.py").read_bytes(),0o644)]
    app += [(f.relative_to(ROOT).as_posix(),f.read_bytes(),0o644) for f in sorted((ROOT/"snoopy").glob("*.py"))]
    manifest=dict(Edition="SnoopyLinux",Version=VERSION,Files={name:hashlib.sha256(payload).hexdigest() for name,payload,_ in app})
    (out/("SnoopyLinuxUpdate-"+VERSION+".tar.gz")).write_bytes(tar_bytes(app+[("UpdatePackage.json",json.dumps(manifest,indent=2).encode(),0o644)]))
    portable=app+[(f,(ROOT/f).read_bytes(),0o755 if f in ("install.sh","snoopy-linux") else 0o644) for f in ("install.py","install.sh","snoopy-linux","snoopy-linux.desktop","README.md","build_packages.py","online_install.py")]
    portable += [(f.relative_to(ROOT).as_posix(),f.read_bytes(),0o644) for f in (ROOT/"tests").glob("*.py")]
    (out/("SnoopyLinux-"+VERSION+".tar.gz")).write_bytes(tar_bytes(portable))
    dependencies="python3 (>= 3.11), python3-pyqt6 (>= 6.4), python3-pyqt6.qtmultimedia, python3-lunardate, tzdata, qt6-wayland, gstreamer1.0-libav, gstreamer1.0-plugins-good, gstreamer1.0-plugins-bad, libxss1, libglib2.0-bin, libnotify-bin"
    control=(f"Package: snoopy-linux\nVersion: {VERSION}\nSection: x11\nPriority: optional\nArchitecture: all\nMaintainer: Snoopy local build <noreply@localhost>\nDepends: {dependencies}\nDescription: Snoopy animations and contextual doghouse scenes\n Shared Python/Qt implementation for Ubuntu and Debian on amd64 and arm64.\n Preview and fullscreen playback, weather, travel time zones and display modes.\n Does not replace or disable the desktop lock screen. Media installed separately.\n").encode()
    data=[("usr/share/snoopy-linux/"+name,payload,mode) for name,payload,mode in app]
    data += [("usr/bin/snoopy-linux",(ROOT/"snoopy-linux").read_bytes(),0o755),("usr/share/applications/snoopy-linux.desktop",(ROOT/"snoopy-linux.desktop").read_bytes(),0o644),("usr/share/doc/snoopy-linux/README.md",(ROOT/"README.md").read_bytes(),0o644)]
    ar_write(out/("snoopy-linux_"+VERSION+"_all.deb"),[("debian-binary",b"2.0\n"),("control.tar.gz",tar_bytes([("control",control,0o644)])),("data.tar.gz",tar_bytes(data,directories=True))])
    for path in sorted(out.iterdir()):
        if path.suffix in (".deb",".gz"):print(path.name,path.stat().st_size)

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("output",type=Path);build(parser.parse_args().output)
