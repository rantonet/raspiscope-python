import asyncio

from gpiozero import InputDevice

from communicator import Communicator

class CuvettePresence():
    def __init__(self,inputPin):
        """CuvettePresence constructor

        Initializes the sensors
        """
        self.communicator      = Communicator("client")
        self.sensor            = InputDevice(inputPin)
        self.presenceThreshold = 0
        self.thresholdSpan     = 0.1
        self.present           = False
        self.stop              = False
    async def run():
        """presenceLoop

        Main loop checking for the presence of the cuvette
        """
        await self.communicator.run()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "CuvetteSensor",
                                        "Destination" : "All",
                                        "Message"     : self.Sensing()
                                    }
                                              )
        while True:
            if self.stop: break
            await self.getPresence()
            asyncio.sleep(0.001)
    async def getPresence(self):
        """getPresence

        Read the presence sensor and sense if che cuvette is present or not
        """
        if (self.sensor < (self.presenceThreshold - self.presenceThreshold*self.thresholdSpan)) \
            or (self.sensor > (self.presenceThreshold + self.presenceThreshold*self.thresholdSpan)):
            if not self.present:
                self.present = True
                self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "CuvetteSensor",
                                        "Destination" : "All",
                                        "Message"     : self.CuvettePresent()
                                    }
                                              )
        else:
            if self.present:
                self.present = False
                self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "CuvetteSensor",
                                        "Destination" : "All",
                                        "Message"     : self.CuvetteAbsent()
                                    }
                                              )
    async def calibrate(self,numberOfSamples=100):
        """calibrate

        Start calibration loop and set the presence threshold
        """
        samples = list()
        for step in range(numberOfSamples):
            samples.append(self.sensor.value)
        if len(samples) == numberOfSamples:
            pass
        else:
            return Exception('Cuvette Sensor calibration failed')
    class CuvettePresent():
        async def __init__(self,data=dict()):
            self.data = data
    class CuvetteAbsent():
        async def __init__(self,data=dict()):
            self.data = data
    class Sensing():
        async def __init__(self,data=dict()):
            self.data = data