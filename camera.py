import numpy
import time
import cv2
import base64
from picamera2 import Picamera2
from threading import Thread
from module import Module

class Camera(Module):
    """
    Gestisce la PiCamera.
    Eredita dalla classe base Module.
    """
    def __init__(self, config):
        super().__init__("Camera")
        self.camera = None
        self.config = config

    def on_start(self):
        """
        Inizializza e configura la fotocamera all'avvio del modulo.
        """
        try:
            self.camera = Picamera2()
            resolution = tuple(self.config.get("resolution", [1920, 1080]))
            cam_config = self.camera.create_still_configuration({"size": resolution})
            self.camera.configure(cam_config)
            self.camera.start()
            print("Fotocamera avviata e configurata.")
        except Exception as e:
            print(f"ERRORE: Impossibile inizializzare la fotocamera: {e}")
            self.camera = None # Assicura che la fotocamera sia None se fallisce

    def handle_message(self, message):
        """
        Gestisce i messaggi in arrivo.
        """
        if not self.camera:
            print("Fotocamera non disponibile, ignoro il comando.")
            return

        msg_type = message.get("Message", {}).get("type")
        
        if msg_type == "CuvettePresent":
            print("Ricevuto segnale di cuvetta presente. Scatto una foto.")
            self.take_picture()
        elif msg_type == "Take":
            print("Ricevuto comando 'Take'. Scatto una foto.")
            self.take_picture()
        elif msg_type == "Calibrate":
            print("Ricevuto comando 'Calibrate'. Avvio calibrazione.")
            self.calibrate()

    def take_picture(self):
        """
        Scatta una foto e la invia al modulo Analysis.
        """
        if not self.camera:
            print("Impossibile scattare foto, fotocamera non inizializzata.")
            return
            
        try:
            print("Scatto foto...")
            # Cattura l'immagine come array numpy
            image_array = self.camera.capture_array()
            
            # Codifica l'immagine in formato JPG e poi in Base64
            _, buffer = cv2.imencode('.jpg', image_array)
            image_b64 = base64.b64encode(buffer).decode('utf-8')
            
            payload = {"image": image_b64}
            self.send_message("Analysis", "Analyze", payload)
            print("Foto scattata e inviata per l'analisi.")
            
        except Exception as e:
            print(f"ERRORE durante lo scatto della foto: {e}")

    def calibrate(self):
        """
        Esegue la calibrazione della fotocamera.
        Placeholder per la logica di calibrazione effettiva.
        """
        print("Avvio calibrazione fotocamera...")
        # TODO: Implementare la logica di calibrazione (es. bilanciamento del bianco, esposizione).
        time.sleep(2) # Simula il tempo di calibrazione
        self.send_message("All", "CameraCalibrated", {"status": "success"})
        print("Calibrazione fotocamera completata.")

    def on_stop(self):
        """
        Ferma la fotocamera quando il modulo viene terminato.
        """
        if self.camera and self.camera.started:
            self.camera.stop()
            print("Fotocamera fermata.")
