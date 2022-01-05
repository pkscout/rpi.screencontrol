import sys
defaults = {'readingdelta': 2,
            'script_running': 'green',
            'kodi_connection': 'blue',
            'no_kodi_connection': 'red',
            'brightness_bar': 'yellow',
            'autodim': True,
            'autodimdelta': 0.25,
            'dark': 5,
            'bright': 80,
            'fetchsuntime': '3:00',
            'specialtriggers': {'dark': 'ScreenOff', 'bright': 'ScreenOn:100', 'dim': 'ScreenOn:40'},
            'timedtriggers': [],
            'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'weekend': ['Saturday', 'Sunday'],
            'which_sensor': 'BME280',
            'i2c_port': 1,
            'bme280_address': 0x76,
            'bme280_sampling': 4,
            'bme280_adjust': -1,
            'sensehat_adjust': True,
            'sensehat_factor': 8.199,
            'which_camera': 'ambient',
            'ambient_address': 0x23,
            'ambient_cmd': 0x20,
            'ambient_oversample': 10,
            'pressuredelta': 180,
            'pressurerapid': 10,
            'pressureregular': 3,
            'kodiuri': 'localhost',
            'kodiwsport': 9090,
            'logbackups': 1,
            'debug': False,
            'testmode': False}

try:
    import data.settings as overrides
    has_overrides = True
except ImportError:
    has_overrides = False
if sys.version_info < (3, 0):
    _reload = reload
elif sys.version_info >= (3, 4):
    from importlib import reload as _reload
else:
    from imp import reload as _reload


def Reload():
    if has_overrides:
        _reload(overrides)


def Get(name):
    setting = None
    if has_overrides:
        setting = getattr(overrides, name, None)
    if not setting:
        setting = defaults.get(name, None)
    return setting
