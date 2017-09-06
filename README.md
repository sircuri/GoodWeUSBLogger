# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Required modules

* ioctl_opt
* configparser
* paho-mqtt

## Config

Create file '/etc/udev/rules.d/98-my-usb-device.rules':

```bash
SUBSYSTEM=="input", GROUP="input", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0084", ATTRS{idProduct}=="0041", MODE="0660", GROUP="plugdev", SYMLINK+="goodwe"
```

Create file '/etc/goodwe/goodwe.conf':

```
[inverter]
dev = /dev/goodwe 		# device name as aliased in above udev config (SYMLINK)
debug = False
pollinterval = 5000

[mqtt]
server = 192.168.x.x		# ip address of MQTT server
port = 1883
topic = power/solar/output
clientid = goodweZ
```

## Usage

Check with lsusb/dmesg which device is attached to the GoodWe Inverter. Use that as device in the call to the constructor.

```python
import GoodWeCommunicator as goodwe

gw = goodwe.GoodWeCommunicator('/dev/hidraw1', False)
gw.start()

while True:
    gw.handle()

```

