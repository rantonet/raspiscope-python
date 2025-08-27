import unittest
from unittest.mock import MagicMock, patch
import time
from cuvetteSensor import CuvetteSensor
import statistics

class TestCuvetteSensor(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "pin"                : 17,
            "poll_interval_s"    : 0.1,
            "calibration"        : {
                "samples"        : 3,
                "threshold_span" : 0.1
            }
        }
        self.mock_network_config = {}
        self.mock_system_config = {}
        
        self.mock_module_patcher = patch('cuvetteSensor.Module', MagicMock(spec=True))
        self.mock_module = self.mock_module_patcher.start()
        
        self.mock_input_device = MagicMock()
        self.mock_input_device.value = 1.0 # Default value
        
        self.mock_gpiozero_patcher = patch('cuvetteSensor.InputDevice', return_value=self.mock_input_device)
        self.mock_gpiozero_patcher.start()
        
        with patch('statistics.mean', return_value=0.5):
            self.sensor_module = CuvetteSensor(self.mock_config, self.mock_network_config, self.mock_system_config)

    def tearDown(self):
        self.mock_module_patcher.stop()
        self.mock_gpiozero_patcher.stop()

    def test_calibrate_success(self):
        """Verifica la corretta calibrazione del sensore."""
        self.sensor_module.calibrate()
        self.assertEqual(self.sensor_module.presenceThreshold, 0.4) # 0.5 - 0.1

    def test_checkPresence_state_change(self):
        """Verifica che il modulo invii messaggi quando lo stato del sensore cambia."""
        self.sensor_module.presenceThreshold = 0.5
        
        # Scenario 1: Nessuna cuvetta -> Cuvetta inserita
        self.sensor_module.isPresent = False
        self.mock_input_device.value = 0.4 # Sotto la soglia
        self.sensor_module.checkPresence()
        self.assertTrue(self.sensor_module.isPresent)
        self.mock_module.sendMessage.assert_called_once_with("All", "CuvettePresent")

        # Scenario 2: Cuvetta inserita -> Cuvetta rimossa
        self.mock_module.sendMessage.reset_mock()
        self.mock_input_device.value = 0.6 # Sopra la soglia
        self.sensor_module.checkPresence()
        self.assertFalse(self.sensor_module.isPresent)
        self.mock_module.sendMessage.assert_called_once_with("All", "CuvetteAbsent")

    def test_mainLoop_polling(self):
        """Verifica che il mainLoop chiami checkPresence a intervalli regolari."""
        with patch.object(self.sensor_module, 'checkPresence') as mock_check, \
             patch('time.sleep') as mock_sleep:
            
            # Ferma il loop dopo 2 iterazioni
            mock_check.side_effect = [None, self.sensor_module.stop_event.set]
            
            self.sensor_module.mainLoop()
            
            self.assertEqual(mock_check.call_count, 2)
            mock_sleep.assert_called_with(self.mock_config['poll_interval_s'])