import json
import time
import websockets
import asyncio
from threading import RLock

class Communicator:
    """
    Classe per le comunicazioni tra moduli tramite WebSocket.
    Può operare in modalità 'server' (usata da EventManager) o 'client' (usata dai moduli).
    """

    def __init__(self, comm_type="server", addr="127.0.0.1", port=1025):
        self.name = "Communicator"
        self.incomingQueue = []
        self.type = comm_type
        self.address = addr
        self.port = port
        
        # Per il server: mappa i nomi dei client ai loro oggetti websocket
        self.clients = {}
        self.lock = RLock()

    def run(self, stop_event=None):
        """Avvia il server o il client in un nuovo loop di eventi asyncio."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if self.type == "server":
            loop.run_until_complete(self.server(stop_event))
        elif self.type == "client":
            # Il client non ha bisogno di un stop_event qui, è gestito dal modulo
            pass # Il client viene eseguito dal modulo stesso
        loop.close()

    async def server(self, stop_event):
        """Logica del server WebSocket."""
        print(f"Server in ascolto su ws://{self.address}:{self.port}")
        async with websockets.serve(self.server_handler, self.address, self.port):
            if stop_event:
                await stop_event.wait()
            else:
                # Esegui per sempre se non c'è un evento di stop
                await asyncio.Future() 

    async def server_handler(self, websocket, path):
        """Gestisce le connessioni dei singoli client."""
        client_name = None
        try:
            # Il primo messaggio deve essere una registrazione
            reg_message_str = await websocket.recv()
            reg_message = json.loads(reg_message_str)
            
            if reg_message.get("Message", {}).get("type") == "register":
                client_name = reg_message["Sender"]
                with self.lock:
                    self.clients[client_name] = websocket
                print(f"Client '{client_name}' connesso e registrato.")
                self.incomingQueue.append(reg_message_str)
            else:
                print("Connessione rifiutata: primo messaggio non di registrazione.")
                return

            # Ascolta i messaggi successivi
            async for message in websocket:
                self.incomingQueue.append(message)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client '{client_name}' disconnesso.")
        finally:
            if client_name:
                with self.lock:
                    if client_name in self.clients:
                        del self.clients[client_name]

    def send_to(self, destination, message):
        """Invia un messaggio a un destinatario specifico."""
        asyncio.run(self._async_send_to(destination, message))

    async def _async_send_to(self, destination, message):
        with self.lock:
            client_ws = self.clients.get(destination)
        if client_ws:
            try:
                await client_ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                print(f"Impossibile inviare a '{destination}': connessione chiusa.")
        else:
            print(f"Destinazione '{destination}' non trovata.")

    def broadcast(self, message, sender):
        """Invia un messaggio a tutti i client tranne il mittente."""
        asyncio.run(self._async_broadcast(message, sender))

    async def _async_broadcast(self, message, sender):
        with self.lock:
            clients_to_send = [ws for name, ws in self.clients.items() if name != sender]
        
        if clients_to_send:
            tasks = [ws.send(message) for ws in clients_to_send]
            await asyncio.gather(*tasks, return_exceptions=True)
