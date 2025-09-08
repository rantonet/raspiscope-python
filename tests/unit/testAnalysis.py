import unittest
import json
import time
import os
import shutil
import tempfile
import base64
import numpy as np
import cv2
from multiprocessing import Process
from multiprocessing import Event as mpEvent
from queue           import Empty

from eventManager    import EventManager
from communicator    import Communicator
from analysis        import Analysis
from module          import Module
from unittest.mock   import patch, MagicMock

# --- Configurazione di Rete e di Sistema per il Test ---
TEST_CONFIG = {
    "network" : {"address": "127.0.0.1", "port": 1025, "client_reconnect_delay_s": 0.1},
    "system"  : {"module_message_queue_timeout_s": 0.1},
    "modules" : {
        "FakeSpectrograms" : {"enabled": True},
        "FakeAnalysis"     : {"enabled": True, "reference_spectra_path": "placeholder", "tolerance_nm": 5},
        "Logger"           : {"enabled": True}
    }
}

# --- Modulo Mock per Generare Spettrogrammi Falsi ---
class FakeSpectrograms(Module):
    """
    Un modulo mock che genera immagini di spettrogrammi fittizi e li invia
    al modulo di analisi per il test.
    """
    def __init__(self, config, networkConfig, systemConfig):
        super().__init__("FakeSpectrograms", networkConfig, systemConfig)

    def generate_and_send_spectrogram(self, substance_name_to_check):
        """
        Genera un'immagine fittizia e invia un messaggio 'Analyze' a FakeAnalysis.
        """
        fake_image = np.zeros((100, 200, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', fake_image)
        image_b64 = base64.b64encode(buffer).decode('utf-8')
        payload = {"image": image_b64, "expected_substance": substance_name_to_check}
        self.sendMessage("FakeAnalysis", "Analyze", payload)

# --- Mappatura dei Moduli per l'EventManager del Test ---
MOCK_MODULE_MAP = {
    "FakeSpectrograms": FakeSpectrograms,
    "FakeAnalysis": Analysis,
    "Logger": MagicMock()
}

def run_event_manager(config_path):
    """Funzione target per eseguire l'EventManager in un processo separato."""
    with patch.dict('eventManager.MODULE_MAP', MOCK_MODULE_MAP):
        manager = EventManager(config_path)
        manager.run()

# --- Classe di Test ---
class TestAnalysisInteractionWithTimeout(unittest.TestCase):

    def setUp(self):
        """Imposta l'ambiente di test prima di ogni esecuzione."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, 'config.json')
        self.ref_spectra_path = os.path.join(self.temp_dir, 'reference_spectra.csv')

        reference_data = "wavelength,substance\n450,SubstanceA\n550,SubstanceB\n650,SubstanceC"
        with open(self.ref_spectra_path, 'w') as f:
            f.write(reference_data)

        TEST_CONFIG["modules"]["FakeAnalysis"]["reference_spectra_path"] = self.ref_spectra_path
        with open(self.config_path, 'w') as f:
            json.dump(TEST_CONFIG, f)

        self.em_process = Process(target=run_event_manager, args=(self.config_path,))
        self.em_process.start()
        time.sleep(2)

        self.test_communicator = Communicator("client", "FakeSpectrograms", TEST_CONFIG['network'])
        self.comm_stop_event = mpEvent()
        self.comm_process = Process(target=self.test_communicator.run, args=(self.comm_stop_event,))
        self.comm_process.start()
        time.sleep(1)

    def tearDown(self):
        """Pulisce le risorse al termine di ogni test."""
        if self.comm_process and self.comm_process.is_alive():
            self.comm_stop_event.set()
            self.comm_process.join(timeout=2)
            if self.comm_process.is_alive():
                self.comm_process.terminate()

        if self.em_process and self.em_process.is_alive():
            self.em_process.terminate()
            self.em_process.join(timeout=2)

        shutil.rmtree(self.temp_dir)

    @patch('analysis.Analysis.compareWithReferences')
    def test_analysis_workflow_with_timeout(self, mock_compare_with_references):
        """
        Testa il flusso di analisi e la terminazione controllata con un timeout totale di 30 secondi.
        """
        start_time = time.time()
        TOTAL_TIMEOUT = 30.0
        SHUTDOWN_TIMEOUT = 10.0

        # 1. Mock della logica di analisi
        expected_substance = "SubstanceB"
        mock_compare_with_references.return_value = {"identified_substances": [expected_substance]}

        # 2. Invio del messaggio di analisi
        analyze_msg = {
            "Sender": "FakeSpectrograms", "Destination": "FakeAnalysis",
            "Message": {"type": "Analyze", "payload": {"image": "fake_base64_image"}}
        }
        self.test_communicator.outgoingQueue.put(analyze_msg)

        # 3. Attesa e verifica della risposta
        try:
            response_msg = self.test_communicator.incomingQueue.get(timeout=10)
            self.assertEqual(response_msg['Message']['type'], "AnalysisComplete")
            self.assertEqual(response_msg['Message']['payload']['identified_substances'], [expected_substance])
        except Empty:
            self.fail("Timeout: Nessun messaggio 'AnalysisComplete' ricevuto entro 10 secondi.")

        # 4. Verifica del tempo trascorso prima dello shutdown
        elapsed_time = time.time() - start_time
        if elapsed_time > TOTAL_TIMEOUT:
            self.fail(f"Test fallito: il tempo limite di {TOTAL_TIMEOUT}s è stato superato prima dello shutdown.")
        
        # 5. Inizio della procedura di shutdown
        print("\nTest: Procedura di shutdown avviata...")
        stop_msg = {"Sender": "TestClient", "Destination": "EventManager", "Message": {"type": "Stop"}}
        
        # Utilizzo di un client temporaneo per inviare il segnale di stop
        stopper_client = Communicator("client", "Stopper", TEST_CONFIG['network'])
        stopper_stop_event = mpEvent()
        stopper_comm_proc = Process(target=stopper_client.run, args=(stopper_stop_event,))
        stopper_comm_proc.start()
        time.sleep(1)
        stopper_client.outgoingQueue.put(stop_msg)
        time.sleep(1) # Lascia il tempo al messaggio di essere inviato
        stopper_stop_event.set()
        stopper_comm_proc.join(timeout=5)

        # 6. Attesa della terminazione dei processi principali
        self.em_process.join(timeout=SHUTDOWN_TIMEOUT)
        self.comm_process.join(timeout=SHUTDOWN_TIMEOUT)

        # 7. Verifica finale
        if self.em_process.is_alive():
            self.fail(f"Shutdown fallito: EventManager non è terminato entro {SHUTDOWN_TIMEOUT}s.")
        if self.comm_process.is_alive():
            self.fail(f"Shutdown fallito: Il modulo FakeSpectrograms non è terminato entro {SHUTDOWN_TIMEOUT}s.")
        
        total_duration = time.time() - start_time
        print(f"Test completato con successo in {total_duration:.2f} secondi.")

if __name__ == '__main__':
    unittest.main()