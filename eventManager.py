import json
import signal
from multiprocessing import Process
from threading       import Thread,Event
from queue           import Empty, Full

# Import delle classi dei moduli e del caricatore di configurazione
from communicator    import Communicator
from configLoader    import ConfigLoader  # <-- Modificato: Importa ConfigLoader
from lightSource     import LightSource
from cuvetteSensor   import CuvetteSensor
from camera          import Camera
from analysis        import Analysis

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
        config_loader     = ConfigLoader(configPath)
        self.config       = config_loader.get_config()
        
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
                    self.log("INFO",f"Instantiating module: {name}")
                    # Iniezione delle dipendenze
                    moduleInstance = ModuleClass(
                        config=modConfig,
                        networkConfig=networkConfig,
                        systemConfig=systemConfig
                    )
                    instantiatedModules.append(moduleInstance)
                else:
                    self.log("WARNING",f"Module '{name}' is enabled in config but has no matching class in MODULE_MAP.")
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
            self.log("INFO",f'Starting {pInfo["name"]}')
            pInfo['process'].start()

        self.log("INFO","EventManager running. Press Ctrl+C to exit.")
        try:
            while not self._stopEvent.is_set():
                self.route()
        finally:
            self._cleanup()
            commThread.join()
            self.log("INFO","EventManager terminated.")

    def route(self):
        """Pops messages from the queue and routes them."""
        try:
            message = self.communicator.incomingQueue.get(timeout=0.1)
            destination = message.get("Destination")
            sender = message.get("Sender")
            msg_type = message.get("Message", {}).get("type")

            if msg_type == "register":
                self.log("INFO",f"Client registration handled: {sender}")
                return  # Registration is handled by the Communicator

            if destination == "EventManager":
                if msg_type == "Stop":
                    self.log("INFO",f"Stop command received from {sender}. Initiating shutdown...")
                    self._handleShutdown(signal.SIGTERM, None)
                else:
                    # Handle other commands for the EventManager here
                    self.log("INFO",f"Command '{msg_type}' received for EventManager from {sender}")
            else:
                # Put into the outgoing queue for sending
                # The tuple (destination,message) is interpreted by the server's consumer
                self.log("INFO",f"Routing message from {sender} to {destination}")
                self.communicator.outgoingQueue.put((destination,message))

        except Empty:
            return # No message,continue
        except (AttributeError,TypeError) as e:
            self.log("ERROR",f"Error while routing message: {e} - Message: {message}")

    def _handleShutdown(self,signum,frame):
        """Handles interruption signals (e.g.,Ctrl+C)."""
        self.log("INFO",f"Shutdown signal received ({signum}). Initiating termination...")
        self._stopEvent.set()

    def _cleanup(self):
        """Cleans up resources and terminates module processes."""
        self.log("INFO","Sending stop signal to all modules...")
        stopMessage = {
            "Sender": self.name,
            "Destination": "All",
            "Message": {"type": "Stop"}
        }
        self.communicator.outgoingQueue.put(("All",stopMessage))

        self.log("INFO","Terminating module processes...")
        for pInfo in self.runningProcesses:
            if pInfo['process'].is_alive():
                pInfo['process'].terminate()
                pInfo['process'].join(timeout=1)
                self.log("INFO",f"Process {pInfo['name']} terminated.")

    def log(self,level,message):
        """
        Sends a log message to the Logger module.

        Args:
            level (str): The log level (e.g., "INFO","ERROR","DEBUG").
            message (str): The text of the log message.
        """
        payload = {
            "level"   : level,
            "message" : message
        }
        log_message = {
            "Sender"      : self.name,
            "Destination" : "Logger",
            "Message"     : {
                                "type"    : "LogMessage",
                                "payload" : payload if payload is not None else {}
                            }
        }
        try:
            self.communicator.outgoingQueue.put(("Logger",log_message))
        except Full:
            pass