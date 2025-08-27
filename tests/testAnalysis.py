import unittest
from unittest.mock import MagicMock, patch, call
import numpy as np
import pandas as pd
from analysis import Analysis
from threading import Thread

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "reference_spectra_path": "mock_data.csv",
            "tolerance_nm": 5
        }
        self.mock_network_config = {}
        self.mock_system_config = {}
        
        # Simula la classe base Module
        self.mock_module_patcher = patch('analysis.Module', MagicMock(spec=True))
        self.mock_module = self.mock_module_patcher.start()
        
        self.analysis_module = Analysis(self.mock_config, self.mock_network_config, self.mock_system_config)
        
        # Dati di riferimento simulati
        self.mock_reference_spectra = pd.DataFrame({
            'wavelength': [450, 550, 650],
            'substance': ['SubstanceA', 'SubstanceB', 'SubstanceC']
        }).set_index('wavelength')
        
    def tearDown(self):
        self.mock_module_patcher.stop()

    def test_onStart_success(self):
        """Verifica il caricamento riuscito dei dati di riferimento."""
        with patch('pandas.read_csv', return_value=self.mock_reference_spectra), \
             patch.object(self.analysis_module, 'sendMessage') as mock_send:
            self.analysis_module.onStart()
            self.assertIsNotNone(self.analysis_module.referenceSpectra)
            mock_send.assert_called_once_with("All", "AnalysisInitialized", {"path": "mock_data.csv", "status": "success"})

    def test_onStart_file_not_found(self):
        """Verifica la gestione di un FileNotFoundError."""
        with patch('pandas.read_csv', side_effect=FileNotFoundError), \
             patch.object(self.analysis_module, 'sendMessage') as mock_send:
            self.analysis_module.onStart()
            self.assertIsNone(self.analysis_module.referenceSpectra)
            mock_send.assert_called_once_with("All", "AnalysisInitialized", {"path": "mock_data.csv", "status": "error", "message": "Reference file not found"})

    @patch('analysis.Thread')
    def test_handleMessage_analyze_with_image(self, mock_thread):
        """Verifica che un messaggio 'Analyze' avvii un nuovo thread."""
        self.analysis_module.referenceSpectra = self.mock_reference_spectra
        mock_payload = {"image": "mock_base64_image_data"}
        mock_image_data = np.zeros((10, 10, 3), dtype=np.uint8)
        
        with patch('base64.b64decode', return_value=b'mock_bytes'), \
             patch('numpy.frombuffer', return_value=np.zeros(10)), \
             patch('cv2.imdecode', return_value=mock_image_data):
            
            message = {"Message": {"type": "Analyze", "payload": mock_payload}}
            self.analysis_module.handleMessage(message)
            
            mock_thread.assert_called_once()
            self.assertEqual(mock_thread.call_args[1]['target'], self.analysis_module.performAnalysis)

    def test_extractSpectrogramProfile(self):
        """Verifica l'estrazione e la pre-elaborazione del profilo spettrale."""
        mock_image = np.zeros((100, 200, 3), dtype=np.uint8)
        mock_image[:, 100:] = 255 # Crea una sezione luminosa
        
        with patch('cv2.cvtColor', return_value=np.mean(mock_image, axis=2)), \
             patch('numpy.mean', return_value=np.linspace(0, 255, 200)):
            
            profile = self.analysis_module.extractSpectrogramProfile(mock_image)
            self.assertEqual(profile.shape, (200,))

    def test_detectAbsorbanceValleys(self):
        """Verifica la corretta rilevazione delle valli (picchi invertiti)."""
        mock_profile = np.array([100, 50, 100, 150, 50, 150])
        with patch('scipy.signal.find_peaks', return_value=(np.array([1, 4]), {})):
            peaks = self.analysis_module.detectAbsorbanceValleys(mock_profile)
            np.testing.assert_array_equal(peaks, np.array([1, 4]))

    def test_compareWithReferences(self):
        """Verifica la corrispondenza dei picchi con i dati di riferimento."""
        self.analysis_module.referenceSpectra = self.mock_reference_spectra
        # Picco al pixel 100 -> 450 nm, Picco al pixel 300 -> 550 nm
        mock_peaks = np.array([100, 300])
        mock_profile = np.full(500, 100)
        mock_profile[100] = 50
        mock_profile[300] = 50
        
        with patch('numpy.isclose', side_effect=lambda a,b,atol: (a == 450 and b==450) or (a==550 and b==550)):
            results = self.analysis_module.compareWithReferences(mock_peaks, mock_profile)
            
            self.assertIn('SubstanceA', results['identified_substances'])
            self.assertIn('SubstanceB', results['identified_substances'])
            self.assertEqual(len(results['detected_peaks']), 2)