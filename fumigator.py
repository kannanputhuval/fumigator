# Fumigation Control
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Updated: 2014-10-04
# Description: This program measures and controls the concentration of CO2 and O3 in
#	growth chambers
# Dependencies: labjackpython, dateutil, xml, PID, multiprocessing

# To do:
#	finish outputO3(), create interface for O3 bulb dimmer

import datetime
import csv
import os
from PID import PID
import time
import u12
from multiprocessing import Process, Pipe
from dateutil import parser
import xml.etree.ElementTree as ET

CO2channel = 0		# U12 AI channel for CO2 sensor input
CO2mult = 400		# 400 ppm / volt
O3channel = 1		# U12 AI channel for O3 sensor input
O3mult = 100		# 100 ppb / volt
sampleChannel = 8 	# U12 DIO channel for sample valve
sampleTime = 5		# Sample for n seconds
purgeTime = 10		# Purge sample lines for n seconds
cycleTime = 5		# Cycle CO2 solenoid every n seconds
dataDir = 'FumigatorData'	# Directory for storage of .csv files
configFile = 'config.xml'	# Configuration file
IOdevice = u12.U12()	# Initialize first LabJack U12 found
chamberDict = {}	# Initialize empty chamber dictionary

def main():
	# print('Launching fumigator...')
	# time.sleep(1)
	IOcheck()	# Check for connection to IOdevice
	IOdevice.watchdog(1,60,[1,1,0],[0,0,0])	# Set 60 second watchdog for IOdevice
	readChambers()
	# bilbo = chamber(jack, channel=0)	# Create chamber for debugging
	# frodo = chamber(jack, channel=1)	# Create chamber for debugging
	# chamberDict = {0:bilbo, 1:frodo}	# List chamber objects for debugging
	# enterChambers()	# Prompt user to enter timepoints for each chamber
	print('Launching fumigation...')
	# bilbo.launchCO2()	# Launch process to control CO2 delivery valve
	# frodo.launchCO2()
	fumigate()	# Launch main fumigation loop

# Main loop through chambers that reads sensors, updates PID, and logs data		
def fumigate():
	while len(chamberDict) > 0:	# If no chambers, do nothing
		for chamber in chamberDict.values():	# Loop through all chambers
			chamber.getTimepoint()	# Get current timepoint and update targets
			IOdevice.eDigitalOut(
				sampleChannel, chamber.channel, writeD=True
				)	# Sample from current chamber
			time.sleep(purgeTime)	# Purge sample lines
			concentrations = sampleGases(sampleTime,CO2channel,O3channel)# Get concentrations from IRGAs	
			chamber.updateCO2PID(concentrations['CO2conc'])	# Update the CO2 PID algorithm
			chamber.updateO3PID(concentrations['O3conc'])	# Update the O3 PID algorithm
			chamber.parentPipe.send(chamber.CO2out)	# Send new CO2 output to valve controller
			# chamber.outputO3()		# Write new O3 output to device
			chamber.saveData()		# Save data to .csv 
			formattedOutput = (
				chamber.channel+1, chamber.CO2conc, chamber.CO2target, chamber.CO2out*100
				)
			print(
				'Chamber %d CO2: %d ppm, target: %d ppm, output: %d%%' % formattedOutput
				)	# Print CO2 concentration

def makeDir(path): # Makes directory at path if necessary
	try:
		os.makedirs(path)
	except OSError: # Directory already exists, so do nothing
		pass
				
# Prompt user to enter parameters for a growth chamber.
def enterChambers():
	for chamber in chamberDict.values():
		print('Initializing chamber %d...' % (chamber.channel+1))
		time.sleep(1)
		print('Chamber %d: enter timepoints and targets' % (chamber.channel+1))
		time.sleep(0.5)
		timepoint = False
		while timepoint is False:	# Prompt for first timepoint, require at least one
			timepoint = enterTimepoint(chamber.channel,len(chamber.timepoints))
			if timepoint is False:
				print('Error: You must enter at least one timepoint.')
				time.sleep(0.5)
		while timepoint is not False:	# Prompt for timepoints until user types 'exit'
			CO2target = enterTarget(timepoint,'CO2')
			# O3target = enterTarget('O3')
			O3target = 0	# No O3 fumigation yet, so do not prompt
			chamber.timepoints[timepoint]['CO2'] = CO2target
			chamber.timepoints[timepoint]['O3'] = O3target
			timepoint = enterTimepoint(
				chamber.channel,len(chamber.timepoints)
				)	# Prompt for next timepoint


def printError():
	print('Error: Could not understand the input.')
	time.sleep(0.5)
	
# Prompt for timepoint and check validity. Return valid timepoint or False to exit.
def enterTimepoint(channel,numPoints):
	success = False	# True when valid timepoint is entered
	while success is False:	# Loop until valid timepoint or exit command is entered
		time.sleep(0.5)
		timeString = raw_input(
			"Enter chamber %d timepoint %d ('exit' to finish): " % (channel+1,numPoints+1))
		if timeString == 'exit':	# Allow user to exit loop
			success = True
			timepoint = False
		else:
			try:	# Attempt to parse user input
				timepoint = parser.parse(timeString).time()
			except ValueError:	# Invalid input, try again
				printError()
			except TypeError:	# Invalid input, try again
				printError()
			else:
				success = True	# Valid input, return timepoint
	return timepoint

# Prompt for target concentration of CO2 or O3 and check validity
def enterTarget(timepoint,gas):
	success = False	# True when valid target is entered
	units = {'CO2':'ppm','O3':'ppb'}
	prompt = 'Enter target %s concentration at %s in %s: ' % (gas,str(timepoint),units[gas])
	while success is False:	# Loop until valid target is entered
		try:	# Attempt to parse user input
			target = float(raw_input(prompt))
		except ValueError:	# Invalid input, try again
			printError()
		else:
			success = True	# Valid input, return target
	return target
	
# Collect 1-second data from IRGAs until sampleTime has elapsed,
# then return means
def sampleGases(sampleTime,CO2channel,O3channel):

	endTime = time.time() + sampleTime	# Set stop time for sample loop 
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
			
			
# Check for connection to LabJack U12
def IOcheck():
	retry = True	# True if user wants to retry
	while retry is True:
		try:
			IOdevice.eAnalogIn(0)	# Test an analog input
			retry = False	# Test succeeded, move on without retry
		except:	# Test failed
			retryString = str(raw_input('Error: No IO device detected. Retry? (y): '))
			if retryString == 'y' or retryString == 'Y':
				retry = True
			else:
				retry = False
				print('No IO device. Exiting...')
				time.sleep(3)
				exit()
				
# Read chambers from the associated config file
def readChambers():
	tree = ET.parse(configFile)
	root = tree.getroot()
	chambers = root.findall('chamber')
	for chamberElement in chambers:
		channel = int(chamberElement.find('channel').text)
		chamberDict[channel] = chamber(configFile, channel)
		
# A chamber object refers to a growth chamber	
class chamber:

	# Initialize a chamber object
	def __init__(self, configFile, channel=0):
		self.configFile = configFile
		self.IOdevice = IOdevice
		self.channel = channel
		self.readParams()
		self.readTimepoints()
		self.CO2PID = PID()
		self.O3PID = PID()
		self.CO2conc = 0
		self.O3conc = 0
		self.CO2out = 0
		self.O3out = 0
		self.CO2enable = True
		self.O3enable = True
		self.parentPipe, self.childPipe = Pipe()
		
	# Get the current timepoint and set targets
	def getTimepoint(self):
		for type in self.timepoints.keys():
			times = sorted(self.timepoints[type].keys())
			now = datetime.datetime.now().time()
			i = 0
			newTime = times[i]
			while i < len(times) and now > times[i]:
				newTime = times[i]
				i += 1
		return newTime
	
	# Set private channel and update chamberDict
	# def setChannel(self, newChannel):
		# self.channel = newChannel
		# chamberDict[newChannel] = self
	
	# # Set private target and PID target
	# def setCO2target(self, newTarget):
		# self.CO2target = newTarget
		# self.CO2PID.setTarget(newTarget)
		
	# # Set private target and PID target	
	# def setO3target(self, newTarget):
		# self.O3target = newTarget
		# self.O3PID.setTarget(newTarget)

	# Update PID algorithm, return CO2 output
	def updateCO2PID(self, CO2conc):
		self.CO2conc = CO2conc
		if self.CO2enable:
			self.readTimepoints()
			self.readParams()
			self.CO2target = self.timepoints['CO2'][self.getTimepoint()]
			self.CO2PID.setParams(
				self.CO2target, self.params['CO2']['kP'], self.params['CO2']['kI'],
				self.params['CO2']['kD'], self.params['CO2']['outMin'], self.params['CO2']['outMax']
				)
			self.CO2out = self.CO2PID.update(self.CO2conc)
		else:
			self.CO2out = 0
		return self.CO2out
	
	# Update PID algorithm, return O3 output
	def updateO3PID(self, O3conc):
		self.O3conc = O3conc
		if self.O3enable:
			self.readTimepoints()
			self.readParams()
			self.O3target = self.timepoints['O3'][self.getTimepoint()]
			self.O3PID.setParams(
				self.O3target, self.params['O3']['kP'], self.params['O3']['kI'],
				self.params['O3']['kD'],self.params['O3']['outMin'], self.params['O3']['outMax']
				)
			self.O3out = self.O3PID.update(self.O3conc)
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
				self.IOdevice.eDigitalOut(self.channel,1,writeD=True)	# Turn on solenoid
				time.sleep(onTime)				# Wait
			if output < 1:	# Only turn off solenoid for output < 1
				self.IOdevice.eDigitalOut(self.channel,0,writeD=True)	# Turn off solenoid
				time.sleep(offTime)				# Wait
	
	# Send O3 output to device. This method is unfinished
	def outputO3(self):
		pass
	
	# Save this chamber's data to .csv file
	def saveData(self):
		homeDir = os.path.expanduser('~')
		subDir = 'chamber' + str(self.channel + 1)
		path = homeDir + '/' + dataDir + '/' + subDir
		makeDir(path)	# Make directory something like 'C:\Data\chamber1\'
		
		now = datetime.datetime.now()
		date = now.date().isoformat()	# Create ISO-formatted date string
		time = now.time().isoformat()	# Create ISO=formatted time string
		filename = date + '.csv'
			# Name file something like '2014-02-21.csv' using today's date
		
		try:
			file = open(path + '/' + filename, 'ab') # Open or create today's file as append binary
			line = [
				date,time,self.channel+1,self.CO2conc,self.CO2target,self.CO2out,self.O3conc,
				self.O3target,self.O3out
				]
			writer = csv.writer(file)	# Create writer object
			writer.writerow(line) # Write one line of data
			file.close()
		except IOError:
			print('Error: File is in use and locked by another program. Cannot write data.')
	
	# Read parameters from the associated config file
	def readParams(self):
		tree = ET.parse(self.configFile)
		root = tree.getroot()
		# Iterate over all chambers
		for chamber in root.findall('chamber'):
			# Select chamber with correct channel
			if int(chamber.find('channel').text) == self.channel:
				self.params = {}
				# Iterate over all processes
				for process in chamber.findall('process'):
					type = process.find('type').text
					self.params[type] = {}
					self.params[type]['kP'] = float(process.find('kP').text)
					self.params[type]['kI'] = float(process.find('kI').text)
					self.params[type]['kD'] = float(process.find('kD').text)
					self.params[type]['outMin'] = float(process.find('outMin').text)
					self.params[type]['outMax'] = float(process.find('outMax').text)
	
	# Read timepoints from the associated config file
	def readTimepoints(self):
		tree = ET.parse(self.configFile)
		root = tree.getroot()
		# Iterate over all chambers
		for chamber in root.findall('chamber'):
			# Select chamber with correct channel
			if int(chamber.find('channel').text) == self.channel:
				self.timepoints = {}
				# Iterate over all processes
				for process in chamber.findall('process'):
					type = process.find('type').text
					self.timepoints[type] = {}
					# Iterate over all timepoints
					for timepoint in process.findall('timepoint'):
						time = parser.parse(timepoint.find('time').text).time()
						target = float(timepoint.find('target').text)
						self.timepoints[type][time] = target

if __name__ == '__main__':
	main()