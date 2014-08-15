import signal, os

def handler(signum, frame):
	print('Signal handler called with signal', signum)
	raise IOError("Couldn't open device!")
	
signal.signal(signal.SIGALRM, handler)
signal.alarm(5)

time.sleep(10)

signal.alarm(0)