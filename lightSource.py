from gpiozero import PWMLED

class LightSource():
    def __init__(self,pin):
        """LightSource constructor

        Initialize the LED output with the required pin
        """
        self.led = PWMLED(pin)
    def turnOn(self):
        """turnOn

        Turn on the LED at maximum brightness
        """
        pass
    def turnOff(self):
        """turnOff

        turn off the LED
        """
        pass
    def dim(self):
        """dim

        Sets the brightness of the led
        """
        pass