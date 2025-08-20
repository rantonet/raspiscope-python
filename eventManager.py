from asyncio         import sleep,run
from multiprocessing import Process
from communicator    import Communicator

class EventManager():
    """Event Manager

    A simple event manager for modules orchestration
    """
    def __init__(self,modules=list(),*args,**kargs):
        """Event Manager Constructor

        Initializes the Event Manager
        """
        self.communicator = Communicator("server")
        if not modules:
            self.modules = list()
        else:
            self.modules = modules
        self.runningModules = list()
    async def run(self):
        await self.communicator.run()
        for module in self.modules:
            print("Starting client")
            self.runningModules.append((Process(target=run,args=(module.run,))))
        for module in self.runningModules:
            module.run()
        await self.route()
        for module in self.runningModules:
            module.terminate()
            module.join()
    async def route(self):
        while True:
            if self.communicator.incomingQueue:
                print(self.communicator.incomingQueue.pop(0))
            await sleep(0.001)
    async def registerModule(self,module=None):
        if not module:
            raise ValueError("No module specified")
        #TODO: implement