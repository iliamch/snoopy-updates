import random
import time
from PyQt6.QtCore import Qt, QTimer, QRectF, QUrl, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QCursor, QFont, QImage, QPainter
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtMultimedia import QMediaPlayer, QVideoSink
from .core import Schedule, calendar_tags, now, media_file
from .render import Renderer, image_rect
from .services import weather, Location
from .interactions import Program,moon_tag

class Job(QThread):
    result=pyqtSignal(object)
    def __init__(self,call,parent=None):super().__init__(parent);self.call=call
    def run(self):
        try:self.result.emit((True,self.call()))
        except Exception as error:self.result.emit((False,str(error)))

class Screen(QWidget):
    def __init__(self,engine,screen,index,preview):
        super().__init__();self.engine,self.screen,self.index=engine,screen,index
        self.preview=preview;self.origin=QCursor.pos();self.opened=time.monotonic()
        self.setWindowTitle("Snoopy — preview" if preview else "Snoopy")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMouseTracking(True)
        if preview:self.resize(960,540);self.show()
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
            self.setCursor(Qt.CursorShape.BlankCursor)
            self.winId();self.windowHandle().setScreen(screen)
            self.setGeometry(screen.geometry());self.showFullScreen()

    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),Qt.GlobalColor.black)
        try:
            e=self.engine
            if e.image.isNull() or e.settings["DisplayLayout"]=="Rotate" and self.index!=e.schedule.active:return
            target=QRectF(self.rect());source=e.image
            layout=e.settings["DisplayLayout"]
            if layout=="Span" and not self.preview:
                g=self.screen.geometry();b=e.bounds
                target=QRectF(b.x()-g.x(),b.y()-g.y(),b.width(),b.height())
            if layout=="Repeat":
                config=e.settings["Displays"].get(self.screen.name(),{})
                width,height=config.get("Width",0),config.get("Height",0)
                if width and height:source=source.scaled(width,height,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawImage(image_rect(source.size(),target,e.settings["SpanFit"]=="Fill"),source)
            if e.settings["ShowClock"] and (layout!="Span" or self.preview or self.index==e.clock_index):
                text=now(e.settings).strftime("%H:%M\n%A, %b %d")
                p.setFont(QFont("Sans Serif",18));p.setPen(Qt.GlobalColor.white)
                box=QRectF(self.width()-340,self.height()-105,315,80)
                p.fillRect(box,QColor(0,0,0,100));p.drawText(box.adjusted(10,8,-10,-8),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,text)
        finally:p.end()

    def mouseMoveEvent(self,event):
        if not self.preview and time.monotonic()-self.opened>2 and (QCursor.pos()-self.origin).manhattanLength()>8:self.engine.stop()
    def keyPressEvent(self,event):self.engine.stop()
    def mousePressEvent(self,event):self.engine.stop()
    def closeEvent(self,event):event.accept();self.engine.stop()

class Engine(QObject):
    done=pyqtSignal()
    failed=pyqtSignal(str)
    def __init__(self,settings,library,preview=False,doghouse=False,forced_weather=None,parent=None):
        super().__init__(parent)
        self.settings,self.library,self.preview=settings,library,preview
        self.force_idle,self.forced_weather=doghouse,forced_weather
        self.schedule=Schedule(settings);self.renderer=Renderer(library)
        self.image=QImage();self.selection=None;self.mode=None;self.previous=None;self.failed_movies=set()
        self.weather_tags=set();self.weather_at=0;self.weather_coordinates=None;self.location=Location()
        self.jobs=[];self.windows=[];self.stopped=False;self.frames=0;self.video_frames=0
        self.video_start_pending=False
        self.interaction_history=set();self.action_frames=0;self.visitor_frames=0
        screens=QApplication.screens()
        self.screens=[s for s in screens if settings["Displays"].get(s.name(),{}).get("Enabled",True)] or screens[:1]
        if preview:self.screens=self.screens[:1]
        self.bounds=self.screens[0].geometry()
        for screen in self.screens[1:]:self.bounds=self.bounds.united(screen.geometry())
        self.clock_index=max(range(len(self.screens)),key=lambda i:(self.screens[i].geometry().right(),self.screens[i].geometry().bottom()))
        self.media=QMediaPlayer(self);self.sink=QVideoSink(self);self.media.setVideoSink(self.sink)
        self.sink.videoFrameChanged.connect(self.video_frame)
        self.media.mediaStatusChanged.connect(self.media_status)
        self.media.errorOccurred.connect(self.media_error)
        self.timer=QTimer(self);self.timer.setTimerType(Qt.TimerType.PreciseTimer);self.timer.setInterval(42);self.timer.timeout.connect(self.tick)
        self.weather_timer=QTimer(self);self.weather_timer.setInterval(600000);self.weather_timer.timeout.connect(self.refresh_weather)
        self.power=None;self.cookie=None

    def start(self):
        self.windows=[Screen(self,s,i,self.preview) for i,s in enumerate(self.screens)]
        if not self.preview:self.hold_power()
        self.next_scene();self.timer.start();self.refresh_weather();self.weather_timer.start()
        QApplication.instance().screenRemoved.connect(self.screen_removed)

    def screen_removed(self,screen):self.stop()

    def hold_power(self):
        # Power inhibition only: never replace, unlock or reconfigure the desktop lock screen.
        try:
            from PyQt6.QtDBus import QDBusConnection,QDBusInterface
            self.power=QDBusInterface("org.freedesktop.PowerManagement.Inhibit","/org/freedesktop/PowerManagement/Inhibit","org.freedesktop.PowerManagement.Inhibit",QDBusConnection.sessionBus())
            self.power.setTimeout(1000)
            if self.power.isValid():
                reply=self.power.call("Inhibit","Snoopy","Screensaver playback")
                if reply.arguments():self.cookie=reply.arguments()[0]
        except (ImportError,RuntimeError):pass

    def tags(self):
        tags=calendar_tags(now(self.settings),(self.settings.get("Latitude") or 0)<0)
        tags.add(moon_tag())
        if self.settings["Weather"] and time.monotonic()-self.weather_at<5400 and self.weather_coordinates==(self.settings.get("Latitude"),self.settings.get("Longitude")):tags|=self.weather_tags
        return tags

    def refresh_weather(self):
        if not self.settings["Weather"] or any(j.isRunning() for j in self.jobs):return
        settings=dict(self.settings)
        def work():
            coordinates=self.location.get() if settings["AutoLocation"] else (settings["Latitude"],settings["Longitude"])
            if None in coordinates:return None
            return coordinates,weather(*coordinates)
        job=Job(work,self);self.jobs.append(job)
        def result(value):
            if value[0] and value[1]:
                coordinates,tags=value[1];self.settings["Latitude"],self.settings["Longitude"]=coordinates
                self.weather_coordinates=tuple(coordinates);self.weather_tags=tags;self.weather_at=time.monotonic()
        job.result.connect(result);job.start()

    def next_scene(self):
        if self.stopped:return
        try:
            self.mode=self.schedule.boundary(len(self.screens),self.force_idle)
            if self.mode=="idle":
                self.media.stop()
                self.selection=self.library.idle(self.tags(),self.previous,self.forced_weather)
                self.previous=self.selection["house"]["Id"];self.pose_step=0
                if self.library.interactions:
                    self.selection['program']=Program(self.library.interactions,self.selection,self.selection['tags'],self.settings['DoghouseMinutes']*60,used=self.interaction_history)
                self.renderer.begin(self.selection);self.image=self.renderer.frame(self.selection,0)
                self.schedule.section=time.monotonic()
            else:
                self.start_movie()
            self.repaint()
        except Exception as e:self.failed.emit(str(e));self.stop()

    def start_movie(self):
        if self.stopped:return
        try:
            scene=self.library.movie(self.tags(),self.previous,self.failed_movies)
            self.previous=scene["Id"];self.image=QImage()
            self.loading_at=time.monotonic()
            self.video_start_pending=True
            self.media.setSource(QUrl.fromLocalFile(str(media_file(self.library.root,scene["File"]))))
        except Exception as e:self.failed.emit(str(e));self.stop()

    def media_status(self,status):
        if self.mode!="movie" or self.stopped:return
        if status==QMediaPlayer.MediaStatus.LoadedMedia and self.video_start_pending:
            self.video_start_pending=False;self.media.setPosition(0);self.media.play()
        elif status==QMediaPlayer.MediaStatus.EndOfMedia:QTimer.singleShot(0,self.next_scene)

    def media_error(self,error,message):
        if self.stopped or self.mode!="movie":return
        self.failed_movies.add(self.previous)
        if len(self.failed_movies)>=3:self.failed.emit("Video decoding failed. Install the media dependencies listed in README. "+message);self.stop()
        else:QTimer.singleShot(0,self.start_movie)

    def video_frame(self,frame):
        if self.stopped or self.mode!="movie" or not frame.isValid():return
        image=frame.toImage()
        if not image.isNull():self.image=image;self.video_frames+=1;self.repaint()

    def tick(self):
        if self.stopped:return
        try:
            if self.mode=="idle":
                elapsed=time.monotonic()-self.schedule.section
                if elapsed>=self.settings["DoghouseMinutes"]*60:self.next_scene();return
                step=int(elapsed/40)
                if "program" not in self.selection and step!=self.pose_step:
                    self.pose_step=step;self.selection["pose"]=random.choice([p for p in self.library.catalog["Poses"] if p["Id"]!=self.selection["pose"]["Id"]])
                self.image=self.renderer.frame(self.selection,elapsed);self.frames+=1
                if 'program' in self.selection:
                    character,visitors=self.selection['program'].at(elapsed)
                    if not character['Pose']:self.action_frames+=1
                    if visitors:self.visitor_frames+=1
                self.repaint()
            elif self.mode=="movie" and self.image.isNull() and time.monotonic()-self.loading_at>20:
                self.failed.emit("The video could not start within 20 seconds. Check the installed media codecs.");self.stop()
        except Exception as e:self.failed.emit(str(e));self.stop()

    def repaint(self):
        for window in self.windows:window.update()

    def stop(self):
        if self.stopped:return
        self.stopped=True;self.timer.stop();self.weather_timer.stop();self.media.stop()
        for window in self.windows:window.close()
        if self.power and self.cookie is not None:
            try:self.power.call("UnInhibit",self.cookie)
            except RuntimeError:pass
        try:QApplication.instance().screenRemoved.disconnect(self.screen_removed)
        except (TypeError,RuntimeError):pass
        # Keep worker objects alive until network requests finish; never destroy a running QThread.
        pending=[j for j in self.jobs if j.isRunning()]
        if pending:
            for job in pending:job.finished.connect(self.finish_when_ready)
        else:self.done.emit()
    def finish_when_ready(self):
        if not any(j.isRunning() for j in self.jobs):self.done.emit()
