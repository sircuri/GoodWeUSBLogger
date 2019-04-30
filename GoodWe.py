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
import gzip

import GoodWeCommunicator as goodwe

millis = lambda: int(round(time.time() * 1000))


def logging_namer(name):
    return name + ".gz"


def logging_rotator(source, dest):
    with open(source, "rb") as sf:
        data = sf.read()
        with gzip.open(dest, "wb") as df:
            df.write(data)
    os.remove(source)


def logging_setup(level):
    formatter = logging.Formatter('%(asctime)-15s %(funcName)s(%(lineno)d) - %(levelname)s: %(message)s')

    filehandler = logging.handlers.RotatingFileHandler('/home/pi/GoodWeUSBLogger/goodwecomm.log', maxBytes=10*1024*1024,
                                                       backupCount=5)
    filehandler.setFormatter(formatter)

    stdouthandler = logging.StreamHandler(sys.stdout)
    stdouthandler.setFormatter(formatter)

    logger = logging.getLogger('main')
    logger.namer = logging_namer
    logger.rotator = logging_rotator
    logger.addHandler(filehandler)
    logger.addHandler(stdouthandler)
    logger.setLevel(logging.DEBUG)

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

        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        logging_setup(numeric_level)
        logger = logging.getLogger('main')

        try:
            client = mqtt.Client(mqttclientid)
            client.connect(mqttserver)
            client.loop_start()
        except Exception as e:
            logger.error(e)
            return

        logger.info('Connected to MQTT %s', mqttserver)

        self.gw = goodwe.GoodWeCommunicator(logger)

        lastUpdate = millis()
        lastCycle = millis()

        while True:
            try:
                self.gw.handle()

                if (millis() - lastUpdate) > interval:

                    inverter = self.gw.getInverter()

                    combinedtopic = mqtttopic + '/' + inverter.serial

                    if inverter.isOnline and self.gw.state == 9:
                        logger.debug('Publishing telegram to MQTT')
                        datagram = inverter.toJSON()  # json.dumps(inverter.__dict__)
                        client.publish(combinedtopic + '/data', datagram)
                        client.publish(combinedtopic + '/online', 1)
                    else:
                        logger.debug('Inverter offline')
                        client.publish(combinedtopic + '/online', 0)

                    lastUpdate = millis()

                time.sleep(0.1)

            except Exception as err:
                logger.exception("Error in RUN-loop")
                break

        client.loop_stop()


if __name__ == "__main__":
    daemon = MyDaemon('/var/run/goodwecomm.pid', '/dev/null', '/var/log/goodwe/comm.out', '/var/log/goodwe/comm.err')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'foreground' == sys.argv[1]:
            daemon.run()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
