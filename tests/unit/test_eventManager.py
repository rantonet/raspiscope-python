import unittest
from unittest.mock import MagicMock, patch, call
from queue import Queue, Empty
from threading import Event
import time
import signal
from functools import wraps

from eventManager import EventManager

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

class TestEventManager(unittest.TestCase):

    @patch('eventManager.ConfigLoader')
    @patch('eventManager.Communicator')
    def setUp(self, mockCommunicator, mockConfigLoader):
        print("Setting up for TestEventManager")
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
        print("Setup complete for TestEventManager")

    @timeout(60)
    def test_initialization(self):
        """
        Tests if the EventManager is initialized correctly.
        """
        print("test_initialization: Starting test")
        self.assertEqual(self.eventManager.name, "EventManager")
        print("test_initialization: Asserted name")
        self.assertIsInstance(self.eventManager.communicator, MagicMock)
        print("test_initialization: Asserted communicator type")
        self.assertEqual(self.eventManager.runningProcesses, [])
        print("test_initialization: Asserted runningProcesses is empty")
        self.assertEqual(self.eventManager.registered_modules, {})
        print("test_initialization: Asserted registered_modules is empty")
        self.assertIsInstance(self.eventManager._stopEvent, Event)
        print("test_initialization: Asserted _stopEvent type")
        print("test_initialization: Test finished")

    @timeout(60)
    @patch('time.time', return_value=1234567890)
    def test_handleRegistration(self, mockTime):
        """
        Tests the registration of a new module.
        """
        print("test_handleRegistration: Starting test")
        moduleName = "testModule"
        self.eventManager._handleRegistration(moduleName)
        print("test_handleRegistration: _handleRegistration called")
        
        self.assertIn(moduleName, self.eventManager.registered_modules)
        print("test_handleRegistration: Asserted module in registered_modules")
        self.assertEqual(self.eventManager.registered_modules[moduleName], {
            "name": moduleName,
            "status": "registered",
            "registrationTime": 1234567890
        })
        print("test_handleRegistration: Asserted module registration data")
        # Verify logging
        self.mockCommInstance.outgoingQueue.put.assert_called()
        print("test_handleRegistration: Asserted outgoingQueue.put called")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertIn("Registering new module", logCall[1]['Message']['payload']['message'])
        print("test_handleRegistration: Asserted log message content")
        print("test_handleRegistration: Test finished")

    @timeout(60)
    def test_handleRegistrationAlreadyRegistered(self):
        """
        Tests that re-registering an existing module logs a warning.
        """
        print("test_handleRegistrationAlreadyRegistered: Starting test")
        moduleName = "testModule"
        self.eventManager.registered_modules[moduleName] = {} # Pre-register
        
        self.eventManager._handleRegistration(moduleName)
        print("test_handleRegistrationAlreadyRegistered: _handleRegistration called")
        
        # Verify logging
        self.mockCommInstance.outgoingQueue.put.assert_called()
        print("test_handleRegistrationAlreadyRegistered: Asserted outgoingQueue.put called")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertIn("is already registered", logCall[1]['Message']['payload']['message'])
        print("test_handleRegistrationAlreadyRegistered: Asserted log message content")
        print("test_handleRegistrationAlreadyRegistered: Test finished")

    @timeout(60)
    def test_handleUnregistration(self):
        """
        Tests the unregistration of a module.
        """
        print("test_handleUnregistration: Starting test")
        moduleName = "testModule"
        self.eventManager.registered_modules[moduleName] = {} # Pre-register
        
        self.eventManager._handleUnregistration(moduleName)
        print("test_handleUnregistration: _handleUnregistration called")
        
        self.assertNotIn(moduleName, self.eventManager.registered_modules)
        print("test_handleUnregistration: Asserted module not in registered_modules")
        # Verify logging
        self.mockCommInstance.outgoingQueue.put.assert_called()
        print("test_handleUnregistration: Asserted outgoingQueue.put called")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertIn("Unregistering module", logCall[1]['Message']['payload']['message'])
        print("test_handleUnregistration: Asserted log message content")
        print("test_handleUnregistration: Test finished")

    @timeout(60)
    def test_handleUnregistrationNotRegistered(self):
        """
        Tests that unregistering a non-existent module logs a warning.
        """
        print("test_handleUnregistrationNotRegistered: Starting test")
        moduleName = "nonExistentModule"
        self.eventManager._handleUnregistration(moduleName)
        print("test_handleUnregistrationNotRegistered: _handleUnregistration called")
        
        # Verify logging
        self.mockCommInstance.outgoingQueue.put.assert_called()
        print("test_handleUnregistrationNotRegistered: Asserted outgoingQueue.put called")
        logCall = self.mockCommInstance.outgoingQueue.put.call_args[0][0]
        self.assertIn("not found for unregistration", logCall[1]['Message']['payload']['message'])
        print("test_handleUnregistrationNotRegistered: Asserted log message content")
        print("test_handleUnregistrationNotRegistered: Test finished")

    @timeout(60)
    def test_routeMessageToModule(self):
        """
        Tests that a message for another module is routed to the outgoing queue.
        """
        print("test_routeMessageToModule: Starting test")
        message = {"Sender": "ModuleA", "Destination": "ModuleB", "Message": {"type": "data"}}
        self.mockCommInstance.incomingQueue.put(message)
        print("test_routeMessageToModule: Message put in incomingQueue")
        
        self.eventManager.route()
        print("test_routeMessageToModule: route called")
        
        self.assertFalse(self.mockCommInstance.outgoingQueue.empty())
        print("test_routeMessageToModule: Asserted outgoingQueue not empty")
        routedMessage = self.mockCommInstance.outgoingQueue.get()
        self.assertEqual(routedMessage, ("ModuleB", message))
        print("test_routeMessageToModule: Asserted routed message content")
        print("test_routeMessageToModule: Test finished")

    @timeout(60)
    def test_routeRegisterMessage(self):
        """
        Tests that a 'register' message is handled by _handleRegistration.
        """
        print("test_routeRegisterMessage: Starting test")
        message = {"Sender": "NewModule", "Destination": "EventManager", "Message": {"type": "register"}}
        self.mockCommInstance.incomingQueue.put(message)
        print("test_routeRegisterMessage: Message put in incomingQueue")
        
        with patch.object(self.eventManager, '_handleRegistration') as mockHandleReg:
            self.eventManager.route()
            print("test_routeRegisterMessage: route called")
            mockHandleReg.assert_called_once_with("NewModule")
            print("test_routeRegisterMessage: Asserted _handleRegistration called")
        print("test_routeRegisterMessage: Test finished")

    @timeout(60)
    def test_routeUnregisterMessage(self):
        """
        Tests that an 'unregister' message is handled by _handleUnregistration.
        """
        print("test_routeUnregisterMessage: Starting test")
        message = {"Sender": "OldModule", "Destination": "EventManager", "Message": {"type": "unregister"}}
        self.mockCommInstance.incomingQueue.put(message)
        print("test_routeUnregisterMessage: Message put in incomingQueue")
        
        with patch.object(self.eventManager, '_handleUnregistration') as mockHandleUnreg:
            self.eventManager.route()
            print("test_routeUnregisterMessage: route called")
            mockHandleUnreg.assert_called_once_with("OldModule")
            print("test_routeUnregisterMessage: Asserted _handleUnregistration called")
        print("test_routeUnregisterMessage: Test finished")

    @timeout(60)
    def test_routeStopMessage(self):
        """
        Tests that a 'Stop' message for the EventManager calls the stop method.
        """
        print("test_routeStopMessage: Starting test")
        message = {"Sender": "Admin", "Destination": "EventManager", "Message": {"type": "Stop"}}
        self.mockCommInstance.incomingQueue.put(message)
        print("test_routeStopMessage: Message put in incomingQueue")
        
        with patch.object(self.eventManager, 'stop') as mockStop:
            self.eventManager.route()
            print("test_routeStopMessage: route called")
            mockStop.assert_called_once()
            print("test_routeStopMessage: Asserted stop called")
        print("test_routeStopMessage: Test finished")

    @timeout(60)
    def test_routeEmptyQueue(self):
        """
        Tests that route handles an empty queue without error.
        """
        print("test_routeEmptyQueue: Starting test")
        # The queue is empty by default
        try:
            self.eventManager.route()
            print("test_routeEmptyQueue: route called")
        except Exception as e:
            self.fail(f"route() raised {e.__class__.__name__} unexpectedly!")
        print("test_routeEmptyQueue: Test finished")

    @timeout(60)
    def test_stop(self):
        """
        Tests that the stop method sets the internal stop event.
        """
        print("test_stop: Starting test")
        self.assertFalse(self.eventManager._stopEvent.is_set())
        print("test_stop: Asserted _stopEvent is not set initially")
        self.eventManager.stop()
        print("test_stop: stop called")
        self.assertTrue(self.eventManager._stopEvent.is_set())
        print("test_stop: Asserted _stopEvent is set")
        print("test_stop: Test finished")

    @timeout(60)
    def test_cleanup(self):
        """
        Tests the cleanup procedure.
        """
        print("test_cleanup: Starting test")
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
        print("test_cleanup: _cleanup called")
        
        # Check that a 'Stop' message was broadcast
        self.assertFalse(self.mockCommInstance.outgoingQueue.empty())
        print("test_cleanup: Asserted outgoingQueue not empty")
        broadcastMessage = self.mockCommInstance.outgoingQueue.get()
        self.assertEqual(broadcastMessage[0], "All")
        print("test_cleanup: Asserted broadcast destination is All")
        self.assertEqual(broadcastMessage[1]['Message']['type'], "Stop")
        print("test_cleanup: Asserted message type is Stop")
        
        # Check that terminate was called on the alive process
        mockProcess1.terminate.assert_called_once()
        print("test_cleanup: Asserted terminate called on alive process")
        mockProcess1.join.assert_called_once_with(timeout=1)
        print("test_cleanup: Asserted join called on alive process")
        
        # Check that terminate was NOT called on the dead process
        mockProcess2.terminate.assert_not_called()
        print("test_cleanup: Asserted terminate not called on dead process")
        print("test_cleanup: Test finished")

    @timeout(60)
    def test_log(self):
        """
        Tests the log method to ensure it queues a correctly formatted log message.
        """
        print("test_log: Starting test")
        level = "INFO"
        message = "This is a test log."
        self.eventManager.log(level, message)
        print("test_log: log called")
        
        self.assertFalse(self.mockCommInstance.outgoingQueue.empty())
        print("test_log: Asserted outgoingQueue not empty")
        logTuple = self.mockCommInstance.outgoingQueue.get()
        
        self.assertEqual(logTuple[0], "Logger")
        print("test_log: Asserted destination is Logger")
        logMessage = logTuple[1]
        self.assertEqual(logMessage['Sender'], "EventManager")
        print("test_log: Asserted Sender")
        self.assertEqual(logMessage['Destination'], "Logger")
        print("test_log: Asserted inner Destination")
        self.assertEqual(logMessage['Message']['type'], "LogMessage")
        print("test_log: Asserted message type")
        self.assertEqual(logMessage['Message']['payload']['level'], level)
        print("test_log: Asserted log level")
        self.assertEqual(logMessage['Message']['payload']['message'], message)
        print("test_log: Asserted log message")
        print("test_log: Test finished")
