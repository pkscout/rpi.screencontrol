# *  Credits:
# *
# *  v.1..0
# *  original RPi Screen classes by pkscout

import time
from six import string_types
try:
    from rpi_backlight import Backlight
    has_backlight = True
except ImportError:
    has_backlight = False
try:
    from sense_hat import SenseHat
    has_sensehat = True
except ImportError:
    has_sensehat = False


class RPiTouchscreen:
    def __init__(self, testmode=False):
        self.BDIRECTION = 1
        self.TESTMODE = testmode
        if has_backlight:
            self.BACKLIGHT = Backlight("/sys/class/backlight/10-0045")
            self.CURRENTBRIGHTNESS = self.BACKLIGHT.brightness
            self.TOUCHSCREEN = True
        else:
            self.CURRENTBRIGHTNESS = 100
            self.TOUCHSCREEN = False

    def SetBrightness(self, brightness, themax=100, themin=0, smooth=True, duration=5):
        brightness = int(brightness)
        if brightness == self.CURRENTBRIGHTNESS:
            return
        if brightness > themax:
            brightness = themax
        elif brightness < themin:
            brightness = themin
        if self.TOUCHSCREEN:
            with self.BACKLIGHT.fade(duration=duration):
                self.BACKLIGHT.brightness = brightness
            self.CURRENTBRIGHTNESS = brightness

    def AdjustBrightness(self, direction, step=25, smooth=True, duration=1):
        themax = int(255 / step) * step
        themin = step
        if self.CURRENTBRIGHTNESS > themax:
            self.CURRENTBRIGHTNESS = themax
        elif self.CURRENTBRIGHTNESS < themin:
            self.CURRENTBRIGHTNESS = themin
        if direction == 'down':
            step = -1 * step
        new_brightness = self.CURRENTBRIGHTNESS + step
        self.SetBrightness(new_brightness, themax=themax,
                           themin=themin, duration=duration)

    def GetBrightness(self):
        return self.CURRENTBRIGHTNESS


class SenseHatLED:
    def __init__(self, low_light=True, rotate=False):
        if has_sensehat:
            try:
                self.SENSE = SenseHat()
                self.SENSE.low_light = low_light
                if rotate:
                    self.SENSE.set_rotation(180)
            except OSError:
                self.SENSE = None
        else:
            self.SENSE = None
        self.PALETTE = {'green': (0, 255, 0), 'yellow': (255, 255, 0), 'blue': (0, 0, 255),
                        'red': (255, 0, 0), 'white': (255, 255, 255), 'nothing': (0, 0, 0),
                        'pink': (255, 105, 180)}

    def Blink(self, x, y, color=(255, 255, 255), pause=0.2, pivot=False):
        if pivot:
            bx = y
            by = x
        else:
            bx = x
            by = y
        self.PixelOn(bx, by, color)
        time.sleep(pause)
        self.PixelOff(bx, by)

    def ClearPanel(self, color=None):
        if self.SENSE:
            if color:
                self.SENSE.clear(color)
            else:
                self.SENSE.clear()

    def Color(self, color):
        if isinstance(color, string_types):
            return self.PALETTE[color.lower()]
        elif isinstance(color, tuple):
            if len(color) == 3:
                return color
        return (255, 255, 255)

    def PixelOff(self, x, y):
        if self.SENSE:
            self.SENSE.set_pixel(x, y, 0, 0, 0)

    def PixelOn(self, x, y, color=(255, 255, 255)):
        if self.SENSE:
            self.SENSE.set_pixel(x, y, color)

    def SetBar(self, level, vertical=False, anchor=0, themin=0, themax=255, color=(255, 255, 255)):
        step = (themax - themin)/8
        height = int((level - themin)/step)
        for loc in range(0, 7):
            if vertical:
                x = anchor
                y = loc
            else:
                x = loc
                y = anchor
            if loc < height:
                self.PixelOn(x, y, color)
            else:
                self.PixelOff(x, y)

    def Sweep(self, vertical=False, anchor=0, start=0, stop=7, color=(255, 255, 255), pause=0.1):
        if start < 0:
            start = 0
        if stop > 7:
            stop = 7
        current = start
        while current <= stop:
            self.Blink(current, anchor, color, pause, vertical)
            current = current + 1
        current = current - 2
        while current >= start:
            self.Blink(current, anchor, color, pause, vertical)
            current = current - 1
