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
        Simula una comunicazione completa tra server e client.
        """
        # Mock per il server e il client
        mock_server_socket = MagicMock()
        mock_client_socket = MagicMock()
        mock_socket.side_effect = [mock_server_socket, mock_client_socket]

        # Configurazione del server
        server_comm = Communicator("server", "EventManager", self.server_config)
        server_thread = Thread(target=server_comm.run, args=(self.stop_event,))
        server_thread.start()

        # Configurazione del client
        client_comm = Communicator("client", "TestModule", self.client_config)
        
        # Simula l'accettazione della connessione da parte del server
        mock_server_socket.accept.return_value = (mock_client_socket, ("127.0.0.1", 12345))
        
        # Simula il messaggio di identificazione del client
        mock_client_name_msg = json.dumps({"name": "TestModule"})
        mock_client_socket.recv.return_value = mock_client_name_msg.encode('utf-8')
        
        # Simula la ricezione e l'invio di messaggi
        mock_client_socket.recv.side_effect = [
            json.dumps({"Sender": "TestModule", "Destination": "All", "Message": {"type": "Heartbeat"}}).encode('utf-8'),
            b''  # Simula la disconnessione
        ]
        
        # Simula l'invio di un messaggio dal client
        client_comm.outgoingQueue.put({"Sender": "TestModule", "Destination": "Analysis", "Message": {"type": "Analyze"}})
        
        # Avvia il thread del client
        client_thread = Thread(target=client_comm.run, args=(self.stop_event,))
        client_thread.start()

        # Attende che i messaggi vengano scambiati
        time.sleep(1)

        # Asserzioni
        self.assertFalse(client_comm.incomingQueue.empty())
        received_msg = client_comm.incomingQueue.get()
        self.assertEqual(received_msg['Message']['type'], 'Heartbeat')

        # Il server ha ricevuto il messaggio di heartbeat
        self.assertFalse(server_comm.incomingQueue.empty())
        server_received_msg = server_comm.incomingQueue.get()
        self.assertEqual(server_received_msg['Message']['type'], 'Heartbeat')

        # Il client ha inviato il messaggio
        mock_client_socket.sendall.assert_called()

        # Stop dei thread
        self.stop_event.set()
        server_thread.join()
        client_thread.join()
        
    def test_client_reconnection(self):
        """Verifica che il client tenti di riconnettersi dopo un errore."""
        with patch('socket.socket') as mock_socket, \
             patch('time.sleep') as mock_sleep:
            
            mock_socket.side_effect = [
                ConnectionRefusedError, # Primo tentativo fallito
                MagicMock()             # Secondo tentativo riuscito
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