import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import json
import numpy
import base64
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

# Mock hardware/heavy dependencies before import
mockPicamera2 = MagicMock()
mockCv2 = MagicMock()
mockBase64 = MagicMock()

sys_modules = {
    'picamera2': MagicMock(Picamera2=mockPicamera2),
    'cv2': mockCv2,
    'base64': mockBase64
}

with patch.dict('sys.modules', sys_modules):
    from camera import Camera

class TestCamera(unittest.TestCase):

    def setUp(self):
        print("Setting up for TestCamera")
        self.mockConfig = {
            "network": {"address": "localhost", "port": 12345},
            "system": {"module_message_queue_timeout_s": 0.1},
            "modules": {
                "camera": {
                    "resolution": [1920, 1080],
                    "gain": 1.0,
                    "exposure": 10000
                }
            }
        }
        # The Camera module uses open() directly, so we mock it here
        mo = mock_open(read_data=json.dumps(self.mockConfig))
        with patch("builtins.open", mo):
            with patch('module.Communicator') as self.mockCommunicator:
                self.mockCommInstance = MagicMock()
                self.mockCommunicator.return_value = self.mockCommInstance
                self.cameraModule = Camera(self.mockConfig['network'], self.mockConfig['system'])

        # Reset mocks and setup mock instances for camera hardware
        mockPicamera2.reset_mock()
        self.mockCameraInstance = MagicMock()
        mockPicamera2.return_value = self.mockCameraInstance
        print("Setup complete for TestCamera")

    @timeout(60)
    def test_initialization(self):
        """
        Tests that the Camera module is initialized with correct config values.
        """
        print("test_initialization: Starting test")
        self.assertEqual(self.cameraModule.name, "Camera")
        print("test_initialization: Asserted name")
        self.assertEqual(self.cameraModule.resolution, [1920, 1080])
        print("test_initialization: Asserted resolution")
        self.assertEqual(self.cameraModule.gain, 1.0)
        print("test_initialization: Asserted gain")
        self.assertEqual(self.cameraModule.exposure, 10000)
        print("test_initialization: Asserted exposure")
        self.assertIsNone(self.cameraModule.camera)
        print("test_initialization: Asserted camera is None")
        print("test_initialization: Test finished")

    @timeout(60)
    def test_onStartSuccess(self):
        """
        Tests the successful camera startup sequence.
        """
        print("test_onStartSuccess: Starting test")
        self.cameraModule.onStart()
        print("test_onStartSuccess: onStart called")
        self.mockCameraInstance.create_still_configuration.assert_called_once()
        print("test_onStartSuccess: Asserted create_still_configuration called")
        self.mockCameraInstance.configure.assert_called_once()
        print("test_onStartSuccess: Asserted configure called")
        self.mockCameraInstance.start.assert_called_once()
        print("test_onStartSuccess: Asserted start called")
        self.assertIsNotNone(self.cameraModule.camera)
        print("test_onStartSuccess: Asserted camera is not None")
        self.mockCommInstance.outgoingQueue.put.assert_any_call(unittest.mock.ANY)
        print("test_onStartSuccess: Asserted registration message sent")
        print("test_onStartSuccess: Test finished")

    @timeout(60)
    def test_onStartFailure(self):
        """
        Tests the startup sequence when Picamera2 initialization fails.
        """
        print("test_onStartFailure: Starting test")
        self.mockCameraInstance.start.side_effect = Exception("Camera hardware error")
        self.cameraModule.onStart()
        print("test_onStartFailure: onStart called")
        self.assertIsNone(self.cameraModule.camera)
        print("test_onStartFailure: Asserted camera is None")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        print("test_onStartFailure: Asserted log level is ERROR")
        self.assertIn("Could not initialize camera", logCall['Message']['payload']['message'])
        print("test_onStartFailure: Asserted log message content")
        print("test_onStartFailure: Test finished")

    @timeout(60)
    @patch('camera.Camera.takePicture')
    def test_handleMessageCuvettePresent(self, mockTakePicture):
        """
        Tests that a 'CuvettePresent' message triggers a picture.
        """
        print("test_handleMessageCuvettePresent: Starting test")
        self.cameraModule.camera = self.mockCameraInstance
        self.cameraModule.handleMessage({"Message": {"type": "CuvettePresent"}})
        print("test_handleMessageCuvettePresent: handleMessage called")
        mockTakePicture.assert_called_once()
        print("test_handleMessageCuvettePresent: Asserted takePicture called")
        print("test_handleMessageCuvettePresent: Test finished")

    @timeout(60)
    @patch('camera.Camera.takePicture')
    def test_handleMessageTake(self, mockTakePicture):
        """
        Tests that a 'Take' message triggers a picture.
        """
        print("test_handleMessageTake: Starting test")
        self.cameraModule.camera = self.mockCameraInstance
        self.cameraModule.handleMessage({"Message": {"type": "Take"}})
        print("test_handleMessageTake: handleMessage called")
        mockTakePicture.assert_called_once()
        print("test_handleMessageTake: Asserted takePicture called")
        print("test_handleMessageTake: Test finished")

    @timeout(60)
    def test_takePictureSuccess(self):
        """
        Tests the successful image capture and sending process.
        """
        print("test_takePictureSuccess: Starting test")
        self.cameraModule.camera = self.mockCameraInstance
        mockImageArray = numpy.zeros((10, 10, 3), dtype=numpy.uint8)
        self.mockCameraInstance.capture_array.return_value = mockImageArray
        
        # Mock cv2 and base64 behavior
        mockCv2.imencode.return_value = (True, b'fakedata')
        mockBase64.b64encode.return_value.decode.return_value = 'ZmFrZWRhdGE='

        self.cameraModule.takePicture()
        print("test_takePictureSuccess: takePicture called")

        self.mockCameraInstance.capture_array.assert_called_once()
        print("test_takePictureSuccess: Asserted capture_array called")
        mockCv2.imencode.assert_called_once_with('.jpg', mockImageArray)
        print("test_takePictureSuccess: Asserted imencode called")
        mockBase64.b64encode.assert_called_once_with(b'fakedata')
        print("test_takePictureSuccess: Asserted b64encode called")
        
        # Check that the message was sent to Analysis
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage['Destination'], 'Analysis')
        print("test_takePictureSuccess: Asserted destination is Analysis")
        self.assertEqual(sentMessage['Message']['type'], 'Analyze')
        print("test_takePictureSuccess: Asserted message type is Analyze")
        self.assertEqual(sentMessage['Message']['payload']['image'], 'ZmFrZWRhdGE=')
        print("test_takePictureSuccess: Asserted image payload")
        print("test_takePictureSuccess: Test finished")

    @timeout(60)
    def test_takePictureNoCamera(self):
        """
        Tests that takePicture logs an error if the camera is not initialized.
        """
        print("test_takePictureNoCamera: Starting test")
        self.cameraModule.camera = None
        self.cameraModule.takePicture()
        print("test_takePictureNoCamera: takePicture called")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        print("test_takePictureNoCamera: Asserted log level is ERROR")
        self.assertIn("camera not initialized", logCall['Message']['payload']['message'])
        print("test_takePictureNoCamera: Asserted log message content")
        print("test_takePictureNoCamera: Test finished")

    @timeout(60)
    def test_onStop(self):
        """
        Tests that onStop stops the camera if it is running.
        """
        print("test_onStop: Starting test")
        self.cameraModule.camera = self.mockCameraInstance
        self.mockCameraInstance.started = True
        self.cameraModule.onStop()
        print("test_onStop: onStop called")
        self.mockCameraInstance.stop.assert_called_once()
        print("test_onStop: Asserted stop called")
        print("test_onStop: Test finished")

    @timeout(60)
    def test_onStopNotStarted(self):
        """
        Tests that onStop does not call stop if camera isn't running.
        """
        print("test_onStopNotStarted: Starting test")
        self.cameraModule.camera = self.mockCameraInstance
        self.mockCameraInstance.started = False
        self.cameraModule.onStop()
        print("test_onStopNotStarted: onStop called")
        self.mockCameraInstance.stop.assert_not_called()
        print("test_onStopNotStarted: Asserted stop not called")
        print("test_onStopNotStarted: Test finished")
