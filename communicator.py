import json

from time                   import sleep
from threading              import Thread
from websockets.sync.server import serve
from websockets.sync.client import connect

class Communicator():
    """Communicator

    Class for communications between modules.

    Messagge format:
    {
        "Destination" : "DESTINATION-NAME"
        "Sender"      : "SENDER-NAME"
        "Message"     : "MESSAGE"
    }
    If Destination is empty: invalid. Just drop the message.
    If Destination is "All": broadcast. Forward to every modules.
    """
    def __init__(self,t="server",addr="127.0.0.1",port=1025):
        """Communicator constructor

        Initializes the incoming and outgoing queues and sets the communicator
        in server or client mode.
        """
        self.name          = "Communicator"
        self.incomingQueue = list()
        self.outgoingQueue = list()
        self.address       = addr
        self.port          = port
        if t == "server" or t == "client":
            self.type = t
        else:
            self.type = None
    def run(self):
        if    self.type == "server": self.server()
        elif  self.type == "client": self.client()
        else: pass
    def server(self):
        with serve(self.parseMessage,self.addr,self.port) as s:
            s.serve_forever()
    def client(self):
        uri = f'ws://{self.address}:{self.port}'
        with connect(uri) as websocket:
            while True:
                while self.outgoingQueue:
                    message = self.outgoingQueue.pop(0)
                    if message["Destination"] == "Communicator" and \
                       message["Message"]     == "Stop":
                        break
                    websocket.send(json.dumps(message))
                    sleep(0.001)
                sleep(0.001)
    def parseMessage(self,websocket):
        for message in websocket:
            data = json.loads(websocket.recv())
            self.incomingQueue.append(data)