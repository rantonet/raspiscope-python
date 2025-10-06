"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

from module       import Module
from configLoader import ConfigLoader

class GUI(Module):
    def __init__(self):
        configLoader = ConfigLoader(configPath)
        config       = configLoader.get_config()
        pass