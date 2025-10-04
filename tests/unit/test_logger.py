import unittest
from unittest.mock import MagicMock, patch, mock_open, call
import json
import time
import signal
from functools import wraps

# Mock the dependencies before importing the class under test
from module import Module
from logger import Logger

class TestLogger(unittest.TestCase):

    @patch('logger.ConfigLoader')
    def setUp(self, mockConfigLoader):
        print("setUp: Starting test setup")
        self.mockConfig = {
            "network": {"address": "localhost", "port": 12345},
            "system": {"module_message_queue_timeout_s": 0.1},
            "modules": {
                "logger": {
                    "destination": "stdout",
                    "path": "test.log"
                }
            }
        }
        print("setUp: Mocking ConfigLoader")
        mockConfigLoader.return_value.get_config.return_value = self.mockConfig

        # We patch the Communicator inside the Module's __init__ via the logger
        print("setUp: Patching Communicator")
        with patch('module.Communicator') as self.mockCommunicator:
            self.mockCommInstance = MagicMock()
            self.mockCommunicator.return_value = self.mockCommInstance
            print("setUp: Initializing Logger for testing")
            self.logger = Logger(self.mockConfig['network'], self.mockConfig['system'])
        print("setUp: Test setup finished")

    def test_initializationSingleDestination(self):
        """
        Tests logger initialization with a single destination string.
        """
        print("test_initializationSingleDestination: Starting test")
        print("test_initializationSingleDestination: Asserting logger name")
        self.assertEqual(self.logger.name, "Logger")
        print("test_initializationSingleDestination: Asserting communicator instance type")
        self.assertIsInstance(self.logger.communicator, MagicMock)
        print("test_initializationSingleDestination: Asserting destinations")
        self.assertEqual(self.logger.destinations, ["stdout"])
        print("test_initializationSingleDestination: Test finished")

    @patch('logger.ConfigLoader')
    def test_initializationMultipleDestinations(self, mockConfigLoader):
        """
        Tests logger initialization with a list of destinations.
        """
        print("test_initializationMultipleDestinations: Starting test")
        print("test_initializationMultipleDestinations: Mocking config for multiple destinations")
        self.mockConfig['modules']['logger']['destination'] = ["file", "websocket"]
        mockConfigLoader.return_value.get_config.return_value = self.mockConfig
        with patch('module.Communicator'):
            print("test_initializationMultipleDestinations: Initializing logger with new config")
            logger = Logger(self.mockConfig['network'], self.mockConfig['system'])
            print("test_initializationMultipleDestinations: Asserting destinations")
            self.assertEqual(logger.destinations, ["file", "websocket"])
        print("test_initializationMultipleDestinations: Test finished")

    @patch("builtins.open", new_callable=mock_open)
    def test_onStartFileDestination(self, mockFile):
        """
        Tests that onStart opens a file when 'file' is a destination.
        """
        print("test_onStartFileDestination: Starting test")
        self.logger.destinations = ["file"]
        print("test_onStartFileDestination: Calling onStart")
        self.logger.onStart()
        
        print("test_onStartFileDestination: Asserting file was opened")
        mockFile.assert_called_once_with("test.log", "a")
        print("test_onStartFileDestination: Asserting log_file is not None")
        self.assertIsNotNone(self.logger.log_file)
        print("test_onStartFileDestination: Asserting registration message was sent")
        self.mockCommInstance.outgoingQueue.put.assert_any_call(
            unittest.mock.ANY
        )
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        print("test_onStartFileDestination: Asserting message destination")
        self.assertEqual(sentMessage['Destination'], 'EventManager')
        print("test_onStartFileDestination: Test finished")

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_onStartFileOpenError(self, mockFile):
        """
        Tests that an error during file opening is handled correctly.
        """
        print("test_onStartFileOpenError: Starting test")
        self.logger.destinations = ["file"]
        print("test_onStartFileOpenError: Calling onStart")
        self.logger.onStart()
        
        print("test_onStartFileOpenError: Asserting log_file is None")
        self.assertIsNone(self.logger.log_file)
        print("test_onStartFileOpenError: Asserting 'stdout' is in destinations")
        self.assertIn("stdout", self.logger.destinations)
        print("test_onStartFileOpenError: Asserting 'file' is not in destinations")
        self.assertNotIn("file", self.logger.destinations)
        sentMessage = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        print("test_onStartFileOpenError: Asserting error log level")
        self.assertEqual(sentMessage['Message']['payload']['level'], 'ERROR')
        print("test_onStartFileOpenError: Asserting error log message")
        self.assertIn("Could not open log file", sentMessage['Message']['payload']['message'])
        print("test_onStartFileOpenError: Test finished")

    @patch('time.strftime', return_value="2023-10-27 10:00:00")
    @patch('builtins.print')
    def test_handleMessageLogToStdout(self, mockPrint, mockTime):
        """
        Tests that a LogMessage is correctly printed to stdout.
        """
        print("test_handleMessageLogToStdout: Starting test")
        self.logger.destinations = ["stdout"]
        logMessage = {
            "Sender": "TestModule",
            "Message": {
                "type": "LogMessage",
                "payload": {"level": "DEBUG", "message": "A debug message"}
            }
        }
        print("test_handleMessageLogToStdout: Calling handleMessage")
        self.logger.handleMessage(logMessage)
        
        expectedOutput = "[2023-10-27 10:00:00] [TestModule] (DEBUG): A debug message"
        print("test_handleMessageLogToStdout: Asserting print was called with correct output")
        mockPrint.assert_called_once_with(expectedOutput)
        print("test_handleMessageLogToStdout: Test finished")

    @patch('time.strftime', return_value="2023-10-27 10:00:00")
    @patch("builtins.open", new_callable=mock_open)
    def test_handleMessageLogToFile(self, mockFile, mockTime):
        """
        Tests that a LogMessage is correctly written to a file.
        """
        print("test_handleMessageLogToFile: Starting test")
        self.logger.destinations = ["file"]
        self.logger.log_file = mockFile()

        logMessage = {
            "Sender": "TestModule",
            "Message": {
                "type": "LogMessage",
                "payload": {"level": "WARNING", "message": "A warning"}
            }
        }
        print("test_handleMessageLogToFile: Calling handleMessage")
        self.logger.handleMessage(logMessage)

        expectedLogEntry = {
            "timestamp": "2023-10-27 10:00:00",
            "sender": "TestModule",
            "level": "WARNING",
            "message": "A warning"
        }
        
        print("test_handleMessageLogToFile: Asserting file write calls")
        mockFile().write.assert_any_call(json.dumps(expectedLogEntry))
        mockFile().write.assert_any_call('\n')
        print("test_handleMessageLogToFile: Asserting file flush was called")
        mockFile().flush.assert_called_once()
        print("test_handleMessageLogToFile: Test finished")

    @patch('time.strftime', return_value="2023-10-27 10:00:00")
    @patch('builtins.print')
    def test_handleMessageLogToWebsocket(self, mockPrint, mockTime):
        """
        Tests the fallback behavior for the websocket destination.
        """
        print("test_handleMessageLogToWebsocket: Starting test")
        self.logger.destinations = ["websocket"]
        logMessage = {
            "Sender": "TestModule",
            "Message": {
                "type": "LogMessage",
                "payload": {"level": "INFO", "message": "WebSocket test"}
            }
        }
        print("test_handleMessageLogToWebsocket: Calling handleMessage")
        self.logger.handleMessage(logMessage)
        
        expectedOutput = "[2023-10-27 10:00:00] [TestModule] (INFO): WebSocket test [Via WebSocket]"
        print("test_handleMessageLogToWebsocket: Asserting print was called with correct output")
        mockPrint.assert_called_once_with(expectedOutput)
        print("test_handleMessageLogToWebsocket: Test finished")

    @patch('builtins.print')
    def test_handleNonLogMessage(self, mockPrint):
        """
        Tests that non-LogMessage types are handled as generic events.
        """
        print("test_handleNonLogMessage: Starting test")
        self.logger.destinations = ["stdout"]
        eventMessage = {
            "Sender": "OtherModule",
            "Message": {"type": "CustomEvent"}
        }
        print("test_handleNonLogMessage: Calling handleMessage")
        self.logger.handleMessage(eventMessage)
        print("test_handleNonLogMessage: Asserting print was called with correct output")
        mockPrint.assert_called_once_with("[OtherModule] - Received event 'CustomEvent'")
        print("test_handleNonLogMessage: Test finished")

    def test_onStopClosesFile(self):
        """
        Tests that onStop closes the log file if it is open.
        """
        print("test_onStopClosesFile: Starting test")
        self.logger.destinations = ["file"]
        self.logger.log_file = MagicMock()
        print("test_onStopClosesFile: Calling onStop")
        self.logger.onStop()
        print("test_onStopClosesFile: Asserting file close was called")
        self.logger.log_file.close.assert_called_once()
        print("test_onStopClosesFile: Test finished")

    def test_onStopNoFile(self):
        """
        Tests that onStop does not error if the file is not open.
        """
        print("test_onStopNoFile: Starting test")
        self.logger.destinations = ["stdout"]
        self.logger.log_file = None
        try:
            print("test_onStopNoFile: Calling onStop")
            self.logger.onStop()
        except Exception as e:
            self.fail(f"onStop() raised an exception unexpectedly: {e}")
        print("test_onStopNoFile: Test finished")