# Fumigation Control
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Date: 2014-02-21
# Updated: 2014-03-27
# Description: This program measures and controls the concentration of CO2 and O3 in
#	growth chambers

# To do:
#	create dialogue for chamber initialization
#	create monitor
#	create timepoints
#	tune PID
#	create SPI interface for O3 bulb dimmer

import datetime
import csv
import os
from PID import PID
import time
import u12
from multiprocessing import Process, Pipe
from dateutil import parser

jack = u12.U12()	# Initialize first LabJack U12 found, call him 'jack'
CO2channel = 0		# U12 ADC channel for CO2 sensor input
CO2mult = 400		# 400 ppm / volt
O3channel = 1		# U12 ADC channel for O3 sensor input
O3mult = 100		# 100 ppb / volt
sampleChannel = 3	# U12 IO channel for sample valve
sampleTime = 1		# Sample gases for 4 seconds
purgeTime = 1		# Purge sample lines for 4 seconds
cycleTime = 1		# Cycle CO2 solenoid every 1 seconds
chamberDict = {}	# Initialize empty dictionary of chambers
dataDir = 'FumigatorData'	# Directory for storage of .csv files
CO2PIDconst = [0.001,0.001,0.001]	# Constants for CO2 PID algorithm
O3PIDconst = [0.001,0.001,0.001]	# Constants for O3 PID algorithm

def makeDir(path): # Makes directory at path if necessary
	try:
		os.makedirs(path)
	except OSError: # Directory already exists, so do nothing
		pass

# Main loop through chambers that reads sensors, updates PID, and logs data		
def fumigate():
	while len(chamberDict) > 0:	# If no chambers, do nothing
		for chamber in chamberDict.values():	# Loop through all chambers
			jack.eDigitalOut(sampleChannel, chamber.channel)	# Sample from current chamber
			# print('Purging for %d seconds...' % purgeTime)	# debugging
			time.sleep(purgeTime)	# Purge sample lines
			# print('Sampling for %d seconds...' % sampleTime)	#debugging
			concentrations = sampleGases()	# Get gas concentrations from IRGAs	
			chamber.updateCO2PID(concentrations['CO2conc'])	# Update the CO2 PID algorithm
			chamber.updateO3PID(concentrations['O3conc'])	# Update the O3 PID algorithm
			chamber.parentPipe.send(chamber.CO2out)	# Send new CO2 output to valve controller
			# chamber.outputO3()		# Write new O3 output to device
			chamber.saveData()		# Save data to .csv file
			
# Prompt user to enter parameters for a growth chamber. This method needs work.
def enterChambers():
	timepoints = {}
	for channel in range (2):
		print('Chamber %d: enter timepoints and targets' % (channel+1))
		timepoint = enterTimepoint(len(timepoints))
			while timepoint is not False:
				CO2target = enterTarget('CO2')
				O3target = enterTarget('O3')
				timepoints[timepoint] = {'CO2':CO2target, 'O3':O3target}
				timepoint = enterTimepoint(len(timepoints))


def printError():
	print('Error. Could not understand the input.')
	time.sleep(0.5)
	
def enterTimepoint(numPoints):
	success = False
	while success is False:
		timeString = input("Enter timepoint #%d ('exit' to finish): " % (numPoints+1))
		if timeString == 'exit':
			success = True
			timepoint = False
		else:
			try:
				timepoint = dateutil.parser.parse(timeString).time()
			except ValueError:
				printError()
			except TypeError:
				printError()
			else:
				success = True
	return timepoint

def enterTarget(gas):
	success = False
	prompts = {'CO2':'Enter CO2 concentration in ppm: ', 
		'O3':'Enter O3 concentration in ppb: '}
	while success is False:
		try:
			target = float(input(prompts[gas]))
		except ValueError:
			printError()
		else:
			success = True
	return target
	
# Collect 1-second data from IRGAs until sampleTime has elapsed, then return means
def sampleGases():

	endTime = time.time() + sampleTime	# Set stop time for sampling loop 
	CO2samples = []	# List of CO2 samples
	O3samples = []	# List of O3 samples
	
	while(time.time() < endTime):	# Sample every second until stop time is reached
		voltages = jack.aiSample(2, [CO2channel, O3channel])['voltages']	# Read raw voltages
		CO2samples.append(voltages[0]*CO2mult)	# Convert to ppm CO2 and add to list
		O3samples.append(voltages[1]*O3mult)	# Convert to ppb O3 and add to list
		time.sleep(1)	# Pause for 1 second
		
	CO2conc = sum(CO2samples) / len(CO2samples)	# Calculate mean ppm CO2
	O3conc = sum(O3samples) / len(O3samples)	# Calculate mean ppb O3
	
	return {'CO2conc':CO2conc, 'O3conc':O3conc}	# Return gas concentration values			
			
# Read CO2 concentration from sensor			
def getCO2():
	CO2string = input('Enter CO2 concentration in ppm: ')	# Prompt user for now
	CO2conc = float(CO2string)
	return CO2conc

# Read O3 concentration from sensor	
def getO3():
	O3string = input('Enter O3 concentration in ppb: ')	# Prompt user for now
	O3conc = float(O3string)
	return O3conc

# A chamber object refers to a growth chamber	
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
			line = [date,time,self.channel+1,self.CO2conc,self.CO2target,self.CO2out,
				self.O3conc,self.O3target,self.O3out]
			writer = csv.writer(file)	# Create writer object
			writer.writerow(line) # Write one line of data
			file.close()
		except IOError:
			pass

if __name__ == '__main__':			
	bilbo = chamber(channel=0, CO2target=600, O3target=0)	# Create chamber for debugging
	frodo = chamber(channel=1, CO2target=600, O3target=100)	# Create chamber for debugging
	chamberDict = {0:bilbo, 1:frodo}	# List chamber objects for debugging
	bilbo.launchCO2()
	frodo.launchCO2()
	fumigate()