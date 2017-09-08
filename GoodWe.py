#!/usr/bin/python -tt

from __future__ import print_function
from daemonpy.daemon import Daemon
from pyudev import Devices, Context, Monitor, MonitorObserver

import configparser
import logging
import sys
import paho.mqtt.client as mqtt
import time
import json
import os

import GoodWeCommunicator as goodwe

millis = lambda: int(round(time.time() * 1000))

logging.basicConfig(filename='goodwe.log', level=logging.INFO)
log = logging.getLogger(__name__)

class MyDaemon(Daemon):
	def run(self):
		config = configparser.RawConfigParser()
		config.read('/etc/goodwe/goodwe.conf')
		
		mqttserver = config.get("mqtt", "server")
		mqttport = config.get("mqtt", "port")
		mqtttopic = config.get("mqtt", "topic")
		mqttclientid = config.get("mqtt", "clientid")
		
		#self.dev = config.get("inverter", "dev")
		debugMode = config.getboolean("inverter", "debug")
		interval = config.getint("inverter", "pollinterval")
		
		self.dev = None
		
		#log.debug('Open connect to {} with: {}'.format(dev, ', '.join('{}={}'.format(key, value) for key, value in config.items())))

		try:
			client = mqtt.Client(mqttclientid);
			client.connect(mqttserver)
			client.loop_start()
		except Exception as e:
			log.error(e)
			return

		log.info('Connected to MQTT %s', mqttserver)
		
		self.context = Context()
		
		self.dev = self.findGoodWeDevice('0084', '0041')
		if self.dev is None:
			log.error('No GoodWe inverter found.')
			return
		log.info('Found GoodWe device at %s', self.dev)
		
		self.gw = goodwe.GoodWeCommunicator(self.dev, debugMode)

		self.monitor = Monitor.from_netlink(self.context)
		self.monitor.filter_by(subsystem='usb')
		self.observer = MonitorObserver(self.monitor, callback=self.add_device_event, name='monitor-observer')
		self.observer.start()		
		
		lastUpdate = millis()
		lastCycle = millis()

		while True:
			try:
				self.gw.handle()

				if (millis() - lastUpdate) > interval:

					inverter = self.gw.getInverter()
					
					if inverter.addressConfirmed:

						combinedtopic = mqtttopic + '/' + inverter.serial

						if inverter.isOnline:
							log.debug('Publishing telegram to MQTT')
							datagram = json.dumps(inverter.__dict__)
							client.publish(combinedtopic + '/data', datagram)
							client.publish(combinedtopic + '/online', 1)
						else:
							log.debug('Inverter offline')
							client.publish(combinedtopic + '/online', 0)
						
					lastUpdate = millis()
				
				time.sleep(0.1)
				
			except Exception as err:
				log.error(err)
				break

		client.loop_stop()
		self.observer.stop()	

		
	def isGoodWeDevice(self, device, vendorId, modelId):
		print(device)
		for el in device:
			print(el)
			print(device[el])
		#if "ID_VENDOR_ID" in device and "ID_MODEL_ID" in device:
		if device['DEVPATH'].find(vendorId + ":" + modelId) > -1:
			return True #device["ID_VENDOR_ID"] == vendorId and device["ID_MODEL_ID"] == modelId

		return False
	
		
	def add_device_event(self, device):
		if device.action == 'add':
			log.info('Detected new USB device %s', device['DEVNAME'])
			newdev = self.findGoodWeDevice('0084', '0041')

			if not newdev is None:
				self.dev = newdev
				log.info ('New GoodWe device at %s', self.dev)
				self.gw.setDevice(self.dev)
			else:
				log.info('Not a GoodWe device?')


	def findGoodWeDevice(self, vendorId, modelId):
		usb_list = [d for d in os.listdir("/dev") if d.startswith("hidraw")]
		for hidraw in usb_list:
			device = "/dev/" + hidraw

			udev = Devices.from_device_file(self.context, device)

			if self.isGoodWeDevice(udev, vendorId, modelId):
				return device
		
		return None

	
if __name__ == "__main__":
	daemon = MyDaemon('/var/run/goodwe/goodwecomm.pid', '/dev/null', '/var/log/goodwe/comm.out', '/var/log/goodwe/comm.err')
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		else:
			print ("Unknown command")
			sys.exit(2)
		sys.exit(0)
	else:
		print ("usage: %s start|stop|restart" % sys.argv[0])
		sys.exit(2)
