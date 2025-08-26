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
    def __init__(self, config, networkConfig, systemConfig):
        super().__init__("Camera", networkConfig, systemConfig)
        self.camera = None
        self.config = config

    def onStart(self):
        """
        Initializes and configures the camera when the module starts.
        """
        try:
            self.camera = Picamera2()
            # La risoluzione viene letta direttamente dalla configurazione iniettata
            resolution = tuple(self.config['resolution'])
            camConfig = self.camera.create_still_configuration({"size": resolution})
            self.camera.configure(camConfig)
            self.camera.start()
            print(f"Camera started and configured with resolution {resolution}.")
        except Exception as e:
            print(f"ERROR: Could not initialize camera: {e}")
            self.camera = None

    def handleMessage(self, message):
        """
        Handles incoming messages.
        """
        if not self.camera:
            print("Camera not available, ignoring command.")
            return

        msgType = message.get("Message", {}).get("type")

        if msgType == "CuvettePresent":
            print("Received cuvette present signal. Taking a picture.")
            self.takePicture()
        elif msgType == "Take":
            print("Received 'Take' command. Taking a picture.")
            self.takePicture()
        elif msgType == "Calibrate":
            print("Received 'Calibrate' command. Starting calibration.")
            self.calibrate()

    def takePicture(self):
        """
        Takes a picture and sends it to the Analysis module.
        """
        if not self.camera:
            print("Cannot take picture, camera not initialized.")
            return

        try:
            print("Taking picture...")
            # Capture the image as a numpy array
            imageArray = self.camera.capture_array()

            # Encode the image in JPG format and then in Base64
            _, buffer = cv2.imencode('.jpg', imageArray)
            imageB64 = base64.b64encode(buffer).decode('utf-8')

            payload = {"image": imageB64}
            self.sendMessage("Analysis", "Analyze", payload)
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
        self.sendMessage("All", "CameraCalibrated", {"status": "success"})
        print("Camera calibration complete.")

    def onStop(self):
        """
        Stops the camera when the module is terminated.
        """
        if self.camera and self.camera.started:
            self.camera.stop()
            print("Camera stopped.")