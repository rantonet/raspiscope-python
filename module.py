import json
import time
from threading import Thread, Event
from queue import Empty,Full
from communicator import Communicator

class Module:
    """
    Abstract base class for all functional modules.
    Manages client communication, lifecycle, and message handling
    using a decoupled Communicator instance.
    """
    def __init__(self, name, networkConfig, systemConfig):
        """
        Initializes the Module.

        Args:
            name (str): The unique name of the module.
            network_config (dict): Dictionary with network parameters ('address', 'port', etc.).
            system_config (dict): Dictionary with system-wide parameters.
        """
        self.name = name
        self.communicator = Communicator(commType="client", name=self.name, config=networkConfig)
        self.stop_event = Event()
        self.communicatorThread = None
        self.queueTimeout = systemConfig.get("module_message_queue_timeout_s", 0.1)

    def run(self):
        #... (invariato)
        print(f"Module '{self.name}' starting.")
        self.communicatorThread = Thread(target=self.communicator.run, args=(self.stop_event,))
        self.communicatorThread.start()

        self.onStart()
        self.mainLoop()

        self.onStop()
        if self.communicatorThread:
            self.communicatorThread.join()
        print(f"Module '{self.name}' terminated.")

    def mainLoop(self):
        """
        The main loop of the module.
        Fetches messages from the incomingQueue and handles them.
        """
        while not self.stop_event.is_set():
            try:
                message = self.communicator.incomingQueue.get(block=True, timeout=self.queueTimeout)

                if message.get("Message", {}).get("type") == "Stop":
                    print(f"Module '{self.name}' received stop signal.")
                    self.stop_event.set()
                    break

                self.handleMessage(message)
                self.communicator.incomingQueue.task_done()

            except Empty:
                continue

    def sendMessage(self, destination, msgType, payload=None):
        """
        Sends a message to the EventManager server via the outgoingQueue.
        This method is thread-safe.
        """
        message = {
            "Sender": self.name,
            "Destination": destination,
            "Message": {
                "type": msgType,
                "payload": payload if payload is not None else {}
            }
        }
        try:
            self.communicator.outgoingQueue.put(message)
        except Full:
            pass

    # --- Methods to be overridden in child classes ---

    def onStart(self):
        """
        Called once when the module starts.
        Useful for initializing hardware, etc.
        """
        pass

    def handleMessage(self, message):
        """
        Called whenever a message arrives from the server.
        Module-specific logic goes here.
        """
        pass

    def onStop(self):
        """
        Called before the module terminates.
        Useful for cleaning up resources (e.g., GPIO pins, files).
        """
        pass