# PID controller
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Updated: 2014-10-03
# Description: This provides an implementation of PID control.
# Dependencies: xml

# To do
#	handle scheduling

import xml.etree.ElementTree as ET

class PID:

	def __init__(self,target=0,kP=0,kI=0,kD=0,outMin=0,outMax=1):	
	
		self.target = target
		self.kP = kP
		self.kI = kI
		self.kD = kD
		self.outMin = outMin
		self.outMax = outMax
		self.lastInput = 0
		self.I = 0
		self.error = 0
		self.output = 0

	def update(self,input):
	
		# Calculate current error
		self.error = input - self.target
		
		# Calculate proportional term
		self.P = self.kP * self.error
		
		# Calculate integral only if output is in bounds
		if self.output > self.outMin and self.output < self.outMax:
			self.I = self.I + self.kI*self.error
			
		# Calculate derivative term
		self.D = self.kD * ( input - self.lastInput)
		
		# Save this input for next iteration
		self.lastInput = input
		
		# Calculate output bounded by min and max
		self.output = self.P + self.I + self.D
		if self.output > self.outMax:
			self.output = self.outMax
		elif self.output < self.outMin:
			self.output = self.outMin

		return self.output

	def setTarget(self,target):
		self.target = target
		
	def setParams(self, target=0, kP=0, kI=0, kD=0, outMin=0, outMax=1):
		
		self.target = target
		self.kP = kP
		self.kI = kI
		self.kD = kD
		self.outMin = outMin
		self.outMax = outMax