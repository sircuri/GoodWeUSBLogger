# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Todo ##
[TODO List](GoodWeUSBLogger)
[[TODO List|GoodWeUSBLogger]]

## Required Python version

I'm currently using **Python 2.7.13** on a Raspberry Pi for this project but the GoodWeUSBLogger has now been ported to python3. This version 
supports both python2 and python3.
Python 2.7 is already installed (at least on my Raspberry Zero W)

```bash
sudo apt-get update
sudo apt-get install -y python-pip
```
for python3 install _python3-pip_ instead of _python-pip_.

## Required python modules

* configparser
* paho-mqtt
* pyudev
* ioctl_opt
* enum34 (standard installed on Raspbian, but see below)
* simplejson

```bash
sudo python -m pip install configparser paho-mqtt pyudev ioctl_opt simplejson
```
Use _pip3_ instead of _pip_ when you want to use python3.

If you installed enum on Raspbian in the past, remove it and re-install the python-enum34 package.
```bash
pip uninstall enum
apt-get install --reinstall python-enum34

The standard package python-enum34 is more feature rich than the enum module.
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
#loglevel = DEBUG
#pollinterval = 2500
#vendorId = 0084
#modelId = 0041
#logfile = /var/log/goodwe.log

[mqtt]
#server = localhost
#port = 1883
#topic = goodwe
#clientid = goodwe-usb
#username = 
#password = mypassword

```
Almost all configuration parameters have sensible defaults and are commented out. The values shown are the defaults. If you need to change a 
setting remove the # in front of the parameter name.
Only when username and the optional password are set, they will be used. Setting the username will trigger authentication for the MQTT server. 
Password can optionally be set.
Please note that the logfile is not used when used in foreground mode.

## Usage

The program will lookup the device on its own by enumerating all USB devices and look for the **_vendorId_** and **_modelId_** as listed above.
My own two GoodWe solar inverters have these vendor and model id. You can lookup your own by connecting the USB device to the raspberry and look for these values in the system logs. These _should_ be the correct IDs for all GoodWe solar inverters.

The application needs to be run as **root** in the current setup. It tries to write a pid-file in _/var/run_ and the high level logs for the daemon are written to _/var/log/goodwe.log_
To start the daemon application:

```bash
$ sudo ./GoodWe.py start
```
The program can also be started in the foreground with all logging to stderr (the logfile is not used). Start the program as follows:

```bash
$ sudo ./Goodwe.py foreground
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

## Systemd

Running under systemd is an option for using restartd. Systemd will collect all logging information in it's journal. 
The service unit allows one to run as a system user.

Create the user as follows:

```bash

useradd --system goodwe

```

and modify the _/etc/udev/rules.d/98-my-usb-device.rules_ as follows:

```bash

SUBSYSTEM=="input", GROUP="input", MODE="0666"
KERNEL=="hidraw*", ATTRS{busnum}=="1", ATTRS{idVendor}=="0084", ATTRS{idProduct}=="0041", MODE="0660", GROUP="goodwe"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0084", ATTRS{idProduct}=="0041", MODE="0660", GROUP="plugdev", SYMLINK+="goodwe"

```
The following goodwe.service file shall be placed in _/etc/systemd/system/goodwe.service_.

```bash
[Unit]
Description=Goodwe USB Logger
After=basic.target

[Service]
Type=simple
User=goodwe
Group=goodwe
ExecStart=/opt/goodweusblogger/GoodWe.py foreground
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```
The program can now as usual be started by _systemctl start goodwe.service_
Systemd will run the program as the user goodwe and take care of restarting it when necessary. All logging information will be shown in the systemd logs.

## python3
Most of the information on python3 can be found above. Right now python2 is the default. If you want to use python3, replace the _#!/usr/bin/python_ at the top of _GoodWe.py_ with _#!/usr/bin/python3_, leave the rest of the line unchanged. The same change has to be made in _DaemonPy/daemonpy.py_.
