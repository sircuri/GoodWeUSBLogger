# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Todo ##
[TODO List](GoodWeUSBLogger)
[[TODO List|GoodWeUSBLogger]]

## Required modules

* pyudev
* ioctl_opt
* configparser
* paho-mqtt
* enum

## Config

Create file '/etc/udev/rules.d/98-my-usb-device.rules':

```bash
SUBSYSTEM=="input", GROUP="input", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0084", ATTRS{idProduct}=="0041", MODE="0666", GROUP="plugdev"
```

Create file '/etc/goodwe/goodwe.conf':

```
[inverter]
loglevel = INFO 			# Default Python loggin framework log level
pollinterval = 5000			# Every 5 seconds the information of the inverter gets pushed to MQTT

[mqtt]
server = 192.168.x.x		# ip address of MQTT server
port = 1883
topic = power				# base mqtt topic. Topics are "<topic>/<serialnumber>/data" and "<topic>/<serialnumber>/online"
clientid = goodweZ
```

## Usage

The program will lookup the device on its own by enumerating all USB devices and look for the idVendor and idProduct as listed above.
This is currently hardcoded in the application. It might be added to the config in a future version.

The application needs to be run as root in the current setup. It tries to write a pid-file in /var/run and the high level logs for the daemon are written to /var/log/goodwe
To start the daemon application:

```bash
$ sudo ./GoodWe.py start
```

Currently I use the 'restartd' program to keep this process running using the following config:

File: /etc/restartd.conf:

```bash
goodwe "GoodWe.py" "cd /home/pi/GoodWeUSBLogger; ./GoodWe.py restart"
```