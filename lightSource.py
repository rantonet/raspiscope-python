import asyncio

from rpi_ws281x import PixelStrip,Color

from communicator import Communicator

class LightSource():
    """LightSource

    Class for Light Source management
    """
    def __init__(self,pin,dma,brightness,pwmChannel):
        """LightSource constructor

        Initialize the LED output with the required pin
        """
        self.communicator = Comunicator("client")
        self.pin = pin
        self.dma = dma
        self.pwmChannel = pwmChannel
        self.brightness = brightness
        self.led = PixelStrip(1,
                              self.pin,
                              800000,
                              self.dma,
                              False,
                              self.brightness,
                              self.pwmChannel
                              )
        self.white = Color(255,255,255)
        self.led.begin()
    async def calibrate(self,rgb=[255,255,255],brightness=255):
        strip.setPixelColor(0, Color(rgb[0],rgb[1],rgb[2]))
        strip.setBrightness(brightness)
        strip.show()
        return True
    async def turnOn(self):
        """turnOn

        Turn on the LED at maximum brightness
        """
        self.led.setPixelColor(0,self.white)
        self.led.show()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Light",
                                        "Destination" : "All",
                                        "Message"     : self.LightTurnedOn()
                                    }
                                              )
        return True
    async def turnOff(self):
        """turnOff

        turn off the LED
        """
        self.led.setBrightness(0)
        self.led.show()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Light",
                                        "Destination" : "All",
                                        "Message"     : self.LightTurnedOff()
                                    }
                                              )
        return True
    async def dim(self,v=0.5):
        """dim

        Sets the brightness of the led
        """
        self.brightness = v
        self.led.setBrightness(self.brightness)
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Light",
                                        "Destination" : "All",
                                        "Message"     : self.LightDimmed()
                                    }
                                              )
        return True
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