import cv2
import numpy
import pandas
import time
import base64
import json
from scipy.signal import find_peaks
from threading import Thread
from module import Module

class Analysis(Module):
    """
    Classe per l'analisi dello spettrogramma.
    Eredita dalla classe base Module.
    """
    def __init__(self, reference_spectra_path="", tolerance_nm=10):
        super().__init__("Analysis")
        self.reference_spectra_path = reference_spectra_path
        self.tolerance_nm = tolerance_nm
        self.reference_spectra = None

    def on_start(self):
        """
        Metodo chiamato all'avvio del modulo.
        Carica i dati di riferimento.
        """
        try:
            self.reference_spectra = pandas.read_csv(self.reference_spectra_path)
            self.reference_spectra.set_index('wavelength', inplace=True)
            print("Dati di riferimento caricati con successo.")
        except FileNotFoundError:
            print(f"ERRORE: File di riferimento non trovato: {self.reference_spectra_path}")
            # Il modulo continuerà a funzionare ma non potrà analizzare
        except Exception as e:
            print(f"ERRORE durante il caricamento dei dati di riferimento: {e}")

    def handle_message(self, message):
        """
        Gestisce i messaggi in arrivo.
        """
        msg_type = message.get("Message", {}).get("type")
        payload = message.get("Message", {}).get("payload", {})

        if msg_type == "Analyze":
            print("Ricevuto comando di analisi.")
            if self.reference_spectra is None:
                print("Impossibile analizzare: dati di riferimento non caricati.")
                return
            
            image_b64 = payload.get("image")
            if image_b64:
                # Decodifica l'immagine da Base64
                img_bytes = base64.b64decode(image_b64)
                img_np = numpy.frombuffer(img_bytes, dtype=numpy.uint8)
                image_data = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                
                # Avvia l'analisi in un thread separato per non bloccare
                analysis_thread = Thread(target=self.perform_analysis, args=(image_data,))
                analysis_thread.start()
            else:
                print("Comando 'Analyze' ricevuto senza dati immagine.")

    def perform_analysis(self, image_data):
        """
        Esegue l'analisi dello spettrogramma.
        Questa è una funzione di placeholder e dovrebbe essere implementata.
        """
        print("Avvio analisi dello spettrogramma...")
        # TODO: Implementare la logica di estrazione della striscia,
        # calcolo dello spettrogramma e confronto.

        # Esempio di invio di risultati (dati fittizi)
        time.sleep(2) # Simula il tempo di elaborazione
        
        results = {
            "substances": ["Sostanza A", "Sostanza B"],
            "spectrogram_data": [1, 2, 3, 4, 5]
        }
        
        self.send_message("All", "AnalysisComplete", results)
        print("Analisi completata e risultati inviati.")
