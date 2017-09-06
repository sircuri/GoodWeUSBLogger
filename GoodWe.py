from __future__ import print_function
from daemonpy.daemon import Daemon

import configparser
import logging
import sys
import paho.mqtt.client as mqtt
import time
import json

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
		
		dev = config.get("inverter", "dev")
		debugMode = config.getboolean("inverter", "debug")
		interval = config.getint("inverter", "pollinterval")
		
		log.debug('Open connect to {} with: {}'.format(dev, ', '.join('{}={}'.format(key, value) for key, value in config.items())))

		try:
			client = mqtt.Client(mqttclientid);
			client.connect(mqttserver)
			client.loop_start()
		except Exception as e:
			log.error(e)
			return

		log.info('Connected to MQTT %s', mqttserver)
			
		try:
			gw = goodwe.GoodWeCommunicator(dev, debugMode)
			gw.start()
		except Exception as e:
			log.error(e)
			sys.exit ("Fout bij het openen van device %s. "  % dev)	  

		log.info('New connection opened to %s', dev)
		
		lastUpdate = millis()

		while True:
			try:
				gw.handle()

				if (millis() - lastUpdate) > interval:

					inverter = gw.getInverter()
					if inverter.isOnline:
						log.debug('Publishing telegram to MQTT')
						datagram = json.dumps(inverter.__dict__)
						client.publish(mqtttopic, datagram)
						client.publish('power/solar/online', 1)
					else:
						log.debug('Inverter offline')
						client.publish('power/solar/online', 0)
						
					lastUpdate = millis()

			except Exception as err:
				log.error(err)
				break

		client.loop_stop()
		

if __name__ == "__main__":
	daemon = MyDaemon('/var/run/goodwecomm.pid', '/dev/null', '/tmp/goodwecomm.out', '/tmp/goodwecomm.err')
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
