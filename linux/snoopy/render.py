"""Render every idle scene into one complete image before presenting it."""
from collections import OrderedDict
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter
from .core import layer_frame, media_file

class Renderer:
    def __init__(self, library):
        self.root = library.root/"IdleAssets"
        self.cache, self.bytes = OrderedDict(), 0
        self.background = None

    def image(self, path):
        if path in self.cache:
            self.cache.move_to_end(path); return self.cache[path]
        img = QImage(str(media_file(self.root,path)))
        if img.isNull(): raise ValueError("Cannot decode image: "+path)
        img = img.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        size = img.sizeInBytes()
        while self.cache and self.bytes+size>96*1024*1024:
            _, old = self.cache.popitem(last=False); self.bytes -= old.sizeInBytes()
        self.cache[path] = img; self.bytes += size
        return img

    @staticmethod
    def color(c):
        return QColor(c["red"],c["green"],c["blue"],round(c["alpha"]*255))

    def begin(self, selection):
        palette = selection["palette"]
        tags=selection.get('tags',set())
        fallback=QColor(25,65,69) if 'timeOfDay:lateNight' in tags else QColor(42,108,99) if 'timeOfDay:evening' in tags else QColor(55,143,123)
        background = self.color(palette["Background"]) if palette else fallback
        overlay = self.color(palette["Overlay"]) if palette else QColor(128,187,159,36)
        result = QImage(1920,1080,QImage.Format.Format_ARGB32_Premultiplied); result.fill(background)
        tint = QImage(1920,1080,result.format()); tint.fill(overlay)
        painter = QPainter(tint)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.drawImage(QRectF(0,0,1920,1080),self.image("halftone.png")); painter.end()
        painter = QPainter(result); painter.drawImage(0,0,tint); painter.end()
        self.background = result

    def frame(self, selection, seconds):
        if self.background is None: self.begin(selection)
        result = self.background.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        house, effect = selection["house"], selection["effect"]
        def draw(asset, offset=False):
            if not asset: return
            for layer in sorted(asset["Layers"],key=lambda l:l["Plane"]!="background"):
                file, opacity = layer_frame(asset,layer,seconds)
                painter.save(); painter.setOpacity(opacity)
                x = layer["X"] + (house["OffsetX"] if offset else 0)
                y = layer["Y"] + (house["OffsetY"] if offset else 0)
                painter.drawImage(QRectF(x,y,layer["Width"],layer["Height"]),self.image(file))
                painter.restore()
        def segment(s,plane=None):
            elapsed=max(0,seconds-s['Start'])
            for layer in s['Layers']:
                if plane and layer['Plane']!=plane:continue
                frame=int(elapsed*layer['Fps'])
                frame=frame%len(layer['Files']) if layer['Loop'] else min(frame,len(layer['Files'])-1)
                x,y,w,h=layer['X'],layer['Y'],layer['Width'],layer['Height']
                if not s['Asset'].get('IgnoreOffset',False):x+=house['OffsetX'];y+=house['OffsetY']
                if 'Rects' in layer:
                    r=layer['Rects'][frame];x+=r[0];y+=r[1];w,h=r[2:]
                painter.drawImage(QRectF(x,y,w,h),self.image(layer['Files'][frame]))
        try:
            behind = effect and effect["Layers"][0]["Plane"]=="backgroundEffect"
            if behind: draw(effect)
            program=selection.get('program')
            character,visitors=program.at(seconds) if program else (None,[])
            for visitor in visitors:segment(visitor,'backgroundVisitor')
            draw(house,True)
            if character:segment(character)
            else:draw(selection['pose'],True)
            for visitor in visitors:segment(visitor,'foregroundVisitor')
            if not behind: draw(effect)
        finally: painter.end()
        return result

def image_rect(source, target, fill):
    """Fit/fill a source size into a target rect without changing monitor modes."""
    scale = (max if fill else min)(target.width()/source.width(),target.height()/source.height())
    width, height = source.width()*scale, source.height()*scale
    return QRectF(target.center().x()-width/2,target.center().y()-height/2,width,height)
