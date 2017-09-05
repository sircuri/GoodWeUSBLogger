# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Required modules

* ioctl_opt

## Usage

Check with lsusb/dmesg which device is attached to the GoodWe Inverter. Use that as device in the call to the constructor.

```python
import GoodWeCommunicator as goodwe

gw = goodwe.GoodWeCommunicator('/dev/hidraw1', False)
gw.start()

while True:
    gw.handle()

```

