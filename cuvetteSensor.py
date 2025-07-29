from gpiozero import InputDevice

class CuvettePresence():
    def __init__(self,inputPin):
        """CuvettePresence constructor

        Initializes the sensors
        """
        self.sensor            = InputDevice(inputPin)
        self.presenceThreshold = 0
    def presenceLoop():
        """presenceLoop

        Main loop checking for the presence of the cuvette
        """
        pass
    def getPresence(self):
        """getPresence

        Read the presence sensor and sense if che cuvette is present or not
        """
        pass
    def calibrate(self):
        """calibrate

        Start calibration loop and set the presence threshold
        """
        pass