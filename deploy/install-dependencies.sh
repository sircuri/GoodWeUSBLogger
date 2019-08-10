#!/bin/bash

echo "Install Python dependencies"
sudo python -m pip install configparser paho-mqtt pyudev ioctl_opt simplejson
sudo apt-get -y install --reinstall python-enum34
