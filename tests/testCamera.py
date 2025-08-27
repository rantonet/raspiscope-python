import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import base64
from camera import Camera

class TestCamera(unittest.TestCase):
    def setUp(self):
        self.mock_config = {"resolution": [1920, 1080]}
        self.mock_network_config = {}
        self.mock_system_config = {}
        
        self.mock_picamera2 = MagicMock()
        self.mock_picamera2.create_still_configuration.return_value = {}
        
        self.mock_module_patcher = patch('camera.Module', MagicMock(spec=True))
        self.mock_module = self.mock_module_patcher.start()
        
        with patch('camera.Picamera2', return_value=self.mock_picamera2):
            self.camera_module = Camera(self.mock_config, self.mock_network_config, self.mock_system_config)

    def tearDown(self):
        self.mock_module_patcher.stop()

    def test_onStart_success(self):
        """Verifica l'inizializzazione e la configurazione della fotocamera."""
        self.camera_module.onStart()
        self.mock_picamera2.create_still_configuration.assert_called_once_with({"size": (1920, 1080)})
        self.mock_picamera2.configure.assert_called_once()
        self.mock_picamera2.start.assert_called_once()

    def test_handleMessage_take(self):
        """Verifica che il messaggio 'Take' attivi la cattura dell'immagine."""
        with patch.object(self.camera_module, 'takePicture') as mock_take_picture:
            self.camera_module.handleMessage({"Message": {"type": "Take"}})
            mock_take_picture.assert_called_once()
    
    def test_handleMessage_cuvette_present(self):
        """Verifica che il messaggio 'CuvettePresent' attivi la cattura dell'immagine."""
        with patch.object(self.camera_module, 'takePicture') as mock_take_picture:
            self.camera_module.handleMessage({"Message": {"type": "CuvettePresent"}})
            mock_take_picture.assert_called_once()
    
    def test_takePicture(self):
        """Verifica la cattura e l'invio dell'immagine."""
        # Simula un'immagine
        mock_image_array = np.zeros((100, 100, 3), dtype=np.uint8)
        self.camera_module.camera = self.mock_picamera2
        self.mock_picamera2.capture_array.return_value = mock_image_array
        
        # Simula la codifica dell'immagine
        mock_encoded_image = b"mock_encoded_image"
        with patch('cv2.imencode', return_value=(True, mock_encoded_image)), \
             patch('base64.b64encode', return_value=b"mock_base64_string"), \
             patch.object(self.camera_module, 'sendMessage') as mock_send_message:
            
            self.camera_module.takePicture()
            
            mock_send_message.assert_called_once_with("Analysis", "Analyze", {"image": "mock_base64_string"})

    def test_onStop(self):
        """Verifica che la fotocamera venga fermata al momento dello stop del modulo."""
        self.camera_module.camera = self.mock_picamera2
        self.mock_picamera2.started = True
        self.camera_module.onStop()
        self.mock_picamera2.stop.assert_called_once()