import asyncio

from communicator import Communicator

class EventManager():
    """Event Manager

    A simple event manager for modules orchestration
    """
    async def __init__(self,modules=dict(),*args,**kargs):
        """Event Manager Constructor

        Initializes the Event Manager
        """
        self.communicator = Communicator("server")
        if not modules:
            self.modules = dict()
        else:
            self.modules = modules
    async def run(self):
        while True:
            #TODO: implement
            pass
    async def registerModule(self,module=None):
        if not module:
            raise ValueError("No module specified")
        #TODO: implement