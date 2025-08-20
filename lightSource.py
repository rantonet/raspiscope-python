from time         import sleep
from rpi_ws281x   import PixelStrip,Color
from threading    import Thread
from communicator import Communicator

class LightSource():
    """LightSource

    Class for Light Source management
    """
    def __init__(self,pin,dma,brightness,pwmChannel):
        """LightSource constructor

        Initialize the LED output with the required pin
        """
        self.name         = "LightSensor"
        self.communicator = Comunicator("client")
        self.pin          = pin
        self.dma          = dma
        self.pwmChannel   = pwmChannel
        self.brightness   = brightness
        self.led          = PixelStrip( 1,
                                        self.pin,
                                        800000,
                                        self.dma,
                                        False,
                                        self.brightness,
                                        self.pwmChannel
                                    )
        self.white = Color(255,255,255)
        self.led.begin()
    def run(self):
        t = Thread(target=self.communicator.run)
        t.start()
        while True:
            if self.communicator.incomingQueue:
                message = self.communicator.incomingQueue.pop(0)
            if message:
                if message["Message"] == "Stop":
                    break
                elif message["Message"] == "Calibrate":
                    self.calibrate()
                elif message["Message"] == "On":
                    self.turnOn()
                elif message["Message"] == "Off":
                    self.turnOff
            sleep(0.001)
        self.communicator.outgoingQueue.append(
                                {
                                    "Sender"      : self.name,
                                    "Destination" : "Communicator",
                                    "Message"     : "stop"
                                }
                                            )
        t.join()
    def calibrate(self,rgb=[255,255,255],brightness=255):
        strip.setPixelColor(0, Color(rgb[0],rgb[1],rgb[2]))
        strip.setBrightness(brightness)
        strip.show()
        return True
    def turnOn(self):
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
    def turnOff(self):
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
    def dim(self,v=0.5):
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
        def __init__(self,data=dict()):
            self.data = data
    class LightTurnedOff():
        """LightTurnedOff

        Signal for Light Turned Off
        """
        def __init__(self,data=dict()):
            self.data = data
    class LightDimmed():
        """LightDimmed

        Signal for Light Dimmed
        """
        def __init__(self,data=dict()):
            self.data = data