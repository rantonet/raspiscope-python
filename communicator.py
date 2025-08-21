import json
import time
import websockets
import asyncio
from threading import RLock

class Communicator:
    """
    Class for communication between modules via WebSocket.
    Can operate in 'server' mode (used by EventManager) or 'client' mode (used by modules).
    """

    def __init__(self, comm_type="server", addr="127.0.0.1", port=1025):
        self.name = "Communicator"
        self.incomingQueue = []
        self.type = comm_type
        self.address = addr
        self.port = port
        
        # For the server: maps client names to their websocket objects
        self.clients = {}
        self.lock = RLock()

    def run(self, stop_event=None):
        """Starts the server or client in a new asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if self.type == "server":
            loop.run_until_complete(self.server(stop_event))
        elif self.type == "client":
            # The client doesn't need a stop_event here, it's managed by the module
            pass # The client is run by the module itself
        loop.close()

    async def server(self, stop_event):
        """WebSocket server logic."""
        print(f"Server listening on ws://{self.address}:{self.port}")
        async with websockets.serve(self.server_handler, self.address, self.port):
            if stop_event:
                await stop_event.wait()
            else:
                # Run forever if there is no stop event
                await asyncio.Future() 

    async def server_handler(self, websocket, path):
        """Handles connections from individual clients."""
        client_name = None
        try:
            # The first message must be a registration
            reg_message_str = await websocket.recv()
            reg_message = json.loads(reg_message_str)
            
            if reg_message.get("Message", {}).get("type") == "register":
                client_name = reg_message["Sender"]
                with self.lock:
                    self.clients[client_name] = websocket
                print(f"Client '{client_name}' connected and registered.")
                self.incomingQueue.append(reg_message_str)
            else:
                print("Connection refused: first message was not a registration.")
                return

            # Listen for subsequent messages
            async for message in websocket:
                self.incomingQueue.append(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client '{client_name}' disconnected.")
        finally:
            if client_name:
                with self.lock:
                    if client_name in self.clients:
                        del self.clients[client_name]

    def send_to(self, destination, message):
        """Sends a message to a specific recipient."""
        asyncio.run(self._async_send_to(destination, message))

    async def _async_send_to(self, destination, message):
        with self.lock:
            client_ws = self.clients.get(destination)
        if client_ws:
            try:
                await client_ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                print(f"Could not send to '{destination}': connection closed.")
        else:
            print(f"Destination '{destination}' not found.")

    def broadcast(self, message, sender):
        """Sends a message to all clients except the sender."""
        asyncio.run(self._async_broadcast(message, sender))

    async def _async_broadcast(self, message, sender):
        with self.lock:
            clients_to_send = [ws for name, ws in self.clients.items() if name != sender]
        
        if clients_to_send:
            tasks = [ws.send(message) for ws in clients_to_send]
            await asyncio.gather(*tasks, return_exceptions=True)