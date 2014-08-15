# Fumigation Control
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Date: 2014-02-21
# Updated: 2014-08-11
# Description: This program measures and controls the concentration of CO2 and O3 in
#	growth chambers
# Dependencies: labjackpython, dateutil
# To do:
#	tune PID
#	make real-time duty cycle
#	create SPI interface for O3 bulb dimmer

import datetime
import csv
import os
from PID import PID
import time
import u12
from multiprocessing import Process, Pipe
from dateutil import parser

CO2channel = 0		# U12 AI channel for CO2 sensor input
CO2mult = 400		# 400 ppm / volt
O3channel = 1		# U12 AI channel for O3 sensor input
O3mult = 100		# 100 ppb / volt
sampleChannel = 3	# U12 IO channel for sample valve
sampleTime = 15		# Sample for n seconds
purgeTime = 15		# Purge sample lines for n seconds
cycleTime = 30		# Cycle CO2 solenoid every n seconds
chamberDict = {}	# Initialize empty dictionary of chambers
dataDir = 'FumigatorData'	# Directory for storage of .csv files

# PID constants
CO2kP = 0.0001
CO2kI = 0
CO2kD = 0
O3kP = 0.0001
O3kI = 0
O3kD = 0
CO2PIDconst = [CO2kP,CO2kI,CO2kD]
O3PIDconst = [O3kP,O3kI,O3kD]

def makeDir(path): # Makes directory at path if necessary
	try:
		os.makedirs(path)
	except OSError: # Directory already exists, so do nothing
		pass

# Main loop through chambers that reads sensors, updates PID, and logs data		
def fumigate(IOdevice):
	while len(chamberDict) > 0:	# If no chambers, do nothing
		for chamber in chamberDict.values():	# Loop through all chambers
			chamber.getTimepoint()	# Get current timepoint and update targets
			IOdevice.eDigitalOut(sampleChannel, chamber.channel)	# Sample from current chamber
			# print('Purging for %d seconds...' % purgeTime)	# debugging
			time.sleep(purgeTime)	# Purge sample lines
			# print('Sampling for %d seconds...' % sampleTime)	#debugging
			concentrations = sampleGases(IOdevice)	# Get gas concentrations from IRGAs	
			chamber.updateCO2PID(concentrations['CO2conc'])	# Update the CO2 PID algorithm
			chamber.updateO3PID(concentrations['O3conc'])	# Update the O3 PID algorithm
			chamber.parentPipe.send(chamber.CO2out)	# Send new CO2 output to valve controller
			# chamber.outputO3()		# Write new O3 output to device
			chamber.saveData()		# Save data to .csv 
			formattedOutput = (chamber.channel+1, chamber.CO2conc, chamber.CO2out*100)
			print('Chamber %d CO2: %d ppm, output: %d%%' % formattedOutput)	# Print CO2 concentration
			
# Prompt user to enter parameters for a growth chamber.
def enterChambers():
	for chamber in chamberDict.values():
		print('Initializing chamber %d...' % (chamber.channel+1))
		time.sleep(1)
		print('Chamber %d: enter timepoints and targets' % (chamber.channel+1))
		time.sleep(0.5)
		timepoint = False
		while timepoint is False:	# Prompt for first timepoint, require at least one
			timepoint = enterTimepoint(len(chamber.timepoints))
			if timepoint is False:
				print('Error: You must enter at least one timepoint.')
				time.sleep(0.5)
		while timepoint is not False:	# Prompt for timepoints until user types 'exit'
			CO2target = enterTarget('CO2')
			# O3target = enterTarget('O3')
			O3target = 0	# No O3 fumigation yet, so do not prompt
			chamber.timepoints[timepoint] = {'CO2':CO2target, 'O3':O3target}	# Store timepoint
			timepoint = enterTimepoint(len(chamber.timepoints))	# Prompt for next timepoint


def printError():
	print('Error: Could not understand the input.')
	time.sleep(0.5)
	
# Prompt for timepoint and check validity. Return valid timepoint or False to exit.
def enterTimepoint(numPoints):
	success = False
	while success is False:
		time.sleep(0.5)
		timeString = raw_input("Enter timepoint #%d ('exit' to finish): " % (numPoints+1))
		if timeString == 'exit':
			success = True
			timepoint = False
		else:
			try:
				timepoint = parser.parse(timeString).time()
			except ValueError:
				printError()
			except TypeError:
				printError()
			else:
				success = True
	return timepoint

# Prompt for target concentration of CO2 or O3 and check validity
def enterTarget(gas):
	success = False
	prompts = {'CO2':'Enter CO2 concentration in ppm: ', 
		'O3':'Enter O3 concentration in ppb: '}
	while success is False:
		try:
			target = float(raw_input(prompts[gas]))
		except ValueError:
			printError()
		else:
			success = True
	return target
	
# Collect 1-second data from IRGAs until sampleTime has elapsed, then return means
def sampleGases(IOdevice):

	endTime = time.time() + sampleTime	# Set stop time for sampling loop 
	CO2samples = []	# List of CO2 samples
	O3samples = []	# List of O3 samples
	
	while(time.time() < endTime):	# Sample every second until stop time is reached
		voltages = IOdevice.aiSample(2, [CO2channel, O3channel])['voltages']	# Read raw voltages
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

# Restrict outputs between low and high
def boundOutput(output,low,high):
	if output < low:
		output = low
	if output > high:
		output = high
	return output
	
# Check for connection to LabJack U12
def IOcheck(IOdevice):
	retry = True
	while retry is True:
		try:
			IOdevice.eAnalogIn(0)	# Test an analog input
			retry = False
		except:
			retryString = str(raw_input('Error: No IO device detected. Retry? (y): '))
			if retryString == 'y' or retryString == 'Y':
				retry = True
			else:
				retry = False
				print('No IO device. Exiting...')
				time.sleep(3)
				exit()

# High-level digital output to U12
def digOut(j, channel, state):
	oldState = j.rawDIO()
	IO3toIO0DirectionsAndStates = int(oldState['IO3toIO0States'])
	if state == 1:
		mask = (1<<channel)
		IO3toIO0DirectionsAndStates = mask | IO3toIO0DirectionsAndStates
	if state == 0:
		mask = 0xFF^(1<<channel)
		IO3toIO0DirectionsAndStates = mask & IO3toIO0DirectionsAndStates
	args = [int(oldState['D15toD8Directions']), int(oldState['D7toD0Directions']), 
		int(oldState['D15toD8States']), int(oldState['D7toD0States']), 
		IO3toIO0DirectionsAndStates, True]
	j.rawDIO(*args)

# A chamber object refers to a growth chamber	
class chamber:

	# Initialize a chamber object
	def __init__(self, IOdevice, channel=0):
		self.IOdevice = IOdevice
		self.setChannel(channel)
		self.CO2PID = PID(*CO2PIDconst)
		self.O3PID = PID(*O3PIDconst)
		self.CO2conc = 0
		self.O3conc = 0
		self.setCO2target(0)
		self.setO3target(0)
		self.CO2out = 0
		self.O3out = 0
		self.CO2enable = True
		self.O3enable = True
		self.parentPipe, self.childPipe = Pipe()
		self.timepoints = {}
		
	# Get the current timepoint and set targets
	def getTimepoint(self):
		times = sorted(self.timepoints.keys())
		now = datetime.datetime.now().time()
		i = 0
		newTimepoint = times[i]
		while i < len(times) and now > times[i]:
			newTimepoint = times[i]
			i += 1
		self.setCO2target(self.timepoints[newTimepoint]['CO2'])
		self.setO3target(self.timepoints[newTimepoint]['O3'])
	
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
			self.CO2out = boundOutput(self.CO2PID.update(self.CO2conc),0,1)
		else:
			self.CO2out = 0
		return self.CO2out
	
	# Update PID algorithm, return O3 output
	def updateO3PID(self, O3conc):
		self.O3conc = O3conc
		if self.O3enable:
			self.O3out = boundOutput(self.O3PID.update(self.O3conc),0,1)
		else:
			self.O3out = 0
		return self.O3out
	
	# Print CO2 output
	def printCO2(self):
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
				self.IOdevice.eDigitalOut(self.channel,1)	# Turn on solenoid
				time.sleep(onTime)				# Wait
			if output < 1:	# Only turn off solenoid for output < 1
				self.IOdevice.eDigitalOut(self.channel,0)	# Turn off solenoid
				time.sleep(offTime)				# Wait
	
	# Send O3 output to device. This method is unfinished
	def outputO3(self):
		pass
	
	# Save this chamber's data to .csv file
	def saveData(self):
		subDir = 'chamber' + str(self.channel + 1)
		path = dataDir + '/' + subDir
		makeDir(path)	# Make directory something like 'C:\Data\chamber1\'
		
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
			print('Error: File is in use and locked by another program. Cannot write data.')

if __name__ == '__main__':
	print('Launching fumigator...')
	time.sleep(1)
	jack = u12.U12()	# Initialize first LabJack U12 found, call him 'jack'
	IOcheck(jack)	# Check for connection to jack
	bilbo = chamber(jack, channel=0)	# Create chamber for debugging
	frodo = chamber(jack, channel=1)	# Create chamber for debugging
	chamberDict = {0:bilbo, 1:frodo}	# List chamber objects for debugging
	enterChambers()	# Prompt user to enter timepoints for each chamber
	print('Launching fumigation...')
	bilbo.launchCO2()	# Launch process to control CO2 delivery valve
	frodo.launchCO2()
	fumigate(jack)	# Launch main fumigation loop using jack

