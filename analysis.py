import cv2
import numpy
import pandas
from time         import sleep
from scipy.signal import find_peaks
from threading    import Thread
from communicator import Communicator

class Analysis():
    """Analysis

    Class for spectrogram analysis
    """
    def __init__(self,reference_spectra_path="",tolerance_nm=10):
        """Analysis constructor

        Initializes the processor with the image data to be analyzed.

        Args:
            image_data (numpy.ndarray): The image's pixel array (e.g., from OpenCV).
                                        Can be color (BGR) or grayscale.
            reference_spectra_path (str): Path to the CSV file containing the reference spectra.
                                          The CSV should have 'wavelength' as the first column
                                          and subsequent columns for each substance.
        """
        self.name         = "Analysis"
        self.stop         = False
        self.image        = image_data
        self.communicator = Communicator("client")
        try:
            self.reference_spectra = pandas.read_csv(reference_spectra_path)
            self.reference_spectra.set_index('wavelength', inplace=True)
        except FileNotFoundError:
            raise FileNotFoundError(f"Reference file not found at: {reference_spectra_path}")
        self.tolerance_nm = tolerance_nm
    def run(self):
        t = Thread(target=self.communicator.run)
        t.start()
        while True:
            if self.communicator.incomingQueue:
                message = self.communicator.incomingQueue.pop(0)
            if message:
                if message["Message"] == "Stop":
                    break
                elif message["Message"] == "Analyze":
                    #TODO: implement get image_tata code
                    if image_data is None or image_data.size == 0:
                        raise ValueError("Provided image data cannot be None.")
                    if not reference_spectra_path.strip():
                        raise ValueError("Provided reference spectra path is empty")
                    if len(self.image.shape) == 3 and self.image.shape[2] == 3:
                        self.gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
                    else:
                        self.gray_image = self.image
                    #TODO: end the function
                elif message["Message"] == "Calibrate":
                    self.calibrate(known_spectrum,known_peaks_pixels,known_peaks_wavelengths)
            sleep(0.001)
        self.communicator.outgoingQueue.append(
                                            {
                                                "Sender"      : self.name,
                                                "Destination" : "Communicator",
                                                "Message"     : "stop"
                                            }
                                            )
        t.join()
    def calibrate(self, spectrum_profile, known_peaks_pixels, known_peaks_wavelengths):
        """calibrate
        Calibrates the pixel axis into wavelengths (nm).
        Uses simple linear interpolation based on known peaks.

        Args:
            spectrum_profile (numpy.ndarray): The spectrum profile.
            known_peaks_pixels (list): A list of pixel locations of known peaks.
            known_peaks_wavelengths (list): A list of the corresponding wavelengths in nm.

        Returns:
            numpy.ndarray: The calibrated wavelength axis.
        """
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Analysis",
                                        "Destination" : "All",
                                        "Message"     : self.Calibrating()
                                    }
                                              )
        pixel_axis = numpy.arange(len(spectrum_profile))
        wavelength_axis = numpy.interp(pixel_axis, known_peaks_pixels, known_peaks_wavelengths)
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Analysis",
                                        "Destination" : "All",
                                        "Message"     : self.Calibrated()
                                    }
                                              )
        return wavelength_axis
    def extractSpectrumProfile(self, y_coord=0, height=5):
        """extractSpectrumProfile

        Extracts the spectrum's intensity profile from a region of the image.

        Args:
            y_coord (int): The central y-coordinate of the row from which to extract the spectrum.
            height (int): The height of the region to average over to reduce noise.

        Returns:
            numpy.ndarray: A 1D array representing the spectrum's intensity.
        """
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Analysis",
                                        "Destination" : "All",
                                        "Message"     : self.GettingSpectrogram()
                                    }
                                              )
        if y_coord < (height // 2):
            raise ValueError("Y coordinate must be greater than half of the height")
        # Calculate the upper and lower bounds of the region of interest (ROI)
        start_y = max(0, y_coord - height // 2)
        end_y = min(self.gray_image.shape[0], y_coord + height // 2 + 1)
        
        # Extract the region of interest (ROI)
        roi = self.gray_image[start_y:end_y, :]
        
        # Calculate the mean intensity along the vertical axis (columns)
        spectrum_profile = numpy.mean(roi, axis=0)
        
        self.communicator.outgoingQueue.append(
                                    {
                                        "Sender"      : "Analysis",
                                        "Destination" : "All",
                                        "Message"     : self.SpectrogramTaken()
                                    }
                                              )

        return spectrum_profile
    def identifySubstance(self, measured_wavelengths, measured_intensities, prominence_threshold=0.1):
        """identifySubstance
        Identifies the substance with the best match in the database.
        Uses an approach based on finding and comparing peaks.

        Args:
            measured_wavelengths (numpy.ndarray): The wavelength axis of the measured spectrum.
            measured_intensities (numpy.ndarray): The intensity of the measured spectrum.
            prominence_threshold (float): The required prominence to consider a peak valid.

        Returns:
            str: The name of the best-matching substance, or "Unknown".
        """
        # Normalize the measured intensities
        normalized_intensities = self.normalizeArray(measured_intensities)

        # Find peaks in the measured spectrum
        peaks, properties = find_peaks(normalized_intensities, prominence=prominence_threshold)
        measured_peak_wavelengths = measured_wavelengths[peaks]

        best_match = "Unknown"
        max_matching_peaks = 0

        print(f"\nDetected peaks in measured spectrum (wavelengths in nm): {measured_peak_wavelengths.round(2)}")

        # Compare with each reference substance
        for substance_name in self.reference_spectra.columns:
            ref_intensities = self.reference_spectra[substance_name].values
            ref_wavelengths = self.reference_spectra.index.values
            ref_intensities = self.normalizeArray(ref_intensities)

            # Find peaks in the reference spectrum
            ref_peaks, _ = find_peaks(ref_intensities, prominence=prominence_threshold)
            ref_peak_wavelengths = ref_wavelengths[ref_peaks]

            # Count how many measured peaks match the reference ones (within a tolerance)
            matching_peaks = 0
            for measured_peak in measured_peak_wavelengths:
                if any(numpy.isclose(measured_peak, ref_peak, atol=self.tolerance_nm) for ref_peak in ref_peak_wavelengths):
                    matching_peaks += 1
            
            print(f"Comparing with '{substance_name}': {matching_peaks} matching peaks.")

            if matching_peaks > max_matching_peaks:
                max_matching_peaks = matching_peaks
                best_match = substance_name

        return best_match
    def normalizeArray(self,arr):
        min_val = numpy.min(arr)
        max_val = numpy.max(arr)
        if max_val - min_val == 0:
            return numpy.zeros_like(arr)  # spettro piatto
        return (arr - min_val) / (max_val - min_val)
    #Signals
    class Calibrating():
        """Calibrating

        Signal for Calibrating Analysis
        """
        def __init__(self):
            self.description = "Calibrating the analysis module"
    class Calibrated():
        """Calibrated

        Signal for Analysis calibrated
        """
        def __init__(self):
            self.description = "Analysis module calibrated"
    class GettingStrip():
        """GettingStrip

        Signal for Getting Strip
        """
        def __init__(self):
            self.description = "Getting the strip from the image"
    class StripTaken():
        """StripTaken

        Signal for Strip Taken"
        """
        def __init__(self):
            self.description = "Strip Taken"
    class GettingSpectrogram():
        """GettingSpectrogram

        Signal for Getting Spectrogram
        """
        def __init__(self):
            self.description = "Taking the spectrogram"
    class SpectrogramTaken():
        """SpectrogramTaken

        Signal for Spectrogram Taken
        """
        def __init__(self):
            self.description = "Spectrogram taken"
    class ComputingMaterials():
        """ComputingMaterials

        Signal for Computing Materials
        """
        def __init__(self):
            self.description = "Computing materials"
    class MaterialsComputed():
        """MaterialsComputed

        Signal for Materials Computed
        """
        def __init__(self):
            self.description = "Materials computed"
    class ComparingSpectrograms():
        """ComparingSpectrograms

        Signal for Comparing Spectrograms
        """
        def __init__(self):
            self.description = "Comparing Spectrograms"
    class SpectrogramsCompared():
        """SpectrogramsCompared

        Signal for Spectrograms Compared
        """
        def __init__(self):
            self.description = "Spectrograms compared"