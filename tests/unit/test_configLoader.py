import unittest
from unittest.mock import patch, mock_open
import sys
import json
import signal
from functools import wraps

from configLoader import ConfigLoader

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

class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        print("Setting up for TestConfigLoader")
        self.validConfig = {
            "network": {"address": "127.0.0.1", "port": 1025},
            "system": {"module_message_queue_timeout_s": 0.1},
            "modules": {"camera": {"enabled": True}}
        }
        self.validConfigJson = json.dumps(self.validConfig)
        print("Setup complete for TestConfigLoader")

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": "json"}')
    @patch("sys.exit")
    @patch("builtins.print")
    def test_invalidJson(self, mockPrint, mockExit, mockFile):
        """
        Tests if the ConfigLoader exits when the JSON is malformed.
        """
        print("test_invalidJson: Starting test")
        ConfigLoader("dummy_path.json")
        print("test_invalidJson: ConfigLoader initialized with invalid JSON")
        mockExit.assert_called_once_with(1)
        print("test_invalidJson: Asserted sys.exit called")
        self.assertIn("is not a valid JSON file", mockPrint.call_args_list[0][0][0])
        print("test_invalidJson: Asserted error message printed")
        print("test_invalidJson: Test finished")

    @timeout(60)
    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("sys.exit")
    @patch("builtins.print")
    def test_fileNotFound(self, mockPrint, mockExit, mockOpen):
        """
        Tests if the ConfigLoader exits when the config file is not found.
        """
        print("test_fileNotFound: Starting test")
        ConfigLoader("non_existent_path.json")
        print("test_fileNotFound: ConfigLoader initialized with non-existent file")
        mockExit.assert_called_once_with(1)
        print("test_fileNotFound: Asserted sys.exit called")
        mockPrint.assert_called_with("CRITICAL ERROR: The configuration file 'non_existent_path.json' was not found.", file=sys.stderr)
        print("test_fileNotFound: Asserted error message printed")
        print("test_fileNotFound: Test finished")

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open, read_data='{"network": {}, "system": {}}') # Missing "modules"
    @patch("sys.exit")
    @patch("builtins.print")
    def test_missingRequiredKeys(self, mockPrint, mockExit, mockFile):
        """
        Tests if the ConfigLoader exits when required keys are missing.
        """
        print("test_missingRequiredKeys: Starting test")
        ConfigLoader("dummy_path.json")
        print("test_missingRequiredKeys: ConfigLoader initialized with missing keys")
        mockExit.assert_called_once_with(1)
        print("test_missingRequiredKeys: Asserted sys.exit called")
        mockPrint.assert_called_with("CRITICAL ERROR: The required key 'modules' is missing from the configuration file.", file=sys.stderr)
        print("test_missingRequiredKeys: Asserted error message printed")
        print("test_missingRequiredKeys: Test finished")

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open)
    def test_successfulLoading(self, mockFile):
        """
        Tests if the ConfigLoader successfully loads a valid config file.
        """
        print("test_successfulLoading: Starting test")
        mockFile.return_value.read.return_value = self.validConfigJson
        with patch("sys.exit") as mockExit:
            loader = ConfigLoader("dummy_path.json")
            print("test_successfulLoading: ConfigLoader initialized with valid config")
            mockExit.assert_not_called()
            print("test_successfulLoading: Asserted sys.exit not called")
            self.assertIsNotNone(loader.get_config())
            print("test_successfulLoading: Asserted config is not None")
        print("test_successfulLoading: Test finished")

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open)
    def test_getConfig(self, mockFile):
        """
        Tests if get_config returns the correct configuration dictionary.
        """
        print("test_getConfig: Starting test")
        mockFile.return_value.read.return_value = self.validConfigJson
        loader = ConfigLoader("dummy_path.json")
        print("test_getConfig: ConfigLoader initialized with valid config")
        self.assertEqual(loader.get_config(), self.validConfig)
        print("test_getConfig: Asserted get_config returns correct config")
        print("test_getConfig: Test finished")
