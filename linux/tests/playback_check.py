"""Exercise the real decoder and its end-of-media transition with a supplied media folder."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from snoopy.core import Library,DEFAULTS
from snoopy.player import Engine

app=QApplication([]);app.setQuitOnLastWindowClosed(False)
lib=Library(sys.argv[1])
engine=Engine(dict(DEFAULTS,Weather=False,AutoLocation=False,DoghouseDelayMinutes=0,DoghouseMinutes=1,RotationMinutes=1),lib,True,True,"cloudy")
errors=[];events=[];states=[]
engine.failed.connect(errors.append);engine.done.connect(app.quit)
engine.media.mediaStatusChanged.connect(lambda status:states.append([status.name,engine.media.position()]))
engine.start();house=engine.selection["house"];step=0;started=time.monotonic()
timer=QTimer();timer.setInterval(100)
def tick():
    global step
    try:
        if step==0 and engine.frames>10:
            assert engine.selection["house"] is house
            engine.schedule.section-=61;engine.tick();assert engine.mode=="movie"
            events.append("doghouse -> regular movie");step=1
        elif step==1 and engine.video_frames>10 and engine.media.duration()>2000:
            engine.media.setPosition(engine.media.duration()-1200)
            events.append("regular movie decoded before seek to final second");step=2
        elif step==2 and engine.mode=="idle":
            events.append("natural movie end -> next doghouse");timer.stop();engine.stop()
        if time.monotonic()-started>25:raise RuntimeError("Transition test timed out; position="+str(engine.media.position()))
    except Exception as error:errors.append(str(error));timer.stop();engine.stop()
timer.timeout.connect(tick);timer.start();app.exec()
result=dict(events=events,errors=errors,states=states)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2));print(json.dumps(result))
raise SystemExit(0 if len(events)==3 and not errors else 1)
