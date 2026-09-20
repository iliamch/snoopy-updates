"""Platform-independent scene rules, preferences and safe media access."""
import json
import os
import random
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULTS = dict(DoghouseDelayMinutes=30, DoghouseMinutes=5, RotationMinutes=30,
                ShowClock=True, City="", Latitude=None, Longitude=None,
                Weather=True, AutoLocation=False, TimeZoneId="", DisplayLayout="Repeat",
                SpanFit="Fit", Displays={}, MediaPath="", AutomaticUpdates=True,
                SkippedVersion="", AutoStart=False, IdleMinutes=5)
SEASONS = {"winter", "spring", "summer", "fall", "startOfWinter", "startOfSpring", "startOfSummer", "startOfFall"}
HOLIDAYS = {101:"newYearsDay",214:"valentinesDay",422:"earthDay",704:"fourthOfJuly",
            720:"peanutsMoonlanding",810:"peanutsSnoopysBirthday",819:"aviationDay",
            1002:"peanutsFirstComicStrip",1004:"peanutsSnoopyDebut",1031:"halloween",
            1216:"peanutsBeethovensBirthday",1224:"christmasEve",1225:"christmas",1231:"newYearsEve"}

def config_root():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home()/".config"))/"snoopy"

def data_root():
    return Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local/share"))/"SnoopyLinux"

def load_settings():
    result = DEFAULTS.copy()
    try:
        result.update(json.loads((config_root()/"settings.json").read_text()))
    except (OSError, ValueError):
        pass
    result["Displays"] = dict(result.get("Displays") or {})
    for key, default in (("RotationMinutes",30),("DoghouseMinutes",5),("IdleMinutes",5)):
        try: result[key] = max(1, min(90, int(result[key])))
        except (ValueError, TypeError): result[key] = default
    return result

def save_settings(settings):
    root = config_root(); root.mkdir(parents=True, exist_ok=True)
    temp = root/"settings.json.new"
    temp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temp.replace(root/"settings.json")

def now(settings):
    zone = settings.get("TimeZoneId")
    try: return datetime.now(ZoneInfo(zone)) if zone else datetime.now().astimezone()
    except (ValueError, KeyError): return datetime.now().astimezone()

def calendar_tags(d, south=False):
    h, md = d.hour, d.month*100+d.day
    season = "winter" if md>=1221 or md<320 else "spring" if md<621 else "summer" if md<922 else "fall"
    if south: season = dict(winter="summer",summer="winter",spring="fall",fall="spring")[season]
    tags = {"calendar:"+season}
    if md in (320,621,922,1221): tags.add("calendar:startOf"+season.title())
    routine = ("lateNight" if h<5 or h>=23 else "morning" if h<10 else "brunch" if h<12
               else "lunch" if h<14 else "afternoon" if h<18 else "dinner" if h<21 else "bedtime")
    tags.add("routine:"+routine)
    if 420<=h*60+d.minute<630: tags.update(("routine:goingToSchool","routine:goingToWork"))
    tags.add("timeOfDay:"+("morning" if 6<=h<12 else "afternoon" if 12<=h<18 else "evening" if 18<=h<23 else "lateNight"))
    if md in HOLIDAYS: tags.add("calendar:"+HOLIDAYS[md])
    if d.month==10: tags.add("calendar:halloweenSeason")
    if d.month==11 and d.day>=15: tags.add("calendar:thanksgivingSeason")
    if d.month==12 or d.month==1 and d.day<=6: tags.add("calendar:christmasSeason")
    if d.month==5 and d.weekday()==6 and 8<=d.day<=14: tags.add("calendar:mothersDay")
    if d.month==6 and d.weekday()==6 and 15<=d.day<=21: tags.add("calendar:fathersDay")
    if d.month==11 and d.weekday()==3 and 22<=d.day<=28: tags.add("calendar:thanksgiving")
    from lunardate import LunarDate
    try:
        lunar = LunarDate.fromSolarDate(d.year,d.month,d.day)
        if lunar.month==1 and lunar.day==1 and not lunar.isLeapMonth: tags.add("calendar:lunarNewYear")
    except ValueError: pass
    return tags

def weather_tags(code, wind, day):
    tags = set()
    if code in (0,1):
        tags.add("weather:clear")
        if day: tags.add("weather:sunny")
    if code in (2,3): tags.add("weather:cloudy")
    if code in (45,48): tags.add("weather:foggy")
    if 51<=code<=57 or 61<=code<=67 or 80<=code<=82: tags.add("weather:rainy")
    if code in (56,57,66,67): tags.add("weather:icy")
    if 71<=code<=77 or code in (85,86): tags.add("weather:snowy")
    if 95<=code<=99: tags.add("weather:stormy")
    if wind>=29: tags.add("weather:windy")
    return tags

def matches(rules, tags, grouped=False):
    if not rules: return True
    if not grouped: return bool(set(rules)&tags)
    groups = defaultdict(set)
    for rule in rules: groups[rule.split(":",1)[0]].add(rule)
    return all(values&tags for values in groups.values())

def house_allowed(asset, tags):
    holidays = [r for r in asset["Rules"] if r.startswith("calendar:") and r[9:] not in SEASONS]
    return (not holidays or bool(set(holidays)&tags)) and matches(asset["Rules"],tags)

def palette_allowed(palette, house, tags):
    return (palette["Id"] not in house["ExcludedPalettes"]
            and (not palette["Parents"] or house["Id"] in palette["Parents"])
            and matches(palette["Rules"],tags,True)
            and ("NewYearsEve" not in palette["Id"] or "calendar:newYearsEve" in tags)
            and ("NewYearsDay" not in palette["Id"] or "calendar:newYearsDay" in tags))

def media_file(root, relative):
    relative = str(relative).replace("\\", "/")
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()): raise ValueError("Media path leaves selected folder")
    return path

def layer_frame(asset, layer, seconds):
    first = min(72,len(layer["Files"])-1) if asset["Id"]=="103_WE007" else 0
    frame = first + int(max(0,seconds)*layer["Fps"])
    frame = frame % len(layer["Files"]) if layer["Loop"] else min(frame,len(layer["Files"])-1)
    return layer["Files"][frame], min(1,max(0,seconds/.5)) if first else 1

class Library:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.scenes = json.loads((self.root/"scenes.json").read_text(encoding="utf-8-sig"))
        self.catalog = json.loads((self.root/"IdleAssets/catalog.json").read_text(encoding="utf-8-sig"))
        for key in ("Houses","Poses","Effects","Palettes"):
            if not self.catalog.get(key): raise ValueError("Incomplete idle catalog: "+key)
        for scene in self.scenes:
            if not media_file(self.root,scene["File"]).is_file(): raise ValueError("Missing movie: "+scene["File"])

    def idle(self, tags, previous=None, forced_weather=None):
        tags = set(tags)
        if forced_weather:
            tags = {t for t in tags if not t.startswith("weather:")}|{"weather:"+forced_weather}
        pool = [a for a in self.catalog["Houses"] if house_allowed(a,tags)]
        pool = [a for a in pool if a["Id"]!=previous] or pool
        house = random.choices(pool,weights=[5 if a["Rules"] else 1 for a in pool])[0]
        poses = self.catalog["Poses"]
        palettes = [p for p in self.catalog["Palettes"] if palette_allowed(p,house,tags)]
        palettes = [p for p in palettes if p["Parents"]] or palettes
        effects = [a for a in self.catalog["Effects"] if matches(a["Rules"],tags,True)
                   and any(r.startswith("weather:") and r in tags for r in a["Rules"])
                   and not set(a["Rules"])&set(house["ExcludedWeather"])]
        return dict(house=house,pose=random.choice(poses),palette=random.choice(palettes) if palettes else None,
                    effect=random.choice(effects) if effects else None)

    def movie(self,tags,previous=None,failed=None):
        pool = [s for s in self.scenes if not s["Id"].startswith("Doghouse_")
                and matches(s["Rules"],tags) and s["Id"] not in (failed or set())]
        pool = [s for s in pool if s["Id"]!=previous] or pool
        if not pool: raise ValueError("No playable regular animations")
        return random.choice(pool)

class Schedule:
    def __init__(self, settings, clock=time.monotonic):
        self.settings, self.clock = settings, clock
        self.started = self.rotated = self.section = clock()
        self.was_idle = False
        self.active = 0

    def boundary(self, count, preview_idle=False):
        t = self.clock()
        if t-self.rotated>=self.settings["RotationMinutes"]*60 and count>1:
            self.active = (self.active+1)%count; self.rotated = t
        delay = self.settings["DoghouseDelayMinutes"]
        idle = not self.was_idle and (preview_idle or delay>=0 and t-self.started>=delay*60)
        self.was_idle, self.section = idle, t
        return "idle" if idle else "movie"
