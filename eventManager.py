# eventManager.py
import json
import signal
from multiprocessing import Process
from threading import Thread, Event
from queue import Empty
from communicator import Communicator

class EventManager:
    """
    Orchestrates modules by running them as separate processes
    and routing messages between them.
    """
    def __init__(self, modules=None):
        """
        Initializes the EventManager.

        Args:
            modules (list, optional): A list of module instances to run. Defaults to None.
        """
        self.name = "EventManager"
        self.communicator = Communicator("server", name=self.name)
        self.modules = modules if modules else []
        self.running_processes = []
        self._stop_event = Event()

    def run(self):
        """Starts the communication server and all module processes."""
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        comm_thread = Thread(target=self.communicator.run, args=(self._stop_event,))
        comm_thread.start()

        for module in self.modules:
            process = Process(target=module.run)
            process.daemon = True
            self.running_processes.append({'process': process, 'name': module.name})

        for p_info in self.running_processes:
            print(f'Starting {p_info["name"]}')
            p_info['process'].start()

        print("EventManager running. Press Ctrl+C to exit.")
        try:
            while not self._stop_event.is_set():
                self.route()
        finally:
            self._cleanup()
            comm_thread.join()
            print("EventManager terminated.")

    def route(self):
        """Pops messages from the queue and routes them."""
        try:
            message = self.communicator.incomingQueue.get(timeout=0.1)
            destination = message.get("Destination")
            sender = message.get("Sender")

            if message.get("Message", {}).get("type") == "register":
                print(f"Client registration handled: {sender}")
                return # Registration is handled by the Communicator

            if destination == "EventManager":
                # Handle commands for the EventManager here
                print(f"Command received for EventManager from {sender}")
            else:
                # Put into the outgoing queue for sending
                # The tuple (destination, message) is interpreted by the server's consumer
                print(f"Routing message from {sender} to {destination}")
                self.communicator.outgoingQueue.put((destination, message))

        except Empty:
            return # No message, continue
        except (AttributeError, TypeError) as e:
            print(f"Error while routing message: {e} - Message: {message}")

    def _handle_shutdown(self, signum, frame):
        """Handles interruption signals (e.g., Ctrl+C)."""
        print(f"\nShutdown signal received ({signum}). Initiating termination...")
        self._stop_event.set()

    def _cleanup(self):
        """Cleans up resources and terminates module processes."""
        print("Sending stop signal to all modules...")
        stop_message = {
            "Sender": self.name,
            "Destination": "All",
            "Message": {"type": "Stop"}
        }
        self.communicator.outgoingQueue.put(("All", stop_message))
        
        print("Terminating module processes...")
        for p_info in self.running_processes:
            if p_info['process'].is_alive():
                p_info['process'].terminate()
                p_info['process'].join(timeout=1)
                print(f"Process {p_info['name']} terminated.")