# *  Credits:
# *
# *  v.1..0
# *  original RPi Screen classes by pkscout

import time
try:
    from rpi_backlight import Backlight
    has_backlight = True
except ImportError:
    has_backlight = False


class RPiTouchscreen:
    def __init__(self, testmode=False):
        self.BDIRECTION = 1
        self.TESTMODE = testmode
        self.BACKLIGHT = None
        if has_backlight:
            try:
                self.BACKLIGHT = Backlight()
            except:
                self.BACKLIGHT = Backlight("/sys/class/backlight/10-0045")
        if self.BACKLIGHT:
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
