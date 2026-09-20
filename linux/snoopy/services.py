import json
import os
import re
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from .core import weather_tags

def fetch_json(url, maximum=2*1024*1024):
    with urlopen(Request(url,headers={"User-Agent":"SnoopyLinux/1.0.0"}),timeout=15) as response:
        raw = response.read(maximum+1)
    if len(raw)>maximum: raise ValueError("Response too large")
    return json.loads(raw)

def geocode(city):
    return fetch_json("https://geocoding-api.open-meteo.com/v1/search?"+urlencode(dict(name=city,count=10,language="en",format="json"))).get("results",[])

def weather(latitude,longitude):
    result = fetch_json("https://api.open-meteo.com/v1/forecast?"+urlencode(dict(latitude=latitude,longitude=longitude,current="weather_code,wind_speed_10m,is_day")))
    c = result["current"]
    return weather_tags(c["weather_code"],c["wind_speed_10m"],c["is_day"]==1)

def dbus_call(destination, path, method, *args, system=False):
    command = ["gdbus","call","--system" if system else "--session","--dest",destination,"--object-path",path,"--method",method,*map(str,args)]
    return subprocess.check_output(command,text=True,stderr=subprocess.DEVNULL,timeout=5).strip()

class Location:
    def __init__(self): self.client = None
    def get(self):
        from PyQt6.QtDBus import QDBusConnection,QDBusInterface,QDBusVariant,QDBusMessage
        dest, props = "org.freedesktop.GeoClue2", "org.freedesktop.DBus.Properties"
        bus=QDBusConnection.systemBus()
        def call(path,interface,method,*args):
            proxy=QDBusInterface(dest,path,interface,bus);proxy.setTimeout(5000)
            reply=proxy.call(method,*args)
            if reply.type()==QDBusMessage.MessageType.ErrorMessage:raise RuntimeError(reply.errorMessage())
            value=reply.arguments()[0] if reply.arguments() else None
            return value.variant() if isinstance(value,QDBusVariant) else value
        if self.client is None:
            self.client = call("/org/freedesktop/GeoClue2/Manager",dest+".Manager","GetClient").path()
            try:
                call(self.client,props,"Set",dest+".Client","DesktopId",QDBusVariant("snoopy-linux"))
                call(self.client,dest+".Client","Start")
            except Exception:
                self.client=None; raise
        path=call(self.client,props,"Get",dest+".Client","Location").path()
        if path=="/": raise RuntimeError("Waiting for desktop location permission or a location fix")
        return [float(call(path,props,"Get",dest+".Location",name)) for name in ("Latitude","Longitude")]

def idle_seconds():
    if os.environ.get("XDG_SESSION_TYPE")=="wayland":
        try:
            reply=dbus_call("org.gnome.Mutter.IdleMonitor","/org/gnome/Mutter/IdleMonitor/Core","org.gnome.Mutter.IdleMonitor.GetIdletime")
            return int(re.search(r"uint64 (\d+)",reply)[1])/1000
        except Exception: return None
    if not os.environ.get("DISPLAY"): return None
    import ctypes as c
    import ctypes.util
    class Info(c.Structure):
        _fields_=[("window",c.c_ulong),("state",c.c_int),("kind",c.c_int),("since",c.c_ulong),("idle",c.c_ulong),("mask",c.c_ulong)]
    try:
        x=c.CDLL(ctypes.util.find_library("X11")); ss=c.CDLL(ctypes.util.find_library("Xss"))
        x.XOpenDisplay.argtypes=[c.c_char_p];x.XOpenDisplay.restype=c.c_void_p
        x.XDefaultRootWindow.argtypes=[c.c_void_p];x.XDefaultRootWindow.restype=c.c_ulong
        x.XCloseDisplay.argtypes=[c.c_void_p]
        ss.XScreenSaverQueryInfo.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(Info)]
        d=x.XOpenDisplay(None)
        if not d:return None
        try:
            info=Info()
            return info.idle/1000 if ss.XScreenSaverQueryInfo(d,x.XDefaultRootWindow(d),c.byref(info)) else None
        finally:x.XCloseDisplay(d)
    except (OSError,TypeError):return None

def locked():
    for dest,path in (("org.gnome.ScreenSaver","/org/gnome/ScreenSaver"),("org.freedesktop.ScreenSaver","/ScreenSaver")):
        try:
            if "true" in dbus_call(dest,path,dest+".GetActive").lower():return True
        except Exception:pass
    return False
