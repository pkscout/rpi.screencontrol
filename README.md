rpi.weatherstation.lite
================
This python script is designed to run as a service on a Raspberry Pi that has a SenseHAT or BME280 sensor installed (and a BH1750 light sensor or Pi Camera for light level based screen dimming).  It is designed to run in conjunction with Kodi running a modified version of the Estuary skin with a companion addon called script.weatherstation.lite.  Together they provide a clock/weather station system based on the Raspberry Pi platform.  Information about the complete setup will be available later on the wiki for this repo.

This script provides a few functions:
1. read the temperature, humidity, and pressure from the SenseHat or BME280 and pass them to Kodi
2. Handle messages sent from Kodi for screen control (brightness and auto dim status)
3. Set the brightness, and screen on/off based on triggers (dark, dim, bright) or times (including sunrise, sunset)


PREREQUISITES:
1. Optimally you should be running Raspian Jessie or later, as it has all the SenseHAT and touchscreen modules and most of the python bindings already included.  If you're running something older, you'll have to run the script, see what imports don't work, and download python modules as needed.

2. Python3 is recommended, although this works in Python2 as well.  If you use Python2, then in step 3 use pip instead of pip3.  You'll also need to edit the rpiwsl.service.txt to call python instead of python3 before you install it (see below for those install instructions).

3. For rpi.weatherstation.lite to function properly, there are some modules you need to install:
From a terminal window:
sudo pip3 install websocket-client		(to communicate with Kodi)
sudo pip3 install rpi-backlight			(to control the RPi Touchscreen)
sudo pip3 install RPi.bme280            (to use the BME280 temp/humidity/pressure sensor)

4. To use the BH1750 ambient light sensor and/or the BME280 temperature sensor, you need to enable i2c in raspi-config. To use the Pi Camera to detect light levels, the camera must be turned on in raspi-config.  Both the camera and i2c options are under INTERFACING OPTIONS in raspi-config.

5. If you are using the official RPi 7" touchscreen you need to also edit the backlight rules.
From a terminal window:
sudo nano /etc/udev/rules.d/backlight-permissions.rules

and add:
SUBSYSTEM=="backlight",RUN+="/bin/chmod 666 /sys/class/backlight/%k/brightness /sys/class/backlight/%k/bl_power"

Then reboot.


INSTALLATION:
It is recommended you install this in /home/pi.  The service file you'll install later assumes this, so if you install it somewhere else, you'll need to edit rpiwsl.service.


CONFIGURATION:
You can run this without further configuration.  If you want to see all how all the settings are set by default, you can look at settings-example.py.  If you want to change any of the defaults, you can either create a new file called settings.py and copy and paste the specific setting(s) you want to change from settings-example.py OR you can copy settings-example.py to settings.py and edit that file.


ABOUT AUTO DIMMING:
Auto dimming allows you to do certain actions based on given triggers or times.  Auto dim understands special triggers and time based triggers.  There are three special triggers: dark, dim, and bright (these require a functioning BH1750 ambient light sensor or RPi camera to do anything).  You can change the light level thresholds if needed.  Time triggers can accept any 24 hour formatted time as well as the keywords Sunrise and Sunset (those times are provided by Kodi via one of its weather plugins).  Time triggers can also be set to run only on weekdays or the weekend.  If you turn off the display manually (i.e. from Kodi) or with a timed trigger, light levels cannot override that.  You MUST turn the display back on manually or with another timed trigger.  See settings-example.py for the exact format for timed triggers.


USAGE:
To run from the terminal (for testing): python3 /home/pi/rpi.sensehat.mon/execute.py
To exit: CNTL-C

Running from the terminal is useful during initial testing, but once you know it's working the way you want, you should set it to autostart.  To do that you need to copy rpiwsl.service.txt to the systemd directory, change the permissions, and configure systemd.
From a terminal window:
sudo cp -R /home/pi/rpi.weatherstation.lite/rpiwsl.service.txt /lib/systemd/system/rpiwsl.service
sudo chmod 644 /lib/systemd/system/rpiwsl.service
sudo systemctl daemon-reload
sudo systemctl enable rpiwsl.service

From now on the script will start automatically after a reboot.  If you want to manually stop or start the service you can do that as well.
From a terminal window:
sudo systemctl stop rpiwsl.service 
sudo systemctl start rpiwsl.service 

You can change settings by editing the settings.py file any time you'd like.  The script will reload the settings automatically.  No need to stop/start the script (unless otherwise noted in the settings file).
