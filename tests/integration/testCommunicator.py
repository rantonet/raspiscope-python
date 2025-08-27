import unittest
from unittest.mock import MagicMock, patch, call
from queue import Queue, Empty
import json
import time
import socket
from threading import Thread, Event
from communicator import Communicator

class TestCommunicator(unittest.TestCase):
    def setUp(self):
        self.server_config = {"address": "127.0.0.1", "port": 1025}
        self.client_config = {"address": "127.0.0.1", "port": 1025, "client_reconnect_delay_s": 0.1}
        self.stop_event = Event()

    @patch('socket.socket')
    def test_server_and_client_communication(self, mock_socket):
        """
        Simulates a complete communication between server and client.
        """
        # Mock for server and client
        mock_server_socket = MagicMock()
        mock_client_socket = MagicMock()
        mock_socket.side_effect = [mock_server_socket, mock_client_socket]

        # Server configuration
        server_comm = Communicator("server", "EventManager", self.server_config)
        server_thread = Thread(target=server_comm.run, args=(self.stop_event,))
        server_thread.start()

        # Client configuration
        client_comm = Communicator("client", "TestModule", self.client_config)
        
        # Simulate connection acceptance by the server
        mock_server_socket.accept.return_value = (mock_client_socket, ("127.0.0.1", 12345))
        
        # Simulate client identification message
        mock_client_name_msg = json.dumps({"name": "TestModule"})
        mock_client_socket.recv.return_value = mock_client_name_msg.encode('utf-8')
        
        # Simulate receiving and sending messages
        mock_client_socket.recv.side_effect = [
            json.dumps({"Sender": "TestModule", "Destination": "All", "Message": {"type": "Heartbeat"}}).encode('utf-8'),
            b''  # Simulate disconnection
        ]
        
        # Simulate sending a message from the client
        client_comm.outgoingQueue.put({"Sender": "TestModule", "Destination": "Analysis", "Message": {"type": "Analyze"}})
        
        # Start client thread
        client_thread = Thread(target=client_comm.run, args=(self.stop_event,))
        client_thread.start()

        # Wait for messages to be exchanged
        time.sleep(1)

        # Assertions
        self.assertFalse(client_comm.incomingQueue.empty())
        received_msg = client_comm.incomingQueue.get()
        self.assertEqual(received_msg['Message']['type'], 'Heartbeat')

        # Server received the heartbeat message
        self.assertFalse(server_comm.incomingQueue.empty())
        server_received_msg = server_comm.incomingQueue.get()
        self.assertEqual(server_received_msg['Message']['type'], 'Heartbeat')

        # Client sent the message
        mock_client_socket.sendall.assert_called()

        # Stop threads
        self.stop_event.set()
        server_thread.join()
        client_thread.join()
        
    def test_client_reconnection(self):
        """Verifies that the client attempts to reconnect after an error."""
        with patch('socket.socket') as mock_socket, \
             patch('time.sleep') as mock_sleep:
            
            mock_socket.side_effect = [
                ConnectionRefusedError, # First failed attempt
                MagicMock()             # Second successful attempt
            ]
            
            client_comm = Communicator("client", "TestModule", self.client_config)
            
            with patch.object(client_comm, '_runClient') as mock_run_client:
                mock_run_client.side_effect = [None, self.stop_event.set]
                client_thread = Thread(target=client_comm.run, args=(self.stop_event,))
                client_thread.start()
                
                time.sleep(0.5)
                
                self.stop_event.set()
                client_thread.join()
                
                mock_sleep.assert_called_once_with(0.1)