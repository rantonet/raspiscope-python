import numpy
import time
import cv2
import base64
from picamera2 import Picamera2
from threading import Thread
from module import Module

class Camera(Module):
    """
    Manages the PiCamera.
    Inherits from the base Module class.
    """
    def __init__(self, config):
        super().__init__("Camera")
        self.camera = None
        self.config = config

    def on_start(self):
        """
        Initializes and configures the camera when the module starts.
        """
        try:
            self.camera = Picamera2()
            resolution = tuple(self.config.get("resolution", [1920, 1080]))
            cam_config = self.camera.create_still_configuration({"size": resolution})
            self.camera.configure(cam_config)
            self.camera.start()
            print("Camera started and configured.")
        except Exception as e:
            print(f"ERROR: Could not initialize camera: {e}")
            self.camera = None # Ensure camera is None if it fails

    def handle_message(self, message):
        """
        Handles incoming messages.
        """
        if not self.camera:
            print("Camera not available, ignoring command.")
            return

        msg_type = message.get("Message", {}).get("type")
        
        if msg_type == "CuvettePresent":
            print("Received cuvette present signal. Taking a picture.")
            self.take_picture()
        elif msg_type == "Take":
            print("Received 'Take' command. Taking a picture.")
            self.take_picture()
        elif msg_type == "Calibrate":
            print("Received 'Calibrate' command. Starting calibration.")
            self.calibrate()

    def take_picture(self):
        """
        Takes a picture and sends it to the Analysis module.
        """
        if not self.camera:
            print("Cannot take picture, camera not initialized.")
            return
            
        try:
            print("Taking picture...")
            # Capture the image as a numpy array
            image_array = self.camera.capture_array()
            
            # Encode the image in JPG format and then in Base64
            _, buffer = cv2.imencode('.jpg', image_array)
            image_b64 = base64.b64encode(buffer).decode('utf-8')
            
            payload = {"image": image_b64}
            self.send_message("Analysis", "Analyze", payload)
            print("Picture taken and sent for analysis.")
            
        except Exception as e:
            print(f"ERROR while taking picture: {e}")

    def calibrate(self):
        """
        Performs camera calibration.
        Placeholder for the actual calibration logic.
        """
        print("Starting camera calibration...")
        # TODO: Implement calibration logic (e.g., white balance, exposure).
        time.sleep(2) # Simulate calibration time
        self.send_message("All", "CameraCalibrated", {"status": "success"})
        print("Camera calibration complete.")

    def on_stop(self):
        """
        Stops the camera when the module is terminated.
        """
        if self.camera and self.camera.started:
            self.camera.stop()
            print("Camera stopped.")