#!/bin/bash

targetpath=/opt/goodweusblogger

echo "Create installation folder $targetpath"
sudo mkdir -p "$targetpath"

echo "Purge installation folder $targetpath"
sudo rm -rf $targetpath/*

echo "Copy application to $targetpath"
sudo cp -r * $targetpath
echo "Add executable flag on $targetpath/GoodWe.py"
sudo chmod +x $targetpath/GoodWe.py

echo "Move ./etc/goodwe.conf to /etc"
sudo cp -f goodwe.conf.replaced /etc/goodwe.conf
