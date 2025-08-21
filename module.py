import json
import time
import asyncio
import websockets
from threading import Thread, Event

class Module:
    """
    Abstract base class for all functional modules.
    Manages client communication, lifecycle, and message handling.
    """
    def __init__(self, name, addr="127.0.0.1", port=1025):
        self.name = name
        self.communicator_uri = f"ws://{addr}:{port}"
        self.stop_event = Event()
        self.websocket = None
        self.communicator_thread = None

    def run(self):
        """
        Main entry point for the module's process.
        Starts the communicator and the module's lifecycle.
        """
        print(f"Module '{self.name}' starting.")
        self.communicator_thread = Thread(target=self.start_communicator)
        self.communicator_thread.start()

        # Wait for the connection to be established
        while not self.websocket and not self.stop_event.is_set():
            time.sleep(0.1)
        
        if self.websocket:
            self.on_start()
            self.main_loop()
        
        self.on_stop()
        if self.communicator_thread:
            self.communicator_thread.join()
        print(f"Module '{self.name}' terminated.")

    def start_communicator(self):
        """Starts the communication client in an asyncio loop."""
        asyncio.run(self.communicator_client())

    async def communicator_client(self):
        """WebSocket client logic."""
        try:
            async with websockets.connect(self.communicator_uri) as websocket:
                self.websocket = websocket
                await self.register()
                
                # Loop to receive messages
                while not self.stop_event.is_set():
                    try:
                        message_str = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        message = json.loads(message_str)
                        
                        # Special handling for the stop message
                        if message.get("Message", {}).get("type") == "Stop":
                            print(f"Module '{self.name}' received stop signal.")
                            self.stop_event.set()
                            break
                        
                        self.handle_message(message)
                    except asyncio.TimeoutError:
                        continue # No message, continue checking the stop_event
                    except json.JSONDecodeError:
                        print(f"JSON decode error in module '{self.name}'")
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"Connection failed for '{self.name}': {e}")
            self.websocket = None
            self.stop_event.set() # Stop the module if it cannot connect

    async def register(self):
        """Sends a registration message to the server."""
        reg_message = {
            "Sender": self.name,
            "Destination": "EventManager",
            "Message": {"type": "register"}
        }
        await self.websocket.send(json.dumps(reg_message))
        print(f"Module '{self.name}' registered.")

    def send_message(self, destination, msg_type, payload=None):
        """
        Sends a message to the EventManager server.
        This method can be called from a non-asyncio thread.
        """
        if not self.websocket:
            print(f"Cannot send message: '{self.name}' is not connected.")
            return

        message = {
            "Sender": self.name,
            "Destination": destination,
            "Message": {
                "type": msg_type,
                "payload": payload if payload is not None else {}
            }
        }
        # Run the send in the communicator's event loop
        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps(message)),
            asyncio.get_running_loop()
        )

    # --- Methods to be overridden in child classes ---

    def on_start(self):
        """
        Called once after the connection has been established.
        Useful for initializing hardware, etc.
        """
        pass

    def main_loop(self):
        """
        The main loop of the module.
        The default behavior is to wait for the stop event.
        Can be overridden for modules that need continuous action.
        """
        self.stop_event.wait()

    def handle_message(self, message):
        """
        Called whenever a message arrives from the server.
        Module-specific logic goes here.
        """
        pass

    def on_stop(self):
        """
        Called before the module terminates.
        Useful for cleaning up resources (e.g., GPIO pins, files).
        """
        pass