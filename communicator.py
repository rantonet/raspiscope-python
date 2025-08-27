# communicator.py
import json
import asyncio
import websockets
from queue import Queue,Empty,Full
from threading import RLock,Event

class Communicator:
    """
    Manages WebSocket communication for a module or the EventManager.
    It uses thread-safe queues to decouple network I/O from the main logic.
    """
    def __init__(self,commType,name,config):
        """
        Initializes the Communicator.

        Args:
            commType (str): The type of communicator,either "client" or "server".
            name (str): The name of the owner module,used for registration.
            config (dict): A dictionary containing network configuration.
                           Expected keys: 'address','port','client_reconnect_delay_s'.
        """
        self.name = name
        self.type = commType
        self.config = config
        self.uri = f"ws://{self.config['address']}:{self.config['port']}"
        
        self.incomingQueue = Queue()
        self.outgoingQueue = Queue()

        self.clients = {}
        self.lock = RLock()
        
        self.loop = None

    def run(self,stopEvent: Event):
        """Starts the main asyncio event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        if self.type == "server":
            self.loop.run_until_complete(self.startServer(stopEvent))
        else: # client
            self.loop.run_until_complete(self.startClient(stopEvent))
        
        self.loop.close()

    async def startServer(self,stopEvent: Event):
        """Starts the WebSocket server and its consumer task."""
        print(f"Server listening on {self.uri}")
        host,port = self.uri.split('//')[1].split(':')
        
        consumerTask = asyncio.create_task(self.serverConsumer(stopEvent))

        async with websockets.serve(self.serverHandler,host,int(port)):
            done,pending = await asyncio.wait([consumerTask,asyncio.create_task(stopEvent.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    async def startClient(self,stopEvent: Event):
        """Starts the WebSocket client and handles reconnection."""
        reconnectDelay = self.config.get("client_reconnect_delay_s",3)
        while not stopEvent.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    print(f"Module '{self.name}' connected to server.")
                    await self.register(websocket)
                    
                    consumerTask = asyncio.create_task(self.clientConsumer(websocket,stopEvent))
                    producerTask = asyncio.create_task(self.producer(websocket))
                    
                    done,pending = await asyncio.wait([consumerTask,asyncio.create_task(stopEvent.wait())],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
            except (ConnectionRefusedError,websockets.exceptions.ConnectionClosed) as e:
                print(f"Connection failed for '{self.name}': {e}. Retrying in {reconnectDelay} seconds...")
                await asyncio.sleep(reconnectDelay)
            except Exception as e:
                print(f"Unexpected error in client communicator: {e}")
                break
    
    async def serverHandler(self,websocket,path):
        """Handles connections from individual clients to the server."""
        clientName = None
        try:
            regMessageStr = await websocket.recv()
            regMessage = json.loads(regMessageStr)
            
            if regMessage.get("Message",{}).get("type") == "register":
                clientName = regMessage.get("Sender")
                with self.lock:
                    self.clients[clientName] = websocket
                print(f"Client '{clientName}' connected and registered.")
                try:
                    self.incomingQueue.put(regMessage) # Forward the registration message
                except Full:
                    pass
            else:
                return

            # This handler now only needs to produce messages from this client.
            # The single serverConsumer handles sending messages TO this client.
            await self.producer(websocket)

        except websockets.exceptions.ConnectionClosed:
            print(f"Client '{clientName}' disconnected.")
        finally:
            if clientName:
                with self.lock:
                    if clientName in self.clients:
                        del self.clients[clientName]

    async def producer(self,websocket):
        """Reads messages from the websocket and puts them into the incomingQueue."""
        async for messageStr in websocket:
            try:
                message = json.loads(messageStr)
                self.incomingQueue.put(message)
            except json.JSONDecodeError:
                print(f"JSON decode error: {messageStr}")
            except Full:
                pass

    async def serverConsumer(self,stopEvent: Event):
        """
        Server-specific consumer. Takes messages from the outgoingQueue 
        and dispatches them to the correct client websocket.
        """
        while not stopEvent.is_set():
            try:
                messageToSend = await self.loop.run_in_executor(
                    None,self.outgoingQueue.get,True,0.1
                )
                
                destination,messageDict = messageToSend
                
                if destination == "All":
                    await self.broadcast(messageDict)
                else:
                    targetWs = None
                    with self.lock:
                        targetWs = self.clients.get(destination)
                    
                    if targetWs:
                        try:
                            await targetWs.send(json.dumps(messageDict))
                        except websockets.exceptions.ConnectionClosed:
                            print(f"Could not send to '{destination}': connection closed.")
                    else:
                        # This can happen if a module disconnects right before a message is sent
                        pass

                self.outgoingQueue.task_done()
            except Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error in server consumer: {e}")

    async def clientConsumer(self,websocket,stopEvent: Event):
        """Client-specific consumer. Takes messages from the outgoingQueue and sends them."""
        while not stopEvent.is_set() and not websocket.closed:
            try:
                messageToSend = await self.loop.run_in_executor(
                    None,self.outgoingQueue.get,True,0.1
                )
                await websocket.send(json.dumps(messageToSend))
                self.outgoingQueue.task_done()
            except Empty:
                await asyncio.sleep(0.01) # Non-blocking wait
            except Full:
                pass
            except websockets.exceptions.ConnectionClosed:
                break

    async def register(self,websocket):
        """Sends the registration message for a client."""
        regMessage = {
            "Sender"      : self.name,
            "Destination" : "EventManager",
            "Message"     : {"type": "register"}
        }
        await websocket.send(json.dumps(regMessage))

    async def broadcast(self,messageDict):
        """Sends a message to all connected clients (server only)."""
        sender = messageDict.get("Sender")
        messageStr = json.dumps(messageDict)
        with self.lock:
            # Create a copy of the list to avoid issues if clients disconnect during iteration
            clientsToSend = [ws for name,ws in self.clients.items() if name!= sender]
        
        if clientsToSend:
            tasks = []
            await asyncio.gather(*tasks,return_exceptions=True)