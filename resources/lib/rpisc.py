import resources.config as config
import calendar
import os
import time
import traceback
import re
import json
from datetime import datetime
from resources.lib.screens import RPiTouchscreen
from resources.lib.cameras import AmbientSensor, RPiCamera
from resources.lib.xlogger import Logger

try:
    import paho.mqtt.publish as publish
    import paho.mqtt.client as mqtt
    has_mqtt = True
except ImportError:
    has_mqtt = False

try:
    import sdnotify
    has_notify = True
except ImportError:
    has_notify = False


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
        device = {'identifiers': [self._cleanup(config.Get('device_identifier'))],
                  'name': config.Get('device_name'),
                  'manufacturer': config.Get('device_manufacturer'),
                  'model': config.Get('device_model'),
                  'sw_version': config.Get('device_version'),
                  'configuration_url': config.Get('device_config_url')}
        self.MQTTAUTH = {'username': config.Get('mqtt_user'),
                         'password': config.Get('mqtt_pass')}
        self.MQTTHOST = config.Get('mqtt_host')
        self.MQTTPORT = config.Get('mqtt_port')
        self.MQTTCLIENT = config.Get('mqtt_clientid')
        self.MQTTPATH = config.Get('mqtt_path')
        self.MQTTRETAIN = config.Get('mqtt_retain')
        self.MQTTSENSORNAME = config.Get('mqtt_sensor_name')
        self.MQTTSENSORID = config.Get('mqtt_sensor_id')
        self.MQTTDISCOVER = config.Get('mqtt_discover')
        self.MQTTQOS = config.Get('mqtt_qos')
        version = config.Get('mqtt_version')
        if version == 'v5':
            self.MQTTVERSION = mqtt.MQTTv5
        elif version == 'v311':
            self.MQTTVERSION = mqtt.MQTTv311
        else:
            self.MQTTVERSION = mqtt.MQTTv31
        if self.MQTTDISCOVER:
            self._send('Light', device=device)
            self._send('Light Level', device=device)
        if config.Get('use_watchdog') and has_notify:
            self.WATCHDOG = sdnotify.SystemdNotifier()
            self.LW.log(['setting up Watchdog'])
            self.WATCHDOG.notify('READY=1')
        else:
            self.WATCHDOG = None
        self._updatesettings()

    def Start(self):
        self.LW.log(['starting up ScreenControl'], 'info')
        try:
            while self.KEEPRUNNING:
                if self.WATCHDOG:
                    self.LW.log(['sending notice to Watchdog'])
                    self.WATCHDOG.notify('WATCHDOG=1')
                if self.AUTODIM:
                    self.LW.log(['checking autodim'])
                    light_level = self.CAMERA.LightLevel()
                    self.LW.log(['got back %s from light sensor' %
                                str(light_level)])
                    do_dark = False
                    do_bright = False
                    do_dim = False
                    if light_level:
                        if light_level <= self.DARKTHRESHOLD:
                            do_dark = True
                            light_detected = 'OFF'
                        elif light_level <= self.BRIGHTTHRESHOLD:
                            do_dim = True
                            light_detected = 'ON'
                        else:
                            do_bright = True
                            light_detected = 'ON'
                        if self.MQTTDISCOVER:
                            self._send('Light', item_state=light_detected)
                            self._send('Light Level', item_state=light_level)
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
            self.KEEPRUNNING = False
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

    def _send(self, item, item_state=None, device=None):
        if self.MQTTSENSORNAME:
            friendly_name = '%s %s' % (self.MQTTSENSORNAME, item)
        else:
            friendly_name = item
        entity_id = self._cleanup(friendly_name)
        if item.lower() == 'light':
            mqtt_type = 'binary_sensor'
            unique_id = self._cleanup(self.MQTTSENSORID) + '_light'
        else:
            mqtt_type = 'sensor'
            unique_id = self._cleanup(self.MQTTSENSORID) + '_light_level'
        mqtt_publish = 'homeassistant/%s/%s' % (mqtt_type, entity_id)
        if device:
            mqtt_config = mqtt_publish + '/config'
            payload = {}
            payload['name'] = friendly_name
            payload['unique_id'] = unique_id
            payload['state_topic'] = mqtt_publish + '/state'
            if mqtt_type == 'binary_sensor':
                payload['device_class'] = 'light'
            else:
                payload['device_class'] = 'illuminance'
                payload['state_class'] = 'measurement'
            payload['device'] = device
            self.LW.log(['sending config for sensor %s to %s' %
                         (friendly_name, self.MQTTHOST)])
            self._mqtt_send(mqtt_config, json.dumps(payload))
        elif item_state:
            self.LW.log(['sending %s as status for sensor %s to %s' %
                        (item_state, friendly_name, self.MQTTHOST)])
            self._mqtt_send(mqtt_publish + '/state', item_state)

    def _mqtt_send(self, mqtt_publish, payload):
        if has_mqtt:
            try:
                publish.single(mqtt_publish,
                               payload=payload,
                               qos=self.MQTTQOS,
                               retain=self.MQTTRETAIN,
                               hostname=self.MQTTHOST,
                               auth=self.MQTTAUTH,
                               client_id=self.MQTTCLIENT,
                               port=self.MQTTPORT,
                               protocol=self.MQTTVERSION)
            except (ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError, ConnectionError, OSError) as e:
                self.LW.log(['MQTT connection problem: ' + e])
        else:
            self.LW.log(
                ['MQTT python libraries are not installed, no message sent'])
        self.LW.log(['sent to %s: %s' % (mqtt_publish, payload)])

    def _cleanup(self, item):
        if item:
            return re.sub(r'[^\w]', '_', item.lower())
        return item

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
