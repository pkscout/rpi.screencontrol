import sys
defaults = {'autodim': True,
            'autodimdelta': 0.25,
            'dark': 5,
            'bright': 80,
            'specialtriggers': {'dark': 'ScreenOff', 'bright': 'ScreenOn:100', 'dim': 'ScreenOn:40'},
            'timedtriggers': [],
            'weekdays': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'weekend': ['Saturday', 'Sunday'],
            'which_camera': 'pi',
            'i2c_port': 1,
            'ambient_address': 0x23,
            'ambient_cmd': 0x20,
            'ambient_oversample': 10,
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
