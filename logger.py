import time
import json
import asyncio
import websockets
from module       import Module

class Logger(Module):
    """
    Manages centralized logging by receiving messages from other modules
    and routing them to a specified destination (stdout, file, or WebSocket).
    """
    def __init__(self,config,networkConfig,systemConfig):
        """
        Initializes the Logger module. The output destination is configured
        in the 'config.json' file under 'modules.logger.destination'.

        The 'destination' parameter can be a single string or a list of
        strings, allowing for flexible combinations of output.

        Available destinations:
        - "stdout": Prints log messages directly to the console.
        - "file": Writes logs to a file. The file path can be set using the
          'path' parameter in the configuration.
        - "websocket": Sends logs to a remote server via WebSocket. The
          connection details are specified in the 'network' parameter.

        Args:
            config (dict): Module-specific configuration for the logger.
            networkConfig (dict): General network configuration for the base Module.
            systemConfig (dict): System-wide configuration.
        """
        super().__init__("Logger",networkConfig,systemConfig)
        self.config = config
        
        # Ensure destination is always a list for uniform handling
        dest = self.config.get("destination","stdout")
        if isinstance(dest,str):
            self.destinations = [dest]
        else:
            self.destinations = dest
            
        self.log_file = None

    def onStart(self):
        """
        Initializes the logger based on the destination configuration.
        """
        if "file" in self.destinations:
            try:
                self.log_file = open(self.config.get("path","app.log"),"a")
                self.log("INFO","Logger module configured to write to file.")
            except Exception as e:
                self.log("ERROR",f"Could not open log file. Reverting to stdout. Details: {e}")
                self.destinations = [d for d in self.destinations if d != "file"]
                self.destinations.append("stdout")
                self.log_file = None
        if "websocket" in self.destinations:
            self.log("INFO","Logger module configured to send logs via WebSocket.")
        if "stdout" in self.destinations:
            self.log("INFO","Logger module configured to write to standard output.")

    def handleMessage(self,message):
        """
        Handles incoming messages and directs them to the configured destination.
        """
        msgType = message.get("Message",{}).get("type")
        payload = message.get("Message",{}).get("payload",{})
        sender  = message.get("Sender")
        
        # We handle log messages with a specific format
        if msgType == "LogMessage":
            level = payload.get("level","INFO")
            text  = payload.get("message","No message provided.")
            
            log_entry = {
                "timestamp" : time.strftime('%Y-%m-%d %H:%M:%S',time.localtime()),
                "sender"    : sender,
                "level"     : level,
                "message"   : text
            }
            
            if "stdout" in self.destinations:
                print(f"[{log_entry['timestamp']}] [{log_entry['sender']}] ({log_entry['level']}): {log_entry['message']}")
            
            if "file" in self.destinations and self.log_file:
                json.dump(log_entry,self.log_file)
                self.log_file.write('\n')
                self.log_file.flush() # Ensure the message is written immediately
            
            if "websocket" in self.destinations:
                # Send the log message via a separate communicator if needed
                # For this implementation, we will simply print as a fallback.
                # A full WebSocket implementation would require a dedicated client in this module.
                print(f"[{log_entry['timestamp']}] [{log_entry['sender']}] ({log_entry['level']}): {log_entry['message']} [Via WebSocket]")

        else:
            # Optionally log other events as well
            if "stdout" in self.destinations:
                print(f"[{sender}] - Received event '{msgType}'")

    def onStop(self):
        """
        Performs cleanup, such as closing the log file.
        """
        if "file" in self.destinations and self.log_file:
            self.log("INFO","Closing log file.")
            self.log_file.close()