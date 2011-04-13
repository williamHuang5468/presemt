from math import sqrt
from os.path import join, dirname, splitext
from . import Screen
from kivy.uix.scatter import ScatterPlane, Scatter
from kivy.clock import Clock
from kivy.graphics import Color, Line
from kivy.factory import Factory
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import NumericProperty, ObjectProperty, StringProperty, \
        BooleanProperty, ListProperty
from kivy.animation import Animation
from kivy.core.image import ImageLoader

default_image = join(dirname(__file__), '..', 'data', 'tests', 'faust_github.jpg')


def prefix(exts):
    return ['*.' + t for t in exts]

SUPPORTED_IMG = []
for loader in ImageLoader.loaders:
    for ext in loader.extensions():
        if ext not in SUPPORTED_IMG:
            SUPPORTED_IMG.append(ext)
# OK, who has a better idea on how to do that that is still acceptable?
SUPPORTED_VID = ['avi', 'mpg', 'mpeg']


def point_inside_polygon(x,y,poly):
    '''Taken from http://www.ariel.com.au/a/python-point-int-poly.html'''

    n = len(poly)
    inside = False

    p1x = poly[0]
    p1y = poly[1]
    for i in xrange(0, n+2, 2):
        p2x = poly[i % n]
        p2y = poly[(i+1) % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y

    return inside

#
# Panel for configuration
# Panel have open() and close() hook, to know when they are displayed or not
#

class Panel(FloatLayout):
    ctrl = ObjectProperty(None)
    def open(self):
        pass
    def close(self):
        pass

class TextPanel(Panel):
    pass

class LocalFilePanel(Panel):
    imgtypes = ListProperty(prefix(SUPPORTED_IMG))
    vidtypes = ListProperty(prefix(SUPPORTED_VID))
    suptypes = ListProperty(prefix(SUPPORTED_IMG + SUPPORTED_VID))


#
# Objects that will be added on the plane
#

class PlaneObject(Scatter):

    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(PlaneObject, self).__init__(**kwargs)
        touch = kwargs.get('touch_follow', None)
        if touch:
            touch.ud.scatter_follow = self
            touch.grab(self)

    def configure(self):
        pass

    def get_configure(self):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.is_double_tap:
            self.configure()
        return super(PlaneObject, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if 'scatter_follow' in touch.ud:
                self.center = touch.pos
        return super(PlaneObject, self).on_touch_move(touch)


class TextPlaneObject(PlaneObject):

    text = StringProperty('Hello world')

    font_size = NumericProperty(48)

    def get_configure(self):
        from kivy.uix.button import Button
        return Button(text='Hello World')


class ImagePlaneObject(PlaneObject):

    source = StringProperty(default_image)


class VideoPlaneObject(PlaneObject):

    source = StringProperty(None)


#
# Main screen, act as a controler for everybody
#

class MainScreen(Screen):

    plane = ObjectProperty(None)

    config = ObjectProperty(None)

    do_selection = BooleanProperty(False)

    selection_points = ListProperty([0, 0])

    def __init__(self, **kwargs):
        self._panel = None
        self._panel_text = None
        self._panel_localfile = None
        super(MainScreen, self).__init__(**kwargs)

    def _create_object(self, cls, touch, pos, **kwargs):
        if touch:
            pos = self.plane.to_local(*touch.pos)
        obj = cls(touch_follow=touch, **kwargs)
        if pos:
            obj.center = touch.pos
        self.plane.add_widget(obj)

   # def on_touch_down(self, touch):
   #     if super(MainScreen, self).on_touch_down(touch):
   #         return True
   #     if not self.do_selection:
   #         self.do_selection = True
   #         self.selection_points = []
   #         x, y = self.plane.to_local(*touch.pos)
   #         self.selection_points.append(x)
   #         self.selection_points.append(y)
   #         touch.grab(self)
   #         return True

   # def on_touch_move(self, touch):
   #     if super(MainScreen, self).on_touch_move(touch):
   #         return True
   #     if touch.grab_current is self and self.do_selection:
   #         x, y = self.plane.to_local(*touch.pos)
   #         self.selection_points.append(x)
   #         self.selection_points.append(y)
   #         self.update_select()

   # def on_touch_up(self, touch):
   #     if super(MainScreen, self).on_touch_up(touch):
   #         return True
   #     if touch.grab_current is self and self.do_selection:
   #         touch.ungrab(self)
   #         self.update_select()
   #         self.selection_align()
   #         self.cancel_selection()
   #         return True

    def update_select(self):
        s = self.selection_points
        for child in self.plane.children:
            child.selected = point_inside_polygon(
                child.center_x, child.center_y, s)

    def selection_align(self):
        childs = [x for x in self.plane.children if x.selected]
        if not childs:
            return
        # do align on x
        left = min([x.x for x in childs])
        right = max([x.right for x in childs])
        middle = left + (right - left) / 2.
        for child in childs:
            child.center_x = middle

    def cancel_selection(self):
        self.do_selection = False
        self.selection_points = [0, 0]
        for child in self.plane.children:
            child.selected = False

    def create_text(self, touch=None, pos=None):
        self._create_object(TextPlaneObject, touch, pos)

    def from_localfile(self, touch, **kwargs):
        source = kwargs['source']
        ext = splitext(source)[-1][1:]
        if ext in SUPPORTED_IMG:
            self.create_image(touch, **kwargs)
        elif ext in SUPPORTED_VID:
            self.create_video(touch, **kwargs)

    def create_image(self, touch=None, pos=None, **kwargs):
        self._create_object(ImagePlaneObject, touch, pos, **kwargs)

    def create_video(self, touch=None, pos=None, **kwargs):
        self._create_object(VideoPlaneObject, touch, pos, **kwargs)

    def get_text_panel(self):
        if not self._panel_text:
            self._panel_text = TextPanel(ctrl=self)
        return self._panel_text

    def get_localfile_panel(self):
        if not self._panel_localfile:
            self._panel_localfile = LocalFilePanel(ctrl=self)
        return self._panel_localfile

    def toggle_panel(self, name=None):
        panel = None
        if name:
            panel = getattr(self, 'get_%s_panel' % name)()
        if self._panel:
            self._panel.close()
            self.config.remove_widget(self._panel)
            same = self._panel is panel
            self._panel = None
            if same:
                return
        if panel:
            self._panel = panel
            self.config.add_widget(panel)
            self._panel.open()


    # used for kv button
    def toggle_text_panel(self):
        self.toggle_panel('text')

    def toggle_localfile_panel(self):
        self.toggle_panel('localfile')

#
# Scatter plane with grid
#

class MainPlane(ScatterPlane):

    grid_spacing = NumericProperty(50)

    grid_count = NumericProperty(1000)

    def __init__(self, **kwargs):
        super(MainPlane, self).__init__(**kwargs)
        self.bind(
            grid_spacing=self._trigger_grid,
            grid_count=self._trigger_grid)
        self._trigger_grid()

    def _trigger_grid(self, *largs):
        Clock.unschedule(self.fill_grid)
        Clock.schedule_once(self.fill_grid)

    def fill_grid(self, *largs):
        self.canvas.clear()
        gs = self.grid_spacing
        gc = self.grid_count * gs
        with self.canvas:
            Color(.1, .1, .1, .9)
            for x in xrange(-gc, gc, gs):
                Line(points=(x, -gc, x, gc))
                Line(points=(-gc, x, gc, x))

Factory.register('MainPlane', cls=MainPlane)
