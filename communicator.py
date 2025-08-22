# communicator.py
import json
import asyncio
import websockets
from queue     import Queue, Empty,Full
from threading import RLock, Event

class Communicator:
    """
    Manages WebSocket communication for a module or the EventManager.
    It uses thread-safe queues to decouple network I/O from the main logic.
    """
    def __init__(self, comm_type, name, config):
        """
        Initializes the Communicator.

        Args:
            comm_type (str): The type of communicator, either "client" or "server".
            name (str): The name of the owner module, used for registration.
            config (dict): A dictionary containing network configuration.
                           Expected keys: 'address', 'port', 'client_reconnect_delay_s'.
        """
        self.name = name
        self.type = comm_type
        self.config = config
        self.uri = f"ws://{self.config['address']}:{self.config['port']}"
        
        self.incomingQueue = Queue()
        self.outgoingQueue = Queue()

        self.clients = {}
        self.lock = RLock()
        
        self.loop = None

    def run(self, stop_event: Event):
        #... (il resto del metodo run rimane invariato)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        if self.type == "server":
            self.loop.run_until_complete(self.start_server(stop_event))
        else: # client
            self.loop.run_until_complete(self.start_client(stop_event))
        
        self.loop.close()

    async def start_server(self, stop_event: Event):
        #... (il resto del metodo rimane invariato)
        print(f"Server listening on {self.uri}")
        host, port = self.uri.split('//')[1].split(':')
        
        consumer_task = asyncio.create_task(self.server_consumer(stop_event))

        async with websockets.serve(self.server_handler, host, int(port)):
            done, pending = await asyncio.wait(
                [consumer_task, self.loop.create_task(stop_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    async def start_client(self, stop_event: Event):
        """Starts the WebSocket client and handles reconnection."""
        reconnect_delay = self.config.get("client_reconnect_delay_s", 3)
        while not stop_event.is_set():
            try:
                async with websockets.connect(self.uri) as websocket:
                    print(f"Module '{self.name}' connected to server.")
                    await self.register(websocket)
                    
                    consumer_task = asyncio.create_task(self.client_consumer(websocket, stop_event))
                    producer_task = asyncio.create_task(self.producer(websocket))
                    
                    done, pending = await asyncio.wait(
                        [consumer_task, producer_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
            except (ConnectionRefusedError, websockets.exceptions.ConnectionClosed) as e:
                print(f"Connection failed for '{self.name}': {e}. Retrying in {reconnect_delay} seconds...")
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                print(f"Unexpected error in client communicator: {e}")
                break
    async def server_handler(self, websocket, path):
        """Handles connections from individual clients to the server."""
        client_name = None
        try:
            reg_message_str = await websocket.recv()
            reg_message = json.loads(reg_message_str)
            
            if reg_message.get("Message", {}).get("type") == "register":
                client_name = reg_message.get("Sender")
                with self.lock:
                    self.clients[client_name] = websocket
                print(f"Client '{client_name}' connected and registered.")
                try:
                    self.incomingQueue.put(reg_message) # Forward the registration message
                except Full:
                    pass
            else:
                return

            # This handler now only needs to produce messages from this client.
            # The single server_consumer handles sending messages TO this client.
            await self.producer(websocket)

        except websockets.exceptions.ConnectionClosed:
            print(f"Client '{client_name}' disconnected.")
        finally:
            if client_name:
                with self.lock:
                    if client_name in self.clients:
                        del self.clients[client_name]

    async def producer(self, websocket):
        """Reads messages from the websocket and puts them into the incomingQueue."""
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                self.incomingQueue.put(message)
            except json.JSONDecodeError:
                print(f"JSON decode error: {message_str}")
            except Full:
                pass

    async def server_consumer(self, stop_event: Event):
        """
        Server-specific consumer. Takes messages from the outgoingQueue 
        and dispatches them to the correct client websocket.
        """
        while not stop_event.is_set():
            try:
                message_to_send = await self.loop.run_in_executor(
                    None, self.outgoingQueue.get, True, 0.1
                )
                
                destination, message_dict = message_to_send
                
                if destination == "All":
                    await self.broadcast(message_dict)
                else:
                    target_ws = None
                    with self.lock:
                        target_ws = self.clients.get(destination)
                    
                    if target_ws:
                        try:
                            await target_ws.send(json.dumps(message_dict))
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

    async def client_consumer(self, websocket, stop_event: Event):
        """Client-specific consumer. Takes messages from the outgoingQueue and sends them."""
        while not stop_event.is_set() and not websocket.closed:
            try:
                message_to_send = await self.loop.run_in_executor(
                    None, self.outgoingQueue.get, True, 0.1
                )
                await websocket.send(json.dumps(message_to_send))
                self.outgoingQueue.task_done()
            except Empty:
                await asyncio.sleep(0.01) # Non-blocking wait
            except Full:
                pass
            except websockets.exceptions.ConnectionClosed:
                break

    async def register(self, websocket):
        """Sends the registration message for a client."""
        reg_message = {
            "Sender": self.name,
            "Destination": "EventManager",
            "Message": {"type": "register"}
        }
        await websocket.send(json.dumps(reg_message))

    async def broadcast(self, message_dict):
        """Sends a message to all connected clients (server only)."""
        sender = message_dict.get("Sender")
        message_str = json.dumps(message_dict)
        with self.lock:
            # Create a copy of the list to avoid issues if clients disconnect during iteration
            clients_to_send = [ws for name, ws in self.clients.items() if name!= sender]
        
        if clients_to_send:
            tasks = [ws.send(message_str) for ws in clients_to_send]
            await asyncio.gather(*tasks, return_exceptions=True)