#!/bin/bash

# sudo apt-get update
installpath=$(get_octopusvariable "Octopus.Action.Package.InstallationDirectoryPath")
targetpath=$(get_octopusvariable "Application.Installation.Path")

sudo python -m pip install pyudev
sudo python -m pip install ioctl_opt
sudo python -m pip install configparser
sudo python -m pip install paho-mqtt
sudo python -m pip install enum

echo "Create installation folder $targetpath"
sudo mkdir -p "$targetpath"

echo "Purge installation folder $targetpath"
sudo rm -rf $targetpath/*

echo "Copy application from $installpath to $targetpath"
sudo cp -r $installpath/* $targetpath
echo "Add executable flag on $targetpath/GoodWe.py"
sudo chmod +x $targetpath/GoodWe.py

echo "Move ./etc/goodwe.conf to /etc"
sudo mv -f $installpath/etc/goodwe.conf /etc
