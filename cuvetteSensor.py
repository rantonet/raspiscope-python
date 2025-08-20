from time         import sleep
from gpiozero     import InputDevice
from threading    import Thread
from communicator import Communicator

class CuvettePresence():
    def __init__(self,inputPin):
        """CuvettePresence constructor

        Initializes the sensors
        """
        self.name              = "CuvetteSensor"
        self.communicator      = Communicator("client")
        self.sensor            = InputDevice(inputPin)
        self.presenceThreshold = 0
        self.thresholdSpan     = 0.1
        self.present           = False
        self.stop              = False
    def run():
        """presenceLoop

        Main loop checking for the presence of the cuvette
        """
        t = Threading(target=self.communicator.run)
        t.start()
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : self.name,
                                        "Destination" : "All",
                                        "Message"     : self.Sensing()
                                    }
                                              )
        while True:
            if self.stop: break
            self.getPresence()
            sleep(0.001)
        self.communicator.outgoingQueue.append(
                                            {
                                                "Sender"      : self.name,
                                                "Destination" : "Communicator",
                                                "Message"     : "stop"
                                            }
                                            )
        t.join()
    def getPresence(self):
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
    def calibrate(self,numberOfSamples=100):
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
        def __init__(self,data=dict()):
            self.data = data
    class CuvetteAbsent():
        def __init__(self,data=dict()):
            self.data = data
    class Sensing():
        def __init__(self,data=dict()):
            self.data = data