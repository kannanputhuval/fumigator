# Calibrate IRGAs
# Author: Kannan K Puthuval, University of Illinois, kputhuva@illinois.edu
# Date: 2014-09-09
# Updated:
# Description: 	This program displays the current CO2 and O3 concentrations while you
#				calibrate the analyzer.
# Dependencies: labjackpython

import fumigator
import u12
import time

CO2channel = 0		# U12 AI channel for CO2 sensor input
O3channel = 1		# U12 AI channel for O3 sensor input
sampleTime = 0.5	# Sample for n seconds

jack = u12.U12()	# Initialize first U12 found, call him jack

while True:
	# Read gas concentrations and store them in a dictionary
	concentrations = fumigator.sampleGases(jack,sampleTime,CO2channel,O3channel)
	# Print gas concentrations
	formattedOutput = (concentrations['CO2conc'],concentrations['O3conc'])
	print('CO2: %d ppm, O3: %d ppb' % formattedOutput)