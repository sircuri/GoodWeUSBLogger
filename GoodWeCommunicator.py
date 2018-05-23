from enum import Enum

import time
from pyudev import Devices, Context, Monitor, MonitorObserver
import datetime
import hidrawpure as hidraw
import os, fcntl
import logging
import json

millis = lambda: int(round(time.time() * 1000))

class IDInfo(object):

	def __init__(self):
		self.function = FC_RESID		# Function 0x82

		self.firmwareVersion = ""
		self.modelName = ""
		self.manufacturer = ""
		self.serialNumber = ""
		self.nominalVpv = 0
		self.internalVersion = ""
		self.safetyCountryCode = 0x0
		
	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
		

class SettingInfo(object):

	def __init__(self):
		self.function = FC_RESSTT		# Function 0x83
		
		self.vpvStart = 0x0
		self.tStart = 0x0
		self.vacMin = 0x0
		self.vacMax = 0x0
		self.facMin = 0x0
		self.facMax = 0x0
		
	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

	
class RunningInfo(object):

	ERRORS = []
	ERRORS.append("GFCI Device Failure")
	ERRORS.append("AC HCT Failure")
	ERRORS.append("TBD")
	ERRORS.append("DCI Consistency Failure")
	ERRORS.append("GFCI Consistency Failure")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("Utility Loss")
	ERRORS.append("Gournd I Failure")
	ERRORS.append("DC Bus High")
	ERRORS.append("Internal Version Unmatch")
	ERRORS.append("Over Temperature")
	ERRORS.append("Auto Test Failure")
	ERRORS.append("PV Over Voltage")
	ERRORS.append("Fan Failure")
	ERRORS.append("Vac Failure")
	ERRORS.append("Isolation Failure")
	ERRORS.append("DC Injection High")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("Fac Consistency Failure")
	ERRORS.append("Vac Consistency Failure")
	ERRORS.append("TBD")
	ERRORS.append("Relay Check Failure")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("TBD")
	ERRORS.append("Fac Failure")
	ERRORS.append("EEPROM R/W Failure")
	ERRORS.append("Internal Communication Failure")


	def __init__(self):
		self.function = FC_RESRUN		# Function 0x81 'Running Info List'

		self.timestamp = ""
		self.vpv1 = 0.0
		self.vpv2 = 0.0
		self.ipv1 = 0.0
		self.ipv2 = 0.0
		self.vac1 = 0.0
		self.vac2 = 0.0
		self.vac3 = 0.0
		self.iac1 = 0.0
		self.iac2 = 0.0
		self.iac3 = 0.0
		self.fac1 = 0.0
		self.fac2 = 0.0
		self.fac3 = 0.0
		self.pac = 0
		self.workMode = 0
		self.temp = 0.0
		self.errorMessage = 0
		self.eTotal = 0
		self.hTotal = 0
		self.tempFault = 0.0
		self.pv1Fault = 0.0
		self.pv2Fault = 0.0
		self.line1VFault = 0.0
		self.line2VFault = 0.0
		self.line3VFault = 0.0
		self.line1FFault = 0.0
		self.line2FFault = 0.0
		self.line3FFault = 0.0
		self.gcfiFault = 0
		self.eDay = 0.0
		
	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

		
class Inverter(object):
	
	def __init__(self):
		self.serialNumber = [17]				#serial number (ascii) from inverter with zero appended
		self.serial = ""						# serial number as string
		self.address = 0						#address provided by this software
		self.addressConfirmed = False			#wether or not the address is confirmed by te inverter
		self.lastSeen = 0						#when was the inverter last seen? If not seen for 30 seconds the inverter is marked offline. 
		self.isOnline = False					#is the inverter online (see above)
		self.inverterType = InverterType.SINGLEPHASE	#1 or 3 phase inverter
		self.runningInfo = RunningInfo()
		self.idInfo = IDInfo()
		self.settingInfo = SettingInfo()
		
	def toJSON(self):
		return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
		

class State(Enum):
	OFFLINE = 1
	CONNECTED = 2
	DISCOVER = 3
	ALLOC = 4
	ALLOC_WAIT_CONFIRM = 5
	ALLOC_ASK_INFO = 6
	ALLOC_ASK_ID = 7
	ALLOC_ASK_SETTING = 8
	RUNNING = 9

class InverterType(Enum):
	SINGLEPHASE = 1
	THREEPHASE = 3
	
# REGISTER CONTROL CODES
CC_REG 		= 0x00

# REGISTER FUNCTION CODES
FC_OFFLINE 	= 0x00
FC_REGREQ 	= 0x80
FC_ALLOCREG = 0x01
FC_ADDCONF 	= 0x81
FC_REMREG 	= 0x02
FC_REMCONF 	= 0x82

# READ CONTROL CODES
CC_READ 	= 0x01

# READ FUNCTION CODES
FC_QRYRUN 	= 0x01
FC_RESRUN 	= 0x81
FC_QRYID 	= 0x02
FC_RESID 	= 0x82
FC_QRYSTT 	= 0x03
FC_RESSTT 	= 0x83

NODATA 		= 0x00
	
class GoodWeCommunicator(object):

	BUFFERSIZE = 96
	GOODWE_COMMS_ADDRESS = 0x80		#our address
	INVERTER_COMMS_ADDRESS = 0x0B	#inverter address. We only have one inverter using USB.
	STATE_TIMEOUT = 10000			#10 seconds timeout between states
	OFFLINE_TIMEOUT = 30000			#30 seconds no data -> inverter offline
	DISCOVERY_INTERVAL = 10000		#10 secs between discovery 
	INFO_INTERVAL = 1000			#get inverter info every second
	DEFAULT_RESETWAIT = 60			#default wait time in seconds


	def __init__(self, logger):
		self.log = logger
		self.inputBuffer = [0] * self.BUFFERSIZE
		self.lastReceived = millis() 			#timeout detection
		self.startPacketReceived = False		#start packet marker
		self.lastReceivedByte = 0				#packet start consist of 2 bytes to test. This holds the previous byte
		self.curReceivePtr = 0					#the ptr in our OutputBuffer when reading
		self.numToRead = 0						#number of bytes to read after the header is read.

		self.lastDiscoverySent = 0				#discovery needs to be sent every 10 secs. 
		self.lastInfoUpdateSent = 0				#last info update sent to the registered inverters

		self.state = State.OFFLINE
		self.statetime = millis()

		self.inverter = Inverter()
		self.rawdevice = None
		self.devfp = None
		self.device = None
	
		self.lastWaitTime = 0
	
	
	def resetWait(self):
		self.log.debug('Wait %s minutes before next device poll', (self.lastWaitTime * self.lastWaitTime))
		time.sleep((self.lastWaitTime * self.lastWaitTime) * self.DEFAULT_RESETWAIT)
		if (self.lastWaitTime < 4): # max of 25 minutes wait
			self.lastWaitTime += 1
	
	
	def resetUSBDevice(self):
		self.closeDevice()
		
		self.resetWait()
		
		self.rawdevice = self.findGoodWeUSBDevice('0084', '0041')
		if self.rawdevice is None:
			self.log.error('No GoodWe Inverter found.')
			return
		
		self.log.debug('Found GoodWe Inverter at %s', self.rawdevice)
		self.lastWaitTime = 0
		
		self.lastReceived = millis()
		self.startPacketReceived = False
		self.curReceivePtr = 0
		self.numToRead = 0
		self.lastReceivedByte = 0x00
		self.inverter.runningInfo = RunningInfo()
		self.inverter.idInfo = IDInfo()
		self.inverter.settingInfo = SettingInfo()
		
		if self.openDevice():
			self.setState(State.CONNECTED)
	
	
	def findGoodWeUSBDevice(self, vendorId, modelId):
		context = Context()
		
		usb_list = [d for d in os.listdir("/dev") if d.startswith("hidraw")]
		for hidraw in usb_list:
			device = "/dev/" + hidraw

			udev = Devices.from_device_file(context, device)
			
			if udev['DEVPATH'].find(vendorId + ":" + modelId) > -1:
				return device
		
		return None
	
	
	def openDevice(self):
		try:
			#open in non-blocking mode
			self.devfp = open(self.rawdevice, 'r+b')
			fd = self.devfp.fileno()
			flag = fcntl.fcntl(fd, fcntl.F_GETFL)
			fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)
		
			self.device = hidraw.HIDRaw(self.devfp)

			self.log.debug ("Connected to %s", self.rawdevice)
			
			return True
		except Exception as e:
			self.log.error("Unable to open %s", self.rawdevice)
			return False
			

	def closeDevice(self):
		self.device = None
		if not self.devfp is None:
			try:
				self.devfp.close()
			except Exception as e:
				self.log.debug("Unable to close device: %s", e)

		self.devfp = None
		self.rawdevice = None

	def setState(self, state):
		self.state = state
		self.statetime = millis()
		

	def sendRemoveRegistration(self):
		#send out the remove address to the inverter. If the inverter is still connected it will reconnect after discovery
		self.sendData(self.INVERTER_COMMS_ADDRESS, CC_REG, FC_REMREG, NODATA)


	def sendData(self, address, controlCode, functionCode, dataLength, data = None):
		if self.devfp is None:
			return
			
		#send the header first
		buffer = bytearray([0xAA, 0x55, self.GOODWE_COMMS_ADDRESS, address, controlCode, functionCode, dataLength])
		#check if we need to write the data part and send it.
		for i in range(dataLength):
			buffer.append(data[i])
		#need to send out the crc which is the addition of all previous values.
		crc = 0
		for cnt in range(7 + dataLength):
			crc += buffer[cnt]

		#write out the high and low
		high = (crc >> 8) & 0xff
		low = crc & 0xff
		buffer.append(high)
		buffer.append(low)

		# First 3 bytes are the header bytes and length of the full USB packet.
		fullBuffer = bytearray([0xCC, 0x99, len(buffer)])
		fullBuffer.extend(buffer)

		self.log.debug("Sending data to inverter: %s", " ".join(hex(b) for b in fullBuffer))
		
		self.device.sendOutputReport(bytes(fullBuffer))
		return len(fullBuffer) #USBHeader, USBlength, header, data, crc


	def checkIncomingData(self):
		try:
			datstr = self.devfp.read(8)

			for data in datstr:
				incomingData = ord(data)
				# continuously check for GoodWe HEADER packets.
				# Some types of Inverters send out garbage all the time. The header packet is the only true marker for a meaningfull command following.
				if self.lastReceivedByte == 0xAA and incomingData == 0x55:
					#packet start received
					self.startPacketReceived = True
					self.curReceivePtr = 0
					self.numToRead = 0
					self.lastReceivedByte = 0x00 #reset last received for next packet

				elif self.startPacketReceived:
					if self.numToRead > 0 or self.curReceivePtr < 5:
						self.inputBuffer[self.curReceivePtr] = incomingData
						self.curReceivePtr += 1
						if self.curReceivePtr == 5:
							#we received the data length. keep on reading until data length is read.
							#we need to add two for the crc calculation
							self.numToRead = self.inputBuffer[4] + 2

						elif self.curReceivePtr > 5:
							self.numToRead -= 1

					if self.curReceivePtr >= 5 and self.numToRead == 0:
						#got the complete packet
						#parse it
						self.startPacketReceived = False
						self.parseIncomingData(self.curReceivePtr)

				self.lastReceivedByte = incomingData #keep track of the last incoming byte so we detect the packet start

			self.lastReceived = millis()
		except IOError as e:
			pass

	def parseIncomingData(self, incomingDataLength):
		#first check the crc
		#Data always start without the start bytes of 0xAA 0x55
		#incomingDataLength also has the crc data in it
		
		crc = 0xAA + 0x55
		for cnt in range(0, incomingDataLength - 2):
			crc += self.inputBuffer[cnt]
 
		high = (crc >> 8) & 0xff
		low = crc & 0xff
 
		#match the crc
		if not (high == self.inputBuffer[incomingDataLength - 2] and low == self.inputBuffer[incomingDataLength - 1]):
			return
		
		src = self.inputBuffer[0]
		dst = self.inputBuffer[1]
		cc = self.inputBuffer[2]
		fc = self.inputBuffer[3]
		len = self.inputBuffer[4]
		data = self.inputBuffer[5:]

		self.log.debug('|0xAA 0x55|%s|%s|%s|%s|%s|%s|OK|', hex(src),hex(dst),hex(cc),hex(fc),hex(len),' '.join(hex(b) for b in data[0:len]))
 
		#check the control code and function code to see what to do
		if cc == CC_REG and fc == FC_REMCONF:
			self.log.debug("Confirm remove device")
		elif cc == CC_REG and fc == FC_REGREQ:
			self.handleRegistration(data, 16)
		elif cc == CC_REG and fc == FC_ADDCONF:
			self.handleRegistrationConfirmation(src)
		elif cc == CC_READ and fc == FC_RESRUN:
			self.handleIncomingInformation(src, len, data)
		elif cc == CC_READ and fc == FC_RESID:
			self.handleIncomingID(src, len, data)
		elif cc == CC_READ and fc == FC_RESSTT:
			self.handleIncomingSetting(src, len, data)


	def handleRegistration(self, serialNumber, length):
		#Add the serialnumber, an address and send it to the inverter
		if length != 16:
			return
 
		self.inverter.addressConfirmed = False
		self.inverter.lastSeen = millis()
		self.inverter.isDTSeries = False
		self.inverter.serialNumber = serialNumber[0:16]
		self.inverter.serial = "".join(map(chr, serialNumber[0:16]))
		self.inverter.address = self.INVERTER_COMMS_ADDRESS
		self.log.info("New inverter found. Register address.")
 
		self.setState(State.ALLOC)
 
		 
	def sendAllocateRegisterAddress(self, serialNumber, address):
		self.log.debug("SendAllocateRegisterAddress address: %s", address)
 
		#create our registrationpacket with serialnumber and address and send it over
		registerData = bytearray()
		registerData.extend(serialNumber[0:16])
		registerData.append(address)
		#need to send alloc msg
		self.sendData(0x7F, CC_REG, FC_ALLOCREG, len(registerData), registerData)
		
		self.setState(State.ALLOC_WAIT_CONFIRM)
 

	def handleRegistrationConfirmation(self, address):
		self.log.debug("Handling registration information for address: %s", address)
 
		#lookup the inverter and set it to confirmed
		if self.inverter.address == address:
			self.log.debug("Confirmed address: %s", address)
			self.inverter.addressConfirmed = True
			self.inverter.isOnline = True #inverter is online, we first need to get its information
			self.inverter.lastSeen = millis()

			self.log.info('Inverter now online.')
 
			#get the information straight away
			self.setState(State.ALLOC_ASK_INFO)
		else:
			self.log.error("Could not find the inverter with address: %s", address)
			self.setState(State.OFFLINE)


	def handleIncomingInformation(self, address, dataLength, data):
		self.log.debug("Handle incoming information")
		if dataLength < 44:
			return

		runningInfo = RunningInfo()
		inverterType = InverterType.SINGLEPHASE
			
		if dataLength == 66:
			inverterType = InverterType.THREEPHASE

		runningInfo.timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		dtPtr = 0
		runningInfo.vpv1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.vpv2 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.ipv1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.ipv2 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.vac1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		if inverterType == InverterType.THREEPHASE:
			runningInfo.vac2 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
			runningInfo.vac3 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
 
		runningInfo.iac1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		if inverterType == InverterType.THREEPHASE:
			runningInfo.iac2 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
			runningInfo.iac3 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
 
		runningInfo.fac1 = self.bytesToFloat(data[dtPtr:], 100)
		dtPtr += 2
		if inverterType == InverterType.THREEPHASE:
			runningInfo.fac2 = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2
			runningInfo.fac3 = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2
 
		runningInfo.pac = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		runningInfo.workMode = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		runningInfo.temp = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		errorMessage = (data[dtPtr] << 24) | (data[dtPtr + 1] << 16) | (data[dtPtr + 2] << 8) | (data[dtPtr + 3])
		runningInfo.errorMessage = [i for i, x in enumerate(reversed(bin(errorMessage))) if x == "1"]
		dtPtr += 4
		runningInfo.eTotal = self.bytes4ToFloat(data[dtPtr:], 10)
		dtPtr += 4
		runningInfo.hTotal = (data[dtPtr] << 24) | (data[dtPtr + 1] << 16) | (data[dtPtr + 2] << 8) | (data[dtPtr + 3])
		dtPtr += 4
		runningInfo.tempFault = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.pv1Fault = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.pv2Fault = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		runningInfo.line1VFault = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		if inverterType == InverterType.THREEPHASE:
			runningInfo.line2VFault = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
			runningInfo.line3VFault = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
		
		runningInfo.line1FFault = self.bytesToFloat(data[dtPtr:], 100)
		dtPtr += 2
		if inverterType == InverterType.THREEPHASE:
			runningInfo.line2FFault = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2
			runningInfo.line3FFault = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2

		runningInfo.gcfiFault = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		runningInfo.eDay = self.bytesToFloat(data[dtPtr:], 10)

		self.inverter.lastSeen = millis()
		self.inverter.isOnline = True
		
		self.inverter.inverterType = inverterType
		self.inverter.runningInfo = runningInfo

		 
	def bytesToFloat(self, bt, factor):
		#convert two byte to float and then dividing it by factor
		return float((bt[0] << 8) | bt[1]) / factor


	def bytes4ToFloat(self, bt, factor):
		#convert four byte to float and then dividing it by factor
		return float( (bt[0] << 24) | (bt[1] << 16) | (bt[2] << 8) | bt[3]) / factor

		
	def handleIncomingID(self, address, dataLength, data):
		self.log.debug("Handle incoming ID")
		
		if dataLength != 64:
			self.log.debug("Wrong package. Expected 64 bytes of data.")
			return
		
		idInfo = IDInfo()
		idInfo.firmwareVersion 		= "".join(map(chr, data[0:5]))
		idInfo.modelName 			= "".join(map(chr, data[5:15]))
		idInfo.manufacturer 		= "".join(map(chr, data[15:31]))
		idInfo.serialNumber 		= "".join(map(chr, data[31:47]))
		idInfo.nominalVpv 			= "".join(map(chr, data[47:51]))
		idInfo.internalVersion 		= "".join(map(chr, data[51:63]))
		idInfo.safetyCountryCode 	= data[63]
	
		self.inverter.idInfo = idInfo

	
	def handleIncomingSetting(self, address, dataLength, data):
		self.log.debug("Handle incoming Setting")
		
		if dataLength != 12:
			self.log.debug("Wrong package. Expected 12 bytes of data.")
			return
			
		settingInfo = SettingInfo()	
		dtPtr = 0
		settingInfo.vpvStart = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		settingInfo.tStart = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		settingInfo.vacMin = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		settingInfo.vacMax = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		settingInfo.facMin = self.bytesToFloat(data[dtPtr:], 100)
		dtPtr += 2
		settingInfo.facMax = self.bytesToFloat(data[dtPtr:], 100)
		
		self.inverter.settingInfo = settingInfo

		
	def sendDiscovery(self):
		if not self.inverter.isOnline:
			#send out discovery for unregistered devices.
			self.log.debug("Sending discovery")
			self.sendData(0x7F, CC_REG, FC_OFFLINE, NODATA)


	def checkOfflineInverter(self):
		#check inverter timeout
		if self.inverter.isOnline:
			newOnline = ((millis() - self.inverter.lastSeen) < self.OFFLINE_TIMEOUT)

			#check if inverter timed out
			if not newOnline and self.inverter.isOnline:
				self.log.info("Marking inverter @ address %s offline", self.inverter.address)
				self.setState(State.OFFLINE)

			self.inverter.isOnline = newOnline
		else:
			self.setState(State.OFFLINE)


	def askInverterForInformation(self, force = False):
		if force or (self.inverter.addressConfirmed and self.inverter.isOnline):
			self.sendData(self.inverter.address, CC_READ, FC_QRYRUN, NODATA)
			self.setState(State.RUNNING)
		else:
			self.log.debug('Skip inverter %s for information. Confirmed = %s, Online = %s', self.inverter.address, self.inverter.addressConfirmed, self.inverter.isOnline)


	def askInverterForID(self):
		if self.inverter.isOnline:
			self.log.debug("askInverterForID")
			self.sendData(self.inverter.address, CC_READ, FC_QRYID, NODATA)
		else:
			self.log.debug('Skip inverter %s for ID. Online = %s', self.inverter.address, self.inverter.isOnline)
			

	def askInverterForSetting(self):
		if self.inverter.isOnline:
			self.log.debug("askInverterForSetting")
			self.sendData(self.inverter.address, CC_READ, FC_QRYSTT, NODATA)
		else:
			self.log.debug('Skip inverter %s for Settings. Online = %s', self.inverter.address, self.inverter.isOnline)
			
			
	def handle(self):
	
		# check for state timeouts
		if ((millis() - self.statetime) > self.STATE_TIMEOUT):
			if self.state == State.RUNNING:
				self.statetime = millis()
			else:
				self.log.debug("State machine time-out. Last state: %s", self.state)
				self.state = State.OFFLINE
	
		if self.state == State.OFFLINE:
			self.resetUSBDevice()
		
		elif self.state == State.CONNECTED:
			self.sendRemoveRegistration()
			self.setState(State.DISCOVER)
			time.sleep(1)
		
		else:
			self.checkIncomingData()
		
			if self.state == State.DISCOVER:
				if millis() - self.lastDiscoverySent >= self.DISCOVERY_INTERVAL:
					self.sendDiscovery()
					self.lastDiscoverySent = millis()
			
			elif self.state == State.ALLOC:
				self.sendAllocateRegisterAddress(self.inverter.serialNumber, self.inverter.address)
	 
			elif self.state == State.ALLOC_ASK_INFO:
				self.askInverterForInformation(True)
				
			elif self.state == State.ALLOC_ASK_ID:
				self.askInverterForID()
				
			elif self.state == State.ALLOC_ASK_SETTING:
				self.askInverterForSetting()

			elif self.state == State.RUNNING:
				#ask for info update every second
				if millis() - self.lastInfoUpdateSent >= 3000:
					self.askInverterForInformation()
					self.lastInfoUpdateSent = millis()
				
				#check response timeout
				self.checkOfflineInverter()

			self.checkIncomingData()


	def getInverter(self):
		return self.inverter

