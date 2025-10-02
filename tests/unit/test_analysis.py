import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import pandas
import numpy
import signal
from functools import wraps

def timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handle_timeout(signum, frame):
                raise TimeoutError(f"Test timed out after {seconds} seconds")
            
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result
        return wrapper
    return decorator

# Mock heavy dependencies before import
mock_cv2 = MagicMock()
mock_base64 = MagicMock()
mock_scipy_signal = MagicMock()
mock_pandas = MagicMock()

sys_modules = {
    'cv2': mock_cv2,
    'base64': mock_base64,
    'scipy.signal': mock_scipy_signal,
    'pandas': mock_pandas
}

with patch.dict('sys.modules', sys_modules):
    from analysis import Analysis

class TestAnalysis(unittest.TestCase):

    def setUp(self):
        self.mockConfig = {
            'reference_spectra_path': 'dummy_path.csv',
            'tolerance_nm': 10
        }
        self.mockNetworkConfig = {'address': 'localhost', 'port': 12345}
        self.mockSystemConfig = {'module_message_queue_timeout_s': 0.1}

        with patch('module.Communicator') as self.mockCommunicator:
            self.mockCommInstance = MagicMock()
            self.mockCommunicator.return_value = self.mockCommInstance
            self.analysisModule = Analysis(self.mockConfig, self.mockNetworkConfig, self.mockSystemConfig)

    @timeout(60)
    def test_initialization(self):
        """
        Tests that the Analysis module is initialized correctly.
        """
        self.assertEqual(self.analysisModule.name, "Analysis")
        self.assertEqual(self.analysisModule.referenceSpectraPath, 'dummy_path.csv')
        self.assertEqual(self.analysisModule.toleranceNm, 10)
        self.assertIsNone(self.analysisModule.referenceSpectra)

    @timeout(60)
    def test_onStartSuccess(self):
        """
        Tests successful loading of reference spectra on start.
        """
        mock_df = MagicMock()
        mock_pandas.read_csv.return_value = mock_df
        
        self.analysisModule.onStart()
        
        mock_pandas.read_csv.assert_called_once_with('dummy_path.csv')
        mock_df.set_index.assert_called_once_with('wavelength', inplace=True)
        self.assertIsNotNone(self.analysisModule.referenceSpectra)
        # Check for registration message
        self.mockCommInstance.outgoingQueue.put.assert_any_call(unittest.mock.ANY)

    @timeout(60)
    def test_onStartFileNotFound(self):
        """
        Tests handling of FileNotFoundError on start.
        """
        mock_pandas.read_csv.side_effect = FileNotFoundError
        self.analysisModule.onStart()
        self.assertIsNone(self.analysisModule.referenceSpectra)
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        self.assertIn("Reference file not found", logCall['Message']['payload']['message'])

    @timeout(60)
    @patch('analysis.Thread')
    def test_handleMessageAnalyzeSuccess(self, mockThread):
        """
        Tests successful handling of an 'Analyze' message.
        """
        self.analysisModule.referenceSpectra = MagicMock() # Pretend it's loaded
        message = {
            "Message": {
                "type": "Analyze",
                "payload": {"image": "fake_base64_string"}
            }
        }
        self.analysisModule.handleMessage(message)
        
        mock_base64.b64decode.assert_called_once_with("fake_base64_string")
        mock_cv2.imdecode.assert_called_once()
        mockThread.assert_called_once()
        self.assertEqual(mockThread.call_args[1]['target'], self.analysisModule.performAnalysis)

    @timeout(60)
    def test_handleMessageAnalyzeNoReferenceData(self):
        """
        Tests that an error is sent if reference data is not loaded.
        """
        self.analysisModule.referenceSpectra = None
        message = {"Message": {"type": "Analyze", "payload": {"image": "..."}}}
        self.analysisModule.handleMessage(message)
        
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        self.assertIn("reference data not loaded", sentMessage[1]['Message']['payload']['message'])

    @timeout(60)
    def test_handleMessageAnalyzeNoImage(self):
        """
        Tests that an error is sent if the image payload is missing.
        """
        self.analysisModule.referenceSpectra = MagicMock()
        message = {"Message": {"type": "Analyze", "payload": {}}}
        self.analysisModule.handleMessage(message)

        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        self.assertIn("without image data", sentMessage[1]['Message']['payload']['message'])

    @timeout(60)
    @patch('analysis.Analysis.extractSpectrogramProfile')
    @patch('analysis.Analysis.detectAbsorbanceValleys')
    @patch('analysis.Analysis.compareWithReferences')
    @patch('analysis.Analysis.sendAnalysisResults')
    def test_performAnalysisOrchestration(self, mockSend, mockCompare, mockDetect, mockExtract):
        """
        Tests the orchestration logic of the performAnalysis method.
        """
        mockExtract.return_value = 'intensity_profile'
        mockDetect.return_value = 'peak_indices'
        mockCompare.return_value = {'final': 'results'}
        imageData = MagicMock()

        self.analysisModule.performAnalysis(imageData)

        mockExtract.assert_called_once_with(imageData)
        mockDetect.assert_called_once_with('intensity_profile')
        mockCompare.assert_called_once_with('peak_indices', 'intensity_profile')
        mockSend.assert_called_once_with({'final': 'results'})

    @timeout(60)
    @patch('analysis.Analysis.extractSpectrogramProfile', side_effect=Exception("Test Error"))
    def test_performAnalysisExceptionHandling(self, mockExtract):
        """
        Tests that exceptions in the pipeline are caught and an error is sent.
        """
        self.analysisModule.performAnalysis(MagicMock())
        
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        self.assertEqual(sentMessage[1]['Message']['payload']['error'], 'Test Error')

    @timeout(60)
    def test_sendAnalysisResults(self):
        """
        Tests that sendAnalysisResults sends the correct message.
        """
        results = {"key": "value"}
        self.analysisModule.sendAnalysisResults(results)

        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[0], 'All')
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisComplete')
        self.assertEqual(sentMessage[1]['Message']['payload'], results)