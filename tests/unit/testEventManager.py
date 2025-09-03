import unittest
import time
import json
from multiprocessing import Process
from multiprocessing import Event   as mpEvent
from queue           import Empty

from eventManager  import EventManager
from communicator  import Communicator
from unittest.mock import patch
from unittest.mock import MagicMock

# Configurazione usata per il test
TEST_CONFIG = {
    "network" : {"address": "127.0.0.1", "port": 1025, "client_reconnect_delay_s": 0.1},
    "system"  : {"module_message_queue_timeout_s": 0.1},
    "modules" : {
        "lightSource"   : {"enabled": True},
        "cuvetteSensor" : {"enabled": True},
    }
}

# Mock delle classi dei moduli per evitare dipendenze hardware
MOCK_MODULE_MAP = {
    "lightSource"   : MagicMock(),
    "cuvetteSensor" : MagicMock(),
}

def run_event_manager():
    """Funzione target per eseguire EventManager in un processo separato."""
    # Applica i mock all'interno del nuovo processo
    with patch('eventManager.loadConfig', return_value=TEST_CONFIG), \
         patch.dict('eventManager.MODULE_MAP', MOCK_MODULE_MAP):
        try:
            manager = EventManager("config.json")
            manager.run()
        except Exception as e:
            print(f"Il processo di EventManager è fallito: {e}")


class TestEventManager(unittest.TestCase):

    def setUp(self):
        self.em_process = None
        self.module_processes = []
        # Avvia l'EventManager in un processo separato per il test
        self.em_process = Process(target=run_event_manager)
        self.em_process.start()
        time.sleep(1)  # Lascia il tempo al server di EventManager di inizializzarsi

    def tearDown(self):
        # Assicura che tutti i processi vengano terminati dopo ogni test
        if self.em_process and self.em_process.is_alive():
            self.em_process.terminate()
        for p in self.module_processes:
            if p.is_alive():
                p.terminate()

    def test_routing_and_shutdown_with_timeout(self):
        """
        Verifica l'instradamento dei messaggi (unicast e multicast) e la gestione
        del segnale di shutdown, con un timeout massimo di 60 secondi.
        """
        start_time = time.time()

        # 1. Crea e avvia i client mock per i moduli
        module1_client = Communicator("client", "lightSource", TEST_CONFIG['network'])
        module2_client = Communicator("client", "cuvetteSensor", TEST_CONFIG['network'])

        m1_stop_event = mpEvent()
        m2_stop_event = mpEvent()

        m1_comm_proc = Process(target=module1_client.run, args=(m1_stop_event,))
        m2_comm_proc = Process(target=module2_client.run, args=(m2_stop_event,))

        self.module_processes.extend([m1_comm_proc, m2_comm_proc])
        m1_comm_proc.start()
        m2_comm_proc.start()
        time.sleep(1)  # Lascia il tempo ai client di connettersi

        # 2. Invia messaggi di test (unicast e multicast)
        unicast_msg = {"Sender": "lightSource", "Destination": "cuvetteSensor", "Message": {"type": "UnicastTest"}}
        multicast_msg = {"Sender": "cuvetteSensor", "Destination": "All", "Message": {"type": "MulticastTest"}}

        module1_client.outgoingQueue.put(unicast_msg)
        module2_client.outgoingQueue.put(multicast_msg)

        # 3. Verifica la corretta ricezione dei messaggi
        try:
            # Il modulo 2 deve ricevere il messaggio unicast
            msg2_uni = module2_client.incomingQueue.get(timeout=5)
            self.assertEqual(msg2_uni['Message']['type'], 'UnicastTest')

            # Entrambi i moduli devono ricevere il messaggio multicast
            msg1_multi = module1_client.incomingQueue.get(timeout=5)
            self.assertEqual(msg1_multi['Message']['type'], 'MulticastTest')
            msg2_multi = module2_client.incomingQueue.get(timeout=5)
            self.assertEqual(msg2_multi['Message']['type'], 'MulticastTest')

        except Empty:
            self.fail("Un modulo non ha ricevuto il messaggio atteso entro il timeout.")

        # 4. Invia il segnale di Stop a EventManager
        stop_msg = {"Sender": "TestClient", "Destination": "EventManager", "Message": {"type": "Stop"}}

        # Usa un client temporaneo per inviare il messaggio di stop
        stopper_client = Communicator("client", "Stopper", TEST_CONFIG['network'])
        stopper_stop_event = mpEvent()
        stopper_comm_proc = Process(target=stopper_client.run, args=(stopper_stop_event,))
        self.module_processes.append(stopper_comm_proc)
        stopper_comm_proc.start()
        time.sleep(1)
        stopper_client.outgoingQueue.put(stop_msg)
        time.sleep(1)
        stopper_stop_event.set()
        stopper_comm_proc.join(timeout=5)

        # 5. Attendi la terminazione di tutti i processi rispettando il timeout globale
        remaining_time = 60.0 - (time.time() - start_time)
        self.em_process.join(timeout=remaining_time)

        # I client dovrebbero terminare dopo la chiusura del server
        m1_comm_proc.join(timeout=5)
        m2_comm_proc.join(timeout=5)

        # 6. Verifica che tutti i processi siano effettivamente terminati
        if self.em_process.is_alive():
            self.fail("Il processo di EventManager non è terminato entro 60 secondi.")

        if m1_comm_proc.is_alive():
            self.fail("Il processo del client del Modulo 1 non è terminato.")

        if m2_comm_proc.is_alive():
            self.fail("Il processo del client del Modulo 2 non è terminato.")


if __name__ == '__main__':
    unittest.main()