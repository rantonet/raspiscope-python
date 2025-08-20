from asyncio import sleep,get_running_loop
import json

from websockets.asyncio.server import serve
from websockets.sync.client    import connect

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
    def __init__(self,t="server"):
        """Communicator constructor

        Initializes the incoming and outgoing queues and sets the communicator
        in server or client mode.
        """
        self.incomingQueue = list()
        self.outgoingQueue = list()
        if t == "server" or t == "client":
            self.type = t
        else:
            self.type = None
    async def run(self):
        if    self.type == "server": await self.server()
        elif  self.type == "client": await self.client()
        else: pass
    async def server(self):
        print("Server starting")
        stop = get_running_loop().create_future()
        async with serve(self.parseMessage, "localhost", 1025) as s:
            print("Server started")
            await stop
    async def client(self):
        print("Connecting to server")
        uri = "ws://localhost:1025"
        with connect(uri) as websocket:
            print("Connected")
            while True:
                while self.outgoingQueue:
                    print("Sending message")
                    message = self.outgoingQueue.pop(0)
                    print(message)
                    if message["Destination"] == "Communicator" and \
                       message["Message"]     == "Stop":
                        break
                    websocket.send()
                    print("Message sent")
                    sleep(0.001)
                sleep(0.001)
    async def parseMessage(self,websocket):
        data = json.loads(await websocket.recv())
        self.incomingQueue.append(data)