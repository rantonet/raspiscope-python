"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

from kivy.app import App

from module       import Module
from configLoader import ConfigLoader

class GUI(Module,App):
    def __init__(self):
        configLoader = ConfigLoader(configPath)
        config       = configLoader.get_config()
        pass
    def onStart(self):
        """
        Initializes and configures the Graphical User Interface
         module.
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
        if msgType == "":
            pass
        elif msgType == "":
            pass
    def onStop(self):
        pass