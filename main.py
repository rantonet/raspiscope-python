from multiprocessing import Pool,Process,Pipe

c  = Camera()
cs = CuvetteSensor()
l  = LightSensor()
a  = Analisys()

e  = EventManager(c,cs,a,l)

#Main loop
eventLoop = Process(e.run())

eventLoop.run() #TODO: check this

#Termination check loop
while True:
    pass

eventLoop.join()