from gpiozero import InputDevice
from asyncio  import sleep

class CuvettePresence():
    async def __init__(self,inputPin):
        """CuvettePresence constructor

        Initializes the sensors
        """
        self.sensor            = InputDevice(inputPin)
        self.presenceThreshold = 0
    async def presenceLoop():
        """presenceLoop

        Main loop checking for the presence of the cuvette
        """
        pass
    async def getPresence(self):
        """getPresence

        Read the presence sensor and sense if che cuvette is present or not
        """
        pass
    async def calibrate(self):
        """calibrate

        Start calibration loop and set the presence threshold
        """
        pass