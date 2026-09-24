import io
import json
import os
import tarfile
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from snoopy.core import *
from snoopy import updater

class PolicyTests(unittest.TestCase):
    def test_holidays(self):
        for date,tag in ((datetime(2026,10,31),"halloween"),(datetime(2026,12,25),"christmas"),(datetime(2026,12,31),"newYearsEve"),(datetime(2027,1,1),"newYearsDay"),(datetime(2026,2,17),"lunarNewYear"),(datetime(2026,11,26),"thanksgiving")):
            self.assertIn("calendar:"+tag,calendar_tags(date))
    def test_southern_seasons(self):self.assertIn("calendar:startOfWinter",calendar_tags(datetime(2026,6,21),True))
    def test_commute_boundary(self):
        self.assertIn("routine:goingToWork",calendar_tags(datetime(2026,7,1,10,29)))
        self.assertNotIn("routine:goingToWork",calendar_tags(datetime(2026,7,1,10,30)))
    def test_weather(self):
        self.assertTrue({"weather:rainy","weather:icy","weather:windy"}<=weather_tags(67,30,False))
        self.assertNotIn("weather:sunny",weather_tags(0,0,False))
        self.assertEqual(weather_tags(3,0,True),{"weather:cloudy"})
    def test_grouped_rules(self):
        rules=["weather:sunny","weather:clear","timeOfDay:morning"]
        self.assertFalse(matches(rules,{"weather:sunny"},True))
        self.assertTrue(matches(rules,{"weather:clear","timeOfDay:morning"},True))
    def test_cloud_frames(self):
        layer=dict(Files=[str(i) for i in range(1007)],Fps=24,Loop=False)
        self.assertEqual(layer_frame(dict(Id="103_WE007"),layer,0),("72",0))
        self.assertEqual(layer_frame(dict(Id="103_WE007"),layer,1),("96",1))
        self.assertEqual(layer_frame(dict(Id="103_WE007"),layer,60),("1006",1))
        self.assertEqual(layer_frame(dict(Id="101_WE002"),layer,0),("0",1))
    def test_rotation_only_at_boundaries(self):
        clock=[0];s=Schedule(dict(DEFAULTS,DoghouseDelayMinutes=0,RotationMinutes=1),lambda:clock[0])
        self.assertEqual(s.boundary(2),"idle")
        clock[0]=65;self.assertEqual(s.active,0)
        self.assertEqual(s.boundary(2),"movie");self.assertEqual(s.active,1)
        clock[0]=75;self.assertEqual(s.boundary(2),"idle");self.assertEqual(s.active,1)
        clock[0]=130;self.assertEqual(s.boundary(2),"movie");self.assertEqual(s.active,0)
    def test_delay_disabled(self):
        s=Schedule(dict(DEFAULTS,DoghouseDelayMinutes=-1),lambda:999999)
        self.assertEqual(s.boundary(2),"movie")
    def test_paths(self):
        root=Path.cwd()
        self.assertEqual(media_file(root,"Videos/a.mp4"),root/"Videos/a.mp4")
        with self.assertRaises(ValueError):media_file(root,"../outside")

class UpdateTests(unittest.TestCase):
    def offer(self):return dict(draft=False,prerelease=False,assets=[dict(name="SnoopyLinuxUpdate-1.1.2.tar.gz",state="uploaded",size=100,digest="sha256:"+"a"*64,url=updater.API+"/releases/assets/1")])
    def test_select(self):
        self.assertEqual(updater.select([self.offer()])["version"],"1.1.2")
        self.assertIsNone(updater.select([self.offer()],"1.1.2"))
        self.assertIsNone(updater.select([dict(self.offer(),prerelease=True)]))
    def test_wrong_platform(self):
        release=self.offer();release["assets"][0]["name"]="SnoopyUpdate-99.0.0.zip"
        self.assertIsNone(updater.select([release]))
    def test_untrusted_asset(self):
        release=self.offer();release["assets"][0]["url"]="https://example.org/file"
        with self.assertRaises(ValueError):updater.select([release])
    def archive(self,path,entries):
        with tarfile.open(path,"w:gz") as package:
            for name,data in entries.items():
                info=tarfile.TarInfo(name);info.size=len(data);package.addfile(info,io.BytesIO(data))
    def test_extract_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=b'VERSION = "1.0.1"\n'
            manifest=dict(Edition="SnoopyLinux",Version="1.0.1",Files={"snoopy/__init__.py":__import__('hashlib').sha256(source).hexdigest()})
            entries={"snoopy/__init__.py":source,"UpdatePackage.json":json.dumps(manifest).encode()}
            self.archive(root/"good.tar.gz",entries);updater.extract(root/"good.tar.gz",root/"ready","1.0.1")
            self.assertEqual((root/"ready/snoopy/__init__.py").read_bytes(),source)
            entries["../escape"]=b"bad";self.archive(root/"bad.tar.gz",entries)
            with self.assertRaises(ValueError):updater.extract(root/"bad.tar.gz",root/"other","1.0.1")
            self.assertFalse((root/"escape").exists())
    def test_tampered_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            entries={"snoopy/__init__.py":b'VERSION="9.0.0"',"UpdatePackage.json":json.dumps(dict(Edition="SnoopyLinux",Version="1.0.1",Files={"snoopy/__init__.py":"0"*64})).encode()}
            self.archive(root/"bad.tar.gz",entries)
            with self.assertRaises(ValueError):updater.extract(root/"bad.tar.gz",root/"ready","1.0.1")
    def test_wrong_edition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.archive(root/"bad.tar.gz",{"UpdatePackage.json":json.dumps(dict(Edition="Windows",Version="1.0.1",Files={})).encode()})
            with self.assertRaises(ValueError):updater.extract(root/"bad.tar.gz",root/"ready","1.0.1")

if __name__=="__main__":unittest.main()
