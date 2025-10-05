import unittest
from unittest.mock import MagicMock, patch, call
from queue import Queue, Empty
from threading import Event
import time
import signal
from functools import wraps

from eventManager import EventManager

class TestEventManager(unittest.TestCase):

    @patch('eventManager.ConfigLoader')
    @patch('eventManager.Communicator')
    def setUp(self, mockCommunicator, mockConfigLoader):
        # Mock ConfigLoader
        self.mockConfig = {
            'network': {'address': 'localhost', 'port': 12345}
        }
        mockConfigLoader.return_value.get_config.return_value = self.mockConfig

        # Mock Communicator
        self.mockCommInstance = MagicMock()
        self.mockCommInstance.incomingQueue = Queue()
        self.mockCommInstance.outgoingQueue = Queue()
        mockCommunicator.return_value = self.mockCommInstance

        # Instantiate EventManager
        self.eventManager = EventManager(configPath="dummy_path.json")

    def _drain_outgoing(self):
        """Utility helper to empty the mocked communicator outgoing queue."""
        drained = []
        while not self.mockCommInstance.outgoingQueue.empty():
            drained.append(self.mockCommInstance.outgoingQueue.get())
        return drained

    def test_initialization(self):
        """
        Tests if the EventManager is initialized correctly.
        """
        self.assertEqual(self.eventManager.name, "EventManager")
        self.assertIsInstance(self.eventManager.communicator, MagicMock)
        self.assertEqual(self.eventManager.runningProcesses, [])
        self.assertEqual(self.eventManager.registered_modules, {})
        self.assertIsInstance(self.eventManager._stopEvent, Event)

    @patch('time.time', return_value=1234567890)
    def test_handleRegistration(self, mockTime):
        """
        Tests the registration of a new module.
        """
        moduleName = "testModule"
        self.eventManager._handleRegistration(moduleName)
        
        self.assertIn(moduleName, self.eventManager.registered_modules)
        self.assertEqual(self.eventManager.registered_modules[moduleName], {
            "name": moduleName,
            "status": "registered",
            "registrationTime": 1234567890
        })
        # Verify logging
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        logTuple = messages[-1]
        self.assertEqual(logTuple[0], "Logger")
        self.assertIn("Registering new module", logTuple[1]['Message']['payload']['message'])

    def test_handleRegistrationAlreadyRegistered(self):
        """
        Tests that re-registering an existing module logs a warning.
        """
        moduleName = "testModule"
        self.eventManager.registered_modules[moduleName] = {} # Pre-register
        
        self.eventManager._handleRegistration(moduleName)
        
        # Verify logging
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        logTuple = messages[-1]
        self.assertEqual(logTuple[0], "Logger")
        self.assertIn("is already registered", logTuple[1]['Message']['payload']['message'])

    def test_handleUnregistration(self):
        """
        Tests the unregistration of a module.
        """
        moduleName = "testModule"
        self.eventManager.registered_modules[moduleName] = {} # Pre-register
        
        self.eventManager._handleUnregistration(moduleName)
        
        self.assertNotIn(moduleName, self.eventManager.registered_modules)
        # Verify logging
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        logTuple = messages[-1]
        self.assertEqual(logTuple[0], "Logger")
        self.assertIn("Unregistering module", logTuple[1]['Message']['payload']['message'])

    def test_handleUnregistrationNotRegistered(self):
        """
        Tests that unregistering a non-existent module logs a warning.
        """
        moduleName = "nonExistentModule"
        self.eventManager._handleUnregistration(moduleName)
        
        # Verify logging
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        logTuple = messages[-1]
        self.assertEqual(logTuple[0], "Logger")
        self.assertIn("not found for unregistration", logTuple[1]['Message']['payload']['message'])

    def test_routeMessageToModule(self):
        """
        Tests that a message for another module is routed to the outgoing queue.
        """
        message = {"Sender": "ModuleA", "Destination": "ModuleB", "Message": {"type": "data"}}
        self.mockCommInstance.incomingQueue.put(message)
        
        self.eventManager.route()
        
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        routedMessage = next((msg for msg in messages if msg[0] != "Logger"), None)
        self.assertIsNotNone(routedMessage)
        self.assertEqual(routedMessage, ("ModuleB", message))

    def test_routeRegisterMessage(self):
        """
        Tests that a 'register' message is handled by _handleRegistration.
        """
        message = {"Sender": "NewModule", "Destination": "EventManager", "Message": {"type": "register"}}
        self.mockCommInstance.incomingQueue.put(message)
        
        with patch.object(self.eventManager, '_handleRegistration') as mockHandleReg:
            self.eventManager.route()
            mockHandleReg.assert_called_once_with("NewModule")

    def test_routeUnregisterMessage(self):
        """
        Tests that an 'unregister' message is handled by _handleUnregistration.
        """
        message = {"Sender": "OldModule", "Destination": "EventManager", "Message": {"type": "unregister"}}
        self.mockCommInstance.incomingQueue.put(message)
        
        with patch.object(self.eventManager, '_handleUnregistration') as mockHandleUnreg:
            self.eventManager.route()
            mockHandleUnreg.assert_called_once_with("OldModule")

    def test_routeStopMessage(self):
        """
        Tests that a 'Stop' message for the EventManager calls the stop method.
        """
        message = {"Sender": "Admin", "Destination": "EventManager", "Message": {"type": "Stop"}}
        self.mockCommInstance.incomingQueue.put(message)
        
        with patch.object(self.eventManager, 'stop') as mockStop:
            self.eventManager.route()
            mockStop.assert_called_once()

    def test_routeEmptyQueue(self):
        """
        Tests that route handles an empty queue without error.
        """
        # The queue is empty by default
        try:
            self.eventManager.route()
        except Exception as e:
            self.fail(f"route() raised {e.__class__.__name__} unexpectedly!")

    def test_stop(self):
        """
        Tests that the stop method sets the internal stop event.
        """
        self.assertFalse(self.eventManager._stopEvent.is_set())
        self.eventManager.stop()
        self.assertTrue(self.eventManager._stopEvent.is_set())

    def test_cleanup(self):
        """
        Tests the cleanup procedure.
        """
        # Mock running processes
        mockProcess1 = MagicMock()
        mockProcess1.is_alive.return_value = True
        mockProcess2 = MagicMock()
        mockProcess2.is_alive.return_value = False # One already dead
        self.eventManager.runningProcesses = [
            {'name': 'Proc1', 'process': mockProcess1},
            {'name': 'Proc2', 'process': mockProcess2}
        ]
        
        self.eventManager._cleanup()
        
        # Check that a 'Stop' message was broadcast
        messages = self._drain_outgoing()
        broadcastMessage = next((msg for msg in messages if msg[0] == "All"), None)
        self.assertIsNotNone(broadcastMessage)
        self.assertEqual(broadcastMessage[1]['Message']['type'], "Stop")
        
        # Check that terminate was called on the alive process
        mockProcess1.terminate.assert_called_once()
        mockProcess1.join.assert_called_once_with(timeout=1)
        
        # Check that terminate was NOT called on the dead process
        mockProcess2.terminate.assert_not_called()

    def test_log(self):
        """
        Tests the log method to ensure it queues a correctly formatted log message.
        """
        level = "INFO"
        message = "This is a test log."
        self.eventManager.log(level, message)
        
        messages = self._drain_outgoing()
        self.assertTrue(messages)
        logTuple = messages[-1]
        
        self.assertEqual(logTuple[0], "Logger")
        logMessage = logTuple[1]
        self.assertEqual(logMessage['Sender'], "EventManager")
        self.assertEqual(logMessage['Destination'], "Logger")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        self.assertEqual(logMessage['Message']['payload']['level'], level)
        self.assertEqual(logMessage['Message']['payload']['message'], message)
