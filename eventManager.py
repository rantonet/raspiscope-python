from time            import sleep
from multiprocessing import Process
from threading       import Thread
from communicator    import Communicator

class EventManager():
    """Event Manager

    A simple event manager for modules orchestration
    """
    def __init__(self,modules=list(),*args,**kargs):
        """Event Manager Constructor

        Initializes the Event Manager
        """
        self.name         = "EventManager"
        self.communicator = Communicator("server")
        if not modules:
            self.modules = list()
        else:
            self.modules = modules
        self.runningModules = list()
    def run(self):
        t = Thread(target=self.communicator.run)
        t.start()
        sleep(0.001)
        for module in self.modules:
            self.runningModules.append(Process(target=module.run))
        for module in self.runningModules:
            print("Starting client")
            module.start()
            sleep(0.001)
        
        while True: self.route()
        
        for module in self.runningModules:
            module.terminate()
            module.join()
        self.communicator.outgoingQueue.append(
                                {
                                    "Sender"      : self.name,
                                    "Destination" : "Communicator",
                                    "Message"     : "stop"
                                }
                                            )
        t.join()
    def route(self):
        print("Routing")
        while True:
            if self.communicator.incomingQueue:
                m = self.communicator.incomingQueue.pop(0)
                for key,value in m.items():
                    print(key + " " + value)
            sleep(0.0005)
    def registerModule(self,module=None):
        if not module:
            raise ValueError("No module specified")
        #TODO: implement