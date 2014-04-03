# Fumigator IO
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Date: 2014-02-21
# Updated: 2014-03-26
# Description: This contains input and output methods for Fumigator

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