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
        self.validConfig = {
            "network": {"address": "127.0.0.1", "port": 1025},
            "system": {"module_message_queue_timeout_s": 0.1},
            "modules": {"camera": {"enabled": True}}
        }
        self.validConfigJson = json.dumps(self.validConfig)

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open, read_data=''''''{"invalid": "json"}'''''')
    @patch("sys.exit")
    @patch("builtins.print")
    def test_invalidJson(self, mockPrint, mockExit, mockFile):
        """
        Tests if the ConfigLoader exits when the JSON is malformed.
        """
        ConfigLoader("dummy_path.json")
        mockExit.assert_called_once_with(1)
        self.assertIn("is not a valid JSON file", mockPrint.call_args_list[0][0][0])

    @timeout(60)
    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("sys.exit")
    @patch("builtins.print")
    def test_fileNotFound(self, mockPrint, mockExit, mockOpen):
        """
        Tests if the ConfigLoader exits when the config file is not found.
        """
        ConfigLoader("non_existent_path.json")
        mockExit.assert_called_once_with(1)
        mockPrint.assert_called_with("CRITICAL ERROR: The configuration file 'non_existent_path.json' was not found.", file=sys.stderr)

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open, read_data='{"network": {}, "system": {}}') # Missing "modules"
    @patch("sys.exit")
    @patch("builtins.print")
    def test_missingRequiredKeys(self, mockPrint, mockExit, mockFile):
        """
        Tests if the ConfigLoader exits when required keys are missing.
        """
        ConfigLoader("dummy_path.json")
        mockExit.assert_called_once_with(1)
        mockPrint.assert_called_with("CRITICAL ERROR: The required key 'modules' is missing from the configuration file.", file=sys.stderr)

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open)
    def test_successfulLoading(self, mockFile):
        """
        Tests if the ConfigLoader successfully loads a valid config file.
        """
        mockFile.return_value.read.return_value = self.validConfigJson
        with patch("sys.exit") as mockExit:
            loader = ConfigLoader("dummy_path.json")
            mockExit.assert_not_called()
            self.assertIsNotNone(loader.get_config())

    @timeout(60)
    @patch("builtins.open", new_callable=mock_open)
    def test_getConfig(self, mockFile):
        """
        Tests if get_config returns the correct configuration dictionary.
        """
        mockFile.return_value.read.return_value = self.validConfigJson
        loader = ConfigLoader("dummy_path.json")
        self.assertEqual(loader.get_config(), self.validConfig)