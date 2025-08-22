import json
import signal
from multiprocessing import Process
from threading import Thread, Event
from queue import Empty

# Import delle classi dei moduli e del caricatore di configurazione
from communicator import Communicator
from configLoader import loadConfig
from lightSource import LightSource
from cuvetteSensor import CuvetteSensor
from camera import Camera
from analysis import Analysis

# Mappatura dai nomi nel config alle classi Python
MODULE_MAP = {
    "lightSource": LightSource,
    "cuvetteSensor": CuvetteSensor,
    "camera": Camera,
    "analysis": Analysis
}

class EventManager:
    """
    Orchestrates modules by running them as separate processes
    and routing messages between them based on a central configuration file.
    """
    def __init__(self, config_path="config.json"):
        """
        Initializes the EventManager.
        """
        self.config = load_config(config_path)
        self.name = "EventManager"
        
        network_config = self.config['network']
        self.communicator = Communicator("server", name=self.name, config=network_config)
        
        self.modules = self._instantiate_modules()
        self.running_processes = []
        self._stop_event = Event()

    def _instantiate_modules(self):
        """
        Instantiates modules based on the configuration file.
        """
        instantiated_modules = []
        module_configs = self.config.get("modules", {})
        network_config = self.config.get("network", {})
        system_config = self.config.get("system", {})

        for name, mod_config in module_configs.items():
            if mod_config.get("enabled", False):
                if name in MODULE_MAP:
                    ModuleClass = MODULE_MAP[name]
                    print(f"Instantiating module: {name}")
                    # Iniezione delle dipendenze
                    module_instance = ModuleClass(
                        config=mod_config, 
                        network_config=network_config, 
                        system_config=system_config
                    )
                    instantiated_modules.append(module_instance)
                else:
                    print(f"WARNING: Module '{name}' is enabled in config but has no matching class in MODULE_MAP.")
        return instantiated_modules

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