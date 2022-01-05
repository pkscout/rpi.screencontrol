# *  Credits:
# *
# *  v.2.0.0~beta1
# *  original RPi Sensor classes by pkscout

import datetime
import random
import subprocess
try:
    from sense_hat import SenseHat
    has_sensehat = True
except ImportError:
    has_sensehat = False
try:
    import smbus2
    import bme280
    has_smbus = True
except ImportError:
    has_smbus = False


class BME280Sensors:
    def __init__(self, port=1, address=0x76, sampling=4, adjust=-1, testmode=False):
        self.TESTMODE = testmode
        self.ADDRESS = address
        self.SAMPLING = sampling
        self.ADJUST = adjust
        self.DATA = None
        if has_smbus:
            self.BUS = smbus2.SMBus(port)
            bme280.load_calibration_params(self.BUS, self.ADDRESS)
        else:
            self.BUS = None

    def Humidity(self):
        if self.BUS:
            self._get_data()
            return self.DATA.humidity
        elif self.TESTMODE:
            return random.randint(43, 68)
        return None

    def Temperature(self):
        if self.BUS:
            self._get_data()
            return self.DATA.temperature + self.ADJUST
        elif self.TESTMODE:
            return random.randint(21, 28)
        return None

    def Pressure(self):
        if self.BUS:
            self._get_data()
            return self.DATA.pressure
        elif self.TESTMODE:
            return random.randint(990, 1020)
        return None

    def PressureTrend(self):
        return None

    def _get_data(self):
        if not self.DATA:
            self._sample()
        else:
            diff = datetime.datetime.now() - self.DATA.timestamp
            if diff.total_seconds() > 60:
                self._sample()

    def _sample(self):
        self.DATA = bme280.sample(
            bus=self.BUS, address=self.ADDRESS, sampling=self.SAMPLING)


class SenseHatSensors:
    def __init__(self, adjust=False, factor=5.466, testmode=False):
        self.ADJUST = adjust
        self.FACTOR = factor
        self.TESTMODE = testmode
        if has_sensehat:
            self.SENSE = SenseHat()
        else:
            self.SENSE = None

    def Humidity(self):
        if self.SENSE:
            for i in range(0, 5):
                reading = self.SENSE.get_humidity()
                if reading:
                    return reading
        elif self.TESTMODE:
            return random.randint(43, 68)
        return None

    def Temperature(self):
        if self.SENSE:
            for i in range(0, 5):
                p_reading = self.SENSE.get_temperature_from_pressure()
                h_reading = self.SENSE.get_temperature()
                if p_reading < h_reading:
                    reading = p_reading
                else:
                    reading = h_reading
                if reading:
                    if self.ADJUST:
                        cpu_raw = subprocess.check_output(
                            "vcgencmd measure_temp", shell=True)
                        cpu_temp = float(cpu_raw.split("=")[1].split("'")[0])
                        return int(round(reading - ((cpu_temp - reading)/self.FACTOR), 0))
                    else:
                        return reading
        elif self.TESTMODE:
            return random.randint(21, 28)
        return None

    def Pressure(self):
        if self.SENSE:
            for i in range(0, 5):
                reading = self.SENSE.get_pressure()
                if reading:
                    return reading
        elif self.TESTMODE:
            return random.randint(990, 1020)
        return None

    def PressureTrend(self):
        return None
