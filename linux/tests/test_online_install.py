import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import online_install as installer

class InstallerTests(unittest.TestCase):
    def test_settings_preserved(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"XDG_CONFIG_HOME":temp}):
            folder=Path(temp)/"snoopy";folder.mkdir();(folder/"settings.json").write_text(json.dumps(dict(ShowClock=False,RotationMinutes=90)))
            installer.configure(Path(temp)/"media")
            saved=json.loads((folder/"settings.json").read_text())
            self.assertFalse(saved["ShowClock"]);self.assertEqual(saved["RotationMinutes"],90)
            self.assertEqual(saved["MediaPath"],str(Path(temp)/"media"))
    def test_invalid_existing_settings_preserved(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"XDG_CONFIG_HOME":temp}):
            folder=Path(temp)/"snoopy";folder.mkdir();(folder/"settings.json").write_text("invalid")
            with self.assertRaises(ValueError):installer.configure(Path(temp)/"media")
            self.assertEqual((folder/"settings.json").read_text(),"invalid")
    def test_media_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/"media.zip"
            files={"Media/scenes.json":b"[]","Media/IdleAssets/catalog.json":b"{}","Media/Videos/test.mp4":b"video"}
            manifest={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
            with zipfile.ZipFile(archive,"w") as package:
                for name,data in files.items():package.writestr(name,data)
                package.writestr("Media/SHA256SUMS.json",json.dumps(manifest))
            target=installer.extract_media(archive,root)
            self.assertEqual((target/"Videos/test.mp4").read_bytes(),b"video")
            self.assertEqual(installer.extract_media(archive,root),target)
    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/"media.zip"
            with zipfile.ZipFile(archive,"w") as package:package.writestr("Media/../../escaped",b"bad")
            with self.assertRaises(ValueError):installer.extract_media(archive,root)
            self.assertFalse((root.parent/"escaped").exists())

if __name__=="__main__":unittest.main()
