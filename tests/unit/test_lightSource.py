import unittest
from unittest.mock import MagicMock, patch, call
import signal
from functools import wraps

# Mock hardware dependencies before importing the class
mockPixelStrip = MagicMock()
mockColor = MagicMock(side_effect=lambda r, g, b: (r, g, b))
sys_modules = {
    'rpi_ws281x': MagicMock(PixelStrip=mockPixelStrip, Color=mockColor)
}

with patch.dict('sys.modules', sys_modules):
    from lightSource import LightSource

class TestLightSource(unittest.TestCase):

    @patch('lightSource.ConfigLoader')
    def setUp(self, mockConfigLoader):
        print("Setting up for TestLightSource")
        self.mockConfig = {
            'network': {'address': 'localhost', 'port': 12345},
            'system': {'module_message_queue_timeout_s': 0.1},
            'pin': 18,
            'dma': 10,
            'brightness': 0.5,
            'pwm_channel': 0,
            'r': 255, 'g': 0, 'b': 0
        }
        mockConfigLoader.return_value.get_config.return_value = self.mockConfig

        with patch('module.Communicator') as self.mockCommunicator:
            self.mockCommInstance = MagicMock()
            self.mockCommunicator.return_value = self.mockCommInstance
            self.lightSource = LightSource(self.mockConfig['network'], self.mockConfig['system'])
            self.mockLed = MagicMock()
            mockPixelStrip.return_value = self.mockLed
        print("Setup complete for TestLightSource")

    def test_initialization(self):
        """
        Tests that the LightSource module is initialized with correct config values.
        """
        print("test_initialization: Starting test")
        self.assertEqual(self.lightSource.name, "LightSource")
        print("test_initialization: Asserted name")
        self.assertEqual(self.lightSource.pin, 18)
        print("test_initialization: Asserted pin")
        self.assertEqual(self.lightSource.brightness, 127) # 0.5 * 255
        print("test_initialization: Asserted brightness")
        self.assertEqual(self.lightSource.color, (255, 0, 0))
        print("test_initialization: Asserted color")
        self.assertIsNone(self.lightSource.led)
        print("test_initialization: Asserted led is None")
        print("test_initialization: Test finished")

    def test_onStartSuccess(self):
        """
        Tests the successful startup sequence.
        """
        print("test_onStartSuccess: Starting test")
        self.lightSource.onStart()
        print("test_onStartSuccess: onStart called")
        
        mockPixelStrip.assert_called_once_with(1, 18, 800000, 10, False, 127, 0)
        print("test_onStartSuccess: Asserted PixelStrip initialized")
        self.mockLed.begin.assert_called_once()
        print("test_onStartSuccess: Asserted led.begin called")
        # onStart calls turnOff, which calls setPixelColor and show
        self.mockLed.setPixelColor.assert_called_once_with(0, (0, 0, 0))
        print("test_onStartSuccess: Asserted setPixelColor called")
        self.mockLed.show.assert_called_once()
        print("test_onStartSuccess: Asserted show called")
        self.mockCommInstance.outgoingQueue.put.assert_any_call(unittest.mock.ANY)
        print("test_onStartSuccess: Asserted registration message sent")
        print("test_onStartSuccess: Test finished")

    def test_onStartFailure(self):
        """
        Tests the startup sequence when PixelStrip initialization fails.
        """
        print("test_onStartFailure: Starting test")
        mockPixelStrip.side_effect = Exception("Hardware error")
        self.lightSource.onStart()
        print("test_onStartFailure: onStart called")
        
        self.assertIsNone(self.lightSource.led)
        print("test_onStartFailure: Asserted led is None")
        # Check that an error was logged
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'ERROR')
        print("test_onStartFailure: Asserted log level is ERROR")
        self.assertIn("Could not initialize light source", logCall['Message']['payload']['message'])
        print("test_onStartFailure: Asserted log message content")
        print("test_onStartFailure: Test finished")

    def test_handleMessageTurnOn(self):
        """
        Tests handling of a 'TurnOn' message.
        """
        print("test_handleMessageTurnOn: Starting test")
        self.lightSource.led = self.mockLed
        self.lightSource.color = (100, 150, 200)
        message = {"Message": {"type": "TurnOn"}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageTurnOn: handleMessage called")
        
        self.mockLed.setPixelColor.assert_called_with(0, (100, 150, 200))
        print("test_handleMessageTurnOn: Asserted setPixelColor called")
        self.mockLed.show.assert_called_once()
        print("test_handleMessageTurnOn: Asserted show called")
        self.assertTrue(self.lightSource.is_on)
        print("test_handleMessageTurnOn: Asserted is_on is True")
        # Should send TurningOn and TurnedOn messages
        self.assertEqual(self.mockCommInstance.outgoingQueue.put.call_count, 3) # log + 2 messages
        print("test_handleMessageTurnOn: Asserted message count")
        print("test_handleMessageTurnOn: Test finished")

    def test_handleMessageTurnOff(self):
        """
        Tests handling of a 'TurnOff' message.
        """
        print("test_handleMessageTurnOff: Starting test")
        self.lightSource.led = self.mockLed
        self.lightSource.is_on = True
        message = {"Message": {"type": "TurnOff"}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageTurnOff: handleMessage called")
        
        self.mockLed.setPixelColor.assert_called_with(0, (0, 0, 0))
        print("test_handleMessageTurnOff: Asserted setPixelColor called")
        self.mockLed.show.assert_called_once()
        print("test_handleMessageTurnOff: Asserted show called")
        self.assertFalse(self.lightSource.is_on)
        print("test_handleMessageTurnOff: Asserted is_on is False")
        print("test_handleMessageTurnOff: Test finished")

    def test_handleMessageDim(self):
        """
        Tests handling of a 'Dim' message.
        """
        print("test_handleMessageDim: Starting test")
        self.lightSource.led = self.mockLed
        self.lightSource.is_on = True
        message = {"Message": {"type": "Dim", "payload": {"brightness": 50}}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageDim: handleMessage called")
        
        self.assertEqual(self.lightSource.brightness, 50)
        print("test_handleMessageDim: Asserted brightness value")
        self.mockLed.setBrightness.assert_called_once_with(50)
        print("test_handleMessageDim: Asserted setBrightness called")
        self.mockLed.show.assert_called_once() # Should be called if light is on
        print("test_handleMessageDim: Asserted show called")
        print("test_handleMessageDim: Test finished")

    def test_handleMessageDimInvalidPayload(self):
        """
        Tests that a 'Dim' message with invalid payload is ignored.
        """
        print("test_handleMessageDimInvalidPayload: Starting test")
        self.lightSource.led = self.mockLed
        message = {"Message": {"type": "Dim", "payload": {"brightness": "not a number"}}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageDimInvalidPayload: handleMessage called")
        
        self.mockLed.setBrightness.assert_not_called()
        print("test_handleMessageDimInvalidPayload: Asserted setBrightness not called")
        # Check that a warning was logged
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'WARNING')
        print("test_handleMessageDimInvalidPayload: Asserted log level is WARNING")
        print("test_handleMessageDimInvalidPayload: Test finished")

    def test_handleMessageSetColor(self):
        """
        Tests handling of a 'SetColor' message.
        """
        print("test_handleMessageSetColor: Starting test")
        self.lightSource.led = self.mockLed
        message = {"Message": {"type": "SetColor", "payload": {"r": 10, "g": 20, "b": 30}}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageSetColor: handleMessage called")
        
        self.assertEqual(self.lightSource.color, (10, 20, 30))
        print("test_handleMessageSetColor: Asserted color value")
        self.mockLed.setPixelColor.assert_called_with(0, (10, 20, 30))
        print("test_handleMessageSetColor: Asserted setPixelColor called")
        self.mockLed.show.assert_called_once()
        print("test_handleMessageSetColor: Asserted show called")
        print("test_handleMessageSetColor: Test finished")

    def test_handleMessageNoLed(self):
        """
        Tests that messages are ignored if the LED is not initialized.
        """
        print("test_handleMessageNoLed: Starting test")
        self.lightSource.led = None
        message = {"Message": {"type": "TurnOn"}}
        
        self.lightSource.handleMessage(message)
        print("test_handleMessageNoLed: handleMessage called")
        
        self.mockLed.setPixelColor.assert_not_called()
        print("test_handleMessageNoLed: Asserted setPixelColor not called")
        # Check that a warning was logged
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertEqual(logCall['Message']['payload']['level'], 'WARNING')
        print("test_handleMessageNoLed: Asserted log level is WARNING")
        self.assertIn("not available", logCall['Message']['payload']['message'])
        print("test_handleMessageNoLed: Asserted log message content")
        print("test_handleMessageNoLed: Test finished")

    def test_onStop(self):
        """
        Tests that onStop turns the light off.
        """
        print("test_onStop: Starting test")
        self.lightSource.led = self.mockLed
        self.lightSource.onStop()
        print("test_onStop: onStop called")
        
        self.mockLed.setPixelColor.assert_called_with(0, (0, 0, 0))
        print("test_onStop: Asserted setPixelColor called")
        self.mockLed.show.assert_called_once()
        print("test_onStop: Asserted show called")
        print("test_onStop: Test finished")
