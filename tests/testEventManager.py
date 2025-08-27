import unittest
from unittest.mock import MagicMock, patch, call
from multiprocessing import Process
from queue import Empty
from eventManager import EventManager, MODULE_MAP

class TestEventManager(unittest.TestCase):
    def setUp(self):
        self.mock_config = {
            "network": {},
            "system": {},
            "modules": {
                "lightSource": {"enabled": True},
                "cuvetteSensor": {"enabled": True},
                "camera": {"enabled": False}, # Disabilitato per test
                "analysis": {"enabled": True}
            }
        }
        
        self.mock_communicator = MagicMock()
        self.mock_communicator.incomingQueue = MagicMock()
        self.mock_communicator.outgoingQueue = MagicMock()
        
        # Simula il caricamento della configurazione
        self.config_loader_patcher = patch('eventManager.loadConfig', return_value=self.mock_config)
        self.config_loader_patcher.start()
        
        # Simula la classe Communicator
        self.communicator_patcher = patch('eventManager.Communicator', return_value=self.mock_communicator)
        self.communicator_patcher.start()
        
        # Simula le classi dei moduli
        for module_name, module_class in MODULE_MAP.items():
            patch(f'eventManager.{module_class.__name__}', MagicMock(spec=module_class)).start()
        
        self.event_manager = EventManager("mock_config.json")

    def tearDown(self):
        self.config_loader_patcher.stop()
        self.communicator_patcher.stop()
        
    def test_instantiateModules(self):
        """Verifica che _instantiateModules istanzi solo i moduli abilitati."""
        enabled_modules = self.event_manager._instantiateModules()
        enabled_names = [m.name for m in enabled_modules]
        
        self.assertIn("lightSource", enabled_names)
        self.assertIn("cuvetteSensor", enabled_names)
        self.assertIn("analysis", enabled_names)
        self.assertNotIn("camera", enabled_names)

    @patch('eventManager.Process', MagicMock(spec=Process))
    @patch('eventManager.Thread')
    def test_run_starts_components(self, mock_thread):
        """Verifica che il metodo run() avvii thread e processi."""
        with patch.object(self.event_manager, '_stopEvent') as mock_stop_event, \
             patch.object(self.event_manager, 'route') as mock_route:
            mock_stop_event.is_set.side_effect = [False, True]
            self.event_manager.run()
            
            mock_thread.assert_called_once() # Verifica il thread del comunicatore
            self.assertEqual(len(self.event_manager.runningProcesses), 3)
            for p_info in self.event_manager.runningProcesses:
                p_info['process'].start.assert_called_once()

    def test_route_message_to_destination(self):
        """Verifica che un messaggio sia correttamente instradato."""
        mock_message = {
            "Sender": "Camera",
            "Destination": "Analysis",
            "Message": {"type": "Analyze"}
        }
        self.mock_communicator.incomingQueue.get.return_value = mock_message
        
        self.event_manager.route()
        
        self.mock_communicator.outgoingQueue.put.assert_called_once_with(("Analysis", mock_message))

    def test_route_empty_queue(self):
        """Verifica che il routing gestisca una coda vuota senza errori."""
        self.mock_communicator.incomingQueue.get.side_effect = Empty
        self.event_manager.route()
        self.mock_communicator.outgoingQueue.put.assert_not_called()

    def test_cleanup(self):
        """Verifica che il metodo _cleanup termini tutti i processi dei moduli."""
        mock_process_1 = MagicMock(spec=Process)
        mock_process_2 = MagicMock(spec=Process)
        self.event_manager.runningProcesses = [
            {'process': mock_process_1, 'name': 'Module1'},
            {'process': mock_process_2, 'name': 'Module2'}
        ]
        self.event_manager._cleanup()
        
        self.mock_communicator.outgoingQueue.put.assert_called_once()
        mock_process_1.terminate.assert_called_once()
        mock_process_2.terminate.assert_called_once()