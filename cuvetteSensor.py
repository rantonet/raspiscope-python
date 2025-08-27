import time
import statistics
from gpiozero     import InputDevice,GPIOZeroError
from threading    import Thread
from module       import Module

class CuvetteSensor(Module):
    """
    Detects the presence of the cuvette using a Hall effect sensor.
    Inherits from the base Module class.
    """
    def __init__(self,config,networkConfig,systemConfig):
        super().__init__("CuvetteSensor",networkConfig,systemConfig)
        self.config            = config
        self.inputPin          = self.config['pin']
        self.sensor            = None
        self.presenceThreshold = 0
        self.thresholdSpan     = self.config['calibration']['threshold_span']
        self.pollInterval      = self.config['poll_interval_s']
        self.isPresent         = False

    def onStart(self):
        """
        Initializes the sensor and starts calibration.
        """
        try:
            self.sensor = InputDevice(self.inputPin)
            print(f"Cuvette sensor initialized on pin {self.inputPin}.")
            self.calibrate()
        except GPIOZeroError as e:
            print(f"ERROR: Could not initialize sensor on pin {self.inputPin}. Details: {e}")
            self.sensor = None

    def mainLoop(self):
        """
        Overrides the main loop to continuously check for presence.
        """
        if not self.sensor:
            time.sleep(1)
            return

        while not self.stop_event.is_set():
            self.checkPresence()
            time.sleep(self.pollInterval)

    def checkPresence(self):
        """
        Checks the sensor value and sends a signal if the state changes.
        """
        try:
            currentValue     = self.sensor.value
            currentlyPresent = currentValue < self.presenceThreshold

            if currentlyPresent and not self.isPresent:
                self.isPresent = True
                self.sendMessage("Camera","CuvettePresent")
            elif not currentlyPresent and self.isPresent:
                self.isPresent = False
                self.sendMessage("Camera","CuvetteAbsent")
        except Exception as e:
            print(f"Error while reading the sensor: {e}")
            self.stop_event.set()

    def calibrate(self):
        """
        Performs calibration to set the presence threshold.
        Assumes the cuvette is NOT present during calibration.
        """
        if not self.sensor:
            self.sendMessage("All", "CalibrationError", {"message": "Cannot calibrate: sensor not initialized."})
            return

        numSamples = self.config['calibration']['samples']
        self.sendMessage("All", "CalibrationStarted", {"message": f"Starting cuvette sensor calibration ({numSamples} samples)..."})
        samples = []
        try:
            for _ in range(numSamples):
                samples.append(self.sensor.value)
                time.sleep(0.01)

            if samples:
                meanValue = statistics.mean(samples)
                self.presenceThreshold = meanValue - self.thresholdSpan
                self.sendMessage("All", "CalibrationComplete", {"threshold": self.presenceThreshold, "message": "Calibration complete."})
            else:
                self.sendMessage("All", "CalibrationError", {"message": "No samples collected during calibration."})
        except Exception as e:
            self.sendMessage("All", "CalibrationError", {"message": f"An error occurred during calibration: {e}"})