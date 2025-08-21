import json
import signal
import time
from multiprocessing import Process, Event
from threading import Thread
from communicator import Communicator

class EventManager:
    """
    Event manager for module orchestration.
    Starts all modules as separate processes and routes messages between them.
    """

    def __init__(self, modules=None):
        """
        EventManager constructor.
        Args:
            modules (list): A list of module instances to run.
        """
        self.name = "EventManager"
        self.communicator = Communicator("server")
        self.modules = modules if modules else []
        self.running_processes = []
        self._stop_event = Event()

    def run(self):
        """Starts the communication server and all module processes."""
        # Set up handlers for a clean shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        comm_thread = Thread(target=self.communicator.run, args=(self._stop_event,))
        comm_thread.start()
        time.sleep(0.1)  # Wait for the server to start

        for module in self.modules:
            process = Process(target=module.run)
            process.daemon = True  # Child processes terminate if the parent dies
            self.running_processes.append({'process': process, 'name': module.name})

        for p_info in self.running_processes:
            print(f'Starting {p_info["name"]}')
            p_info['process'].start()
            time.sleep(0.01)

        print("EventManager running. Press Ctrl+C to exit.")
        try:
            while not self._stop_event.is_set():
                self.route()
                time.sleep(0.001)
        finally:
            self._cleanup()
            comm_thread.join()
            print("EventManager shut down.")

    def route(self):
        """Pops messages from the queue and routes them."""
        if not self.communicator.incomingQueue:
            return

        message_str = self.communicator.incomingQueue.pop(0)
        try:
            message = json.loads(message_str)
            destination = message.get("Destination")
            sender = message.get("Sender")

            # Handle client registration
            if message.get("Message", {}).get("type") == "register":
                print(f"Registering client: {sender}")
                # The communicator logic now handles the name-to-websocket association
                return

            print(f"Routing message from {sender} to {destination}")

            if destination == "All":
                self.communicator.broadcast(message_str, sender)
            elif destination:
                self.communicator.send_to(destination, message_str)

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error while routing message: {e} - Message: {message_str}")

    def _handle_shutdown(self, signum, frame):
        """Handles interruption signals (e.g., Ctrl+C)."""
        print(f"\nReceived shutdown signal ({signum}). Initiating shutdown...")
        self._stop_event.set()

    def _cleanup(self):
        """Cleans up resources and terminates module processes."""
        print("Sending stop signal to all modules...")
        stop_message = json.dumps({
            "Sender": self.name,
            "Destination": "All",
            "Message": {"type": "Stop"}
        })
        self.communicator.broadcast(stop_message, self.name)
        time.sleep(1) # Give modules time to shut down

        print("Terminating module processes...")
        for p_info in self.running_processes:
            if p_info['process'].is_alive():
                p_info['process'].terminate()
                p_info['process'].join(timeout=1)
                print(f"Process {p_info['name']} terminated.")