import asyncio

from gpiozero import PWMLED

from communicator import Communicator

class LightSource():
    """LightSource

    Class for Light Source management
    """
    async def __init__(self,pin):
        """LightSource constructor

        Initialize the LED output with the required pin
        """
        self.communicator = Comunicator("client")
        self.led = PWMLED(pin)
    async def turnOn(self):
        """turnOn

        Turn on the LED at maximum brightness
        """
        self.led.on()
    async def turnOff(self):
        """turnOff

        turn off the LED
        """
        self.led.off()
    async def dim(self,v=0.5):
        """dim

        Sets the brightness of the led
        """
        self.led.value(v)
    #Signals
    class LightTurnedOn():
        """LightTurnedOn

        Signal for Light Turned On
        """
        async def __init__(self,data=dict()):
            self.data = data
    class LightTurnedOff():
        """LightTurnedOff

        Signal for Light Turned Off
        """
        async def __init__(self,data=dict()):
            self.data = data
    class LightDimmed():
        """LightDimmed

        Signal for Light Dimmed
        """
        async def __init__(self,data=dict()):
            self.data = data