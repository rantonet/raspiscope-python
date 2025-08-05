import asyncio

from communicator import Communicator

class EventManager():
    def __init__(self,*args,**kargs):
        self.communicator = Communicator("server")
    def run(self):
        while True:
            pass