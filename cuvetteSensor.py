# cuvetteSensor.py
import time
from gpiozero import InputDevice, GPIOZeroError
from threading import Thread
from module import Module
import statistics

class CuvetteSensor(Module):
    """
    Detects the presence of the cuvette using a Hall effect sensor.
    Inherits from the base Module class.
    """
    def __init__(self, config, network_config, system_config):
        super().__init__("CuvetteSensor", network_config, system_config)
        self.config = config
        self.input_pin = self.config['pin']
        self.sensor = None
        self.presence_threshold = 0
        self.threshold_span = self.config['calibration']['threshold_span']
        self.poll_interval = self.config['poll_interval_s']
        self.is_present = False

    def on_start(self):
        """
        Initializes the sensor and starts calibration.
        """
        try:
            self.sensor = InputDevice(self.input_pin)
            print(f"Cuvette sensor initialized on pin {self.input_pin}.")
            self.calibrate()
        except GPIOZeroError as e:
            print(f"ERROR: Could not initialize sensor on pin {self.input_pin}. Details: {e}")
            self.sensor = None

    def main_loop(self):
        """
        Overrides the main loop to continuously check for presence.
        """
        if not self.sensor:
            time.sleep(1)
            return

        while not self.stop_event.is_set():
            self.check_presence()
            time.sleep(self.poll_interval)

    def check_presence(self):
        """
        Checks the sensor value and sends a signal if the state changes.
        """
        try:
            current_value = self.sensor.value
            currently_present = current_value < self.presence_threshold
            
            if currently_present and not self.is_present:
                self.is_present = True
                print("Cuvette inserted.")
                self.send_message("All", "CuvettePresent")
            elif not currently_present and self.is_present:
                self.is_present = False
                print("Cuvette removed.")
                self.send_message("All", "CuvetteAbsent")
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

        num_samples = self.config['calibration']['samples']
        print(f"Starting cuvette sensor calibration ({num_samples} samples)...")
        samples = num_samples
        try:
            for _ in range(num_samples):
                samples.append(self.sensor.value)
                time.sleep(0.01)
            
            if samples:
                mean_value = statistics.mean(samples)
                self.presence_threshold = mean_value - self.threshold_span
                print(f"Calibration complete. Threshold set to: {self.presence_threshold:.4f}")
            else:
                raise ValueError("No samples collected.")
        except Exception as e:
            print(f"ERROR during sensor calibration: {e}")