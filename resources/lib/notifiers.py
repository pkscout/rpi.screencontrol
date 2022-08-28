from resources.lib import url
import json
import re
try:
    import paho.mqtt.publish as publish
    import paho.mqtt.client as mqtt
    has_mqtt = True
except ImportError:
    has_mqtt = False


def _cleanup(item):
    if item:
        return re.sub(r'[^\w]', '_', item.lower())
    return item


class MqttNotifier:
    def __init__(self, config):
        self.MQTTAUTH = {'username': config.Get('mqtt_user'),
                         'password': config.Get('mqtt_pass')}
        self.MQTTHOST = config.Get('host')
        self.MQTTPORT = config.Get('mqtt_port')
        self.MQTTCLIENT = config.Get('mqtt_clientid')
        self.MQTTPATH = config.Get('mqtt_path')
        self.MQTTRETAIN = config.Get('mqtt_retain')
        self.MQTTDISCOVER = config.Get('mqtt_discover')
        self.MQTTQOS = config.Get('mqtt_qos')
        version = config.Get('mqtt_version')
        if version == 'v5':
            self.MQTTVERSION = mqtt.MQTTv5
        elif version == 'v311':
            self.MQTTVERSION = mqtt.MQTTv311
        else:
            self.MQTTVERSION = mqtt.MQTTv31
        self.SENSORNAME = config.Get('sensor_name')
        self.SENSORID = config.Get('sensor_id')
        self.DEVICE = {'identifiers': [_cleanup(config.Get('device_identifier'))],
                       'name': config.Get('device_name'),
                       'manufacturer': config.Get('device_manufacturer'),
                       'model': config.Get('device_model'),
                       'sw_version': config.Get('device_version'),
                       'configuration_url': config.Get('device_config_url')}

    def _mqtt_send(self, mqtt_publish, payload):
        loglines = []
        conn_error = ''
        if has_mqtt:
            try:
                publish.single(mqtt_publish,
                               payload=payload,
                               retain=self.MQTTRETAIN,
                               qos=self.MQTTQOS,
                               hostname=self.MQTTHOST,
                               auth=self.MQTTAUTH,
                               client_id=self.MQTTCLIENT,
                               port=self.MQTTPORT,
                               protocol=self.MQTTVERSION)
            except (ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError, ConnectionError, OSError) as e:
                loglines.append('MQTT connection problem: ' + str(e))
        else:
            loglines.append(
                'MQTT python libraries are not installed, no message sent')
        return loglines

    def Send(self, device, device_state):
        loglines = []
        payload = {}
        if self.SENSORNAME:
            friendly_name = '%s %s' % (self.SENSORNAME, device)
        else:
            friendly_name = device
        entity_id = self._cleanup(friendly_name)
        if device.lower() == 'light':
            mqtt_type = 'binary_sensor'
            unique_id = self._cleanup(self.SENSORID) + '_light'
        else:
            mqtt_type = 'sensor'
            unique_id = self._cleanup(self.SENSORID) + '_light_level'
        mqtt_publish = 'homeassistant/%s/%s' % (mqtt_type, entity_id)
        if self.MQTTDISCOVER:
            mqtt_config = mqtt_publish + '/config'
            payload['name'] = friendly_name
            payload['unique_id'] = unique_id
            payload['state_topic'] = mqtt_publish + '/state'
            if mqtt_type == 'binary_sensor':
                payload['device_class'] = 'light'
            else:
                payload['device_class'] = 'illuminance'
                payload['state_class'] = 'measurement'
            payload['device'] = self.DEVICE
            loglines.append(['sending config for sensor %s to %s' %
                             (friendly_name, self.MQTTHOST)])
            self._mqtt_send(mqtt_config, json.dumps(payload))
        loglines.append(['sending %s as status for sensor %s to %s' %
                         (device_state, friendly_name, self.MQTTHOST)])
        self._mqtt_send(mqtt_publish + '/state', device_state)
        return loglines


class HaRestNotifier:
    def __init__(self, config):
        self.LOCATION = config.Get('tracker_location')
        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'
        headers['Authorization'] = 'Bearer %s' % config.Get('rest_token')
        self.JSONURL = url.URL('json', headers=headers)
        self.RESTURL = 'http://%s:%s/api/states/' % (config.Get(
            'host'), config.Get('rest_port'))

    def Send(self, device, device_state):
        if self.SENSORNAME:
            friendly_name = '%s %s' % (self.SENSORNAME, device)
        else:
            friendly_name = device
        entity_id = self._cleanup(friendly_name)
        if device.lower() == 'light':
            rest_type = 'binary_sensor'
        else:
            rest_type = 'sensor'
        payload = {'state': device_state, 'attributes': {
            'friendly_name': friendly_name}}
        returned = self.JSONURL.Post('%s%s.%s' %
                                     (self.RESTURL, rest_type, entity_id),
                                     data=json.dumps(payload))
        return returned[1]


class NoNotifier:
    def __init__(self, config):
        pass

    def Send(self, device, device_state):
        return []
