#!/usr/bin/python -tt
from daemonpy.daemon import Daemon

import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import paho.mqtt.client as mqtt
import time
import json
import os

import GoodWeCommunicator as goodwe

millis = lambda: int(round(time.time() * 1000))

class MyDaemon(Daemon):
	def run(self):
		config = configparser.RawConfigParser()
		config.read('/etc/goodwe/goodwe.conf')
		
		mqttserver = config.get("mqtt", "server")
		mqttport = config.get("mqtt", "port")
		mqtttopic = config.get("mqtt", "topic")
		mqttclientid = config.get("mqtt", "clientid")
		
		loglevel = config.get("inverter", "loglevel")
		interval = config.getint("inverter", "pollinterval")
		
		logfile = config.get("inverter", "logfile")

		numeric_level = getattr(logging, loglevel.upper(), None)
		if not isinstance(numeric_level, int):
			raise ValueError('Invalid log level: %s' % loglevel)
			
		logging.basicConfig(format='%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s', filename=logfile, level=numeric_level)
		
		try:
			client = mqtt.Client(mqttclientid);
			client.connect(mqttserver)
			client.loop_start()
		except Exception as e:
			logging.error(e)
			return

		logging.info('Connected to MQTT %s', mqttserver)
		
		self.gw = goodwe.GoodWeCommunicator(logging)

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
							logging.debug('Publishing telegram to MQTT')
							datagram = inverter.toJSON()
							client.publish(combinedtopic + '/data', datagram)
							client.publish(combinedtopic + '/online', 1)
						else:
							logging.debug('Inverter offline')
							client.publish(combinedtopic + '/online', 0)
						
					lastUpdate = millis()
				
				time.sleep(0.1)
				
			except Exception as err:
				logging.exception("Error in RUN-loop")
				break

		client.loop_stop()

	
if __name__ == "__main__":
	daemon = MyDaemon('/var/run/goodwecomm.pid', '/dev/null', '/dev/null', '/dev/null')
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
