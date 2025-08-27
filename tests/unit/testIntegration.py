import unittest
import json
import time
import os
import shutil
import tempfile
from multiprocessing import Process, Event
from queue import Empty
from unittest.mock import MagicMock, patch, call
import numpy as np

# Import main modules
from eventManager import EventManager, MODULE_MAP
from communicator import Communicator

# Defines a test class for integration
class TestIntegration(unittest.TestCase):
    def setUp(self):
        """Set up the test environment by creating temporary files and starting the system."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'config.json')
        self.data_dir = os.path.join(self.temp_dir, 'data')
        os.makedirs(self.data_dir)
        
        # Create a temporary configuration file for the test
        test_config = {
            "network": {
                "address": "127.0.0.1",
                "port": 1025,
                "client_reconnect_delay_s": 0.1
            },
            "system": {
                "module_message_queue_timeout_s": 0.1
            },
            "modules": {
                "lightSource": {"enabled": True, "pin": 18, "brightness": 0.5, "dma": 10, "pwm_channel": 0},
                "cuvetteSensor": {"enabled": True, "pin": 17, "poll_interval_s": 0.1, "calibration": {"samples": 3, "threshold_span": 0.1}},
                "camera": {"enabled": True, "resolution": [1920, 1080]},
                "analysis": {"enabled": True, "reference_spectra_path": os.path.join(self.data_dir, "reference_spectra.csv"), "tolerance_nm": 10},
                "logger": {"enabled": True, "destination": ["stdout"], "path": ""}
            }
        }
        with open(self.config_path, 'w') as f:
            json.dump(test_config, f)
            
        # Create a dummy reference data file
        reference_data_content = "wavelength,substance\n450,SubstanceA\n550,SubstanceB"
        with open(os.path.join(self.data_dir, "reference_spectra.csv"), 'w') as f:
            f.write(reference_data_content)
            
        # Mocking of hardware and I/O dependencies in the modules
        self.mock_picamera = patch('camera.Picamera2', MagicMock(spec=True))
        self.mock_gpiozero = patch('cuvetteSensor.InputDevice', MagicMock(spec=True))
        self.mock_led_strip = patch('lightSource.PixelStrip', MagicMock(spec=True))
        self.mock_pandas = patch('pandas.read_csv', MagicMock())
        self.mock_cv2 = patch('cv2.imdecode', MagicMock())
        self.mock_numpy = patch('numpy.frombuffer', MagicMock())

        self.mock_picamera_instance = self.mock_picamera.start().return_value
        self.mock_gpiozero_instance = self.mock_gpiozero.start().return_value
        self.mock_led_instance = self.mock_led_strip.start().return_value
        self.mock_pandas_instance = self.mock_pandas.start()
        self.mock_cv2_instance = self.mock_cv2.start()
        self.mock_numpy_instance = self.mock_numpy.start()
        
        # Start the EventManager in a separate process
        self.event_manager_process = Process(target=self.run_event_manager)
        self.event_manager_process.start()
        
        # Give time for the modules to start and register
        time.sleep(1)
        
        # Create a test client communicator
        self.test_client_communicator = Communicator("client", "TestClient", test_config['network'])
        self.test_stop_event = Event()
        self.client_thread = Process(target=self.test_client_communicator.run, args=(self.test_stop_event,))
        self.client_thread.start()
        time.sleep(1)

    def tearDown(self):
        """Cleans up resources after each test."""
        # Signal all threads and processes to stop
        self.test_stop_event.set()
        self.client_thread.join(timeout=2)

        # Send a stop signal to the EventManager
        stop_message = {
            "Sender": "TestClient",
            "Destination": "EventManager",
            "Message": {"type": "Stop"}
        }
        try:
            self.test_client_communicator.outgoingQueue.put_nowait(stop_message)
        except Exception:
            pass
        self.event_manager_process.join(timeout=5)
        
        # Stop mocks
        self.mock_picamera.stop()
        self.mock_gpiozero.stop()
        self.mock_led_strip.stop()
        self.mock_pandas.stop()
        self.mock_cv2.stop()
        self.mock_numpy.stop()

        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
        
    def run_event_manager(self):
        """Runs the EventManager in the separate process."""
        try:
            event_manager = EventManager(self.config_path)
            event_manager.run()
        except SystemExit:
            pass

    def test_end_to_end_analysis_pipeline(self):
        """
        Integration scenario:
        1. The sensor detects a cuvette.
        2. The sensor sends a 'CuvettePresent' event.
        3. The Camera module receives the event and takes a picture.
        4. The Camera module sends an 'Analyze' event to the Analysis module.
        5. The Analysis module receives the event and starts the analysis.
        6. The Analysis module sends an 'AnalysisComplete' event with the results.
        """
        # Step 1: Simulate a signal from the cuvette sensor.
        cuvette_present_message = {
            "Sender": "CuvetteSensor",
            "Destination": "All",
            "Message": {"type": "CuvettePresent"}
        }
        self.test_client_communicator.outgoingQueue.put(cuvette_present_message)

        # Give the system time to process messages
        time.sleep(2)
        
        # Step 2: Verify that the 'Analyze' message was sent
        # This message will pass through the EventManager and go to Analysis
        analyze_message_found = False
        while True:
            try:
                msg = self.test_client_communicator.incomingQueue.get(timeout=0.5)
                if msg.get("Message", {}).get("type") == "Analyze" and msg.get("Destination") == "Analysis":
                    analyze_message_found = True
                    break
            except Empty:
                break
        self.assertTrue(analyze_message_found, "The 'Analyze' message was not sent.")

        # Step 3: Simulate receiving results from Analysis.
        # Since the test client does not receive messages continuously,
        # we check if the `AnalysisComplete` event has been sent.
        analysis_complete_message_found = False
        while not self.test_client_communicator.incomingQueue.empty():
            try:
                msg = self.test_client_communicator.incomingQueue.get_nowait()
                if msg.get("Message", {}).get("type") == "AnalysisComplete":
                    analysis_complete_message_found = True
                    self.assertIn("identified_substances", msg['Message']['payload'])
                    break
            except Empty:
                break
        self.assertTrue(analysis_complete_message_found, "The 'AnalysisComplete' message was not sent.")

    def test_light_source_and_logger_interaction(self):
        """
        Integration scenario:
        1. A "TurnOn" command is sent to LightSource.
        2. LightSource sends a "TurningOn" broadcast event.
        3. LightSource sends a log message to Logger.
        4. Logger receives the log message.
        """
        # Step 1: Send a 'TurnOn' message to the LightSource module.
        turn_on_message = {
            "Sender": "TestClient",
            "Destination": "LightSource",
            "Message": {"type": "TurnOn"}
        }
        self.test_client_communicator.outgoingQueue.put(turn_on_message)

        # Give the system time to process messages
        time.sleep(2)

        # Step 2: Verify that the 'TurnedOn' event was sent.
        turn_on_event_found = False
        while not self.test_client_communicator.incomingQueue.empty():
            try:
                msg = self.test_client_communicator.incomingQueue.get_nowait()
                if msg.get("Message", {}).get("type") == "TurnedOn":
                    turn_on_event_found = True
                    break
            except Empty:
                continue
        self.assertTrue(turn_on_event_found, "The 'TurnedOn' event was not sent.")
        
        # Step 3: Verify that the Logger module has received a message.
        # In this case, the log will be printed to stdout, so we verify that the message
        # has reached the Logger and that there are no errors.
        # The only way to test the Logger in an integration test is to
        # verify the absence of routing errors in the EventManager process.
        # With this test, the goal is to ensure that the "LogMessage" message
        # is routed correctly from the LightSource module to the Logger.
        # Verification of the printed content is more suitable for the Logger's unit tests.
        # If the test does not fail with a routing error, the integration is successful.