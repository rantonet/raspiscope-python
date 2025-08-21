import json
import time
import asyncio
import websockets
from threading import Thread, Event

class Module:
    """
    Classe base astratta per tutti i moduli funzionali.
    Gestisce la comunicazione client, il ciclo di vita e la gestione dei messaggi.
    """
    def __init__(self, name, addr="127.0.0.1", port=1025):
        self.name = name
        self.communicator_uri = f"ws://{addr}:{port}"
        self.stop_event = Event()
        self.websocket = None
        self.communicator_thread = None

    def run(self):
        """
        Punto di ingresso principale per il processo del modulo.
        Avvia la comunicazione e il ciclo di vita del modulo.
        """
        print(f"Modulo '{self.name}' in avvio.")
        self.communicator_thread = Thread(target=self.start_communicator)
        self.communicator_thread.start()

        # Attendi che la connessione sia stabilita
        while not self.websocket and not self.stop_event.is_set():
            time.sleep(0.1)
        
        if self.websocket:
            self.on_start()
            self.main_loop()
        
        self.on_stop()
        if self.communicator_thread:
            self.communicator_thread.join()
        print(f"Modulo '{self.name}' terminato.")

    def start_communicator(self):
        """Avvia il client di comunicazione in un loop asyncio."""
        asyncio.run(self.communicator_client())

    async def communicator_client(self):
        """Logica del client WebSocket."""
        try:
            async with websockets.connect(self.communicator_uri) as websocket:
                self.websocket = websocket
                await self.register()
                
                # Loop per ricevere messaggi
                while not self.stop_event.is_set():
                    try:
                        message_str = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                        message = json.loads(message_str)
                        
                        # Gestione speciale del messaggio di stop
                        if message.get("Message", {}).get("type") == "Stop":
                            print(f"Modulo '{self.name}' ha ricevuto il segnale di stop.")
                            self.stop_event.set()
                            break
                        
                        self.handle_message(message)
                    except asyncio.TimeoutError:
                        continue # Nessun messaggio, continua a controllare lo stop_event
                    except json.JSONDecodeError:
                        print(f"Errore di decodifica JSON nel modulo '{self.name}'")
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
            print(f"Connessione fallita per '{self.name}': {e}")
            self.websocket = None
            self.stop_event.set() # Ferma il modulo se non può connettersi

    async def register(self):
        """Invia un messaggio di registrazione al server."""
        reg_message = {
            "Sender": self.name,
            "Destination": "EventManager",
            "Message": {"type": "register"}
        }
        await self.websocket.send(json.dumps(reg_message))
        print(f"Modulo '{self.name}' registrato.")

    def send_message(self, destination, msg_type, payload=None):
        """
        Invia un messaggio al server EventManager.
        Questo metodo può essere chiamato da un thread non-asyncio.
        """
        if not self.websocket:
            print(f"Impossibile inviare messaggio: '{self.name}' non è connesso.")
            return

        message = {
            "Sender": self.name,
            "Destination": destination,
            "Message": {
                "type": msg_type,
                "payload": payload if payload is not None else {}
            }
        }
        # Esegui l'invio nel loop di eventi del comunicatore
        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps(message)),
            asyncio.get_running_loop()
        )

    # --- Metodi da sovrascrivere nelle classi figlie ---

    def on_start(self):
        """
        Chiamato una volta dopo che la connessione è stata stabilita.
        Utile per l'inizializzazione di hardware, ecc.
        """
        pass

    def main_loop(self):
        """
        Il loop principale del modulo.
        Il comportamento predefinito è attendere l'evento di stop.
        Può essere sovrascritto per moduli che necessitano di un'azione continua.
        """
        self.stop_event.wait()

    def handle_message(self, message):
        """
        Chiamato ogni volta che arriva un messaggio dal server.
        La logica specifica del modulo va qui.
        """
        pass

    def on_stop(self):
        """
        Chiamato prima che il modulo termini.
        Utile per la pulizia delle risorse (es. pin GPIO, file).
        """
        pass
