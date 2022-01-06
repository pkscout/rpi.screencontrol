
import resources.config as config
import calendar
import os
import time
import traceback
from datetime import datetime
from resources.lib.screens import RPiTouchscreen
from resources.lib.cameras import AmbientSensor, RPiCamera
from resources.lib.xlogger import Logger


class ScreenControl:

    def __init__(self, lw):
        self.LW = lw
        self.KEEPRUNNING = True
        self.WHICHCAMERA = config.Get('which_camera')
        self.FIXEDBRIGHTNESS = 'Brightness:100'
        self.CAMERA = self._pick_camera()
        self.SCREEN = self._pick_screen()
        self.STOREDBRIGHTNESS = self.SCREEN.GetBrightness()
        self.SCREENSTATE = 'On'
        self.DARKRUN = False
        self.BRIGHTRUN = False
        self.DIMRUN = False
        self.WAITTIME = config.Get('autodimdelta') * 60
        self._updatesettings()

    def Start(self):
        self.LW.log(['starting up ScreenControl'], 'info')
        try:
            while self.KEEPRUNNING:
                if self.AUTODIM:
                    self.LW.log(['checking autodim'])
                    lightlevel = self.CAMERA.LightLevel()
                    self.LW.log(['got back %s from light sensor' %
                                str(lightlevel)])
                    css = self.SCREENSTATE
                    do_dark = False
                    do_bright = False
                    do_dim = False
                    if lightlevel:
                        if lightlevel <= self.DARKTHRESHOLD:
                            do_dark = True
                        elif lightlevel <= self.BRIGHTTHRESHOLD:
                            do_dim = True
                        else:
                            do_bright = True
                    if do_dark and not self.DARKRUN:
                        self.LW.log(
                            ['dark trigger activated with ' + self.DARKACTION])
                        self._handleaction(self.DARKACTION)
                        self.DARKRUN = True
                        self.BRIGHTRUN = False
                        self.DIMRUN = False
                    elif do_bright and not self.BRIGHTRUN:
                        self.LW.log(
                            ['bright trigger activated with ' + self.BRIGHTACTION])
                        self._handleaction(self.BRIGHTACTION)
                        self.DARKRUN = False
                        self.BRIGHTRUN = True
                        self.DIMRUN = False
                    elif do_dim and not self.DIMRUN:
                        self.LW.log(
                            ['dim trigger activated with ' + self.DIMACTION])
                        self._handleaction(self.DIMACTION)
                        self.DARKRUN = False
                        self.BRIGHTRUN = False
                        self.DIMRUN = True
                    else:
                        triggers = self.TIMEDTRIGGERS
                        for onetrigger in triggers:
                            try:
                                checkdays = onetrigger[2]
                            except IndexError:
                                checkdays = ''
                            if self._is_time(onetrigger[0], checkdays=checkdays):
                                self.LW.log(['timed trigger %s activated with %s' % (
                                    onetrigger[0], onetrigger[1])])
                                self._handleaction(onetrigger[1])
                time.sleep(self.WAITTIME)
                self._updatesettings()
        except KeyboardInterrupt:
            self._handleaction(self.FIXEDBRIGHTNESS)
            self.KEEPRUNNING = False
        except Exception as e:
            self._handleaction(self.FIXEDBRIGHTNESS)
            self.LW.log([traceback.format_exc()], 'error')
            print(traceback.format_exc())

    def _handleaction(self, action):
        action = action.lower()
        if action == 'brightnessup' and self.SCREENSTATE == 'On':
            self.SCREEN.AdjustBrightness(direction='up')
            self.LW.log(['turned brightness up'])
        elif action == 'brightnessdown' and self.SCREENSTATE == 'On':
            self.SCREEN.AdjustBrightness(direction='down')
            self.LW.log(['turned brightness down'])
        elif action.startswith('screenon'):
            sb = action.split(':')
            try:
                brightness = sb[1]
            except IndexError:
                brightness = self.STOREDBRIGHTNESS
            self.SCREEN.SetBrightness(brightness=brightness)
            self.SCREENSTATE = 'On'
            self.LW.log(
                ['turned screen on to brightness of ' + str(brightness)])
            if self.DIMRUN and self.BRIGHTRUN:
                self.DARKRUN = False
                self.DIMRUN = False
                self.BRIGHTRUN = False
        elif action == 'screenoff' and self.SCREENSTATE == 'On':
            self.STOREDBRIGHTNESS = self.SCREEN.GetBrightness()
            self.SCREEN.SetBrightness(brightness=0)
            self.SCREENSTATE = 'Off'
            self.LW.log(
                ['turned screen off and saved brightness as ' + str(self.STOREDBRIGHTNESS)])
            if not self.DARKRUN:
                self.DARKRUN = True
                self.DIMRUN = True
                self.BRIGHTRUN = True
        elif action.startswith('brightness:'):
            try:
                level = int(action.split(':')[1])
            except ValueError:
                level = None
            if level:
                if self.SCREENSTATE == 'On':
                    self.SCREEN.SetBrightness(brightness=level)
                    self.LW.log(['set brightness to ' + str(level)])
                else:
                    self.STOREDBRIGHTNESS = level
                    self.LW.log(
                        ['screen is off, so set stored brightness to ' + str(level)])

    def _updatesettings(self):
        self.AUTODIM = config.Get('autodim')
        self.DARKACTION = config.Get('specialtriggers').get('dark')
        self.DIMACTION = config.Get('specialtriggers').get('dim')
        self.BRIGHTACTION = config.Get('specialtriggers').get('bright')
        self.DARKTHRESHOLD = config.Get('dark')
        self.BRIGHTTHRESHOLD = config.Get('bright')
        self.TIMEDTRIGGERS = config.Get('timedtriggers')
        if not self.AUTODIM:
            self.DARKRUN = False
            self.BRIGHTRUN = False
            self.DIMRUN = False
            self._handleaction(self.FIXEDBRIGHTNESS)

    def _is_time(self, thetime, checkdays=''):
        action_time = self._set_datetime(thetime)
        if not action_time:
            return False
        elif checkdays.lower().startswith('weekday') and not calendar.day_name[action_time.weekday()] in config.Get('weekdays'):
            return False
        elif checkdays.lower().startswith('weekend') and not calendar.day_name[action_time.weekday()] in config.Get('weekend'):
            return False
        rightnow = datetime.now()
        action_diff = rightnow - action_time
        if abs(action_diff.total_seconds()) < config.Get('autodimdelta') * 30:
            return True
        else:
            return False

    def _set_datetime(self, str_time):
        tc = str_time.split(':')
        now = datetime.now()
        try:
            fulldate = datetime(year=now.year, month=now.month,
                                day=now.day, hour=int(tc[0]), minute=int(tc[1]))
        except ValueError:
            fulldate = None
        return fulldate

    def _convert_to_24_hour(self, timestr):
        time_split = timestr.split(' ')
        if time_split[1] == 'AM':
            return time_split[0]
        else:
            hm = time_split[0].split(':')
            hour = str(int(hm[0]) + 12)
            return '%s:%s' % (hour, hm[1])

    def _pick_camera(self):
        self.LW.log(['setting up %s light sensor' % self.WHICHCAMERA])
        if self.WHICHCAMERA.lower() == 'pi':
            return RPiCamera(testmode=config.Get('testmode'))
        else:
            return AmbientSensor(port=config.Get('i2c_port'), address=config.Get('ambient_address'),
                                 cmd=config.Get('ambient_cmd'), oversample=config.Get('ambient_oversample'),
                                 testmode=config.Get('testmode'))

    def _pick_screen(self):
        return RPiTouchscreen(testmode=config.Get('testmode'))


class Main:

    def __init__(self, thepath):
        self.LW = Logger(logfile=os.path.join(os.path.dirname(thepath), 'data', 'logs', 'logfile.log'),
                         numbackups=config.Get('logbackups'), logdebug=config.Get('debug'))
        self.LW.log(['script started, debug set to %s' %
                    str(config.Get('debug'))], 'info')
        self.SCREENCONTROL = ScreenControl(self.LW)
        self.SCREENCONTROL.Start()
        self.LW.log(['closing down ScreenControl'], 'info')
