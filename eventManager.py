import json
import signal
from multiprocessing import Process
from threading import Thread,Event
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
    def __init__(self,configPath="config.json"):
        """
        Initializes the EventManager.
        """
        self.config           = loadConfig(configPath)
        self.name             = "EventManager"
        networkConfig         = self.config['network']
        self.communicator     = Communicator("server",name=self.name,config=networkConfig)
        self.modules          = self._instantiateModules()
        self.runningProcesses = []
        self._stopEvent       = Event()

    def _instantiateModules(self):
        """
        Instantiates modules based on the configuration file.
        """
        instantiatedModules = []
        moduleConfigs       = self.config.get("modules",{})
        networkConfig       = self.config.get("network",{})
        systemConfig        = self.config.get("system",{})

        for name,modConfig in moduleConfigs.items():
            if modConfig.get("enabled",False):
                if name in MODULE_MAP:
                    ModuleClass = MODULE_MAP[name]
                    print(f"Instantiating module: {name}")
                    # Iniezione delle dipendenze
                    moduleInstance = ModuleClass(
                        config=modConfig,
                        networkConfig=networkConfig,
                        systemConfig=systemConfig
                    )
                    instantiatedModules.append(moduleInstance)
                else:
                    print(f"WARNING: Module '{name}' is enabled in config but has no matching class in MODULE_MAP.")
        return instantiatedModules

    def run(self):
        """Starts the communication server and all module processes."""
        signal.signal(signal.SIGINT,self._handleShutdown)
        signal.signal(signal.SIGTERM,self._handleShutdown)

        commThread = Thread(target=self.communicator.run,args=(self._stopEvent,))
        commThread.start()

        for module in self.modules:
            process = Process(target=module.run)
            process.daemon = True
            self.runningProcesses.append({'process': process,'name': module.name})

        for pInfo in self.runningProcesses:
            print(f'Starting {pInfo["name"]}')
            pInfo['process'].start()

        print("EventManager running. Press Ctrl+C to exit.")
        try:
            while not self._stopEvent.is_set():
                self.route()
        finally:
            self._cleanup()
            commThread.join()
            print("EventManager terminated.")

    def route(self):
        """Pops messages from the queue and routes them."""
        try:
            message = self.communicator.incomingQueue.get(timeout=0.1)
            destination = message.get("Destination")
            sender = message.get("Sender")

            if message.get("Message",{}).get("type") == "register":
                print(f"Client registration handled: {sender}")
                return # Registration is handled by the Communicator

            if destination == "EventManager":
                # Handle commands for the EventManager here
                print(f"Command received for EventManager from {sender}")
            else:
                # Put into the outgoing queue for sending
                # The tuple (destination,message) is interpreted by the server's consumer
                print(f"Routing message from {sender} to {destination}")
                self.communicator.outgoingQueue.put((destination,message))

        except Empty:
            return # No message,continue
        except (AttributeError,TypeError) as e:
            print(f"Error while routing message: {e} - Message: {message}")

    def _handleShutdown(self,signum,frame):
        """Handles interruption signals (e.g.,Ctrl+C)."""
        print(f"\nShutdown signal received ({signum}). Initiating termination...")
        self._stopEvent.set()

    def _cleanup(self):
        """Cleans up resources and terminates module processes."""
        print("Sending stop signal to all modules...")
        stopMessage = {
            "Sender": self.name,
            "Destination": "All",
            "Message": {"type": "Stop"}
        }
        self.communicator.outgoingQueue.put(("All",stopMessage))

        print("Terminating module processes...")
        for pInfo in self.runningProcesses:
            if pInfo['process'].is_alive():
                pInfo['process'].terminate()
                pInfo['process'].join(timeout=1)
                print(f"Process {pInfo['name']} terminated.")