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
import build_packages
import tarfile

class ReleaseDetectionTests(unittest.TestCase):
    def test_supported_releases(self):
        cases=[{"ID":"ubuntu","VERSION_ID":version} for version in ("24.04","24.10","26.04")]
        cases += [{"ID":"debian","VERSION_ID":version} for version in ("12","12.1","13")]
        cases += [dict(ID="linuxmint",VERSION_ID=version,ID_LIKE="ubuntu debian",VERSION_CODENAME=codename,UBUNTU_CODENAME="noble")
                  for version,codename in (("22","wilma"),("22.1","xia"),("22.2","zara"),("22.3","zena"))]
        cases.append(dict(ID="linuxmint",VERSION_ID="22.3",ID_LIKE="debian\tubuntu",UBUNTU_CODENAME="noble"))
        for release in cases:
            with self.subTest(release=release):self.assertTrue(installer.supported_release(release))

    def test_unsupported_releases(self):
        cases=[{"ID":"ubuntu","VERSION_ID":version} for version in ("22.04","24.03","24")]
        cases += [{"ID":"debian","VERSION_ID":"11"}, {"ID":"fedora","VERSION_ID":"42","ID_LIKE":"ubuntu debian"}]
        mint=dict(ID="linuxmint",VERSION_ID="22.3",ID_LIKE="ubuntu debian",UBUNTU_CODENAME="noble")
        cases += [dict(mint,VERSION_ID=version) for version in ("21.3","23","6","7")]
        cases += [dict(mint,UBUNTU_CODENAME=base) for base in ("jammy","bookworm","","Noble",None)]
        cases += [dict(mint,ID_LIKE=ancestry) for ancestry in ("debian","ubuntuish","",None)]
        cases += [dict(mint,ID="other")]
        cases += [{key:value for key,value in mint.items() if key!=missing} for missing in ("ID","VERSION_ID","ID_LIKE","UBUNTU_CODENAME")]
        for release in cases:
            with self.subTest(release=release):self.assertFalse(installer.supported_release(release))

    def test_malformed_versions(self):
        for distro in ("ubuntu","debian","linuxmint"):
            for version in (None,24,"","noble","24.bad","bad.24.04","24..04","24.04."," 24.04","24.04\n","-24.04","24.04-beta","\u0662\u0664.\u0660\u0664"):
                release=dict(ID=distro,VERSION_ID=version,ID_LIKE="ubuntu debian",UBUNTU_CODENAME="noble")
                with self.subTest(release=release):self.assertFalse(installer.supported_release(release))

    def test_main_accepts_peters_mint_before_python_check(self):
        release=dict(ID="linuxmint",VERSION_ID="22.3",ID_LIKE="ubuntu debian",VERSION_CODENAME="zena",UBUNTU_CODENAME="noble")
        with patch.object(installer.sys,"platform","linux"), patch.object(installer.os,"geteuid",return_value=1000,create=True), patch.object(installer.platform,"machine",return_value="x86_64"), patch.object(installer.platform,"freedesktop_os_release",return_value=release), patch.object(installer.sys,"version_info",(3,10)), patch.object(installer.subprocess,"run") as run, patch.object(installer,"Path") as path:
            with self.assertRaisesRegex(SystemExit,"Python 3.11"):installer.main()
            run.assert_not_called();path.assert_not_called()

    def test_main_rejects_unsupported_before_side_effects(self):
        release=dict(ID="linuxmint",VERSION_ID="21.3",ID_LIKE="ubuntu debian",UBUNTU_CODENAME="jammy")
        with patch.object(installer.sys,"platform","linux"), patch.object(installer.os,"geteuid",return_value=1000,create=True), patch.object(installer.platform,"machine",return_value="x86_64"), patch.object(installer.platform,"freedesktop_os_release",return_value=release), patch.object(installer.subprocess,"run") as run, patch.object(installer,"Path") as path:
            with self.assertRaisesRegex(SystemExit,"requires Ubuntu"):installer.main()
            run.assert_not_called();path.assert_not_called()

    def test_built_installers_match_source(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp);build_packages.build(out)
            source=(build_packages.ROOT/"online_install.py").read_bytes()
            self.assertEqual((out/"SnoopyUbuntuInstall.py").read_bytes(),source)
            with tarfile.open(out/("SnoopyLinux-"+build_packages.VERSION+".tar.gz")) as package:
                self.assertEqual(package.extractfile("online_install.py").read(),source)

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
