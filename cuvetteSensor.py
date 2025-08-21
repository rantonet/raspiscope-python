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
    def __init__(self, input_pin):
        super().__init__("CuvetteSensor")
        self.input_pin = input_pin
        self.sensor = None
        self.presence_threshold = 0
        self.threshold_span = 0.1
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
            print(f"ERROR: Could not initialize sensor on pin {self.input_pin}. Check connections and permissions. Details: {e}")
            self.sensor = None

    def main_loop(self):
        """
        Overrides the main loop to continuously check for presence.
        """
        if not self.sensor:
            # If the sensor was not initialized, do nothing.
            time.sleep(1)
            return

        while not self.stop_event.is_set():
            self.check_presence()
            time.sleep(0.1) # Check every 100ms

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
            # It might be useful to stop the loop or try to reinitialize
            self.stop_event.set()


    def calibrate(self, num_samples=100):
        """
        Performs calibration to set the presence threshold.
        Assumes the cuvette is NOT present during calibration.
        """
        if not self.sensor:
            print("Cannot calibrate: sensor not initialized.")
            return

        print("Starting cuvette sensor calibration... (make sure the cuvette is not present)")
        samples = []
        try:
            for _ in range(num_samples):
                samples.append(self.sensor.value)
                time.sleep(0.01)
            
            if samples:
                # The threshold is the average of the empty readings minus a margin
                mean_value = statistics.mean(samples)
                self.presence_threshold = mean_value - self.threshold_span
                print(f"Calibration complete. Threshold set to: {self.presence_threshold:.4f}")
            else:
                raise ValueError("No samples collected.")
        except Exception as e:
            print(f"ERROR during sensor calibration: {e}")