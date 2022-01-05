rpi.screencontrol
================
This python script is designed to run as a service on a Raspberry Pi that has a BH1750 light sensor or Pi Camera for light level based screen dimming.

This script sets the brightness, and screen on/off based on triggers (dark, dim, bright) or times.


PREREQUISITES:
1. You should be running Raspian Buster or later, although right now I wouldn't recommend Bullseye unless you like beta testing software.

2. Python3 is required.

3. For rpi.screencontrol to function properly, there are some modules you need to install:
From a terminal window:
sudo pip3 install rpi-backlight			(to control the RPi Touchscreen)

4. To use the BH1750 ambient light sensor and/or the BME280 temperature sensor, you need to enable i2c in raspi-config. To use the Pi Camera to detect light levels, the camera must be turned on in raspi-config.  Both the camera and i2c options are under INTERFACING OPTIONS in raspi-config.  If you are running Bullseye, you must enable the camera in legacy mode, as there are currently no Python bindings for libcamera.  If that doesn't work, use Buster.

5. To control the RPi 7" touchscreen you need to also edit the backlight rules.
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
Auto dimming allows you to do certain actions based on given triggers or times.  Auto dim understands special triggers and time based triggers.  There are three special triggers: dark, dim, and bright (these require a functioning BH1750 ambient light sensor or RPi camera to do anything).  You can change the light level thresholds if needed.  Time triggers can accept any 24 hour formatted time.  Time triggers can also be set to run only on weekdays or the weekend.  If you turn off the display with a timed trigger, light levels cannot override that.  You MUST turn the display back on with another timed trigger.  See settings-example.py for the exact format for timed triggers.


USAGE:
To run from the terminal (for testing): python3 /home/pi/rpi.screencontrol/execute.py
To exit: CNTL-C

Running from the terminal is useful during initial testing, but once you know it's working the way you want, you should set it to autostart.  To do that you need to copy rpiwsl.service.txt to the systemd directory, change the permissions, and configure systemd.
From a terminal window:
sudo cp -R /home/pi/rpi.screencontrol/rpisc.service.txt /lib/systemd/system/rpisc.service
sudo chmod 644 /lib/systemd/system/rpisc.service
sudo systemctl daemon-reload
sudo systemctl enable rpisc.service

From now on the script will start automatically after a reboot.  If you want to manually stop or start the service you can do that as well.
From a terminal window:
sudo systemctl stop rpisc.service 
sudo systemctl start rpisc.service 

You can change settings by editing the settings.py file any time you'd like.  The script will reload the settings automatically.  No need to stop/start the script (unless otherwise noted in the settings file).
