"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

import time

from threading    import Thread
from module       import Module
from configLoader import ConfigLoader

class CLI(Module):
    def __init__(self):
        configLoader = ConfigLoader(configPath)
        config       = configLoader.get_config()
        pass
    def _promptLoop(self):
        while not self.stopEvent.is_set():
            command = input("Prompt: ")
            if command == "Take picture":
                self.sendMessage("Camera","Take")
            elif command == "Make analysis":
                self.sendMessage("Camera","Analyze")
            elif command == "Calibrate camera":
                pass
            elif command == "Calibrate sensor":
                pass
    def onStart(self):
        """
        Initializes and configures the command line module.
        """
        self.sendMessage("EventManager", "Register")
        self.promptLoop = Thread(target=self._promptLoop)
        self.promptLoop.start()
    def handleMessage(self,message):
         """
        Handles incoming messages.
        """
        if not self.camera:
            self.log("WARNING","Camera not available,ignoring command.")
            return

        msgType = message.get("Message",{}).get("type")
        payload = message.get("Message",{}).get("payload",{})
        if msgType == "PictureTaken":
            self.log("INFO","Received 'Picture Taken' signal. Picture received.")
            if payload:
                picture = payload.get("image")
                if picture:
                    pass
        elif msgType == "AnalysisComplete":
            self.log("INFO","Received 'Analysis Complete' command. Showing analysis results.")
            pass
    def onStop(self):
        pass