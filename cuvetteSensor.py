import time
from gpiozero import InputDevice,GPIOZeroError
from threading import Thread
from module import Module
import statistics

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
                print("Cuvette inserted.")
                self.sendMessage("All","CuvettePresent")
            elif not currentlyPresent and self.isPresent:
                self.isPresent = False
                print("Cuvette removed.")
                self.sendMessage("All","CuvetteAbsent")
        except Exception as e:
            print(f"Error while reading the sensor: {e}")
            self.stop_event.set()

    def calibrate(self):
        """
        Performs calibration to set the presence threshold.
        Assumes the cuvette is NOT present during calibration.
        """
        if not self.sensor:
            print("Cannot calibrate: sensor not initialized.")
            return

        numSamples = self.config['calibration']['samples']
        print(f"Starting cuvette sensor calibration ({numSamples} samples)...")
        samples = numSamples
        try:
            for _ in range(numSamples):
                samples.append(self.sensor.value)
                time.sleep(0.01)

            if samples:
                meanValue = statistics.mean(samples)
                self.presenceThreshold = meanValue - self.thresholdSpan
                print(f"Calibration complete. Threshold set to: {self.presenceThreshold:.4f}")
            else:
                raise ValueError("No samples collected.")
        except Exception as e:
            print(f"ERROR during sensor calibration: {e}")