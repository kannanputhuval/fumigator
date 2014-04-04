import u12

j = u12.U12()

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
