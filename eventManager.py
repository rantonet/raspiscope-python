import json
import signal
import time
from multiprocessing import Process, Event
from threading import Thread
from communicator import Communicator

class EventManager:
    """
    Gestore di eventi per l'orchestrazione dei moduli.
    Avvia tutti i moduli come processi separati e instrada i messaggi tra di loro.
    """

    def __init__(self, modules=None):
        """
        Costruttore dell'EventManager.
        Args:
            modules (list): Lista di istanze di moduli da eseguire.
        """
        self.name = "EventManager"
        self.communicator = Communicator("server")
        self.modules = modules if modules else []
        self.running_processes = []
        self._stop_event = Event()

    def run(self):
        """Avvia il server di comunicazione e tutti i processi dei moduli."""
        # Imposta i gestori per uno spegnimento pulito
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        comm_thread = Thread(target=self.communicator.run, args=(self._stop_event,))
        comm_thread.start()
        time.sleep(0.1)  # Attesa per l'avvio del server

        for module in self.modules:
            process = Process(target=module.run)
            process.daemon = True  # I processi figli terminano se il padre muore
            self.running_processes.append({'process': process, 'name': module.name})

        for p_info in self.running_processes:
            print(f'Starting {p_info["name"]}')
            p_info['process'].start()
            time.sleep(0.01)

        print("EventManager in esecuzione. Premere Ctrl+C per uscire.")
        try:
            while not self._stop_event.is_set():
                self.route()
                time.sleep(0.001)
        finally:
            self._cleanup()
            comm_thread.join()
            print("EventManager terminato.")

    def route(self):
        """Estrae i messaggi dalla coda e li instrada."""
        if not self.communicator.incomingQueue:
            return

        message_str = self.communicator.incomingQueue.pop(0)
        try:
            message = json.loads(message_str)
            destination = message.get("Destination")
            sender = message.get("Sender")

            # Gestione della registrazione del client
            if message.get("Message", {}).get("type") == "register":
                print(f"Registrazione del client: {sender}")
                # La logica del comunicatore ora gestisce l'associazione nome-websocket
                return

            print(f"Routing messaggio da {sender} a {destination}")

            if destination == "All":
                self.communicator.broadcast(message_str, sender)
            elif destination:
                self.communicator.send_to(destination, message_str)

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Errore durante il routing del messaggio: {e} - Messaggio: {message_str}")

    def _handle_shutdown(self, signum, frame):
        """Gestisce i segnali di interruzione (es. Ctrl+C)."""
        print(f"\nRicevuto segnale di spegnimento ({signum}). Avvio terminazione...")
        self._stop_event.set()

    def _cleanup(self):
        """Pulisce le risorse e termina i processi dei moduli."""
        print("Invio del segnale di stop a tutti i moduli...")
        stop_message = json.dumps({
            "Sender": self.name,
            "Destination": "All",
            "Message": {"type": "Stop"}
        })
        self.communicator.broadcast(stop_message, self.name)
        time.sleep(1) # Dà tempo ai moduli di terminare

        print("Terminazione dei processi dei moduli...")
        for p_info in self.running_processes:
            if p_info['process'].is_alive():
                p_info['process'].terminate()
                p_info['process'].join(timeout=1)
                print(f"Processo {p_info['name']} terminato.")
