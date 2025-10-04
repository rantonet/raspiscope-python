import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import json
import signal
from functools import wraps
import sys
import time
import statistics

# Mock hardware dependencies before import
mockInputDevice = MagicMock()
sys_modules = {
    'gpiozero': MagicMock(InputDevice=mockInputDevice, GPIOZeroError=Exception)
}

with patch.dict('sys.modules', sys_modules):
    from cuvetteSensor import CuvetteSensor

class TestCuvetteSensor(unittest.TestCase):

    @patch('cuvetteSensor.ConfigLoader')
    def setUp(self, mockConfigLoader):
        print("Setting up for TestCuvetteSensor")
        self.mockConfig = {
            "network": {"address": "localhost", "port": 12345},
            "system": {"module_message_queue_timeout_s": 0.1},
            "modules": {
                "cuvetteSensor": {
                    "pin": 17,
                    "poll_interval_s": 0.05,
                    "calibration": {
                        "samples": 5,
                        "threshold_span": 0.1
                    }
                }
            }
        }
        mockConfigLoader.return_value.get_config.return_value = self.mockConfig

        with patch('module.Communicator') as self.mockCommunicator:
            self.mockCommInstance = MagicMock()
            self.mockCommunicator.return_value = self.mockCommInstance
            self.sensorModule = CuvetteSensor(self.mockConfig['network'], self.mockConfig['system'])
            self.mockSensorDevice = MagicMock()
            mockInputDevice.return_value = self.mockSensorDevice
        print("Setup complete for TestCuvetteSensor")

    def test_initialization(self):
        """
        Tests that the CuvetteSensor is initialized with correct config values.
        """
        print("test_initialization: Starting test")
        self.assertEqual(self.sensorModule.name, "CuvetteSensor")
        print("test_initialization: Asserted name")
        self.assertEqual(self.sensorModule.inputPin, 17)
        print("test_initialization: Asserted inputPin")
        self.assertEqual(self.sensorModule.pollInterval, 0.05)
        print("test_initialization: Asserted pollInterval")
        self.assertEqual(self.sensorModule.numSamples, 5)
        print("test_initialization: Asserted numSamples")
        self.assertIsNone(self.sensorModule.sensor)
        print("test_initialization: Asserted sensor is None")
        print("test_initialization: Test finished")

    def test_onStartSuccess(self):
        """
        Tests the successful startup sequence.
        """
        print("test_onStartSuccess: Starting test")
        self.sensorModule.onStart()
        print("test_onStartSuccess: onStart called")
        mockInputDevice.assert_called_once_with(17)
        print("test_onStartSuccess: Asserted InputDevice called with correct pin")
        self.assertIsNotNone(self.sensorModule.sensor)
        print("test_onStartSuccess: Asserted sensor is not None")
        self.mockCommInstance.outgoingQueue.put.assert_any_call(unittest.mock.ANY)
        print("test_onStartSuccess: Asserted registration message sent")
        print("test_onStartSuccess: Test finished")

    def test_onStartFailure(self):
        """
        Tests the startup sequence when InputDevice initialization fails.
        """
        print("test_onStartFailure: Starting test")
        mockInputDevice.side_effect = Exception("GPIO error")
        self.sensorModule.onStart()
        print("test_onStartFailure: onStart called")
        self.assertIsNone(self.sensorModule.sensor)
        print("test_onStartFailure: Asserted sensor is None")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        print("test_onStartFailure: Asserted log level is ERROR")
        self.assertIn("Could not initialize sensor", logCall['Message']['payload']['message'])
        print("test_onStartFailure: Asserted log message content")
        print("test_onStartFailure: Test finished")

    def test_checkPresenceBecomesPresent(self):
        """
        Tests the state change from absent to present.
        """
        print("test_checkPresenceBecomesPresent: Starting test")
        self.sensorModule.sensor = self.mockSensorDevice
        self.sensorModule.presenceThreshold = 0.5
        self.sensorModule.isPresent = False
        self.mockSensorDevice.value = 0.2 # Below threshold

        self.sensorModule.checkPresence()
        print("test_checkPresenceBecomesPresent: checkPresence called")

        self.assertTrue(self.sensorModule.isPresent)
        print("test_checkPresenceBecomesPresent: Asserted isPresent is True")
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage['Destination'], 'Camera')
        print("test_checkPresenceBecomesPresent: Asserted destination is Camera")
        self.assertEqual(sentMessage['Message']['type'], 'CuvettePresent')
        print("test_checkPresenceBecomesPresent: Asserted message type is CuvettePresent")
        print("test_checkPresenceBecomesPresent: Test finished")

    def test_checkPresenceBecomesAbsent(self):
        """
        Tests the state change from present to absent.
        """
        print("test_checkPresenceBecomesAbsent: Starting test")
        self.sensorModule.sensor = self.mockSensorDevice
        self.sensorModule.presenceThreshold = 0.5
        self.sensorModule.isPresent = True
        self.mockSensorDevice.value = 0.8 # Above threshold

        self.sensorModule.checkPresence()
        print("test_checkPresenceBecomesAbsent: checkPresence called")

        self.assertFalse(self.sensorModule.isPresent)
        print("test_checkPresenceBecomesAbsent: Asserted isPresent is False")
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage['Destination'], 'Camera')
        print("test_checkPresenceBecomesAbsent: Asserted destination is Camera")
        self.assertEqual(sentMessage['Message']['type'], 'CuvetteAbsent')
        print("test_checkPresenceBecomesAbsent: Asserted message type is CuvetteAbsent")
        print("test_checkPresenceBecomesAbsent: Test finished")

    def test_checkPresenceNoChange(self):
        """
        Tests that no message is sent when the state does not change.
        """
        print("test_checkPresenceNoChange: Starting test")
        self.sensorModule.sensor = self.mockSensorDevice
        self.sensorModule.presenceThreshold = 0.5
        self.sensorModule.isPresent = True
        self.mockSensorDevice.value = 0.2 # Still present

        self.sensorModule.checkPresence()
        print("test_checkPresenceNoChange: checkPresence called")

        self.mockCommInstance.outgoingQueue.put.assert_not_called()
        print("test_checkPresenceNoChange: Asserted outgoingQueue.put not called")
        print("test_checkPresenceNoChange: Test finished")

    @patch('time.sleep')
    @patch('statistics.mean', return_value=0.8)
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"modules": {"cuvetteSensor": {}}}))
    def test_calibrateSuccess(self, mockFile, mockMean, mockSleep):
        """
        Tests the successful calibration sequence.
        """
        print("test_calibrateSuccess: Starting test")
        self.sensorModule.sensor = self.mockSensorDevice
        self.mockSensorDevice.value = 0.8 # Simulate sensor reading
        self.sensorModule.numSamples = 5

        self.sensorModule.calibrate()
        print("test_calibrateSuccess: calibrate called")

        self.assertEqual(mockSleep.call_count, 5)
        print("test_calibrateSuccess: Asserted sleep call count")
        self.assertEqual(len(mockMean.call_args[0][0]), 5) # 5 samples
        print("test_calibrateSuccess: Asserted number of samples for mean")
        self.assertEqual(self.sensorModule.presenceThreshold, 0.8 - self.sensorModule.thresholdSpan)
        print("test_calibrateSuccess: Asserted presenceThreshold calculation")

        # Check for correct messages
        self.assertIn(call(('All', {'Sender': 'CuvetteSensor', 'Destination': 'All', 'Message': {'type': 'CalibrationStarted', 'payload': {'message': 'Starting cuvette sensor calibration (5 samples).'}}})), self.mockCommInstance.outgoingQueue.put.call_args_list)
        print("test_calibrateSuccess: Asserted CalibrationStarted message sent")
        self.assertIn(call(('All', {'Sender': 'CuvetteSensor', 'Destination': 'All', 'Message': {'type': 'CalibrationComplete', 'payload': {'threshold': self.sensorModule.presenceThreshold, 'message': 'Calibration complete.'}}})), self.mockCommInstance.outgoingQueue.put.call_args_list)
        print("test_calibrateSuccess: Asserted CalibrationComplete message sent")

        # Check that config saving was attempted
        mockFile.assert_called_with('config.json', 'r+')
        print("test_calibrateSuccess: Asserted config file opened for writing")
        mockFile().seek.assert_called_once_with(0)
        print("test_calibrateSuccess: Asserted seek(0) on config file")
        mockFile().truncate.assert_called_once()
        print("test_calibrateSuccess: Asserted truncate on config file")
        print("test_calibrateSuccess: Test finished")

    def test_calibrateNoSensor(self):
        """
        Tests that calibrate sends an error if the sensor is not initialized.
        """
        print("test_calibrateNoSensor: Starting test")
        self.sensorModule.sensor = None
        self.sensorModule.calibrate()
        print("test_calibrateNoSensor: calibrate called")

        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(sentMessage[0], 'All')
        print("test_calibrateNoSensor: Asserted destination is All")
        self.assertEqual(sentMessage[1]['Message']['type'], 'CalibrationError')
        print("test_calibrateNoSensor: Asserted message type is CalibrationError")
        self.assertIn("sensor not initialized", sentMessage[1]['Message']['payload']['message'])
        print("test_calibrateNoSensor: Asserted error message content")
        print("test_calibrateNoSensor: Test finished")
