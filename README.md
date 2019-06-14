# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Todo ##
[TODO List](GoodWeUSBLogger)
[[TODO List|GoodWeUSBLogger]]

## Required Python version

I'm currently using **Python 2.7.13** on a Raspberry Pi for this project. It has been verified that it is **_NOT_** working with Python 3.
Python 2.7 is already installed (at least on my Raspberry Zero W)

```bash
sudo apt-get update
sudo apt-get install -y python-pip
```

## Required python modules

* configparser
* paho-mqtt
* pyudev
* ioctl_opt
* enum

```bash
sudo python -m pip install configparser paho-mqtt pyudev ioctl_opt enum
```

## Config

Create file _/etc/udev/rules.d/98-my-usb-device.rules_ with:

```bash
SUBSYSTEM=="input", GROUP="input", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0084", ATTRS{idProduct}=="0041", MODE="0660", GROUP="plugdev", SYMLINK+="goodwe"
```

Create file _/etc/goodwe.conf_:

```
[inverter]
loglevel = INFO
pollinterval = 2500
vendorId = 0084
modelId = 0041
logfile = /var/log/goodwe.log

[mqtt]
server = <MQTT Server IP>
port = 1883
topic = goodwe
clientid = <unique MQTT client id>
```

## Usage

The program will lookup the device on its own by enumerating all USB devices and look for the **_vendorId_** and **_modelId_** as listed above.
My own two GoodWe solar inverters have these vendor and model id. You can lookup your own by connecting the USB device to the raspberry and look for these values in the system logs. These _should_ be the correct IDs for all GoodWe solar inverters.

The application needs to be run as **root** in the current setup. It tries to write a pid-file in _/var/run_ and the high level logs for the daemon are written to _/var/log/goodwe.log_
To start the daemon application:

```bash
$ sudo ./GoodWe.py start
```

## Inverter information

You can lookup the serial number of your inverter in the _/var/log/goodwe.log_ file after a succesfull start.

```
2019-06-14 17:44:42,135 run(48) - INFO: Connected to MQTT 192.168.2.240
2019-06-14 17:45:22,863 handleRegistration(415) - INFO: New inverter found with serial id: 15000DTU166W0157. Register address.
2019-06-14 17:45:23,078 handleRegistrationConfirmation(443) - INFO: Inverter now online.
```

The application will start to deliver information packets on the configured MQTT channel.
The channels are composed as:
* '**goodwe** / **_SERIALID_** / **data**' for the data packets
* '**goodwe** / **_SERIALID_** / **online**' for a simple 1 or 0 as the online status.

## Optional

Currently I use the 'restartd' program to keep this process running using the following config:

File: /etc/restartd.conf:

```bash
goodwe "GoodWe.py" "cd /opt/goodweusblogger; ./GoodWe.py restart"
```

I have everything running from _/opt/goodweusblogger_. If you have your application installed somewhere else you need to update the above statement.
