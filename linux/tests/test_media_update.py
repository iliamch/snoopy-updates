import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from snoopy import media_update as media

class MediaUpdateTests(unittest.TestCase):
    def package(self,root,extra=None):
        files={'catalog.json':b'{}','interactions.json':b'{"Assets":[]}','halftone.png':b'image'}
        files.update(extra or {})
        manifest=json.dumps({'Version':'2','Files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}).encode()
        archive=root/'pack.zip'
        with zipfile.ZipFile(archive,'w') as z:
            z.writestr('package-manifest.json',manifest)
            for n,b in files.items():z.writestr(n,b)
        return archive,hashlib.sha256(manifest).hexdigest()
    def test_verified_media_and_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive,manifest=self.package(root);stage=root/'IdleAssets';stage.mkdir()
            with patch.object(media,'SHA',media.digest(archive)),patch.object(media,'MANIFEST_SHA',manifest):
                media.extract(archive,stage);self.assertTrue(media.complete(root))
                self.assertEqual((stage/'halftone.png').read_bytes(),b'image')
    def test_corrupt_pack_keeps_old_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive,_=self.package(root);sentinel=root/'sentinel';sentinel.write_text('old')
            with self.assertRaises(ValueError):media.extract(archive,root)
            self.assertEqual(sentinel.read_text(),'old')
    def test_traversal_rejected_even_in_pinned_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive,manifest=self.package(root,{'../escape.png':b'bad'})
            with patch.object(media,'SHA',media.digest(archive)),patch.object(media,'MANIFEST_SHA',manifest):
                with self.assertRaises(ValueError):media.extract(archive,root/'stage')
            self.assertFalse((root/'escape.png').exists())
    def test_unsafe_extensions_rejected(self):
        for name in ('../a.png','x.exe','/a.png','a\\b.png','a/../b.png','C:/a.png'):
            self.assertFalse(media.safe(name))
