# module.py
import json
import time
from threading import Thread, Event
from queue import Empty
from communicator import Communicator

class Module:
    """
    Classe base astratta per tutti i moduli funzionali.
    Gestisce la comunicazione client, il ciclo di vita e la gestione dei messaggi
    utilizzando un'istanza di Communicator disaccoppiata.
    """
    def __init__(self, name, addr="127.0.0.1", port=1025):
        self.name = name
        self.communicator = Communicator(comm_type="client", name=self.name, addr=addr, port=port)
        self.stop_event = Event()
        self.communicator_thread = None

    def run(self):
        """
        Punto di ingresso principale per il processo del modulo.
        Avvia il communicator e il ciclo di vita del modulo.
        """
        print(f"Modulo '{self.name}' in avvio.")
        self.communicator_thread = Thread(target=self.communicator.run, args=(self.stop_event,))
        self.communicator_thread.start()

        self.on_start()
        self.main_loop()
        
        self.on_stop()
        if self.communicator_thread:
            self.communicator_thread.join()
        print(f"Modulo '{self.name}' terminato.")

    def main_loop(self):
        """
        Il ciclo principale del modulo.
        Estrae i messaggi dalla incomingQueue e li gestisce.
        """
        while not self.stop_event.is_set():
            try:
                message = self.communicator.incomingQueue.get(block=True, timeout=0.1)

                # Gestione speciale per il messaggio di stop
                if message.get("Message", {}).get("type") == "Stop":
                    print(f"Modulo '{self.name}' ha ricevuto il segnale di stop.")
                    self.stop_event.set()
                    break
                
                self.handle_message(message)
                self.communicator.incomingQueue.task_done()

            except Empty:
                continue # Nessun messaggio, continua a controllare lo stop_event

    def send_message(self, destination, msg_type, payload=None):
        """
        Invia un messaggio al server EventManager tramite la outgoingQueue.
        Questo metodo è thread-safe.
        """
        message = {
            "Sender": self.name,
            "Destination": destination,
            "Message": {
                "type": msg_type,
                "payload": payload if payload is not None else {}
            }
        }
        self.communicator.outgoingQueue.put(message)

    # --- Metodi da sovrascrivere nelle classi figlie ---

    def on_start(self):
        """
        Chiamato una volta all'avvio del modulo.
        Utile per inizializzare hardware, ecc.
        """
        pass

    def handle_message(self, message):
        """
        Chiamato ogni volta che arriva un messaggio dal server.
        La logica specifica del modulo va qui.
        """
        pass

    def on_stop(self):
        """
        Chiamato prima che il modulo termini.
        Utile per pulire le risorse (es. pin GPIO, file).
        """
        pass