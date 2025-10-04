import unittest
from unittest.mock import MagicMock, patch, call
import json
import socket
from queue import Queue
from threading import Event, Thread
import signal
from functools import wraps

# Assuming communicator.py is in the parent directory or accessible via PYTHONPATH
from communicator import Communicator

class TestCommunicator(unittest.TestCase):

    def setUp(self):
        print("Setting up for TestCommunicator")
        self.config = {'address': 'localhost', 'port': 12345}
        self.stopEvent = Event()
        print("Setup complete for TestCommunicator")

    @patch('socket.socket')
    def test_clientInitialization(self, mockSocket):
        print("test_clientInitialization: Starting test")
        client = Communicator(commType="client", name="TestClient", config=self.config)
        print("test_clientInitialization: Communicator initialized")
        self.assertEqual(client.commType, "client")
        print("test_clientInitialization: Asserted commType")
        self.assertEqual(client.name, "TestClient")
        print("test_clientInitialization: Asserted name")
        self.assertEqual(client.config, self.config)
        print("test_clientInitialization: Asserted config")
        self.assertIsInstance(client.incomingQueue, Queue)
        print("test_clientInitialization: Asserted incomingQueue type")
        self.assertIsInstance(client.outgoingQueue, Queue)
        print("test_clientInitialization: Asserted outgoingQueue type")
        print("test_clientInitialization: Test finished")

    @patch('socket.socket')
    def test_serverInitialization(self, mockSocket):
        print("test_serverInitialization: Starting test")
        server = Communicator(commType="server", name="Server", config=self.config)
        print("test_serverInitialization: Communicator initialized")
        self.assertEqual(server.commType, "server")
        print("test_serverInitialization: Asserted commType")
        self.assertEqual(server.name, "Server")
        print("test_serverInitialization: Asserted name")
        self.assertEqual(server.config, self.config)
        print("test_serverInitialization: Asserted config")
        self.assertIsInstance(server.incomingQueue, Queue)
        print("test_serverInitialization: Asserted incomingQueue type")
        self.assertIsInstance(server.outgoingQueue, Queue)
        print("test_serverInitialization: Asserted outgoingQueue type")
        print("test_serverInitialization: Test finished")

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_clientRunStartsAndConnects(self, mockSocket, mockThread):
        print("test_clientRunStartsAndConnects: Starting test")
        mockConn = MagicMock()
        mockSocket.return_value = mockConn

        client = Communicator(commType="client", name="TestClient", config=self.config)
        
        # Mock the receive loop to stop the run loop
        client._clientReceiveLoop = MagicMock()
        client._clientReceiveLoop.side_effect = lambda stopEvent: stopEvent.set()

        client.run(self.stopEvent)
        print("test_clientRunStartsAndConnects: client.run() called")

        mockSocket.assert_called_with(socket.AF_INET, socket.SOCK_STREAM)
        print("test_clientRunStartsAndConnects: Asserted socket created")
        mockConn.connect.assert_called_with(('localhost', 12345))
        print("test_clientRunStartsAndConnects: Asserted connect called")
        
        initialMsg = json.dumps({"name": "TestClient"}) + '\n'
        mockConn.sendall.assert_called_with(initialMsg.encode('utf-8'))
        print("test_clientRunStartsAndConnects: Asserted initial message sent")
        
        # Check that the send thread was started
        self.assertEqual(mockThread.call_count, 1)
        print("test_clientRunStartsAndConnects: Asserted thread started")
        self.assertEqual(mockThread.call_args[1]['target'], client._clientSendLoop)
        print("test_clientRunStartsAndConnects: Asserted thread target")
        print("test_clientRunStartsAndConnects: Test finished")

    @patch('time.sleep')
    @patch('socket.socket')
    def test_clientConnectionRefused(self, mockSocket, mockSleep):
        print("test_clientConnectionRefused: Starting test")
        mockConn = MagicMock()
        mockConn.connect.side_effect = [ConnectionRefusedError, lambda *args: None] # Fail once, then succeed
        mockSocket.return_value = mockConn

        client = Communicator(commType="client", name="TestClient", config=self.config)
        
        # Mock loops to stop after successful connection
        client._clientReceiveLoop = MagicMock(side_effect=lambda stopEvent: stopEvent.set())
        client._clientSendLoop = MagicMock()

        client.run(self.stopEvent)
        print("test_clientConnectionRefused: client.run() called")

        # Check that connect was called twice
        self.assertEqual(mockConn.connect.call_count, 2)
        print("test_clientConnectionRefused: Asserted connect called twice")
        mockSleep.assert_called_once_with(3) # Default reconnect delay
        print("test_clientConnectionRefused: Asserted sleep called")
        print("test_clientConnectionRefused: Test finished")

    def test_clientReceiveMessage(self):
        print("test_clientReceiveMessage: Starting test")
        client = Communicator(commType="client", name="TestClient", config=self.config)
        mockConn = MagicMock()
        client.conn = mockConn

        message = {"Sender": "Server", "Destination": "TestClient", "Message": {"type": "test"}}
        mockConn.recv.return_value = (json.dumps(message) + '\n').encode('utf-8')

        # Run receive loop once
        client._clientReceiveLoop(Event())
        print("test_clientReceiveMessage: _clientReceiveLoop called")
        
        self.assertFalse(client.incomingQueue.empty())
        print("test_clientReceiveMessage: Asserted incomingQueue not empty")
        receivedMessage = client.incomingQueue.get()
        self.assertEqual(receivedMessage, message)
        print("test_clientReceiveMessage: Asserted received message content")
        print("test_clientReceiveMessage: Test finished")

    def test_clientSendMessage(self):
        print("test_clientSendMessage: Starting test")
        client = Communicator(commType="client", name="TestClient", config=self.config)
        mockConn = MagicMock()
        client.conn = mockConn
        
        message = {"Sender": "TestClient", "Destination": "Server", "Message": {"type": "test"}}
        client.outgoingQueue.put(message)
        print("test_clientSendMessage: Message put in outgoingQueue")

        # To stop the loop after one iteration
        self.stopEvent.set()
        client._clientSendLoop(self.stopEvent)
        print("test_clientSendMessage: _clientSendLoop called")

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        mockConn.sendall.assert_called_once_with(expectedData)
        print("test_clientSendMessage: Asserted sendall called with correct data")
        self.assertTrue(client.outgoingQueue.empty())
        print("test_clientSendMessage: Asserted outgoingQueue is empty")
        print("test_clientSendMessage: Test finished")

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_serverRunInitializesAndAccepts(self, mockSocket, mockThread):
        print("test_serverRunInitializesAndAccepts: Starting test")
        mockServerSocket = MagicMock()
        mockSocket.return_value = mockServerSocket

        server = Communicator(commType="server", name="Server", config=self.config)
        
        # Mock accept to stop the loop
        mockServerSocket.accept.side_effect = socket.timeout
        
        server.run(self.stopEvent)
        print("test_serverRunInitializesAndAccepts: server.run() called")

        mockServerSocket.bind.assert_called_with(('localhost', 12345))
        print("test_serverRunInitializesAndAccepts: Asserted bind called")
        mockServerSocket.listen.assert_called_with(5)
        print("test_serverRunInitializesAndAccepts: Asserted listen called")
        
        # Check that the send thread was started
        self.assertEqual(mockThread.call_count, 1)
        print("test_serverRunInitializesAndAccepts: Asserted thread started")
        self.assertEqual(mockThread.call_args[1]['target'], server._serverSendLoop)
        print("test_serverRunInitializesAndAccepts: Asserted thread target")
        print("test_serverRunInitializesAndAccepts: Test finished")

    @patch('communicator.Thread')
    @patch('socket.socket')
    def test_serverHandlesClientConnection(self, mockSocket, mockThread):
        print("test_serverHandlesClientConnection: Starting test")
        mockServerSocket = MagicMock()
        mockClientConn = MagicMock()
        mockAddr = ('127.0.0.1', 54321)

        # Simulate one connection then timeout
        mockServerSocket.accept.side_effect = [(mockClientConn, mockAddr), socket.timeout]
        mockSocket.return_value = mockServerSocket

        # Simulate client identification
        clientName = "Client1"
        initialMsg = json.dumps({"name": clientName}) + '\n'
        mockClientConn.recv.return_value = initialMsg.encode('utf-8')

        server = Communicator(commType="server", name="Server", config=self.config)
        
        # Mock the handler thread target to prevent it from running
        server._serverHandleClient = MagicMock()
        
        server.run(self.stopEvent)
        print("test_serverHandlesClientConnection: server.run() called")

        self.assertIn(clientName, server.client_sockets)
        print("test_serverHandlesClientConnection: Asserted client name in client_sockets")
        self.assertEqual(server.client_sockets[clientName], mockClientConn)
        print("test_serverHandlesClientConnection: Asserted client socket object")
        
        # Check that a handler thread was created for the client
        self.assertEqual(mockThread.call_count, 2) # Send loop + client handler
        print("test_serverHandlesClientConnection: Asserted thread count")
        clientThreadCall = mockThread.call_args_list[1]
        self.assertEqual(clientThreadCall[1]['target'], server._serverHandleClient)
        print("test_serverHandlesClientConnection: Asserted client handler thread target")
        self.assertEqual(clientThreadCall[1]['args'][0], clientName)
        print("test_serverHandlesClientConnection: Asserted client handler thread args")
        print("test_serverHandlesClientConnection: Test finished")

    def test_serverReceivesMessage(self):
        print("test_serverReceivesMessage: Starting test")
        server = Communicator(commType="server", name="Server", config=self.config)
        mockConn = MagicMock()
        clientName = "TestClient"
        
        message = {"Sender": clientName, "Destination": "Server", "Message": {"type": "data"}}
        mockConn.recv.return_value = (json.dumps(message) + '\n').encode('utf-8')

        # Run handler once, then stop
        self.stopEvent.set()
        server._serverHandleClient(clientName, mockConn, self.stopEvent)
        print("test_serverReceivesMessage: _serverHandleClient called")

        self.assertFalse(server.incomingQueue.empty())
        print("test_serverReceivesMessage: Asserted incomingQueue not empty")
        self.assertEqual(server.incomingQueue.get(), message)
        print("test_serverReceivesMessage: Asserted received message content")
        print("test_serverReceivesMessage: Test finished")

    def test_serverSendsUnicastMessage(self):
        print("test_serverSendsUnicastMessage: Starting test")
        server = Communicator(commType="server", name="Server", config=self.config)
        mockSock1 = MagicMock()
        mockSock2 = MagicMock()
        server.client_sockets = {"Client1": mockSock1, "Client2": mockSock2}

        message = {"Sender": "Server", "Destination": "Client1", "Message": {"type": "test"}}
        server.outgoingQueue.put(("Client1", message))
        print("test_serverSendsUnicastMessage: Message put in outgoingQueue")

        # Stop loop after one message
        self.stopEvent.set()
        server._serverSendLoop(self.stopEvent)
        print("test_serverSendsUnicastMessage: _serverSendLoop called")

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        mockSock1.sendall.assert_called_once_with(expectedData)
        print("test_serverSendsUnicastMessage: Asserted sendall called on correct socket")
        mockSock2.sendall.assert_not_called()
        print("test_serverSendsUnicastMessage: Asserted sendall not called on other socket")
        print("test_serverSendsUnicastMessage: Test finished")

    def test_serverSendsBroadcastMessage(self):
        print("test_serverSendsBroadcastMessage: Starting test")
        server = Communicator(commType="server", name="Server", config=self.config)
        mockSock1 = MagicMock()
        mockSock2 = MagicMock()
        mockSock3 = MagicMock()
        server.client_sockets = {"SenderClient": mockSock1, "Client2": mockSock2, "Client3": mockSock3}

        message = {"Sender": "SenderClient", "Destination": "All", "Message": {"type": "test"}}
        server.outgoingQueue.put(("All", message))
        print("test_serverSendsBroadcastMessage: Message put in outgoingQueue")

        self.stopEvent.set()
        server._serverSendLoop(self.stopEvent)
        print("test_serverSendsBroadcastMessage: _serverSendLoop called")

        expectedData = (json.dumps(message) + '\n').encode('utf-8')
        
        # Should not send to sender
        mockSock1.sendall.assert_not_called()
        print("test_serverSendsBroadcastMessage: Asserted not sent to sender")
        # Should send to all others
        mockSock2.sendall.assert_called_once_with(expectedData)
        print("test_serverSendsBroadcastMessage: Asserted sent to client 2")
        mockSock3.sendall.assert_called_once_with(expectedData)
        print("test_serverSendsBroadcastMessage: Asserted sent to client 3")
        print("test_serverSendsBroadcastMessage: Test finished")

    def test_logMessageClient(self):
        print("test_logMessageClient: Starting test")
        client = Communicator(commType="client", name="TestClient", config=self.config)
        client.log("INFO", "Test log message")
        print("test_logMessageClient: log() called")
        
        self.assertFalse(client.outgoingQueue.empty())
        print("test_logMessageClient: Asserted outgoingQueue not empty")
        logMessage = client.outgoingQueue.get()
        
        self.assertEqual(logMessage['Sender'], "TestClient")
        print("test_logMessageClient: Asserted Sender")
        self.assertEqual(logMessage['Destination'], "Logger")
        print("test_logMessageClient: Asserted Destination")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        print("test_logMessageClient: Asserted message type")
        self.assertEqual(logMessage['Message']['payload']['level'], "INFO")
        print("test_logMessageClient: Asserted log level")
        self.assertEqual(logMessage['Message']['payload']['message'], "Test log message")
        print("test_logMessageClient: Asserted log message")
        print("test_logMessageClient: Test finished")

    def test_logMessageServer(self):
        print("test_logMessageServer: Starting test")
        server = Communicator(commType="server", name="Server", config=self.config)
        server.log("ERROR", "Test log message")
        print("test_logMessageServer: log() called")

        self.assertFalse(server.outgoingQueue.empty())
        print("test_logMessageServer: Asserted outgoingQueue not empty")
        destination, logMessage = server.outgoingQueue.get()

        self.assertEqual(destination, "Logger")
        print("test_logMessageServer: Asserted destination")
        self.assertEqual(logMessage['Sender'], "Server")
        print("test_logMessageServer: Asserted Sender")
        self.assertEqual(logMessage['Destination'], "Logger")
        print("test_logMessageServer: Asserted inner Destination")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        print("test_logMessageServer: Asserted message type")
        self.assertEqual(logMessage['Message']['payload']['level'], "ERROR")
        print("test_logMessageServer: Asserted log level")
        self.assertEqual(logMessage['Message']['payload']['message'], "Test log message")
        print("test_logMessageServer: Asserted log message")
        print("test_logMessageServer: Test finished")

    def test_parseMessages(self):
        print("test_parseMessages: Starting test")
        comm = Communicator("client", "Test", {})
        validJsonStr = '{"key": "value"}'
        messages = comm._parseMessages(validJsonStr)
        print("test_parseMessages: _parseMessages called with valid JSON")
        self.assertEqual(len(messages), 1)
        print("test_parseMessages: Asserted one message parsed")
        self.assertEqual(messages[0], {"key": "value"})
        print("test_parseMessages: Asserted message content")
        print("test_parseMessages: Test finished")

    def test_parseInvalidMessage(self):
        print("test_parseInvalidMessage: Starting test")
        comm = Communicator("client", "Test", {})
        invalidJsonStr = '{"key": "value"' # Missing closing brace
        
        with patch.object(comm, 'log') as mockLog:
            messages = comm._parseMessages(invalidJsonStr)
            print("test_parseInvalidMessage: _parseMessages called with invalid JSON")
            self.assertEqual(len(messages), 0)
            print("test_parseInvalidMessage: Asserted no messages parsed")
            mockLog.assert_called_once()
            print("test_parseInvalidMessage: Asserted log was called")
            self.assertIn("JSON parsing error", mockLog.call_args[0][1])
            print("test_parseInvalidMessage: Asserted log message content")
            print("test_parseInvalidMessage: Test finished")