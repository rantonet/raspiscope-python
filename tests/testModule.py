import unittest
from unittest.mock import MagicMock, patch, call
from queue import Empty
import time
from module import Module
import json

class TestModule(unittest.TestCase):
    def setUp(self):
        self.mock_network_config = {"address": "127.0.0.1", "port": 1025}
        self.mock_system_config = {"module_message_queue_timeout_s": 0.1}
        self.mock_communicator = MagicMock()
        with patch('module.Communicator', return_value=self.mock_communicator):
            self.test_module = Module("TestModule", self.mock_network_config, self.mock_system_config)

    def test_run_lifecycle(self):
        """Verifica che il metodo run() chiami onStart, mainLoop e onStop."""
        with patch.object(self.test_module, 'onStart') as mock_onStart, \
             patch.object(self.test_module, 'mainLoop') as mock_mainLoop, \
             patch.object(self.test_module, 'onStop') as mock_onStop, \
             patch.object(self.test_module, 'log') as mock_log:
            
            mock_mainLoop.side_effect = self.test_module.stopEvent.set
            self.test_module.run()
            
            mock_onStart.assert_called_once()
            mock_mainLoop.assert_called_once()
            mock_onStop.assert_called_once()
            self.assertEqual(mock_log.call_count, 2)
            mock_log.assert_has_calls([
                call("INFO", "Module 'TestModule' starting."),
                call("INFO", "Module 'TestModule' terminated.")
            ])

    def test_mainLoop_message_handling(self):
        """Verifica che il mainLoop gestisca i messaggi in arrivo e il segnale di stop."""
        mock_message = {"Message": {"type": "TestMessage", "payload": {}}}
        self.mock_communicator.incomingQueue.get.side_effect = [
            mock_message,
            {"Message": {"type": "Stop"}}
        ]
        
        with patch.object(self.test_module, 'handleMessage') as mock_handleMessage, \
             patch.object(self.test_module, 'log') as mock_log:
            self.test_module.mainLoop()
            
            mock_handleMessage.assert_called_once_with(mock_message)
            mock_log.assert_called_once_with("INFO", "Module 'TestModule' received stop signal.")
            self.assertTrue(self.test_module.stopEvent.is_set())

    def test_mainLoop_empty_queue(self):
        """Verifica che il mainLoop non si blocchi se la coda è vuota."""
        self.mock_communicator.incomingQueue.get.side_effect = [
            Empty,
            {"Message": {"type": "Stop"}}
        ]
        
        with patch.object(self.test_module, 'handleMessage') as mock_handleMessage:
            self.test_module.mainLoop()
            
            mock_handleMessage.assert_not_called()

    def test_sendMessage(self):
        """Verifica che sendMessage formatti correttamente il messaggio e lo metta nella coda."""
        destination = "TargetModule"
        msg_type = "Ping"
        payload = {"data": 123}
        
        self.test_module.sendMessage(destination, msg_type, payload)
        
        expected_message = {
            "Sender": "TestModule",
            "Destination": "TargetModule",
            "Message": {
                "type": "Ping",
                "payload": {"data": 123}
            }
        }
        self.mock_communicator.outgoingQueue.put.assert_called_once_with(expected_message)

    def test_log(self):
        """Verifica che il metodo log chiami sendMessage con il formato corretto."""
        with patch.object(self.test_module, 'sendMessage') as mock_send_message:
            self.test_module.log("ERROR", "Test error message")
            
            mock_send_message.assert_called_once_with("Logger", "LogMessage", {
                "level": "ERROR",
                "message": "Test error message"
            })