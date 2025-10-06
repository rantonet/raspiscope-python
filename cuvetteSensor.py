"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

import time
import statistics
import json
from gpiozero     import InputDevice,GPIOZeroError
from threading    import Thread
from module       import Module
from configLoader import ConfigLoader

class CuvetteSensor(Module):
    """
    Detects the presence of the cuvette using a Hall effect sensor.
    Inherits from the base Module class.
    """
    def __init__(self,moduleConfig,networkConfig,systemConfig):
        if moduleConfig is None:
            full_config = ConfigLoader().get_config()
            moduleConfig = full_config.get("modules", {}).get("cuvetteSensor", {})

        super().__init__("CuvetteSensor",networkConfig,systemConfig)
        self.config            = moduleConfig or {}
        calibrationCfg         = self.config.get('calibration', {})
        self.inputPin          = self.config.get('pin')
        self.sensor            = None
        self.presenceThreshold = self.config.get('presence_threshold', 0)
        self.thresholdSpan     = calibrationCfg.get('threshold_span', 0)
        self.pollInterval      = self.config.get('poll_interval_s', 1.0)
        self.isPresent         = False
        self.numSamples        = calibrationCfg.get('samples', 0)


    def onStart(self):
        """
        Initializes the sensor and starts calibration.
        """
        self.sendMessage("EventManager", "Register")
        try:
            if self.inputPin is None:
                raise ValueError("Missing 'pin' configuration for CuvetteSensor")
            self.sensor = InputDevice(self.inputPin)
            self.log("INFO",f"Cuvette sensor initialized on pin {self.inputPin}.")
        except GPIOZeroError as e:
            self.log("ERROR",f"Could not initialize sensor on pin {self.inputPin}. Details: {e}")
            self.sensor = None
        except ValueError as e:
            self.log("ERROR", str(e))
            self.sensor = None

    def mainLoop(self):
        """
        Overrides the main loop to continuously check for presence.
        """
        if not self.sensor:
            time.sleep(1)
            return

        while not self.stopEvent.is_set():
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
            self.log("ERROR",f"Error while reading the sensor: {e}")
            self.stopEvent.set()

    def calibrate(self):
        """
        Performs calibration to set the presence threshold.
        Assumes the cuvette is NOT present during calibration.
        """
        if not self.sensor:
            self.sendMessage("All", "CalibrationError", {"message": "Cannot calibrate: sensor not initialized."})
            return

        self.sendMessage("All", "CalibrationStarted", {"message": f"Starting cuvette sensor calibration ({self.numSamples} samples)..."})
        samples = []
        try:
            for _ in range(self.numSamples):
                samples.append(self.sensor.value)
                time.sleep(0.01)

            if samples:
                meanValue = statistics.mean(samples)
                self.thresholdSpan = (max(samples) - min(samples)) / 2
                self.presenceThreshold = meanValue - self.thresholdSpan

                # Keep in-memory configuration updated for subsequent operations
                self.config['presence_threshold'] = self.presenceThreshold
                calibrationCfg = self.config.setdefault('calibration', {})
                calibrationCfg['threshold_span'] = self.thresholdSpan
                calibrationCfg['samples'] = self.numSamples

                # Save config to file
                try:
                    with open('config.json', 'r+') as f:
                        data = json.load(f)
                        data['modules']['cuvetteSensor']['threshold_span']     = self.thresholdSpan
                        data['modules']['cuvetteSensor']['presence_threshold'] = self.presenceThreshold
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
                    self.log("INFO", "Calibration settings saved to config.json.")
                except (IOError, json.JSONDecodeError) as e:
                    self.log("ERROR", f"Could not save calibration settings to config.json: {e}")

                self.sendMessage("All", "CalibrationComplete", {"threshold": self.presenceThreshold, "message": "Calibration complete."})
            else:
                self.sendMessage("All", "CalibrationError", {"message": "No samples collected during calibration."})
        except Exception as e:
            self.sendMessage("All", "CalibrationError", {"message": f"An error occurred during calibration: {e}"})
