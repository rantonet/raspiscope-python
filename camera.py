"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

import numpy
import time
import cv2
import base64
from picamera2 import Picamera2
from threading import Thread
from module    import Module

class Camera(Module):
    """
    Manages the PiCamera.
    Inherits from the base Module class.
    """
    def __init__(self,config,networkConfig,systemConfig):
        super().__init__("Camera",networkConfig,systemConfig)
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
            camConfig  = self.camera.create_still_configuration({"size": resolution})
            self.camera.configure(camConfig)
            self.camera.start()
            self.log("INFO",f"Camera started and configured with resolution {resolution}.")
        except Exception as e:
            self.log("ERROR",f"Could not initialize camera: {e}")
            self.camera = None

    def handleMessage(self,message):
        """
        Handles incoming messages.
        """
        if not self.camera:
            self.log("WARNING","Camera not available,ignoring command.")
            return

        msgType = message.get("Message",{}).get("type")

        if msgType == "CuvettePresent":
            self.log("INFO","Received cuvette present signal. Taking a picture.")
            self.takePicture()
        elif msgType == "Take":
            self.log("INFO","Received 'Take' command. Taking a picture.")
            self.takePicture()
        elif msgType == "Calibrate":
            self.log("INFO","Received 'Calibrate' command. Starting calibration.")
            self.calibrate()

    def takePicture(self):
        """
        Takes a picture and sends it to the Analysis module.
        """
        if not self.camera:
            self.log("ERROR","Cannot take picture,camera not initialized.")
            return

        try:
            self.log("INFO","Taking picture...")
            # Capture the image as a numpy array
            imageArray = self.camera.capture_array()

            # Encode the image in JPG format and then in Base64
            _,buffer = cv2.imencode('.jpg',imageArray)
            imageB64 = base64.b64encode(buffer).decode('utf-8')

            payload = {"image": imageB64}
            self.sendMessage("Analysis","Analyze",payload)
            self.log("INFO","Picture taken and sent for analysis.")

        except Exception as e:
            self.log("ERROR",f"ERROR while taking picture: {e}")

    def calibrate(self):
        """
        Performs an automated calibration by iterating through various combinations
        of ISO, exposure, and brightness settings to find the optimal set that
        maximizes image quality, as measured by the image gradient. The
        calibration process follows the logic defined in the project's diagrams.
        
        The best settings are then saved and applied to the camera.
        This method does not modify the camera's resolution.
        """
        if not self.camera:
            self.log("WARNING", "Cannot perform calibration, camera not initialized.")
            self.sendMessage("All", "CameraCalibrated", {"status": "error", "message": "Camera not initialized."})
            return

        self.log("INFO", "Starting camera calibration...")
        self.sendMessage("All", "CalibrationStarted", {"message": "Starting camera calibration..."})

        # Placeholder: These lists should be defined based on the camera's capabilities.
        iso_list        = [100, 200, 400, 800]
        exposure_list   = [5000, 10000, 20000, 40000] # in microseconds
        brightness_list = [0.1, 0.5, 0.9] # values from 0 to 1

        best_settings = {"iso": None, "exposure": None, "brightness": None, "gradient": 0}

        try:
            # Iterate through all combinations of settings
            for iso in iso_list:
                for exposure in exposure_list:
                    for brightness in brightness_list:
                        # 1. Setting the parameters
                        self.camera.set_controls({"AnalogueGain": iso/100, "ExposureTime": exposure})
                        self.camera.set_brightness(brightness)
                        
                        # 2. Capturing the image
                        image_array = self.camera.capture_array()
                        
                        # 3. Calculating the gradient (measure of contrast/detail)
                        gray_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
                        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=5)
                        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=5)
                        gradient = numpy.sqrt(sobelx**2 + sobely**2).mean()

                        self.log("DEBUG", f"Testing settings: ISO={iso}, Exposure={exposure}, Brightness={brightness}, Gradient={gradient}")
                        
                        # 4. Updating the best settings
                        if gradient > best_settings["gradient"]:
                            best_settings["iso"]        = iso
                            best_settings["exposure"]   = exposure
                            best_settings["brightness"] = brightness
                            best_settings["gradient"]   = gradient

            # 5. Applying the best settings found
            if best_settings["iso"]:
                self.camera.set_controls({
                    "AnalogueGain": best_settings["iso"]/100,
                    "ExposureTime": best_settings["exposure"]
                })
                self.camera.set_brightness(best_settings["brightness"])
                self.log("INFO", f"Calibration complete. Best settings found: {best_settings}")
                self.sendMessage("All", "CameraCalibrated", {"status": "success", "settings": best_settings})
            else:
                self.log("ERROR", "Calibration failed: could not find best settings.")
                self.sendMessage("All", "CameraCalibrated", {"status": "error", "message": "No optimal settings found."})

        except Exception as e:
            self.log("ERROR", f"An error occurred during calibration: {e}")
            self.sendMessage("All", "CameraCalibrated", {"status": "error", "message": f"Calibration failed: {e}"})
    def onStop(self):
        """
        Stops the camera when the module is terminated.
        """
        if self.camera and self.camera.started:
            self.camera.stop()
            self.log("INFO","Camera stopped.")