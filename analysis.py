import cv2
import numpy
import pandas
import time
import base64
import json
from scipy.signal import find_peaks
from threading import Thread
from module import Module

class Analysis(Module):
    """
    Class for spectrogram analysis.
    Inherits from the base Module class.
    """
    def __init__(self, config, networkConfig, systemConfig):
        super().__init__("Analysis", networkConfig, systemConfig)
        self.config = config
        self.referenceSpectraPath = self.config['reference_spectra_path']
        self.toleranceNm = self.config['tolerance_nm']
        self.referenceSpectra = None

    def onStart(self):
        """
        Method called when the module starts.
        Loads the reference data.
        """
        try:
            self.referenceSpectra = pandas.read_csv(self.referenceSpectraPath)
            self.referenceSpectra.set_index('wavelength', inplace=True)
            print(f"Reference data loaded successfully from '{self.referenceSpectraPath}'.")
        except FileNotFoundError:
            print(f"ERROR: Reference file not found: {self.referenceSpectraPath}")
        except Exception as e:
            print(f"ERROR while loading reference data: {e}")

    def handleMessage(self, message):
        """
        Handles incoming messages.
        """
        msgType = message.get("Message", {}).get("type")
        payload = message.get("Message", {}).get("payload", {})

        if msgType == "Analyze":
            print("Received analysis command.")
            if self.referenceSpectra is None:
                print("Cannot analyze: reference data not loaded.")
                return

            imageB64 = payload.get("image")
            if imageB64:
                # Decode the image from Base64
                imgBytes = base64.b64decode(imageB64)
                imgNp = numpy.frombuffer(imgBytes, dtype=numpy.uint8)
                imageData = cv2.imdecode(imgNp, cv2.IMREAD_COLOR)

                # Start analysis in a separate thread to avoid blocking
                analysisThread = Thread(target=self.performAnalysis, args=(imageData,))
                analysisThread.start()
            else:
                print("'Analyze' command received without image data.")

    def performAnalysis(self, imageData):
        """
        Performs the spectrogram analysis.
        This is a placeholder function and should be implemented.
        """
        print("Starting spectrogram analysis...")
        # TODO: Implement the logic for strip extraction,
        # spectrogram calculation, and comparison.

        # Example of sending results (dummy data)
        time.sleep(2) # Simulate processing time

        results = {
            "substances": ["Substance A", "Substance B"],
            "spectrogram_data": [1, 2, 3, 4, 5]
        }

        self.sendMessage("All", "AnalysisComplete", results)
        print("Analysis complete and results sent.")