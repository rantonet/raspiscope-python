import unittest
import time
import json
from multiprocessing import Process, Event as mpEvent, Queue as mpQueue
from queue import Empty

from communicator import Communicator
from eventManager import EventManager
from unittest.mock import patch

# --- Configurazione di Rete per il Test ---
TEST_CONFIG = {
    "network": {"address": "127.0.0.1", "port": 1025, "client_reconnect_delay_s": 0.1},
    "system": {"module_message_queue_timeout_s": 0.1},
    "modules": {"FakeModule1": {"enabled": True}, "FakeModule2": {"enabled": True}}
}

# --- Modulo Fittizio per il Test di Comunicazione ---
def fake_module_run(name, stop_event, messages_to_send, received_messages_queue):
    """
    Funzione eseguita da un processo che simula un modulo.
    Invia una lista di messaggi e raccoglie tutti i messaggi ricevuti.
    """
    communicator = Communicator("client", name, TEST_CONFIG['network'])
    comm_process = Process(target=communicator.run, args=(stop_event,))
    comm_process.start()

    # Attende la connessione
    time.sleep(1) 

    # Invia tutti i messaggi in sequenza
    for msg in messages_to_send:
        communicator.outgoingQueue.put(msg)
        time.sleep(0.1) # Simula un piccolo ritardo tra i messaggi

    # Raccoglie i messaggi in arrivo finché non viene impostato l'evento di stop
    while not stop_event.is_set():
        try:
            received_msg = communicator.incomingQueue.get(timeout=0.1)
            received_messages_queue.put(received_msg)
        except Empty:
            continue
    
    comm_process.join()

def run_event_manager():
    """Funzione target per eseguire l'EventManager in un processo separato."""
    with patch('eventManager.loadConfig', return_value=TEST_CONFIG), \
         patch('eventManager.MODULE_MAP', new={}): # Nessun modulo reale istanziato
        manager = EventManager("config.json")
        manager.run()

# --- Classe di Test ---
class TestCommunicatorEndToEnd(unittest.TestCase):

    def setUp(self):
        """Prepara l'ambiente di test avviando l'EventManager."""
        self.em_process = Process(target=run_event_manager)
        self.em_process.start()
        time.sleep(1.5) # Attesa per l'avvio del server

    def tearDown(self):
        """Pulisce le risorse terminando il processo dell'EventManager."""
        if self.em_process.is_alive():
            self.em_process.terminate()

    def test_message_exchange_and_shutdown_with_timeout(self):
        """
        Verifica lo scambio di messaggi tra due moduli e la loro terminazione
        controllata, rispettando un timeout totale di 30 secondi.
        """
        start_time = time.time()
        TOTAL_TIMEOUT = 30.0
        SHUTDOWN_WAIT_TIME = 5.0

        # 1. Definisce i messaggi da scambiare
        messages_from_m1 = [
            {"Sender": "FakeModule1", "Destination": "FakeModule2", "Message": {"type": "Ping", "payload": 1}},
            {"Sender": "FakeModule1", "Destination": "All", "Message": {"type": "Broadcast", "payload": "Hello"}}
        ]
        messages_from_m2 = [
            {"Sender": "FakeModule2", "Destination": "FakeModule1", "Message": {"type": "Ack", "payload": 1}},
            {"Sender": "FakeModule2", "Destination": "FakeModule1", "Message": {"type": "Data", "payload": [1, 2, 3]}}
        ]

        # 2. Prepara e avvia i processi dei moduli fittizi
        m1_stop_event = mpEvent()
        m2_stop_event = mpEvent()
        m1_received_q = mpQueue()
        m2_received_q = mpQueue()

        m1_proc = Process(target=fake_module_run, args=("FakeModule1", m1_stop_event, messages_from_m1, m1_received_q))
        m2_proc = Process(target=fake_module_run, args=("FakeModule2", m2_stop_event, messages_from_m2, m2_received_q))

        m1_proc.start()
        m2_proc.start()

        # Attende che i messaggi vengano scambiati
        time.sleep(2) 

        # 3. Verifica dei messaggi ricevuti
        m1_received_list = [m1_received_q.get() for _ in range(m1_received_q.qsize())]
        m2_received_list = [m2_received_q.get() for _ in range(m2_received_q.qsize())]
        
        # Estrae solo il corpo del messaggio per un confronto più semplice
        m1_payloads = [msg['Message'] for msg in m1_received_list]
        m2_payloads = [msg['Message'] for msg in m2_received_list]
        m2_expected_payloads = [msg['Message'] for msg in messages_from_m1]
        m1_expected_payloads = [msg['Message'] for msg in messages_from_m2] + [m2_expected_payloads[1]] # M1 riceve anche il suo broadcast

        self.assertCountEqual(m1_payloads, m1_expected_payloads, "Modulo 1 ha ricevuto messaggi inattesi.")
        self.assertCountEqual(m2_payloads, m2_expected_payloads, "Modulo 2 ha ricevuto messaggi inattesi.")

        # 4. Invia segnale di stop e attende la terminazione
        print("\nTest: Invio del segnale di stop ai moduli...")
        m1_stop_event.set()
        m2_stop_event.set()

        m1_proc.join(timeout=SHUTDOWN_WAIT_TIME)
        m2_proc.join(timeout=SHUTDOWN_WAIT_TIME)
        
        # 5. Verifica la terminazione e il timeout totale
        if m1_proc.is_alive():
            m1_proc.terminate()
            self.fail(f"Modulo 1 non è terminato entro {SHUTDOWN_WAIT_TIME} secondi.")
        if m2_proc.is_alive():
            m2_proc.terminate()
            self.fail(f"Modulo 2 non è terminato entro {SHUTDOWN_WAIT_TIME} secondi.")
            
        elapsed_time = time.time() - start_time
        if elapsed_time > TOTAL_TIMEOUT:
            self.fail(f"Il test ha superato il timeout totale di {TOTAL_TIMEOUT} secondi (durata: {elapsed_time:.2f}s).")
            
        print(f"Test completato con successo in {elapsed_time:.2f} secondi.")

if __name__ == '__main__':
    unittest.main()