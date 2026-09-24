import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import available_timezones
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,
    QLabel,QLineEdit,QComboBox,QSpinBox,QCheckBox,QPushButton,QFileDialog,QMessageBox,QScrollArea,
    QTableWidget,QHeaderView,QAbstractItemView)
from . import VERSION
from .core import load_settings,save_settings,Library,data_root,config_root
from .player import Engine,Job
from .services import geocode,idle_seconds,locked
from . import updater, media_update

def autostart(enabled):
    folder=Path(os.environ.get("XDG_CONFIG_HOME",Path.home()/".config"))/"autostart"
    file=folder/"snoopy-linux.desktop"
    if enabled:
        folder.mkdir(parents=True,exist_ok=True)
        launcher=Path.home()/".local/bin/snoopy-linux"
        executable=str(launcher) if launcher.exists() else "/usr/bin/snoopy-linux"
        escaped=executable.replace("\\","\\\\").replace('"','\\"').replace('`','\\`').replace('$','\\$')
        file.write_text('[Desktop Entry]\nType=Application\nName=Snoopy automatic playback\nExec="'+escaped+'" --watch\nX-GNOME-Autostart-enabled=true\n')
    elif file.exists():file.unlink()

class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__();self.settings=load_settings();self.jobs=[];self.engines=[];self.offer=None;self.media_preparing=False
        self.setWindowTitle("Snoopy for Linux "+VERSION);self.resize(850,800)
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.setCentralWidget(scroll)
        body=QWidget();scroll.setWidget(body);layout=QVBoxLayout(body);form=QFormLayout();layout.addLayout(form)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.media=QLineEdit(self.settings["MediaPath"]);browse=QPushButton("Choose media folder…")
        browse.clicked.connect(self.choose_media);row=QHBoxLayout();row.addWidget(self.media);row.addWidget(browse);form.addRow("Animations",row)
        note=QLabel("Select the folder containing Videos, IdleAssets and scenes.json. The included Linux media bundle uses the same animations as Windows.");note.setWordWrap(True);form.addRow(note)
        self.zone=QComboBox();self.zone.addItem("Follow this computer","")
        for zone in sorted(available_timezones()):self.zone.addItem(zone,zone)
        self.zone.setCurrentIndex(max(0,self.zone.findData(self.settings["TimeZoneId"])));form.addRow("Time zone",self.zone)
        self.clock=QCheckBox("Show date and time");self.clock.setChecked(self.settings["ShowClock"]);form.addRow(self.clock)
        self.weather=QCheckBox("Use local weather for scene selection");self.weather.setChecked(self.settings["Weather"]);form.addRow(self.weather)
        self.location=QCheckBox("Use desktop location when available (GeoClue)");self.location.setChecked(self.settings["AutoLocation"]);form.addRow(self.location)
        self.city=QLineEdit(self.settings["City"]);find=QPushButton("Find city");find.clicked.connect(self.find_city)
        row=QHBoxLayout();row.addWidget(self.city);row.addWidget(find);form.addRow("Weather location",row)
        self.cities=QComboBox();self.cities.currentIndexChanged.connect(self.city_selected);form.addRow("Search results",self.cities)
        self.coords=QLabel(self.coordinate_text());form.addRow(self.coords)
        self.layout_choice=QComboBox()
        for title,key in (("Repeat on selected screens","Repeat"),("Span one scene across screens","Span"),("Rotate — inactive screens black","Rotate")):self.layout_choice.addItem(title,key)
        self.layout_choice.setCurrentIndex(max(0,self.layout_choice.findData(self.settings["DisplayLayout"])));form.addRow("Multiple screens",self.layout_choice)
        self.fit=QComboBox();self.fit.addItems(["Fit","Fill"]);self.fit.setCurrentText(self.settings["SpanFit"]);form.addRow("Picture fit",self.fit)
        self.rotation=self.minutes(self.settings["RotationMinutes"]);form.addRow("Rotate after minutes (at scene end)",self.rotation)
        self.delay=QComboBox()
        for delay in (-1,0,30,40):self.delay.addItem("Off" if delay<0 else "From the start" if delay==0 else "After %d minutes"%delay,delay)
        self.delay.setCurrentIndex(max(0,self.delay.findData(self.settings["DoghouseDelayMinutes"])));form.addRow("Doghouse scenes",self.delay)
        self.duration=self.minutes(self.settings["DoghouseMinutes"]);form.addRow("Doghouse duration in minutes",self.duration)
        self.displays=QTableWidget(len(QApplication.screens()),4);self.displays.setHorizontalHeaderLabels(["Screen","Enabled","Width (0 = auto)","Height (0 = auto)"])
        self.displays.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.displays.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.displays.setMinimumHeight(140);self.display_rows=[]
        for i,screen in enumerate(QApplication.screens()):
            config=self.settings["Displays"].get(screen.name(),{})
            self.displays.setCellWidget(i,0,QLabel(screen.name()+" (%d × %d)"%(screen.geometry().width(),screen.geometry().height())))
            enabled=QCheckBox();enabled.setChecked(config.get("Enabled",True));self.displays.setCellWidget(i,1,enabled)
            dimensions=[]
            for column,key in ((2,"Width"),(3,"Height")):
                value=QSpinBox();value.setRange(0,16384);value.setValue(config.get(key,0));self.displays.setCellWidget(i,column,value);dimensions.append(value)
            self.display_rows.append((screen.name(),enabled,*dimensions))
        form.addRow(self.displays)
        note=QLabel("Manual resolution changes Snoopy's picture in Repeat mode. Windows/Linux monitor resolution stays unchanged. Rotate always waits for the whole video or doghouse section to finish.");note.setWordWrap(True);form.addRow(note)
        self.auto=QCheckBox("Start automatically when this desktop is idle");self.auto.setChecked(self.settings["AutoStart"]);form.addRow(self.auto)
        self.idle=self.minutes(self.settings["IdleMinutes"]);form.addRow("Idle minutes before starting",self.idle)
        self.updates=QCheckBox("Check GitHub for updates daily");self.updates.setChecked(self.settings["AutomaticUpdates"]);form.addRow(self.updates)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        for title,action in (("Save settings",self.save),("Preview",lambda:self.play(True)),("Preview clouds",lambda:self.play(True,True,"cloudy")),("Start fullscreen",lambda:self.play(False))):
            button=QPushButton(title);button.clicked.connect(action);buttons.addWidget(button)
        row=QHBoxLayout();layout.addLayout(row)
        self.check_button=QPushButton("Check for an update");self.check_button.clicked.connect(lambda:self.check_update(False));row.addWidget(self.check_button)
        self.update_button=QPushButton("Update now");self.update_button.setEnabled(False);self.update_button.clicked.connect(self.install_update);row.addWidget(self.update_button)
        self.keep_button=QPushButton("Keep old");self.keep_button.setEnabled(False);self.keep_button.clicked.connect(self.keep_old);row.addWidget(self.keep_button)
        self.status=QLabel("Ready. Automatic launch depends on your desktop's idle interface. Your existing screen lock remains in control.");self.status.setWordWrap(True);layout.addWidget(self.status)
        if self.settings["AutomaticUpdates"] and time.time()-self.settings.get("LastUpdateCheck",0)>86400:QTimer.singleShot(800,lambda:self.check_update(True))

        QTimer.singleShot(1000,self.prepare_media)

    @staticmethod
    def minutes(value):
        box=QSpinBox();box.setRange(1,90);box.setSingleStep(1);box.setValue(value);return box

    def coordinate_text(self):return "Selected: "+self.settings["City"]+"  "+str(self.settings["Latitude"])+", "+str(self.settings["Longitude"])
    def choose_media(self):
        folder=QFileDialog.getExistingDirectory(self,"Select Snoopy media folder",self.media.text())
        if folder:self.media.setText(folder)
    def task(self,call,done):
        job=Job(call,self);self.jobs.append(job);job.result.connect(done);job.start()
    def find_city(self):
        city=self.city.text().strip()
        if not city:return
        self.status.setText("Searching for "+city+"…")
        def done(result):
            if not result[0]:self.status.setText(result[1]);return
            self.cities.clear()
            for item in result[1]:self.cities.addItem(", ".join(str(item[k]) for k in ("name","admin1","country") if item.get(k)),item)
            self.status.setText("Select your city." if result[1] else "No matching city found.")
        self.task(lambda:geocode(city),done)
    def city_selected(self,index):
        item=self.cities.itemData(index)
        if item:
            self.settings.update(City=self.cities.itemText(index),Latitude=item["latitude"],Longitude=item["longitude"])
            self.city.setText(self.settings["City"]);self.coords.setText(self.coordinate_text())
    def collect(self):
        displays={name:dict(Enabled=enabled.isChecked(),Width=width.value(),Height=height.value()) for name,enabled,width,height in self.display_rows}
        if not any(d["Enabled"] for d in displays.values()):raise ValueError("Select at least one display")
        for d in displays.values():
            if bool(d["Width"])!=bool(d["Height"]):raise ValueError("Enter both width and height, or set both to 0 for Auto")
        self.settings.update(MediaPath=self.media.text().strip(),TimeZoneId=self.zone.currentData(),ShowClock=self.clock.isChecked(),
            Weather=self.weather.isChecked(),AutoLocation=self.location.isChecked(),DisplayLayout=self.layout_choice.currentData(),
            SpanFit=self.fit.currentText(),RotationMinutes=self.rotation.value(),DoghouseDelayMinutes=self.delay.currentData(),
            DoghouseMinutes=self.duration.value(),Displays=displays,AutoStart=self.auto.isChecked(),IdleMinutes=self.idle.value(),AutomaticUpdates=self.updates.isChecked())
    def save(self):
        try:
            self.collect();save_settings(self.settings)
            if sys.platform.startswith("linux"):autostart(self.settings["AutoStart"])
            self.status.setText("Settings saved. Automatic playback changes take effect at next login.")
            return True
        except Exception as error:self.status.setText(str(error));return False
    def play(self,preview,doghouse=False,forced=None):
        if self.media_preparing:
            self.status.setText("Please wait for the new animations to finish installing.");return
        if not self.save():return
        try:
            library=Library(self.settings["MediaPath"])
            engine=Engine(dict(self.settings),library,preview,doghouse,forced,self)
            engine.failed.connect(lambda message:self.status.setText(message));self.engines.append(engine);engine.start()
        except Exception as error:self.status.setText(str(error))
    def check_update(self,automatic):
        self.check_button.setEnabled(False);self.status.setText("Checking GitHub…")
        def done(result):
            self.check_button.setEnabled(True)
            if not result[0]:self.status.setText("Update check unavailable: "+result[1]);return
            self.settings["LastUpdateCheck"]=time.time();save_settings(self.settings)
            self.offer=result[1]
            if automatic and self.offer and self.offer["version"]==self.settings["SkippedVersion"]:self.offer=None
            self.update_button.setEnabled(bool(self.offer));self.keep_button.setEnabled(bool(self.offer))
            self.status.setText("Version "+self.offer["version"]+" is available." if self.offer else "No newer Linux release is available. Installed: "+VERSION)
        self.task(updater.check,done)
    def keep_old(self):
        if self.offer:
            self.settings["SkippedVersion"]=self.offer["version"];save_settings(self.settings)
            self.update_button.setEnabled(False);self.keep_button.setEnabled(False);self.status.setText("Keeping the current version. You can check manually later.")
    def prepare_media(self):
        if not self.settings["MediaPath"] or media_update.complete(self.settings["MediaPath"]):return
        self.media_preparing=True
        self.check_button.setEnabled(False);self.update_button.setEnabled(False)
        self.status.setText("Downloading and verifying the new doghouse scenes. Your existing library is kept until this finishes…")
        def done(result):
            self.media_preparing=False;self.check_button.setEnabled(True)
            self.status.setText("New doghouse scenes are ready." if result[0] else "New scenes could not finish downloading. Reopen Settings to retry. "+result[1])
        self.task(lambda:media_update.ensure(self.settings["MediaPath"]),done)

    def install_update(self):
        if not self.offer:return
        self.update_button.setEnabled(False);self.keep_button.setEnabled(False);self.check_button.setEnabled(False)
        self.status.setText("Downloading and verifying the update…")
        def done(result):
            self.check_button.setEnabled(True)
            self.status.setText("Update installed. Close and reopen Snoopy to use it; your settings and media are kept." if result[0] else "Update failed; current version kept. "+result[1])
        self.task(lambda:updater.install(self.offer),done)
    def closeEvent(self,event):
        if any(job.isRunning() for job in self.jobs):
            self.status.setText("Please wait for the current operation to finish before closing.");event.ignore();return
        for engine in self.engines:engine.stop()
        if any(job.isRunning() for engine in self.engines for job in engine.jobs):event.ignore();return
        event.accept()

def watch():
    # One watcher per account. Never replace the system locker or disable its timeout.
    import fcntl
    root=config_root();root.mkdir(parents=True,exist_ok=True)
    lock=open(root/"watch.lock","w")
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:return
    child=None;armed=True;last_check=0
    while True:
        settings=load_settings()
        if not settings["AutoStart"]:return
        idle=idle_seconds()
        if idle is None:
            (root/"automatic-playback.txt").write_text("Desktop idle monitoring is unavailable. Use Start fullscreen, or an X11 desktop session for automatic playback.")
            time.sleep(30);continue
        if idle<2:armed=True
        if child and child.poll() is None:
            if locked():child.terminate()
        elif armed and idle>=settings["IdleMinutes"]*60 and not locked():
            entry=data_root()/"current/main.py"
            if not entry.is_file():entry=Path(__file__).resolve().parents[1]/"main.py"
            child=subprocess.Popen([sys.executable,str(entry),"--play"]);armed=False
        if settings["AutomaticUpdates"] and time.time()-settings.get("LastUpdateCheck",0)>86400 and time.time()-last_check>3600:
            last_check=time.time()
            try:
                offer=updater.check();settings["LastUpdateCheck"]=time.time();save_settings(settings)
                if offer and offer["version"]!=settings["SkippedVersion"]:
                    subprocess.run(["notify-send","Snoopy update available","Version "+offer["version"]+" is ready. Open Snoopy to choose Update now or Keep old."],timeout=5,check=False)
            except Exception:pass
        time.sleep(2)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--play",action="store_true");parser.add_argument("--preview",action="store_true")
    parser.add_argument("--doghouse",action="store_true");parser.add_argument("--weather",choices=["cloudy","rainy","windy","snowy"])
    parser.add_argument("--media");parser.add_argument("--watch",action="store_true");parser.add_argument("--smoke",type=int,default=0)
    parser.add_argument("--report");args=parser.parse_args()
    if args.watch:watch();return 0
    app=QApplication(sys.argv);app.setApplicationName("SnoopyLinux");app.setDesktopFileName("snoopy-linux")
    if args.play or args.preview or args.smoke:
        app.setQuitOnLastWindowClosed(False)
        settings=load_settings()
        if args.media:settings["MediaPath"]=args.media
        if args.smoke:settings.update(Weather=False,AutoLocation=False,ShowClock=False,DoghouseDelayMinutes=0 if args.doghouse else -1)
        try:engine=Engine(settings,Library(settings["MediaPath"]),args.preview or bool(args.smoke),args.doghouse,args.weather)
        except Exception as error:print(error,file=sys.stderr);return 1
        errors=[];engine.failed.connect(errors.append);engine.done.connect(app.quit);engine.start()
        if args.smoke:QTimer.singleShot(args.smoke*1000,engine.stop)
        app.exec()
        result=dict(idle_frames=engine.frames,video_frames=engine.video_frames,action_frames=engine.action_frames,visitor_frames=engine.visitor_frames,errors=errors)
        if args.report:Path(args.report).write_text(json.dumps(result,indent=2))
        if args.smoke:return 0 if not errors and (engine.frames if args.doghouse else engine.video_frames)>args.smoke*5 else 1
        return int(bool(errors))
    window=SettingsWindow();window.show();return app.exec()
