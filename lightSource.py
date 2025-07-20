from gpiozero import PWMLED

class LightSource():
    async def __init__(self,pin):
        """LightSource constructor

        Initialize the LED output with the required pin
        """
        self.led = PWMLED(pin)
    async def turnOn(self):
        """turnOn

        Turn on the LED at maximum brightness
        """
        pass
    async def turnOff(self):
        """turnOff

        turn off the LED
        """
        pass
    async def dim(self):
        """dim

        Sets the brightness of the led
        """
        pass