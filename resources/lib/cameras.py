# *  Credits:
# *
# *  v.1.1.0
# *  original Light Sensor classes by pkscout

import time
import numpy as np
import random
try:
    import picamera
    import picamera.array
    has_legacy = True
except ImportError:
    has_legacy = False
try:
    from picamera2 import Picamera2
    has_camera = True
except:
    has_camera = False
try:
    import smbus2
    has_smbus = True
except ImportError:
    has_smbus = False


class AmbientSensor:
    def __init__(self, port=1, address=0x23, cmd=0x20, oversample=10, testmode=False):
        self.ADDRESS = address
        self.CMD = cmd
        self.OVERSAMPLE = int(oversample)
        self.TESTMODE = testmode
        if has_smbus:
            self.BUS = smbus2.SMBus(port)
        else:
            self.BUS = None

    def LightLevel(self):
        if self.BUS:
            level = 0
            for x in range(0, self.OVERSAMPLE):
                data = self.BUS.read_i2c_block_data(self.ADDRESS, self.CMD, 2)
                level = level + self._converttonumber(data)
                time.sleep(0.1)
            return level/self.OVERSAMPLE + 1
        elif self.TESTMODE:
            return random.randint(1, 100)
        return None

    def _converttonumber(self, data):
        return ((data[1] + (256 * data[0])) / 1.2)


class RPiCamera:
    def __init__(self, useled=False, testmode=False):
        self.WIDTH = 128
        self.HEIGHT = 80
        self.TESTMODE = testmode
        if has_camera:
            self._set_camera()
        elif has_legacy:
            self._set_legacy()

    def LightLevel(self):
        if has_camera:
            return self._check_camera()
        elif has_legacy:
            return self._check_legacy()
        elif self.TESTMODE:
            return random.randint(1, 100)
        return None

    def _set_camera(self):
        self.CAMERA = Picamera2()
        config = self.CAMERA.create_still_configuration(
            lores={"size": (self.WIDTH, self.HEIGHT)})
        self.CAMERA.configure(config)

    def _check_camera(self):
        no_camera = True
        while no_camera:
            try:
                self.CAMERA.start()
                no_camera = False
            except RuntimeError:
                no_camera = True
            if no_camera:
                time.sleep(1)
        np_array = self.CAMERA.capture_array('lores')
        self.CAMERA.stop()
        return int(100*np.average(np_array[:self.HEIGHT, :])/235) + 1

    def _set_legacy(self):
        self.CAMERA = picamera.PiCamera()
        self.CAMERA.exposure_mode = 'auto'
        self.CAMERA.awb_mode = 'auto'
        self.CAMERA.resolution = (self.WIDTH, self.HEIGHT)
        self.CAMERA.led = useled

    def _check_legacy(self):
        reading = None
        for i in range(0, 5):
            with picamera.array.PiRGBArray(self.CAMERA) as stream:
                self.CAMERA.capture(stream, format='rgb')
                reading = int(np.average(stream.array[..., 1])) + 1
        return reading
