#!/usr/bin/env python3
"""Install without replacing system files or changing the desktop lock screen."""
import os
import shutil
import sys
from pathlib import Path
from snoopy import VERSION
from snoopy.core import data_root,load_settings,save_settings

def main():
    if not sys.platform.startswith("linux"):raise SystemExit("Run this installer on Ubuntu or Debian Linux.")
    try:
        from PyQt6.QtMultimedia import QMediaPlayer
        import lunardate
    except ImportError:
        raise SystemExit("Install the native dependencies first:\nsudo apt install python3-pyqt6 python3-pyqt6.qtmultimedia python3-lunardate qt6-wayland gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad libxss1 libglib2.0-bin libnotify-bin")
    if os.geteuid()==0:raise SystemExit("Run install.sh as your normal desktop user, without sudo.")
    source=Path(__file__).resolve().parent;root=data_root();versions=root/"versions";versions.mkdir(parents=True,exist_ok=True)
    target=versions/(VERSION+"-"+os.urandom(4).hex())
    target.mkdir();shutil.copytree(source/"snoopy",target/"snoopy",ignore=shutil.ignore_patterns("__pycache__"));shutil.copy2(source/"main.py",target/"main.py")
    link=root/"current.new"
    if link.is_symlink():link.unlink()
    link.symlink_to(target,target_is_directory=True);os.replace(link,root/"current")
    bin_dir=Path.home()/".local/bin";bin_dir.mkdir(parents=True,exist_ok=True)
    launcher=bin_dir/"snoopy-linux";shutil.copy2(source/"snoopy-linux",launcher);launcher.chmod(0o755)
    applications=Path(os.environ.get("XDG_DATA_HOME",Path.home()/".local/share"))/"applications";applications.mkdir(parents=True,exist_ok=True)
    desktop=(source/"snoopy-linux.desktop").read_text()
    escaped=str(launcher).replace("\\","\\\\").replace('"','\\"').replace('`','\\`').replace('$','\\$')
    (applications/"snoopy-linux.desktop").write_text(desktop.replace("Exec=snoopy-linux","Exec=\""+escaped+'"'))
    settings=load_settings()
    media=source/"Media"
    if (media/"scenes.json").exists():settings["MediaPath"]=str(media);save_settings(settings)
    print("Installed Snoopy "+VERSION+" for this account. Open Snoopy from the applications menu.")
    print("In Settings, choose your extracted Media folder. Keep that folder on this computer.")

if __name__=="__main__":main()
