#!/bin/bash

if service --status-all 2>&1 | grep -Fq 'restartd'; then
    echo "Stop Restartd daemon"
    sudo service restartd stop
fi

echo "Stop application if running"
ps aux | grep '[G]oodWe.py'
sudo kill $(ps aux | grep '[G]oodWe.py' | awk '{print $2}')
