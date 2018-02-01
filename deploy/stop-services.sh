#!/bin/bash

# Verify pre-conditions for deployment
stepname=$(get_octopusvariable "Application.Installation.UploadStepName")
installpath=$(get_octopusvariable "Octopus.Action[$stepname].Output.Package.InstallationDirectoryPath")
targetpath=$(get_octopusvariable "Application.Installation.Path")

echo "Stepname: $stepname"
echo "Installpath: $installpath"
echo "Targetpath: $targetpath"

if [ -z "$stepname" ] || [ -z "$installpath" ] || [ -z "$targetpath" ]
then
	fail_step "Missing some required system variables"
fi

if service --status-all 2>&1 | grep -Fq 'restartd'; then
    echo "Stop Restartd daemon"
    sudo service restartd stop
fi

echo "Stop application if running"
ps aux | grep '[G]oodWe.py'
sudo kill $(ps aux | grep '[G]oodWe.py' | awk '{print $2}')
