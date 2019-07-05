#!/usr/bin/python -tt
from __future__ import absolute_import
from __future__ import print_function
from daemonpy.daemon import Daemon

import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import paho.mqtt.client as mqtt
import time
import os

import GoodWeCommunicator as goodwe

millis = lambda: int(round(time.time() * 1000))

class GoodWeProcessor(object):
    def run_process(self, foreground):
        config = configparser.RawConfigParser()
        config.read('/etc/goodwe.conf')
        
        mqttserver = config.get("mqtt", "server", fallback="localhost")
        mqttport = config.getint("mqtt", "port", fallback=1883)
        mqtttopic = config.get("mqtt", "topic", fallback="goodwe")
        mqttclientid = config.get("mqtt", "clientid", fallback="goodwe-usb")
        mqttusername = config.get("mqtt", "username", fallback="")
        mqttpasswd = config.get("mqtt", "password", fallback=None) 

        
        loglevel = config.get("inverter", "loglevel", fallback="INFO")
        interval = config.getint("inverter", "pollinterval", fallback=2500)
        vendorId = config.get("inverter", "vendorId", fallback="0084")
        modelId = config.get("inverter", "modelId", fallback="0041")
        
        logfile = config.get("inverter", "logfile", fallback="/var/log/goodwe.log")

        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        
        # If we are running in the foreground we use stderr for logging, if running as forking daemon we use the logfile            
        if (foreground):
            logging.basicConfig(format='%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s', stream=sys.stderr, level=numeric_level)
        else:
            logging.basicConfig(format='%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s', filename=logfile, level=numeric_level)
        
        try:
            client = mqtt.Client(mqttclientid)
            if mqttusername != "":
                client.username_pw_set(mqttusername, mqttpasswd);
                logging.debug("Set username -%s-, password -%s-", mqttusername, mqttpasswd)
            client.connect(mqttserver,port=mqttport )
            client.loop_start()
        except Exception as e:
            logging.error("%s:%s: %s",mqttserver, mqttport, e)
            return 3

        logging.info('Connected to MQTT %s:%s', mqttserver, mqttport)
        
        self.gw = goodwe.GoodWeCommunicator(logging, vendorId, modelId)

        lastUpdate = millis()

        while True:
            try:
                self.gw.handle()

                if (millis() - lastUpdate) > interval:

                    inverter = self.gw.getInverter()
                    
                    if inverter.addressConfirmed:

                        combinedtopic = mqtttopic + '/' + inverter.serial

                        if inverter.isOnline:
                            datagram = inverter.toJSON()
                            logging.debug('Publishing telegram to MQTT on channel ' + combinedtopic + '/data')
                            client.publish(combinedtopic + '/data', datagram)
                            logging.debug('Publishing 1 to MQTT on channel ' + combinedtopic + '/online')
                            client.publish(combinedtopic + '/online', 1)
                        else:
                            logging.debug('Publishing 0 to MQTT on channel ' + combinedtopic + '/online')
                            client.publish(combinedtopic + '/online', 0)
                        
                    lastUpdate = millis()
                
                time.sleep(0.1)
                
            except Exception as err:
                logging.exception("Error in RUN-loop")
                break

        client.loop_stop()
        return 0

class MyDaemon(Daemon):
    def run(self):
        processor = GoodWeProcessor()
        processor.run_process(foreground=False)

    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print ("usage: %s start|stop|restart|foreground" % sys.argv[0])
        sys.exit(2)

    if 'foreground' == sys.argv[1]:
        processor = GoodWeProcessor()
        retval = processor.run_process(foreground=True)
        sys.exit(retval)

    daemon = MyDaemon('/var/run/goodwecomm.pid', '/dev/null', '/dev/null', '/dev/null')
 
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
