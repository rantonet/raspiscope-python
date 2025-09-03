import unittest
import cv2
import base64
import numpy       as np
import pandas      as pd
from unittest.mock import MagicMock, patch, call
from analysis      import Analysis
from threading     import Thread
from queue         import Queue

class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "reference_spectra_path": "mock_data.csv",
            "tolerance_nm": 5
        }
        self.mock_network_config = {}
        self.mock_system_config = {}
        
        self.mock_module_patcher = patch('analysis.Module', MagicMock(spec=True))
        self.mock_module = self.mock_module_patcher.start()
        self.mock_module.log = MagicMock()
        
        self.analysis_module = Analysis(self.mock_config, self.mock_network_config, self.mock_system_config)
        
        self.mock_reference_spectra = pd.DataFrame({
            'wavelength': [450, 550, 650],
            'substance': ['SubstanceA', 'SubstanceB', 'SubstanceC']
        }).set_index('wavelength')
        
    def tearDown(self):
        self.mock_module_patcher.stop()

    def test_onStart_success(self):
        """Verifies the successful loading of reference data."""
        with patch('pandas.read_csv', return_value=self.mock_reference_spectra), \
             patch.object(self.analysis_module, 'sendMessage') as mock_send:
            self.analysis_module.onStart()
            self.assertIsNotNone(self.analysis_module.referenceSpectra)
            mock_send.assert_called_once_with("All", "AnalysisInitialized", {"path": "mock_data.csv", "status": "success"})
            self.mock_module.log.assert_called_once_with("INFO", "Reference data loaded successfully.")

    def test_onStart_file_not_found(self):
        """Verifies the handling of a FileNotFoundError."""
        with patch('pandas.read_csv', side_effect=FileNotFoundError), \
             patch.object(self.analysis_module, 'sendMessage') as mock_send:
            self.analysis_module.onStart()
            self.assertIsNone(self.analysis_module.referenceSpectra)
            mock_send.assert_called_once_with("All", "AnalysisInitialized", {"path": "mock_data.csv", "status": "error", "message": "Reference file not found"})
            self.mock_module.log.assert_called_once_with("ERROR", "Reference file not found.")

    @patch('analysis.Thread')
    def test_handleMessage_analyze_with_image(self, mock_thread):
        """Verifies that an 'Analyze' message starts a new thread."""
        self.analysis_module.referenceSpectra = self.mock_reference_spectra
        mock_payload = {"image": "mock_base64_image_data"}
        mock_image_data = np.zeros((10, 10, 3), dtype=np.uint8)
        
        with patch('base64.b64decode', return_value=b'mock_bytes'), \
             patch('numpy.frombuffer', return_value=np.zeros(10)), \
             patch('cv2.imdecode', return_value=mock_image_data), \
             patch.object(self.analysis_module, 'sendMessage') as mock_send:
            
            message = {"Message": {"type": "Analyze", "payload": mock_payload}}
            self.analysis_module.handleMessage(message)
            
            mock_send.assert_called_once_with("All", "AnalysisRequested", {"status": "received"})
            mock_thread.assert_called_once()
            self.assertEqual(mock_thread.call_args[1]['target'], self.analysis_module.performAnalysis)
            self.mock_module.log.assert_called_once_with("INFO", "Analysis requested. Starting new thread.")

    def test_performAnalysis_success(self):
        """Verifies that the analysis pipeline runs successfully."""
        mock_image = np.zeros((100, 200, 3), dtype=np.uint8)
        self.analysis_module.referenceSpectra = self.mock_reference_spectra
        
        with patch.object(self.analysis_module, 'extractSpectrogramProfile', return_value=np.zeros(200)), \
             patch.object(self.analysis_module, 'detectAbsorbanceValleys', return_value=np.array([100])), \
             patch.object(self.analysis_module, 'compareWithReferences', return_value={"identified_substances": ["Test"]}), \
             patch.object(self.analysis_module, 'sendAnalysisResults') as mock_send_results:
            
            self.analysis_module.performAnalysis(mock_image)
            
            mock_send_results.assert_called_once()
            self.mock_module.log.assert_called_once_with("INFO", "Starting absorption spectrogram analysis...")