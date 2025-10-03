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
        print("Setting up for TestAnalysis")
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
        print("Setup complete for TestAnalysis")

    @timeout(60)
    def test_initialization(self):
        """
        Tests that the Analysis module is initialized correctly.
        """
        print("test_initialization: Starting test")
        self.assertEqual(self.analysisModule.name, "Analysis")
        print("test_initialization: Asserted name")
        self.assertEqual(self.analysisModule.referenceSpectraPath, 'dummy_path.csv')
        print("test_initialization: Asserted referenceSpectraPath")
        self.assertEqual(self.analysisModule.toleranceNm, 10)
        print("test_initialization: Asserted toleranceNm")
        self.assertIsNone(self.analysisModule.referenceSpectra)
        print("test_initialization: Asserted referenceSpectra is None")
        print("test_initialization: Test finished")

    @timeout(60)
    def test_onStartSuccess(self):
        """
        Tests successful loading of reference spectra on start.
        """
        print("test_onStartSuccess: Starting test")
        mock_df = MagicMock()
        mock_pandas.read_csv.return_value = mock_df
        
        self.analysisModule.onStart()
        print("test_onStartSuccess: onStart called")
        
        mock_pandas.read_csv.assert_called_once_with('dummy_path.csv')
        print("test_onStartSuccess: Asserted read_csv called")
        mock_df.set_index.assert_called_once_with('wavelength', inplace=True)
        print("test_onStartSuccess: Asserted set_index called")
        self.assertIsNotNone(self.analysisModule.referenceSpectra)
        print("test_onStartSuccess: Asserted referenceSpectra is not None")
        # Check for registration message
        self.mockCommInstance.outgoingQueue.put.assert_any_call(unittest.mock.ANY)
        print("test_onStartSuccess: Asserted registration message sent")
        print("test_onStartSuccess: Test finished")

    @timeout(60)
    def test_onStartFileNotFound(self):
        """
        Tests handling of FileNotFoundError on start.
        """
        print("test_onStartFileNotFound: Starting test")
        mock_pandas.read_csv.side_effect = FileNotFoundError
        self.analysisModule.onStart()
        print("test_onStartFileNotFound: onStart called")
        self.assertIsNone(self.analysisModule.referenceSpectra)
        print("test_onStartFileNotFound: Asserted referenceSpectra is None")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        print("test_onStartFileNotFound: Asserted log level is ERROR")
        self.assertIn("Reference file not found", logCall['Message']['payload']['message'])
        print("test_onStartFileNotFound: Asserted log message content")
        print("test_onStartFileNotFound: Test finished")

    @timeout(60)
    @patch('analysis.Thread')
    def test_handleMessageAnalyzeSuccess(self, mockThread):
        """
        Tests successful handling of an 'Analyze' message.
        """
        print("test_handleMessageAnalyzeSuccess: Starting test")
        self.analysisModule.referenceSpectra = MagicMock() # Pretend it's loaded
        message = {
            "Message": {
                "type": "Analyze",
                "payload": {"image": "fake_base64_string"}
            }
        }
        self.analysisModule.handleMessage(message)
        print("test_handleMessageAnalyzeSuccess: handleMessage called")
        
        mock_base64.b64decode.assert_called_once_with("fake_base64_string")
        print("test_handleMessageAnalyzeSuccess: Asserted b64decode called")
        mock_cv2.imdecode.assert_called_once()
        print("test_handleMessageAnalyzeSuccess: Asserted imdecode called")
        mockThread.assert_called_once()
        print("test_handleMessageAnalyzeSuccess: Asserted Thread called")
        self.assertEqual(mockThread.call_args[1]['target'], self.analysisModule.performAnalysis)
        print("test_handleMessageAnalyzeSuccess: Asserted thread target")
        print("test_handleMessageAnalyzeSuccess: Test finished")

    @timeout(60)
    def test_handleMessageAnalyzeNoReferenceData(self):
        """
        Tests that an error is sent if reference data is not loaded.
        """
        print("test_handleMessageAnalyzeNoReferenceData: Starting test")
        self.analysisModule.referenceSpectra = None
        message = {"Message": {"type": "Analyze", "payload": {"image": "..."}}}
        self.analysisModule.handleMessage(message)
        print("test_handleMessageAnalyzeNoReferenceData: handleMessage called")
        
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        print("test_handleMessageAnalyzeNoReferenceData: Asserted message type is AnalysisError")
        self.assertIn("reference data not loaded", sentMessage[1]['Message']['payload']['message'])
        print("test_handleMessageAnalyzeNoReferenceData: Asserted error message content")
        print("test_handleMessageAnalyzeNoReferenceData: Test finished")

    @timeout(60)
    def test_handleMessageAnalyzeNoImage(self):
        """
        Tests that an error is sent if the image payload is missing.
        """
        print("test_handleMessageAnalyzeNoImage: Starting test")
        self.analysisModule.referenceSpectra = MagicMock()
        message = {"Message": {"type": "Analyze", "payload": {}}}
        self.analysisModule.handleMessage(message)
        print("test_handleMessageAnalyzeNoImage: handleMessage called")

        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        print("test_handleMessageAnalyzeNoImage: Asserted message type is AnalysisError")
        self.assertIn("without image data", sentMessage[1]['Message']['payload']['message'])
        print("test_handleMessageAnalyzeNoImage: Asserted error message content")
        print("test_handleMessageAnalyzeNoImage: Test finished")

    @timeout(60)
    @patch('analysis.Analysis.extractSpectrogramProfile')
    @patch('analysis.Analysis.detectAbsorbanceValleys')
    @patch('analysis.Analysis.compareWithReferences')
    @patch('analysis.Analysis.sendAnalysisResults')
    def test_performAnalysisOrchestration(self, mockSend, mockCompare, mockDetect, mockExtract):
        """
        Tests the orchestration logic of the performAnalysis method.
        """
        print("test_performAnalysisOrchestration: Starting test")
        mockExtract.return_value = 'intensity_profile'
        mockDetect.return_value = 'peak_indices'
        mockCompare.return_value = {'final': 'results'}
        imageData = MagicMock()

        self.analysisModule.performAnalysis(imageData)
        print("test_performAnalysisOrchestration: performAnalysis called")

        mockExtract.assert_called_once_with(imageData)
        print("test_performAnalysisOrchestration: Asserted extractSpectrogramProfile called")
        mockDetect.assert_called_once_with('intensity_profile')
        print("test_performAnalysisOrchestration: Asserted detectAbsorbanceValleys called")
        mockCompare.assert_called_once_with('peak_indices', 'intensity_profile')
        print("test_performAnalysisOrchestration: Asserted compareWithReferences called")
        mockSend.assert_called_once_with({'final': 'results'})
        print("test_performAnalysisOrchestration: Asserted sendAnalysisResults called")
        print("test_performAnalysisOrchestration: Test finished")

    @timeout(60)
    @patch('analysis.Analysis.extractSpectrogramProfile', side_effect=Exception("Test Error"))
    def test_performAnalysisExceptionHandling(self, mockExtract):
        """
        Tests that exceptions in the pipeline are caught and an error is sent.
        """
        print("test_performAnalysisExceptionHandling: Starting test")
        self.analysisModule.performAnalysis(MagicMock())
        print("test_performAnalysisExceptionHandling: performAnalysis called")
        
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisError')
        print("test_performAnalysisExceptionHandling: Asserted message type is AnalysisError")
        self.assertEqual(sentMessage[1]['Message']['payload']['error'], 'Test Error')
        print("test_performAnalysisExceptionHandling: Asserted error message content")
        print("test_performAnalysisExceptionHandling: Test finished")

    @timeout(60)
    def test_sendAnalysisResults(self):
        """
        Tests that sendAnalysisResults sends the correct message.
        """
        print("test_sendAnalysisResults: Starting test")
        results = {"key": "value"}
        self.analysisModule.sendAnalysisResults(results)
        print("test_sendAnalysisResults: sendAnalysisResults called")

        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[0], 'All')
        print("test_sendAnalysisResults: Asserted message recipient is All")
        self.assertEqual(sentMessage[1]['Message']['type'], 'AnalysisComplete')
        print("test_sendAnalysisResults: Asserted message type is AnalysisComplete")
        self.assertEqual(sentMessage[1]['Message']['payload'], results)
        print("test_sendAnalysisResults: Asserted message payload")
        print("test_sendAnalysisResults: Test finished")
