<<<<<<< HEAD
from multiprocessing import Process, Pipe
import time
import u12
jack = u12.U12()

def foo(childPipe):
	bar = 0.1
	while(1):
		if childPipe.poll():
			bar = childPipe.recv()
		jack.eDigitalOut(0,1)
		time.sleep(bar)
		jack.eDigitalOut(0,0)
		time.sleep(bar)

if __name__ == '__main__':
	parentPipe, childPipe = Pipe()
	parentPipe.send(1)
	p = Process(target=foo, args=(childPipe,))
	p.start()
	# p.join()
	while(1):
		period = input('Enter period in seconds: ')
		parentPipe.send(period)
		time.sleep(4)
=======
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
>>>>>>> b9103cbd7b8a472b1cc98c2b293f238c649c927a
