import unittest
import json
import sys
from unittest.mock import patch, mock_open
from configLoader import loadConfig

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        # Reset the cached config for each test
        loadConfig._config = None

    def test_loadConfig_success(self):
        """Verifies the successful loading of a valid configuration file."""
        valid_config_data = {
            "network": {},
            "system": {},
            "modules": {}
        }
        json_data = json.dumps(valid_config_data)
        
        with patch('builtins.open', mock_open(read_data=json_data)), \
             patch('json.load', return_value=valid_config_data):
            config = loadConfig("config.json")
            self.assertEqual(config, valid_config_data)
            self.assertEqual(loadConfig._config, valid_config_data)

    def test_loadConfig_file_not_found(self):
        """Verifies the handling of a FileNotFoundError."""
        with patch('builtins.open', side_effect=FileNotFoundError), \
             patch('sys.exit') as mock_exit, \
             patch('builtins.print'): # Suppress print
            loadConfig("non_existent_file.json")
            mock_exit.assert_called_once_with(1)
            
    def test_loadConfig_invalid_json(self):
        """Verifies the handling of invalid JSON."""
        invalid_json_data = "{'network': 'invalid'"
        with patch('builtins.open', mock_open(read_data=invalid_json_data)), \
             patch('json.JSONDecodeError', create=True) as mock_json_error, \
             patch('sys.exit') as mock_exit, \
             patch('builtins.print'): # Suppress print
            mock_json_error.msg = "Mock error"
            mock_json_error.doc = ""
            mock_json_error.pos = 0
            
            with patch('json.load', side_effect=mock_json_error):
                loadConfig("invalid_config.json")
                mock_exit.assert_called_once_with(1)

    def test_loadConfig_missing_key(self):
        """Verifies the handling of a missing key."""
        incomplete_config_data = {
            "network": {},
            "system": {}
        }
        json_data = json.dumps(incomplete_config_data)
        
        with patch('builtins.open', mock_open(read_data=json_data)), \
             patch('json.load', return_value=incomplete_config_data), \
             patch('sys.exit') as mock_exit, \
             patch('builtins.print'): # Suppress print
            loadConfig("incomplete_config.json")
            mock_exit.assert_called_once_with(1)