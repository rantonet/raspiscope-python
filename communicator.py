import asyncio
import json

from websockets.asyncio.server import serve
from websockets.sync.client    import connect

class Communicator():
    """Communicator

    Class for communications between modules.

    Messagge format:
    {
        "Destination" : "DESTINATION-NAME"
        "Sender"   : "SENDER-NAME"
        "Message"  : "MESSAGE"
    }
    If Destination is empty: invalid. Just drop the message.
    If Destination is "All": broadcast. Forward to every modules.
    """
    async def __init__(self,t="server"):
        """Communicator constructor

        Initializes the incoming and outgoing queues and sets the communicator
        in server or client mode.
        """
        self.incomingQueue = list()
        self.outgoingQueue = list()
        if t == "server" or self.t == "client":
            self.type = t
        else:
            self.type = None
    async def run():
        if self.type == "server":
            async with serve(self.parseMessage, "localhost", 1025) as server:
                await server.serve_forever()
        elif self.type == "client":
                uri = "ws://localhost:8765"
                with connect(uri) as websocket:
                    while True:
                        while self.outgoingQueue:
                            websocket.send(self.outgoingQueue.pop(0))
                            asyncio.sleep(0.001)
                        asyncio.sleep(0.001)
        else:
            pass
    async def parseMessage(self,websocket):
        data = json.loads(await websocket.recv())
        self.incomingQueue.append(data)