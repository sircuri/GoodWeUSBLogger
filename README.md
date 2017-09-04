# GoodWeUSBLogger
Python based logger for GoodWe inverters using USB.

based on: https://github.com/jantenhove/GoodWeLogger

## Required modules

* ioctl_opt

## Usage

```python
import hidrawpure as hidraw

gw = goodwe.GoodWeCommunicator('/dev/hidraw1', False)
gw.start()

while True:
    gw.handle()

```

