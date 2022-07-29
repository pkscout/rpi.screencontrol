# rpi.screencontrol
This python script is designed to run as a service on a Raspberry Pi that has a BH1750 light sensor or Pi Camera for light level based screen dimming.

This script sets the brightness, and screen on/off based on triggers (dark, dim, bright) or times.

## PREREQUISITES:
1. You should be running Raspian Buster or later.  This script does support the new Picamera2 in Raspian Bullseye.
1. Python3 is required.

## PI CONFIGURATION:
To use the BH1750 ambient light sensor, you need to enable i2c in raspi-config. If you are using Raspian Buster and the Pi Camera to detect light levels, the camera must be turned on in raspi-config.  Both the camera and i2c options are under INTERFACING OPTIONS in raspi-config.

To control the RPi 7" touchscreen you need to also edit the backlight rules. From a terminal window:
```
sudo nano /etc/udev/rules.d/backlight-permissions.rules
```

and add:
```
SUBSYSTEM=="backlight",RUN+="/bin/chmod 666 /sys/class/backlight/%k/brightness /sys/class/backlight/%k/bl_power"
```
Then reboot.

## INSTALLATION:
For the script to work properly, you need to install a few things first.  You'll need the module to control the brightness of the screen:
```
sudo pip3 install rpi-backlight
```
If you are running on Raspian Bullseye or later and using the camera as a light sensor, you'll also need:
```
sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-pyqt5 python3-prctl libatlas-base-dev ffmpeg python3-pip
sudo pip3 install numpy --upgrade
sudo pip3 install picamera2
```
If you are going to use an MQTT broker to communicate light level to Home Assistant, you will also need the following:
```
pip3 install paho-mqtt
```

It is recommended you install this in `/home/pi`.  The service file you'll install later assumes this, so if you install it somewhere else, you'll need to edit rpisc.service.

## CONFIGURATION:
You can run this without further configuration.  If you want to change any of the defaults, you should create a new file called `settings.py` in the `data` folder.  The `data` folder is created at first run, or you can create in manually.  There are a number of options available in the settings:

* `autodimdelta = <float>` (default `0.25`)  
The time in minutes between light level checks.

* `dark = <int>` (default `5`)  
The light threshold below which the system considers it to be dark.  Between the `dark` and `bright` thresholds the system considers the light level to be dim.

* `specialtriggers = <dict>` (default `{'dark': 'ScreenOff', 'bright': 'ScreenOn:100', 'dim': 'ScreenOn:60'}`)  
These are special actions to take when certain conditions are true.  `ScreenOff` turns the screen off, `ScreenOn` with a level changes the screen brightness to the given level (from 1 to 100).

* `timedtriggers = <list>` (default `[]`)  
This is a list of times to trigger an action.  Each entry is itself a list.  The first item is a time (in a valid format), the second time is the action (`ScreenOff` or `ScreenOn` with a brightness level) and the last item (which is optional) is a string of either `weekdays` or `weekends` indicating whether the trigger runs only certain parts of the week.

* `which_camera = <str>` (default `pi`)  
Which device to use as a light sensor.  The default is to use a Raspberry Pi camera.  If you are using an i2c based light sensor, change this to `ambient`.

* `i2c_port = <int>` (default `1`)  
The i2c port of the light sensor.

* `ambient_address = <hex>` (default `0x23`)  
The i2c address of the light sensor.

* `ambient_cmd = <hex>` (default `0x20`)  
The i2c command prefix for the light sensor.

* `ambient_oversample = <int>` (default `10`)  
To get an accurate reading from the light sensor, the script gets the level multiple times and averages them.  This is the number of samples to take.

* `mqtt_host = <str>` (default `127.0.0.1`)  
The IP address of your MQTT broker.

* `mqtt_port = <int>` (default `1883`)  
The port of your MQTT broker.

* `mqtt_user = <str>` (default `mqtt`)  
The username needed if authentication is required for your MQTT broker.

* `mqtt_pass = <str>` (default `mqtt_password`)  
The password needed if authentication is required for your MQTT broker.

* `mqtt_clientid = <str>` (default `lightsensor`)  
The client ID provided to the MQTT broker.

* `mqtt_retain = <boolean>` (default `True`)  
Tells the MQTT broker whether to retain the messages to send to clients when they first connect.

* `mqtt_discover = <boolean>` (default `False`)  
Tells the script whether to send MQTT updates.

* `mqtt_sensor_name = <str>` (default `empty string`)  
A string to use at the beginning of the friendly name for the sensors.  By default the sensors are just called `Light` and `Light Level`, so this let's you have something like `Living Room Light` and `Living Room Light Level`.

* `mqtt_sensor_id = <str>` (default `BPQjLznvX3NJJ2ty8zD8P8P6q7cPso7GCM32Zcan`)  
This is a random string to ensure the sensor id is unique.  `_light` and `_light level` are added at the end of this string to differential the sensors.  If you include a `mqtt_sensor_name` that is appended as well.  If you're running this on multiple devices, it's probably worth changing this for each device.


* `device_name = <str>` (default `Light Sensor`)  
The name of the device.  If you run multiple presence trackers in a house, by default all tracker entities will show up under one device (when using the MQTT notifier).  If you want separate devices for each light sensor, you need to change the name of the device.  You also need to change the identifier (below).

* `device_identifier = <str>` (default `dLa6kirY3JrhzNDFEjDeyyHxRHgiBJmExQRFVC7U`)  
The "serial number" of the device.  If you run multiple presence trackers in a house, by default all tracker entities will show up under one device (when using the MQTT notifier).  If you want separate devices for each presence tracker, you need to change the identifier of the device.  You also need to change the name (above).

* `device_version = <str>`  
The version number of the device. This is bumped automatically anytime the script is updated. I have no idea why you would want to override this, but you can.

* `device_manufacturer = <str>` (default `pkscout`)  
The manufacturer of the device. This is my github handle by default, but if you don't want to see my handle on the device, you can change this.

* `device_model = <str>` (default `LS1000`)  
The model of the device.

* `device_config_url = <str>` (default `https://github.com/pkscout/rpi.screencontrol`)  
The configuration URL for the device. This gives you a link in the device to the README for the script in case you need to reference it.  If you don't want to link in your Home Assistant device, just set this to an empty string.

* `logbackups = <int>` (default `1`)  
The number of days of logs to keep.

* `debug = <boolean>` (default `False`)  
For debugging you can get a more verbose log by setting this to True.


## ABOUT AUTO DIMMING:
Auto dimming allows you to do certain actions based on given triggers or times.  Auto dim understands special triggers and time based triggers.  There are three special triggers: dark, dim, and bright (these require a functioning BH1750 ambient light sensor or RPi camera to do anything).  You can change the light level thresholds if needed.  Time triggers can accept any 24 hour formatted time.  Time triggers can also be set to run only on weekdays or the weekend.  If you turn off the display with a timed trigger, light levels cannot override that.  You MUST turn the display back on with another timed trigger.

## USAGE: 
To run from the terminal (for testing): `python3 /home/pi/rpi.screencontrol/execute.py`  
To exit: CNTL-C

Running from the terminal is useful during initial testing, but once you know it's working the way you want, you should set it to autostart.  To do that you need to copy rpiwsl.service.txt to the systemd directory, change the permissions, and configure systemd. From a terminal window:
```
sudo cp -R /home/pi/rpi.screencontrol/rpisc.service.txt /lib/systemd/system/rpisc.service
sudo chmod 644 /lib/systemd/system/rpisc.service
sudo systemctl daemon-reload
sudo systemctl enable rpisc.service
```

From now on the script will start automatically after a reboot.  If you want to manually stop or start the service you can do that as well. From a terminal window:
```
sudo systemctl stop rpisc.service 
sudo systemctl start rpisc.service 
```

If you change any settings, it's best to restart the service.

### USING WITH HOME ASSISTANT

By default, the MQTT messaging is disabled.  To enable it, see the `mqtt_discover` setting above.  When enabled, the script uses [MQTT Discovery](https://www.home-assistant.io/docs/mqtt/discovery/) to create a light binary sensor and a generic light level sensor in Home Assistant under a single device.  You can use those entities or device as desired in automations and Lovelace display.