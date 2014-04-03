# Title: chamber
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Date: 2014-04-01
# Updated: 2014-04-01
# Description: This file contains the 'chamber' class

# A chamber object refers to a growth chamber. It contains methods for
# interacting with that chamber.

import datetime
import csv
import os
from PID import PID
import time
import u12
from multiprocessing import Process, Pipe

class chamber:

	# Initialize a chamber object
	def __init__(self, channel=0, CO2target=0, O3target=0):
		self.setChannel(channel)
		self.CO2PID = PID(*CO2PIDconst)
		self.O3PID = PID(*O3PIDconst)
		self.CO2conc = 0
		self.O3conc = 0
		self.setCO2target(CO2target)
		self.setO3target(O3target)
		self.CO2out = 0
		self.O3out = 0
		self.CO2enable = True
		self.O3enable = True
		self.parentPipe, self.childPipe = Pipe()
	
	# Set private channel and update chamberDict
	def setChannel(self, newChannel):
		self.channel = newChannel
		chamberDict[newChannel] = self
	
	# Set private target and PID target
	def setCO2target(self, newTarget):
		self.CO2target = newTarget
		self.CO2PID.setPoint(newTarget)
		
	# Set private target and PID target	
	def setO3target(self, newTarget):
		self.O3target = newTarget
		self.O3PID.setPoint(newTarget)

	# Update PID algorithm, return CO2 output
	def updateCO2PID(self, CO2conc):
		self.CO2conc = CO2conc
		if self.CO2enable:
			self.CO2out = self.CO2PID.update(self.CO2conc)
		else:
			self.CO2out = 0
		return self.CO2out
	
	# Update PID algorithm, return O3 output
	def updateO3PID(self, O3conc):
		self.O3conc = O3conc
		if self.O3enable:
			self.O3out = self.O3PID.update(self.O3conc)
		else:
			self.O3out = 0
		return self.O3out
	
	# Print CO2 output
	def outputCO2(self):
		print('Chamber %d CO2 concentration: %d CO2 output: %d' % 
			(self.channel, self.CO2conc, self.CO2out))
	
	# Launch CO2valveControl as a separate process
	def launchCO2(self):
		p = Process(target=self.CO2valveControl, args=())
		p.start()
	
	# Control loop that opens the CO2 valve for a set fraction of the cycle time
	def CO2valveControl(self):
		output = 0	# Initialize zero output
		timeout = 0	# Timeout to kill this process if parent process has ended
		while(timeout < 20):
			if self.childPipe.poll():	# Check for new value received from main loop
				output = self.childPipe.recv()	# Store value received from main loop
				timeout = 0	# Reset timeout
			else:
				timeout = timeout + 1	# Increment timeout because no input from parent
			if output < 0:	# Require 0 <= output <= 1
				output = 0
			if output > 1:
				output = 1
			onTime = output*cycleTime		# Calculate time solenoid is on
			offTime = (1-output)*cycleTime	# Calculate time solenoid is off
			if output > 0:	# Only turn on solenoid for nonzero output
				jack.eDigitalOut(self.channel,1)	# Turn on solenoid
				time.sleep(onTime)				# Wait
			if output < 1:	# Only turn off solenoid for output < 1
				jack.eDigitalOut(self.channel,0)	# Turn off solenoid
				time.sleep(offTime)				# Wait
	
	# Send O3 output to device. This method is unfinished
	def outputO3(self):
		pass
	
	# Save this chamber's data to .csv file
	def saveData(self):
		subDir = 'chamber' + str(self.channel)
		path = dataDir + '/' + subDir
		makeDir(path)	# Make directory something like 'C:\Data\chamber0\'
		
		now = datetime.datetime.now()
		date = now.date().isoformat()	# Create ISO-formatted date string
		time = now.time().isoformat()	# Create ISO=formatted time string
		filename = date + '.csv'
			# Name file something like '2014-02-21.csv' using today's date
		
		try:
			file = open(path + '/' + filename, 'ab') # Open or create today's file as append binary
			line = [date,time,self.channel,self.CO2conc,self.CO2target,self.CO2out,
				self.O3conc,self.O3target,self.O3out]
			writer = csv.writer(file)	# Create writer object
			writer.writerow(line) # Write one line of data
			file.close()
		except IOError:
			pass