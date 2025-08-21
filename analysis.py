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
    def __init__(self, reference_spectra_path="", tolerance_nm=10):
        super().__init__("Analysis")
        self.reference_spectra_path = reference_spectra_path
        self.tolerance_nm = tolerance_nm
        self.reference_spectra = None

    def on_start(self):
        """
        Method called when the module starts.
        Loads the reference data.
        """
        try:
            self.reference_spectra = pandas.read_csv(self.reference_spectra_path)
            self.reference_spectra.set_index('wavelength', inplace=True)
            print("Reference data loaded successfully.")
        except FileNotFoundError:
            print(f"ERROR: Reference file not found: {self.reference_spectra_path}")
            # The module will continue to run but will not be able to analyze
        except Exception as e:
            print(f"ERROR while loading reference data: {e}")

    def handle_message(self, message):
        """
        Handles incoming messages.
        """
        msg_type = message.get("Message", {}).get("type")
        payload = message.get("Message", {}).get("payload", {})

        if msg_type == "Analyze":
            print("Received analysis command.")
            if self.reference_spectra is None:
                print("Cannot analyze: reference data not loaded.")
                return
            
            image_b64 = payload.get("image")
            if image_b64:
                # Decode the image from Base64
                img_bytes = base64.b64decode(image_b64)
                img_np = numpy.frombuffer(img_bytes, dtype=numpy.uint8)
                image_data = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                
                # Start analysis in a separate thread to avoid blocking
                analysis_thread = Thread(target=self.perform_analysis, args=(image_data,))
                analysis_thread.start()
            else:
                print("'Analyze' command received without image data.")

    def perform_analysis(self, image_data):
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
        
        self.send_message("All", "AnalysisComplete", results)
        print("Analysis complete and results sent.")