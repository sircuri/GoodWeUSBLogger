#!/bin/bash

# sudo apt-get update
installpath=$(get_octopusvariable "Octopus.Action.Package.InstallationDirectoryPath")

sudo python -m pip install pyudev
sudo python -m pip install ioctl_opt
sudo python -m pip install configparser
sudo python -m pip install paho-mqtt
sudo python -m pip install enum

echo "Remove symlink if previously created"
if [ -e ~/octopus ]; then
  rm -rf ~/octopus
fi

echo "Make 'GoodWe.py' script executable"
chmod +x "${installpath}/GoodWe.py"
echo "Make symlink from ${installpath} to ~/octopus"
ln -s "${installpath}" ~/octopus
