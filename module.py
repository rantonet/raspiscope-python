# module.py
import json
import time
from threading import Thread, Event
from queue import Empty
from communicator import Communicator

class Module:
    """
    Abstract base class for all functional modules.
    Manages client communication, lifecycle, and message handling
    using a decoupled Communicator instance.
    """
    def __init__(self, name, addr="127.0.0.1", port=1025):
        """
        Initializes the Module.

        Args:
            name (str): The unique name of the module.
            addr (str, optional): The IP address of the EventManager. Defaults to "127.0.0.1".
            port (int, optional): The port of the EventManager. Defaults to 1025.
        """
        self.name = name
        self.communicator = Communicator(comm_type="client", name=self.name, addr=addr, port=port)
        self.stop_event = Event()
        self.communicator_thread = None

    def run(self):
        """
        Main entry point for the module's process.
        Starts the communicator and the module's lifecycle.
        """
        print(f"Module '{self.name}' starting.")
        self.communicator_thread = Thread(target=self.communicator.run, args=(self.stop_event,))
        self.communicator_thread.start()

        self.on_start()
        self.main_loop()
        
        self.on_stop()
        if self.communicator_thread:
            self.communicator_thread.join()
        print(f"Module '{self.name}' terminated.")

    def main_loop(self):
        """
        The main loop of the module.
        Fetches messages from the incomingQueue and handles them.
        """
        while not self.stop_event.is_set():
            try:
                message = self.communicator.incomingQueue.get(block=True, timeout=0.1)

                # Special handling for the stop message
                if message.get("Message", {}).get("type") == "Stop":
                    print(f"Module '{self.name}' received stop signal.")
                    self.stop_event.set()
                    break
                
                self.handle_message(message)
                self.communicator.incomingQueue.task_done()

            except Empty:
                # No message, continue checking the stop_event
                continue

    def send_message(self, destination, msg_type, payload=None):
        """
        Sends a message to the EventManager server via the outgoingQueue.
        This method is thread-safe.
        """
        message = {
            "Sender": self.name,
            "Destination": destination,
            "Message": {
                "type": msg_type,
                "payload": payload if payload is not None else {}
            }
        }
        self.communicator.outgoingQueue.put(message)

    # --- Methods to be overridden in child classes ---

    def on_start(self):
        """
        Called once when the module starts.
        Useful for initializing hardware, etc.
        """
        pass

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