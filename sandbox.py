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