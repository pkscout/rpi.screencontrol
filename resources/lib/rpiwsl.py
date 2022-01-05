
import resources.config as config
import calendar
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime
from threading import Thread
from collections import deque
from resources.lib.sensors import BME280Sensors, SenseHatSensors
from resources.lib.screens import RPiTouchscreen, SenseHatLED
from resources.lib.cameras import AmbientSensor, RPiCamera
from resources.lib.xlogger import Logger
try:
    import websocket
    has_websockets = True
except ImportError:
    has_websockets = False


def _send_json(wsc, lw, thetype, thedata):
    if not wsc:
        return
    if thetype.lower() == 'update':
        jsondict = {"id": 1, "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll",
                    "params": {"sender": "Weatherstation", "message": "RPIWSL_VariablePass", "data": thedata}}
    elif thetype.lower() == 'infolabelquery':
        jsondict = {'id': '2', 'jsonrpc': '2.0',  'method': 'XBMC.GetInfoLabels',
                    'params': {'labels': thedata}}
    elif thetype.lower() == 'requestsettings':
        jsondict = {"id": 1, "jsonrpc": "2.0", "method": "JSONRPC.NotifyAll",
                    "params": {"sender": "Weatherstation", "message": "RPIWSL_SettingsRequest", "data": thedata}}
    if jsondict:
        jdata = json.dumps(jsondict)
        lw.log(['sending Kodi ' + jdata])
        wsc.send(jdata)


class ScreenControl:

    def __init__(self, lw):
        self.KODIACTIONMAP = ['None', 'ScreenOff', 'ScreenOn']
        self.KODIDAYMAP = ['', 'Weekdays', 'Weekend']
        self.KODICAMERAMAP = ['Ambient', 'Pi']
        self.LW = lw
        self.WSC = None
        self.KEEPRUNNING = True
        self.UpdateSettings()
        self.STOREDBRIGHTNESS = self.SCREEN.GetBrightness()
        self.SCREENSTATE = 'On'
        self.LED = SenseHatLED()
        self.LED.PixelOn(0, 7, self.LED.Color(config.Get('script_running')))
        self.LED.PixelOn(1, 7, self.LED.Color(
            config.Get('no_kodi_connection')))
        self.SUNRISE = ''
        self.SUNSET = ''
        self.DARKRUN = False
        self.BRIGHTRUN = False
        self.DIMRUN = False
        self.WAITTIME = config.Get('autodimdelta') * 60

    def Start(self):
        self.LW.log(['starting up ScreenControl thread'], 'info')
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
                        self.HandleAction(self.DARKACTION)
                        self.DARKRUN = True
                        self.BRIGHTRUN = False
                        self.DIMRUN = False
                    elif do_bright and not self.BRIGHTRUN:
                        self.LW.log(
                            ['bright trigger activated with ' + self.BRIGHTACTION])
                        self.HandleAction(self.BRIGHTACTION)
                        self.DARKRUN = False
                        self.BRIGHTRUN = True
                        self.DIMRUN = False
                    elif do_dim and not self.DIMRUN:
                        self.LW.log(
                            ['dim trigger activated with ' + self.DIMACTION])
                        self.HandleAction(self.DIMACTION)
                        self.DARKRUN = False
                        self.BRIGHTRUN = False
                        self.DIMRUN = True
                    if self._is_time(config.Get('fetchsuntime')):
                        self.LW.log(
                            ['getting updated sunrise and sunset times'])
                        self.HandleAction('GetSunriseSunset')
                    else:
                        triggers = self.TIMEDTRIGGERS
                        for onetrigger in triggers:
                            if onetrigger[0].lower() == 'sunrise':
                                onetrigger[0] = self.SUNRISE
                            if onetrigger[0].lower() == 'sunset':
                                onetrigger[0] = self.SUNSET
                            try:
                                checkdays = onetrigger[2]
                            except IndexError:
                                checkdays = ''
                            if self._is_time(onetrigger[0], checkdays=checkdays):
                                self.LW.log(['timed trigger %s activated with %s' % (
                                    onetrigger[0], onetrigger[1])])
                                self.HandleAction(onetrigger[1])
                    if css != self.SCREENSTATE:
                        _send_json(self.WSC, self.LW, thetype='update',
                                   thedata='ScreenStatus:' + self.SCREENSTATE)
                time.sleep(self.WAITTIME)
        except Exception as e:
            self.LW.log([traceback.format_exc()], 'error')
            print(traceback.format_exc())

    def Stop(self):
        self.LW.log(['closing down ScreenControl thread'], 'info')
        self.LED.ClearPanel()
        self.KEEPRUNNING = False

    def HandleAction(self, action):
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
            _send_json(self.WSC, self.LW, thetype='update',
                       thedata='ScreenStatus:ScreenOn')
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
            _send_json(self.WSC, self.LW, thetype='update',
                       thedata='ScreenStatus:ScreenOff')
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
        elif action == 'getsunrisesunset':
            self.SetSunriseSunset()
        self._set_brightness_bar()

    def SetSunriseSunset(self, jsonresult=None):
        if jsonresult:
            self.SUNRISE = self._convert_to_24_hour(
                jsonresult.get('Window(Weather).Property(Today.Sunrise)'))
            self.SUNSET = self._convert_to_24_hour(
                jsonresult.get('Window(Weather).Property(Today.Sunset)'))
            self.LW.log(['set sunrise to %s and sunset to %s' %
                        (self.SUNRISE, self.SUNSET)])
        else:
            if not self.AUTODIM:
                return
            self.LW.log(['getting sunrise and sunset times from Kodi'])
            _send_json(self.WSC, self.LW, thetype='infolabelquery',
                       thedata=['Window(Weather).Property(Today.Sunrise)', 'Window(Weather).Property(Today.Sunset)'])

    def SetWebsocketClient(self, wsc):
        self.WSC = wsc

    def UpdateSettings(self, thedata=None):
        if thedata:
            self._map_returned_settings(thedata)
        else:
            self._get_config_settings()
        self.CAMERA = self._pick_camera()
        self.SCREEN = self._pick_screen()
        if not self.AUTODIM:
            self.DARKRUN = False
            self.BRIGHTRUN = False
            self.DIMRUN = False
            self.HandleAction(self.FIXEDBRIGHTNESS)

    def _get_config_settings(self):
        self.WHICHCAMERA = config.Get('which_camera')
        self.FIXEDBRIGHTNESS = 'Brightness:100'
        self.AUTODIM = config.Get('autodim')
        self.DARKACTION = config.Get('specialtriggers').get('dark')
        self.DIMACTION = config.Get('specialtriggers').get('dim')
        self.BRIGHTACTION = config.Get('specialtriggers').get('bright')
        self.DARKTHRESHOLD = config.Get('dark')
        self.BRIGHTTHRESHOLD = config.Get('bright')
        self.TIMEDTRIGGERS = config.Get('timedtriggers')

    def _map_returned_settings(self, thedata):
        self.WHICHCAMERA = self.KODICAMERAMAP[thedata.get('which_camera', 0)]
        self.FIXEDBRIGHTNESS = 'Brightness:' + \
            thedata.get('fixed_brightness', '100')
        self.DARKTHRESHOLD = thedata.get('dark_threshold', 5)
        self.BRIGHTTHRESHOLD = thedata.get('bright_threshold', 80)
        self.AUTODIM = thedata.get('auto_dim', True)
        self.DARKACTION = self._determine_action(thedata.get(
            'dark_action', 0), thedata.get('dark_level', '10'))
        self.DIMACTION = self._determine_action(thedata.get(
            'dim_action', 0), thedata.get('dim_level', '40'))
        self.BRIGHTACTION = self._determine_action(thedata.get(
            'bright_action', 0), thedata.get('bright_level', '100'))
        self.TIMEDTRIGGERS = []
        self.TIMEDTRIGGERS.append(['sunrise',
                                   self._determine_action(thedata.get(
                                       'sunrise_action', 0), thedata.get('sunrise_level', '100')),
                                   self.KODIDAYMAP[thedata.get('sunrise_days', 0)]])
        self.TIMEDTRIGGERS.append(['sunset',
                                   self._determine_action(thedata.get(
                                       'sunset_action', 0), thedata.get('sunset_level', '50')),
                                   self.KODIDAYMAP[thedata.get('sunset_days', 0)]])
        self.TIMEDTRIGGERS.append([thedata.get('timer_one_time', '00:00'),
                                   self._determine_action(thedata.get(
                                       'timer_one_action', 0), thedata.get('timer_one_level', '100')),
                                   self.KODIDAYMAP[thedata.get('timer_one_days', 0)]])
        self.TIMEDTRIGGERS.append([thedata.get('timer_two_time', '00:00'),
                                   self._determine_action(thedata.get(
                                       'timer_two_action', 0), thedata.get('timer_two_level', '100')),
                                   self.KODIDAYMAP[thedata.get('timer_two_days', 0)]])
        self.TIMEDTRIGGERS.extend(config.Get('timedtriggers'))

    def _determine_action(self, action, level):
        if action == 2:
            return '%s:%s' % (self.KODIACTIONMAP[action], level)
        else:
            return self.KODIACTIONMAP[action]

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
        # so +/- window is total' ) readingdelta
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

    def _set_brightness_bar(self):
        self.LED.SetBar(level=self.SCREEN.GetBrightness(), anchor=6, themin=25, themax=225,
                        color=self.LED.Color(config.Get('brightness_bar')))

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


class PassSensorData:

    def __init__(self, lw, ledcolor=(255, 255, 255)):
        self.KEEPRUNNING = True
        self.LW = lw
        self.WSC = None
        self.KODISENSORMAP = ['BME280', 'Sensehat']
        self.LED = SenseHatLED()
        self.LEDCOLOR = ledcolor
        self.READINGDELTA = config.Get('readingdelta') * 60
        self.PRESSUREHISTORY = deque()
        self.UpdateSettings()

    def Start(self):
        self.LW.log(['starting up PassSensorData thread'], 'info')
        try:
            while self.KEEPRUNNING:
                temperature = self.SENSOR.Temperature()
                humidity = self.SENSOR.Humidity()
                pressure = self.SENSOR.Pressure()
                pressuretrend = self.SENSOR.PressureTrend()
                s_data = []
                s_data.append('IndoorTemp:' + str(temperature))
                s_data.append('IndoorHumidity:' + str(humidity))
                s_data.append('IndoorPressure:' + str(pressure))
                if pressuretrend:
                    s_data.append('PressureTrend:' + pressuretrend)
                else:
                    s_data.append('PressureTrend:' +
                                  self._get_pressure_trend(pressure))
                d_str = ''
                for item in s_data:
                    d_str = '%s;%s' % (d_str, item)
                d_str = d_str[1:]
                self.LW.log(['sensor data: ' + d_str])
                self.LED.Sweep(anchor=7, start=1, color=self.LEDCOLOR)
                self.LED.PixelOn(1, 7, self.LEDCOLOR)
                _send_json(self.WSC, self.LW, thetype='update', thedata=d_str)
                time.sleep(self.READINGDELTA)
        except Exception as e:
            self.LW.log([traceback.format_exc()], 'error')
            print(traceback.format_exc())

    def Stop(self):
        self.LW.log(['closing down PassSensorData thread'], 'info')
        self.KEEPRUNNING = False

    def SetWebsocketClient(self, wsc):
        self.WSC = wsc

    def UpdateSettings(self, thedata=None):
        if thedata:
            self.WHICHSENSOR = self.KODISENSORMAP[thedata.get(
                'which_sensor', 0)]
        else:
            self.WHICHSENSOR = config.Get('which_sensor')
        self.SENSOR = self._pick_sensor()

    def _get_pressure_trend(self, current_pressure):
        if current_pressure is None:
            return 'steady'
        self.PRESSUREHISTORY.append(current_pressure)
        if len(self.PRESSUREHISTORY) > config.Get('pressuredelta') / config.Get('readingdelta'):
            self.PRESSUREHISTORY.popleft()
        previous_pressure = self.PRESSUREHISTORY[0]
        diff = current_pressure - previous_pressure
        if diff < 0:
            direction = 'falling'
        else:
            direction = 'rising'
        if abs(diff) >= config.Get('pressurerapid'):
            return 'rapidly ' + direction
        elif abs(diff) >= config.Get('pressureregular'):
            return direction
        return 'steady'

    def _pick_sensor(self):
        self.LW.log(['setting up %s weather sensor' % self.WHICHSENSOR])
        if self.WHICHSENSOR.lower() == 'sensehat':
            return SenseHatSensors(adjust=config.Get('sensehat_adjust'), factor=config.Get('sensehat_factor'),
                                   testmode=config.Get('testmode'))
        else:
            return BME280Sensors(port=config.Get('i2c_port'), address=config.Get('bme280_address'),
                                 sampling=config.Get('bme280_sampling'), adjust=config.Get('bme280_adjust'),
                                 testmode=config.Get('testmode'))


class Main:

    def __init__(self, thepath):
        try:
            self.LW = Logger(logfile=os.path.join(os.path.dirname(thepath), 'data', 'logs', 'logfile.log'),
                             numbackups=config.Get('logbackups'), logdebug=config.Get('debug'))
            self.LW.log(['script started, debug set to %s' %
                        str(config.Get('debug'))], 'info')
            if not has_websockets:
                self.LW.log(['websockets is not installed, exiting'], 'info')
                return
            self.KODIURL = 'ws://%s:%s/jsponrpc' % (
                config.Get('kodiuri'), config.Get('kodiwsport'))
            signal.signal(signal.SIGINT, self.signal_handler)
            while True:
                self.KODICONN = True
                self.SCREENCONTROL = ScreenControl(self.LW)
                self.PASSSENSORDATA = PassSensorData(self.LW)
                sc_thread = Thread(target=self.SCREENCONTROL.Start)
                sc_thread.setDaemon(True)
                sc_thread.start()
                psd_thread = Thread(target=self.PASSSENSORDATA.Start)
                psd_thread.setDaemon(True)
                psd_thread.start()
                self._websocket_client()
                self.LW.log(
                    ['connection to Kodi was closed, will try and reestablish connection in 1 minute'], 'info')
                self.KODICONN = False
                self.SCREENCONTROL.Stop()
                self.PASSSENSORDATA.Stop()
                del sc_thread
                del psd_thread
                self.SCREENCONTROL = None
                self.PASSSENSORDATA = None
                time.sleep(60)
        except Exception as e:
            self.LW.log([traceback.format_exc()], 'error')
            print(traceback.format_exc())

    def signal_handler(self, sig, frame):
        try:
            self.SCREENCONTROL.Stop()
            self.PASSSENSORDATA.Stop()
        except AttributeError:
            self.LW.log(['threads not running, so no need to stop them'])
        if self.KODICONN:
            ws = websocket.create_connection(self.KODIURL)
            _send_json(ws, self.LW, thetype='update',
                       thedata='IndoorTemp:None;IndoorHumidity:None;IndoorPressure:None;PressureTrend:None')
            ws.close()
        self.LW.log(['script finished'], 'info')
        sys.exit(0)

    def _websocket_client(self):
        def on_message(ws, message):
            self.LW.log(['Kodi said: %s' % message])
            jm = json.loads(message)
            if jm.get('id') == '2':
                self.SCREENCONTROL.SetSunriseSunset(
                    jsonresult=jm.get('result'))
            elif jm.get('method') == 'Other.ReturningSettings':
                self.SCREENCONTROL.UpdateSettings(
                    thedata=jm.get('params', {}).get('data'))
                self.PASSSENSORDATA.UpdateSettings(
                    thedata=jm.get('params', {}).get('data'))
            elif jm.get('method') == 'Other.ScreenOn':
                self.SCREENCONTROL.HandleAction('screenon')
            elif jm.get('method') == 'Other.ScreenOff':
                self.SCREENCONTROL.HandleAction('screenoff')
            elif jm.get('method') == 'System.OnQuit':
                wsc.close()

        def on_error(ws, error):
            if not str(error) == '0':
                self.LW.log(['error reading data from Kodi: ' + str(error)])

        def on_open(ws):
            self.LW.log(['opening websocket connection to Kodi'], 'info')
            _send_json(wsc, self.LW, thetype='requestsettings', thedata='all')
            self.SCREENCONTROL.SetWebsocketClient(wsc)
            self.PASSSENSORDATA.SetWebsocketClient(wsc)
            self.SCREENCONTROL.SetSunriseSunset()

        def on_close(ws):
            self.LW.log(['closing websocket connection to Kodi'], 'info')

        wsc = websocket.WebSocketApp(
            self.KODIURL, on_message=on_message, on_error=on_error, on_close=on_close)
        wsc.on_open = on_open
        wsc.run_forever()
