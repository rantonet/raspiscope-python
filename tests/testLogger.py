import unittest
import json
import os
from unittest.mock import MagicMock, patch, mock_open
import time
from logger import Logger

class TestLogger(unittest.TestCase):
    def setUp(self):
        self.mock_network_config = {}
        self.mock_system_config = {}
        
        self.logger_config_stdout = {"destination": ["stdout"]}
        self.logger_config_file = {"destination": ["file"], "path": "test_log.json"}
        self.logger_config_websocket = {"destination": ["websocket"]}

    @patch('builtins.print')
    def test_handle_stdout_destination(self, mock_print):
        """Verifica che i messaggi di log siano stampati su stdout."""
        logger_module = Logger(self.logger_config_stdout, self.mock_network_config, self.mock_system_config)
        logger_module.handleMessage({
            "Sender": "TestModule",
            "Message": {
                "type": "LogMessage",
                "payload": {
                    "level": "INFO",
                    "message": "Test message."
                }
            }
        })
        mock_print.assert_called_once()
        self.assertIn("[TestModule] (INFO): Test message.", mock_print.call_args[0][0])

    def test_handle_file_destination(self):
        """Verifica che i messaggi di log siano scritti su un file."""
        mock_file_open = mock_open()
        with patch('builtins.open', mock_file_open), \
             patch.object(time, 'strftime', return_value="2025-01-01 12:00:00"):
            
            logger_module = Logger(self.logger_config_file, self.mock_network_config, self.mock_system_config)
            logger_module.onStart()
            
            logger_module.handleMessage({
                "Sender": "TestModule",
                "Message": {
                    "type": "LogMessage",
                    "payload": {
                        "level": "INFO",
                        "message": "File message."
                    }
                }
            })
            
            mock_file_open.assert_called_once_with('test_log.json', 'a')
            mock_file_open().write.assert_called_once_with(
                '{"timestamp": "2025-01-01 12:00:00", "sender": "TestModule", "level": "INFO", "message": "File message."}\n'
            )
            mock_file_open().flush.assert_called_once()
            
            logger_module.onStop()
            mock_file_open().close.assert_called_once()
    
    @patch('builtins.print')
    def test_handle_file_and_stdout_destination(self, mock_print):
        """Verifica che i messaggi siano inviati sia al file che a stdout."""
        mock_file_open = mock_open()
        with patch('builtins.open', mock_file_open), \
             patch.object(time, 'strftime', return_value="2025-01-01 12:00:00"):
            
            combined_config = {"destination": ["stdout", "file"], "path": "combined_log.json"}
            logger_module = Logger(combined_config, self.mock_network_config, self.mock_system_config)
            logger_module.onStart()

            logger_module.handleMessage({
                "Sender": "TestModule",
                "Message": {
                    "type": "LogMessage",
                    "payload": {
                        "level": "INFO",
                        "message": "Combined message."
                    }
                }
            })
            
            mock_print.assert_called_once()
            mock_file_open().write.assert_called_once()
            mock_file_open().flush.assert_called_once()

    def test_onStop(self):
        """Verifica che onStop chiuda il file di log."""
        mock_file_open = mock_open()
        with patch('builtins.open', mock_file_open):
            logger_module = Logger(self.logger_config_file, self.mock_network_config, self.mock_system_config)
            logger_module.onStart()
            logger_module.onStop()
            mock_file_open().close.assert_called_once()