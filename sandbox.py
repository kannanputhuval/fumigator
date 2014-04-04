import datetime

timepoints = {datetime.time(6,0):'6am', datetime.time(18,0):'6pm'}

def getTimepoint():
	times = sorted(timepoints.keys())
	now = datetime.datetime.now().time()
	i = 0
	newTimepoint = times[i]
	while now > times[i] and i < len(times):
		newTimepoint = times[i]
		i += 1
	return newTimepoint