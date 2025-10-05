import unittest
from unittest.mock import MagicMock, patch, call
import json
import socket
from queue import Queue
from threading import Event, Thread
import signal
from functools import wraps
import time

from communicator import Communicator
import communicator

class TestCommunicator(unittest.TestCase):

    def setUp(self):
        self.config = {'address': 'localhost', 'port': 12345}
        self.stopEvent = Event()

    def tearDown(self):
        self.stopEvent.set()
        time.sleep(0.01) # Give threads a moment to stop

    @patch('socket.socket')
    def test_clientInitialization(self, mockSocket):
        client = Communicator(commType="client", name="TestClient", config=self.config)
        self.assertEqual(client.commType, "client")
        self.assertEqual(client.name, "TestClient")
        self.assertEqual(client.config, self.config)
        self.assertIsInstance(client.incomingQueue, Queue)
        self.assertIsInstance(client.outgoingQueue, Queue)

    @patch('socket.socket')
    def test_serverInitialization(self, mockSocket):
        server = Communicator(commType="server", name="Server", config=self.config)
        self.assertEqual(server.commType, "server")
        self.assertEqual(server.name, "Server")
        self.assertEqual(server.config, self.config)
        self.assertIsInstance(server.incomingQueue, Queue)
        self.assertIsInstance(server.outgoingQueue, Queue)

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_clientRunStartsAndConnects(self, mockSocket, mockThread):
        mockConn = MagicMock()
        mockSocket.return_value = mockConn

        client = Communicator(commType="client", name="TestClient", config=self.config)
        
        # Mock the receive loop to stop the run loop
        client._clientReceiveLoop = MagicMock()
        client._clientReceiveLoop.side_effect = lambda stopEvent: stopEvent.set()

        client.run(self.stopEvent)

        mockSocket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        mockConn.connect.assert_called_with(('localhost', 12345))
        
        initialMsg = json.dumps({"name": "TestClient"}) + '\n'
        mockConn.sendall.assert_called_with(initialMsg.encode('utf-8'))
        
        # Check that the send thread was started
        self.assertEqual(mockThread.call_count, 1)
        self.assertEqual(mockThread.call_args[1]['target'], client._clientSendLoop)

    @patch('time.sleep')
    @patch('socket.socket')
    def test_clientConnectionRefused(self, mockSocket, mockSleep):
        mockConn = MagicMock()
        mockConn.connect.side_effect = [ConnectionRefusedError, lambda *args: None] # Fail once, then succeed
        mockSocket.return_value = mockConn

        client = Communicator(commType="client", name="TestClient", config=self.config)
        
        # Mock loops to stop after successful connection
        client._clientReceiveLoop = MagicMock(side_effect=lambda stopEvent: stopEvent.set())
        client._clientSendLoop = MagicMock()

        client.run(self.stopEvent)

        # Check that connect was called twice
        self.assertEqual(mockConn.connect.call_count, 2)
        self.assertGreaterEqual(mockSleep.call_count, 2)
        self.assertEqual(mockSleep.call_args_list[0], call(3)) # Default reconnect delay
        self.assertIn(call(0.001), mockSleep.call_args_list)

    def test_clientReceiveMessage(self):
        client = Communicator(commType="client", name="TestClient", config=self.config)
        mockConn = MagicMock()
        client.conn = mockConn

        message = {"Sender": "Server", "Destination": "TestClient", "Message": {"type": "test"}}
        # Simulate receiving one message, then an empty byte string to indicate disconnection
        mockConn.recv.side_effect = [(json.dumps(message) + '\n').encode('utf-8'), b'']

        # The loop should now terminate on its own after processing the message
        client._clientReceiveLoop(self.stopEvent)
        
        self.assertFalse(client.incomingQueue.empty())
        receivedMessage = client.incomingQueue.get()
        self.assertEqual(receivedMessage, message)

    def test_clientSendMessage(self):
        client = Communicator(commType="client", name="TestClient", config=self.config)
        mockConn = MagicMock()
        client.conn = mockConn
        
        message = {"Sender": "TestClient", "Destination": "Server", "Message": {"type": "test"}}
        client.outgoingQueue.put(message)

        def sendall_side_effect(*args, **kwargs):
            self.stopEvent.set()

        mockConn.sendall.side_effect = sendall_side_effect

        client._clientSendLoop(self.stopEvent)

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        mockConn.sendall.assert_called_once_with(expectedData)
        self.assertTrue(client.outgoingQueue.empty())

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_serverRunInitializesAndAccepts(self, mockSocket, mockThread):
        mockServerSocket = MagicMock()
        mockSocket.return_value = mockServerSocket

        server = Communicator(commType="server", name="Server", config=self.config)
        
        # Mock accept to stop the loop after one timeout
        def accept_side_effect(*args, **kwargs):
            self.stopEvent.set()
            raise socket.timeout()

        mockServerSocket.accept.side_effect = accept_side_effect

        with patch.object(communicator, 'send_thread', mockThread.return_value, create=True):
            server.run(self.stopEvent)

        mockServerSocket.bind.assert_called_with(('localhost', 12345))
        mockServerSocket.listen.assert_called_with(5)
        
        # Check that the send thread was started
        self.assertEqual(mockThread.call_count, 1)
        self.assertEqual(mockThread.call_args[1]['target'], server._serverSendLoop)

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_serverHandlesClientConnection(self, mockSocket, mockThread):
        mockServerSocket = MagicMock()
        mockClientConn = MagicMock()
        mockAddr = ('127.0.0.1', 54321)

        # Simulate one connection then timeout
        def accept_side_effect():
            yield (mockClientConn, mockAddr)
            self.stopEvent.set()
            raise socket.timeout()

        mockServerSocket.accept.side_effect = accept_side_effect()
        mockSocket.return_value = mockServerSocket

        # Simulate client identification
        clientName = "Client1"
        initialMsg = json.dumps({"name": clientName}) + '\n'
        mockClientConn.recv.return_value = initialMsg.encode('utf-8')

        server = Communicator(commType="server", name="Server", config=self.config)
        
        # Mock the handler thread target to prevent it from running
        server._serverHandleClient = MagicMock()
        
        with patch.object(communicator, 'send_thread', mockThread.return_value, create=True):
            server.run(self.stopEvent)

        self.assertIn(clientName, server.client_sockets)
        self.assertEqual(server.client_sockets[clientName], mockClientConn)
        
        # Check that a handler thread was created for the client
        self.assertEqual(mockThread.call_count, 2) # Send loop + client handler
        clientThreadCall = mockThread.call_args_list[1]
        self.assertEqual(clientThreadCall[1]['target'], server._serverHandleClient)
        self.assertEqual(clientThreadCall[1]['args'][0], clientName)

    def test_serverReceivesMessage(self):
        server = Communicator(commType="server", name="Server", config=self.config)
        mockConn = MagicMock()
        clientName = "TestClient"
        
        message = {"Sender": clientName, "Destination": "Server", "Message": {"type": "data"}}
        # Simulate receiving one message, then an empty byte string to indicate disconnection
        mockConn.recv.side_effect = [(json.dumps(message) + '''
''').encode('utf-8'), b'']

        # The loop should now terminate on its own after processing the message
        server._serverHandleClient(clientName, mockConn, self.stopEvent)

        self.assertFalse(server.incomingQueue.empty())
        self.assertEqual(server.incomingQueue.get(), message)

    def test_serverSendsUnicastMessage(self):
        server = Communicator(commType="server", name="Server", config=self.config)
        mockSock1 = MagicMock()
        mockSock2 = MagicMock()
        server.client_sockets = {"Client1": mockSock1, "Client2": mockSock2}

        message = {"Sender": "Server", "Destination": "Client1", "Message": {"type": "test"}}
        server.outgoingQueue.put(("Client1", message))

        def unicast_sendall_side_effect(*args, **kwargs):
            self.stopEvent.set()

        mockSock1.sendall.side_effect = unicast_sendall_side_effect

        server._serverSendLoop(self.stopEvent)

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        mockSock1.sendall.assert_called_once_with(expectedData)
        mockSock2.sendall.assert_not_called()

    def test_serverSendsBroadcastMessage(self):
        server = Communicator(commType="server", name="Server", config=self.config)
        mockSock1 = MagicMock()
        mockSock2 = MagicMock()
        mockSock3 = MagicMock()
        server.client_sockets = {"SenderClient": mockSock1, "Client2": mockSock2, "Client3": mockSock3}

        message = {"Sender": "SenderClient", "Destination": "All", "Message": {"type": "test"}}
        server.outgoingQueue.put(("All", message))

        send_calls = {'count': 0}

        def broadcast_sendall_side_effect(*args, **kwargs):
            send_calls['count'] += 1
            if send_calls['count'] >= 2:
                self.stopEvent.set()

        mockSock2.sendall.side_effect = broadcast_sendall_side_effect
        mockSock3.sendall.side_effect = broadcast_sendall_side_effect

        server._serverSendLoop(self.stopEvent)

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        
        # Should not send to sender
        mockSock1.sendall.assert_not_called()
        # Should send to all others
        mockSock2.sendall.assert_called_once_with(expectedData)
        mockSock3.sendall.assert_called_once_with(expectedData)

    def test_logMessageClient(self):
        client = Communicator(commType="client", name="TestClient", config=self.config)
        client.log("INFO", "Test log message")
        
        self.assertFalse(client.outgoingQueue.empty())
        logMessage = client.outgoingQueue.get()
        
        self.assertEqual(logMessage['Sender'], "TestClient")
        self.assertEqual(logMessage['Destination'], "Logger")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        self.assertEqual(logMessage['Message']['payload']['level'], "INFO")
        self.assertEqual(logMessage['Message']['payload']['message'], "Test log message")

    def test_logMessageServer(self):
        server = Communicator(commType="server", name="Server", config=self.config)
        server.log("ERROR", "Test log message")

        self.assertFalse(server.outgoingQueue.empty())
        destination, logMessage = server.outgoingQueue.get()

        self.assertEqual(destination, "Logger")
        self.assertEqual(logMessage['Sender'], "Server")
        self.assertEqual(logMessage['Destination'], "Logger")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        self.assertEqual(logMessage['Message']['payload']['level'], "ERROR")
        self.assertEqual(logMessage['Message']['payload']['message'], "Test log message")

    def test_parseMessages(self):
        comm = Communicator("client", "Test", {})
        validJsonStr = '{"key": "value"}'
        messages = comm._parseMessages(validJsonStr)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], {"key": "value"})

    def test_parseInvalidMessage(self):
        comm = Communicator("client", "Test", {})
        invalidJsonStr = '{"key": "value"' # Missing closing brace
        
        with patch.object(comm, 'log') as mockLog:
            messages = comm._parseMessages(invalidJsonStr)
            self.assertEqual(len(messages), 0)
            mockLog.assert_called_once()
            self.assertIn("JSON parsing error", mockLog.call_args[0][1])
