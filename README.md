# rpi.screencontrol
This python script is designed to run as a service on a Raspberry Pi that has a BH1750 light sensor or Pi Camera for light level based screen dimming.

This script sets the brightness, and screen on/off based on triggers (dark, dim, bright) or times.

## PREREQUISITES:
1. You should be running Raspian Buster or later.  This script does support the new Picamera2 in Raspian Bullseye.
1. Python3 is required.

## PI CONFIGURATION:
To use the BH1750 ambient light sensor and/or the BME280 temperature sensor, you need to enable i2c in raspi-config. If you are using Raspian Buster and the Pi Camera to detect light levels, the camera must be turned on in raspi-config.  Both the camera and i2c options are under INTERFACING OPTIONS in raspi-config.

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
If you are running on Raspian Bullseye or later, and using the camera as a light sensor, you'll also need:
```
sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-pyqt5 python3-prctl libatlas-base-dev ffmpeg python3-pip
sudo pip3 install numpy --upgrade
sudo pip3 install picamera2
```

It is recommended you install this in `/home/pi`.  The service file you'll install later assumes this, so if you install it somewhere else, you'll need to edit rpisc.service.

## CONFIGURATION:
You can run this without further configuration.  If you want to change any of the defaults, you should create a new file called settings.py and update the specific setting(s) you want to change.

## ABOUT AUTO DIMMING:
Auto dimming allows you to do certain actions based on given triggers or times.  Auto dim understands special triggers and time based triggers.  There are three special triggers: dark, dim, and bright (these require a functioning BH1750 ambient light sensor or RPi camera to do anything).  You can change the light level thresholds if needed.  Time triggers can accept any 24 hour formatted time.  Time triggers can also be set to run only on weekdays or the weekend.  If you turn off the display with a timed trigger, light levels cannot override that.  You MUST turn the display back on with another timed trigger.  See settings-example.py for the exact format for timed triggers.

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
