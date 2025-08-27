import unittest
from unittest.mock import MagicMock, patch, call
import time
from cuvetteSensor import CuvetteSensor
import statistics
from gpiozero import GPIOZeroError

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

    def test_onStart_success(self):
        """Verifies the correct initialization of the sensor and calibration."""
        with patch.object(self.sensor_module, 'calibrate') as mock_calibrate:
            self.sensor_module.onStart()
            self.mock_module.log.assert_called_once_with("INFO", "Cuvette sensor initialized.")
            mock_calibrate.assert_called_once()
            
    def test_onStart_error(self):
        """Verifies the handling of a sensor initialization error."""
        with patch('cuvetteSensor.InputDevice', side_effect=GPIOZeroError("Test error")):
            self.sensor_module.onStart()
            self.mock_module.log.assert_called_once_with("ERROR", "Could not initialize sensor on pin 17. Details: Test error")
            self.assertIsNone(self.sensor_module.sensor)

    def test_calibrate_success(self):
        """Verifies the correct calibration of the sensor."""
        self.sensor_module.sensor = self.mock_input_device
        self.sensor_module.calibrate()
        self.assertEqual(self.sensor_module.presenceThreshold, 0.4) # 0.5 - 0.1
        self.mock_module.sendMessage.assert_has_calls([
            call("All", "CalibrationStarted", {"message": "Starting cuvette sensor calibration (3 samples)..."}),
            call("All", "CalibrationComplete", {"threshold": 0.4, "message": "Calibration complete."})
        ])

    def test_calibrate_error_no_sensor(self):
        """Verifies logging an error if the sensor is not initialized."""
        self.sensor_module.sensor = None
        self.sensor_module.calibrate()
        self.mock_module.sendMessage.assert_called_once_with("All", "CalibrationError", {"message": "Cannot calibrate: sensor not initialized."})

    def test_checkPresence_state_change(self):
        """Verifies that the module sends messages when the sensor state changes."""
        self.sensor_module.presenceThreshold = 0.5
        
        # Scenario 1: No cuvette -> Cuvette inserted
        self.sensor_module.isPresent = False
        self.sensor_module.sensor = self.mock_input_device
        self.mock_input_device.value = 0.4 # Below the threshold
        self.sensor_module.checkPresence()
        self.assertTrue(self.sensor_module.isPresent)
        self.mock_module.sendMessage.assert_has_calls([
            call("All", "CuvettePresent"),
            call("Logger", "LogMessage", {"level": "INFO", "message": "Cuvette inserted."})
        ])

        # Scenario 2: Cuvette inserted -> Cuvette removed
        self.mock_module.sendMessage.reset_mock()
        self.mock_input_device.value = 0.6 # Above the threshold
        self.sensor_module.checkPresence()
        self.assertFalse(self.sensor_module.isPresent)
        self.mock_module.sendMessage.assert_has_calls([
            call("All", "CuvetteAbsent"),
            call("Logger", "LogMessage", {"level": "INFO", "message": "Cuvette removed."})
        ])

    def test_mainLoop_polling(self):
        """Verifies that the mainLoop calls checkPresence at regular intervals."""
        self.sensor_module.sensor = self.mock_input_device
        with patch.object(self.sensor_module, 'checkPresence') as mock_check, \
             patch.object(self.sensor_module, 'stop_event') as mock_stop_event, \
             patch('time.sleep') as mock_sleep:
            
            mock_stop_event.is_set.side_effect = [False, False, True]
            self.sensor_module.mainLoop()
            
            self.assertEqual(mock_check.call_count, 2)
            mock_sleep.assert_called_with(self.mock_config['poll_interval_s'])