#!/bin/bash

targetpath=/opt/goodweusblogger

echo "Install Restartd daemon"
# Prevent launch of servers during apt-get install
sudo mkdir -p /usr/sbin/
printf '%s\n%s\n' '#!/bin/bash' 'exit 101' | sudo tee -a /usr/sbin/policy-rc.d >/dev/null
sudo chmod 755 /usr/sbin/policy-rc.d

# Install daemon
sudo apt-get update && sudo apt-get -y install restartd

echo "Add config entry to /etc/restartd.conf"
restartd_cmd="goodwe \"GoodWe.py\" \"cd $targetpath; ./GoodWe.py restart\""

if grep -q "GoodWe.py" /etc/restartd.conf; then 
    sudo sed -i "/GoodWe.py/c $restartd_cmd" /etc/restartd.conf
else
    printf "\n$restart_cmd\n" | sudo tee -a /etc/restartd.conf > /dev/null
fi

echo "Start Restartd daemon"
sudo service restartd start

sudo rm -f /usr/sbin/policy-rc.d
