from __future__ import print_function

import time
#import pyudev
import hidrawpure as hidraw
import os, fcntl

millis = lambda: int(round(time.time() * 1000))

class GoodweInverterInformation(object):

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
		self.serialNumber = [17]	#serial number (ascii) from inverter with zero appended
		self.serial = ""
		self.address = 0		#address provided by this software
		self.addressConfirmed = False	#wether or not the address is confirmed by te inverter
		self.lastSeen = 0		#when was the inverter last seen? If not seen for 30 seconds the inverter is marked offline. 
		self.isOnline = False		#is the inverter online (see above)
		self.version = 0		#1 or 3 phase inverter

		#inverert info from inverter pdf. Updated by the inverter info command
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

class GoodWeCommunicator(object):

	BUFFERSIZE = 96
	GOODWE_COMMS_ADDRESS = 0x80		#our address
	PACKET_TIMEOUT = 500			#0.5 sec packet timeout
	OFFLINE_TIMEOUT = 30000			#30 seconds no data -> inverter offline
	DISCOVERY_INTERVAL = 10000		#10 secs between discovery 
	INFO_INTERVAL = 1000			#get inverter info every second

	def __init__(self, device, inDebug):
		self.debugMode = inDebug
		self.inputBuffer = [0] * self.BUFFERSIZE
		self.lastReceived = 0 					#timeout detection
		self.startPacketReceived = False		#start packet marker
		self.lastReceivedByte = 0				#packet start consist of 2 bytes to test. This holds the previous byte
		self.curReceivePtr = 0					#the ptr in our OutputBuffer when reading
		self.numToRead = 0						#number of bytes to read after the header is read.

		self.lastDiscoverySent = 0				#discovery needs to be sent every 10 secs. 
		self.lastInfoUpdateSent = 0				#last info update sent to the registered inverters

		self.inverter = GoodweInverterInformation()

		#open in non-blocking mode
		self.devfp = open(device, 'r+b')
		fd = self.devfp.fileno()
		flag = fcntl.fcntl(fd, fcntl.F_GETFL)
		fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NONBLOCK)
		
		self.device = hidraw.HIDRaw(self.devfp)

		
	def start(self):

		#remove registered inverter. This is usefull when restarting the ESP. The inverter still thinks it is registered
		#but self program does not know the address. The timeout is 10 minutes.
		#for cnt in range(1, 255):
		self.sendRemoveRegistration(11)
		time.sleep(1)

		print("GoodWe Communicator started.")


	def sendRemoveRegistration(self, address):
		#send out the remove address to the inverter. If the inverter is still connected it will reconnect after discovery
		self.sendData(address, 0x00, 0x02, 0)	
				

	def sendData(self, address, controlCode, functionCode, dataLength, data = None):
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

		fullBuffer = bytearray([0xCC, 0x99, len(buffer)])
		fullBuffer.extend(buffer)

		if self.debugMode:
			print("Sending data to inverter(s): ", end='')
                	for cnt in range(len(fullBuffer)):
                                self.debugPrintHex(fullBuffer[cnt])
                        print("CRC high/low: ", end='')
                        self.debugPrintHex(high)
                        self.debugPrintHex(low)
                        print(".")

		self.device.sendOutputReport(bytes(fullBuffer))
		return len(buffer) #header, data, crc


	def debugPrintHex(self, bt):
		print(hex(bt), end='')
		print(" ", end='')


	def checkIncomingData(self):
		try:
                        datstr = self.devfp.read(64)

			for data in datstr:
				incomingData = ord(data)
				if not self.startPacketReceived and (self.lastReceivedByte == 0xAA and incomingData == 0x55):
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
							#we received the data langth. keep on reading until data length is read.
							#we need to add two for the crc calculation
							self.numToRead = self.inputBuffer[4] + 2

						elif self.curReceivePtr > 5:
							self.numToRead -= 1

					if self.curReceivePtr >= 5 and self.numToRead == 0:
						#got the complete packet
						#parse it
						self.startPacketReceived = False
						self.parseIncomingData(self.curReceivePtr)

				elif not self.startPacketReceived:
					self.lastReceivedByte = incomingData #keep track of the last incoming byte so we detect the packet start

			self.lastReceived = millis()
		except IOError as e:
			if self.startPacketReceived and millis() - self.lastReceived > self.PACKET_TIMEOUT:
				#there is an open packet timeout. 
				self.startPacketReceived = False #wait for start packet again
				if self.debugMode:
					print("Comms timeout.")


	def parseIncomingData(self, incomingDataLength):
		#first check the crc
		#Data always start without the start bytes of 0xAA 0x55
		#incomingDataLength also has the crc data in it
#		if self.debugMode:
#			print("Parsing incoming data with length: ", end='')
#			self.debugPrintHex(incomingDataLength)
#			print(". ", end='')
#			self.debugPrintHex(0xAA)
#			self.debugPrintHex(0x55)
#			for cnt in range(0, incomingDataLength):
#				self.debugPrintHex(self.inputBuffer[cnt])
#			print(".", end='')
 
		crc = 0xAA + 0x55
		for cnt in range(0, incomingDataLength - 2):
			crc += self.inputBuffer[cnt]
 
		high = (crc >> 8) & 0xff
		low = crc & 0xff
 
#		if self.debugMode:
#			print("CRC received: ", end='')
#			self.debugPrintHex(self.inputBuffer[incomingDataLength - 2])
#			self.debugPrintHex(self.inputBuffer[incomingDataLength - 1])
#			print(", CRC: ", end='')
#			self.debugPrintHex(high)
#			self.debugPrintHex(low)
#			print(".")
 
		#match the crc
		if not (high == self.inputBuffer[incomingDataLength - 2] and low == self.inputBuffer[incomingDataLength - 1]):
			return
		if self.debugMode:
			print("CRC match.")
 
		#check the contorl code and function code to see what to do
		if self.inputBuffer[2] == 0x00 and self.inputBuffer[3] == 0x80:
			self.handleRegistration(self.inputBuffer[5:], 16)
		elif self.inputBuffer[2] == 0x00 and self.inputBuffer[3] == 0x81:
			self.handleRegistrationConfirmation(self.inputBuffer[0])
		elif self.inputBuffer[2] == 0x01 and self.inputBuffer[3] == 0x81:
			self.handleIncomingInformation(self.inputBuffer[0], self.inputBuffer[4], self.inputBuffer[5:])


	def handleRegistration(self, serialNumber, length):
		#check if the serialnumber isn't listed yet. If it is use that one
		#Add the serialnumber, an address and send it to the inverter
		if length != 16:
			return
 
		if self.inverter.serialNumber == serialNumber[0:16]:
			print("Already registered inverter reregistered with address: ", end='')
			print(self.inverter.address)
			#Set to unconfirmed and send out the existing address to the inverter
			self.inverter.addressConfirmed = False
			self.inverter.lastSeen = millis()
			self.sendAllocateRegisterAddress(serialNumber, self.inverter.address)
			return
 
		self.inverter.addressConfirmed = False
		self.inverter.lastSeen = millis()
		self.inverter.isDTSeries = False
		self.inverter.serialNumber = serialNumber[0:16]
		self.inverter.serial = "".join(map(chr, serialNumber[0:16]))
		self.inverter.address = 11
		if self.debugMode:
			print("New inverter found")
 
		self.sendAllocateRegisterAddress(serialNumber, self.inverter.address)
 
		 
	def sendAllocateRegisterAddress(self, serialNumber, address):
		if self.debugMode:
			print("SendAllocateRegisterAddress address: ", end='')
			print(address)
 
		#create our registrationpacket with serialnumber and address and send it over
		registerData = bytearray()
		registerData.extend(serialNumber[0:16])
		registerData.append(address)
		#need to send alloc msg
		self.sendData(0x7F, 0x00, 0x01, 17, registerData)
 

	def handleRegistrationConfirmation(self, address):
		if self.debugMode:
			print("Handling registration information for address: ", end='')
			print(address)
 
		#lookup the inverter and set it to confirmed
		if self.inverter.address == address:
			if self.debugMode:
				print("Inverter information found .", end='')
			self.inverter.addressConfirmed = True
			self.inverter.isOnline = False; #inverter is online, we first need to get its information
			self.inverter.lastSeen = millis()
 
		else:
			if self.debugMode:
				print("Error. Could not find the inverter with address: ", end='')
				print(address)
 
		#get the information straight away
		self.askInverterForInformation(True)


	def handleIncomingInformation(self, address, dataLength, data):
		if self.debugMode:
			print("Handle incoming information")
		#need to parse the information and update our struct
		#parse all pairs of two bytes and output them
		if dataLength < 44: #minimum for non dt series
			return

		#data from iniverter, online
		self.inverter.lastSeen = millis()
		if dataLength == 66:
			self.inverter.version = 3
		else:
			self.inverter.version = 1
		dtPtr = 0
		self.inverter.vpv1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		self.inverter.vpv2 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		self.inverter.ipv1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		self.inverter.ipv2 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		self.inverter.vac1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		if self.inverter.version == 3:
			self.inverter.vac2 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
			self.inverter.vac3 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
 
		self.inverter.iac1 = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
		if self.inverter.version == 3:
			self.inverter.iac2 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
			self.inverter.iac3 = self.bytesToFloat(data[dtPtr:], 10)
			dtPtr += 2
 
		self.inverter.fac1 = self.bytesToFloat(data[dtPtr:], 100)
		dtPtr += 2
		if self.inverter.version == 3:
			self.inverter.fac2 = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2
			self.inverter.fac3 = self.bytesToFloat(data[dtPtr:], 100)
			dtPtr += 2
 
		self.inverter.pac = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		self.inverter.workMode = (data[dtPtr] << 8) | (data[dtPtr + 1])
		dtPtr += 2
		self.inverter.temp = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
                errorMessage = (data[dtPtr] << 24) | (data[dtPtr + 1] << 16) | (data[dtPtr + 2] << 8) | (data[dtPtr + 3])
		self.inverter.errorMessage = [i for i, x in enumerate(reversed(bin(errorMessage))) if x == "1"]
		dtPtr += 4
		self.inverter.eTotal = self.bytes4ToFloat(data[dtPtr:], 10)
                dtPtr += 4
                self.inverter.hTotal = (data[dtPtr] << 24) | (data[dtPtr + 1] << 16) | (data[dtPtr + 2] << 8) | (data[dtPtr + 3])
		dtPtr += 4
		self.inverter.tempFault = self.bytesToFloat(data[dtPtr:], 10)
		dtPtr += 2
                self.inverter.pv1Fault = self.bytesToFloat(data[dtPtr:], 10)
                dtPtr += 2
                self.inverter.pv2Fault = self.bytesToFloat(data[dtPtr:], 10)
                dtPtr += 2
                self.inverter.line1VFault = self.bytesToFloat(data[dtPtr:], 10)
                dtPtr += 2
		if self.inverter.version == 3:
                	self.inverter.line2VFault = self.bytesToFloat(data[dtPtr:], 10)
                	dtPtr += 2
                	self.inverter.line3VFault = self.bytesToFloat(data[dtPtr:], 10)
                	dtPtr += 2
		
                self.inverter.line1FFault = self.bytesToFloat(data[dtPtr:], 100)
                dtPtr += 2
                if self.inverter.version == 3:
                        self.inverter.line2FFault = self.bytesToFloat(data[dtPtr:], 100)
                        dtPtr += 2
                        self.inverter.line3FFault = self.bytesToFloat(data[dtPtr:], 100)
                        dtPtr += 2

                self.inverter.gcfiFault = (data[dtPtr] << 8) | (data[dtPtr + 1])
                dtPtr += 2
		self.inverter.eDay = self.bytesToFloat(data[dtPtr:], 10)

		#isonline is set after first batch of data is set so readers get actual data
		self.inverter.isOnline = True

		 
	def bytesToFloat(self, bt, factor):
		#convert two byte to float and then dividing it by factor
		return float((bt[0] << 8) | bt[1]) / factor


        def bytes4ToFloat(self, bt, factor):
                #convert four byte to float and then dividing it by factor
                return float( (bt[0] << 24) | (bt[1] << 16) | (bt[2] << 8) | bt[3]) / factor


	def sendDiscovery(self):
		if not self.inverter.isOnline:
			#send out discovery for unregistered devices.
			if self.debugMode:
				print("Sending discovery")
			self.sendData(0x7F, 0x00, 0x00, 0x00)


	def checkOfflineInverter(self):
		#check inverter timeout
		if self.inverter.isOnline:
			newOnline = (millis() - self.inverter.lastSeen < self.OFFLINE_TIMEOUT)

			#check if inverter timed out
			if not newOnline and self.inverter.isOnline:
				if self.debugMode:
					print("Marking inverter @ address: ", end='')
					print(self.inverter.address)
					print("offline.")

				self.sendRemoveRegistration(self.inverter.address); #send in case the inverter thinks we are online

			self.inverter.isOnline = newOnline;


	def askInverterForInformation(self, force = False):
		if force or (self.inverter.addressConfirmed and self.inverter.isOnline):
			self.sendData(self.inverter.address, 0x01, 0x01, 0)
		else:
			if self.debugMode:
				print("Not asking inverter with address: ", end='')
				print(self.inverter.address, end='')
				print(" for information. Addressconfirmed: ", end='')
				print(self.inverter.addressConfirmed, end='')
				print(", isOnline: ", end='')
				print(self.inverter.isOnline, end='')
				print(".")


	def handle(self):
		#always check for incoming data
		self.checkIncomingData()

		#check for offline inverters
		self.checkOfflineInverter()

		#discovery every 10 secs.
		if millis() - self.lastDiscoverySent >= self.DISCOVERY_INTERVAL:
			self.sendDiscovery()
			self.lastDiscoverySent = millis()

		#ask for info update every second
		if millis() - self.lastInfoUpdateSent >= 1000:
			self.askInverterForInformation()
			self.lastInfoUpdateSent = millis()

		self.checkIncomingData()


	def getInverter(self):
		return self.inverter

