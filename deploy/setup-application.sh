#!/bin/bash

# sudo apt-get update
stepname=$(get_octopusvariable "Application.Installation.UploadStepName")
installpath=$(get_octopusvariable "Octopus.Action[$stepname].Output.Package.InstallationDirectoryPath")
targetpath=$(get_octopusvariable "Application.Installation.Path")

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
