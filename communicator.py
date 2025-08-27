import json
import socket
from threading import Thread,Event
from queue import Queue,Empty,Full

class Communicator:
    """
    Handles inter-process communication (IPC) for modules and the EventManager.
    It works as either a server (for the EventManager) or a client (for modules),
    using a network socket to send and receive JSON-formatted messages.

    The event format is a JSON dictionary with the following mandatory keys:

    - **"Sender"** (str): The unique name of the module that sent the message (e.g., "CuvetteSensor").
    - **"Destination"** (str): The unique name of the target module. "All" can be used for broadcast messages.
    - **"Message"** (dict): A nested dictionary containing the message details.
      - **"type"** (str): A string representing the type of event (e.g., "CuvettePresent", "TurnOn", "LogMessage").
      - **"payload"** (dict, optional): A dictionary containing the data associated with the event. The structure of this dictionary depends on the `type` of the message. This field is optional and can be an empty dictionary if no data is needed.
    """
    def __init__(self,commType,name,config):
        """
        Initializes the Communicator instance.

        Args:
            commType (str): "server" for the EventManager or "client" for a Module.
            name (str): The name of the module or "Server" for the EventManager.
            config (dict): The network configuration with 'address' and 'port'.
        """
        self.commType       = commType
        self.name           = name
        self.config         = config
        self.conn           = None
        self.server_socket  = None
        self.incomingQueue  = Queue()
        self.outgoingQueue  = Queue()
        self.client_threads = []
        self.client_sockets = {}

    def run(self,stopEvent=None):
        """
        Starts the communication loop. The behavior depends on whether the
        instance is a server or a client.
        """
        if self.commType == "server":
            self._runServer(stopEvent)
        elif self.commType == "client":
            self._runClient(stopEvent)
        else:
            print(f"Error: Unknown communicator type '{self.commType}'")

    # --- Server-side methods ---
    def _runServer(self,stopEvent):
        """
        Runs the server loop for the EventManager.
        Accepts connections and manages threads for each client.
        """
        self.server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        self.server_socket.settimeout(1.0) # To allow graceful exit

        try:
            self.server_socket.bind((self.config['address'],self.config['port']))
            self.server_socket.listen(5)
            print(f"Server started on {self.config['address']}:{self.config['port']}")
        except OSError as e:
            print(f"ERROR: Could not start server. Details: {e}")
            return
        
        while not stopEvent.is_set():
            try:
                conn,addr = self.server_socket.accept()
                print(f"Accepted connection from {addr}")
                
                # Identify client by its initial message
                initial_msg_data = conn.recv(1024).decode('utf-8')
                initial_msg = json.loads(initial_msg_data)
                client_name = initial_msg.get('name')
                
                if client_name:
                    self.client_sockets[client_name] = conn
                    conn.settimeout(1.0)
                    client_thread = Thread(target=self._serverHandleClient,args=(client_name,conn,stopEvent))
                    client_thread.daemon = True
                    self.client_threads.append(client_thread)
                    client_thread.start()
                    print(f"Client thread started for '{client_name}'")
                else:
                    conn.close()
                    print("Received connection from unknown client. Connection closed.")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Server error: {e}")
                
        # Cleanup
        for client_thread in self.client_threads:
            if client_thread.is_alive():
                client_thread.join(timeout=1.0)
        self.server_socket.close()

    def _serverHandleClient(self,client_name,conn,stopEvent):
        """
        Thread-specific loop for handling a single client connection.
        """
        # A server handler might also need to send messages to the client,
        # but for this specific application, the EventManager handles routing
        # and doesn't directly send back to the client. This is a placeholder.
        while not stopEvent.is_set():
            try:
                data = conn.recv(4096).decode('utf-8')
                if data:
                    messages = self._parseMessages(data)
                    for message in messages:
                        self.incomingQueue.put(message)
                else: # Client disconnected
                    print(f"Client '{client_name}' disconnected.")
                    break
            except socket.timeout:
                continue
            except (socket.error,ConnectionResetError):
                print(f"Client '{client_name}' connection lost.")
                break
            except Exception as e:
                print(f"Error handling client '{client_name}': {e}")
                break

    # --- Client-side methods ---
    def _runClient(self,stopEvent):
        """
        Runs the client loop for a module.
        Manages connection to the server and message exchange.
        """
        while not stopEvent.is_set():
            try:
                self.conn = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.conn.connect((self.config['address'],self.config['port']))
                self.conn.settimeout(1.0)
                
                # Send name for identification
                initial_msg = json.dumps({"name": self.name})
                self.conn.sendall(initial_msg.encode('utf-8'))

                print(f"Client '{self.name}' connected to server.")
                
                # Start a separate thread to handle sending messages
                send_thread = Thread(target=self._clientSendLoop,args=(stopEvent,))
                send_thread.daemon = True
                send_thread.start()

                self._clientReceiveLoop(stopEvent)
                
                send_thread.join()

            except (ConnectionRefusedError,socket.timeout):
                print("Connection failed. Retrying in 3 seconds...")
                time.sleep(3)
            except Exception as e:
                print(f"Client '{self.name}' error: {e}")
                self.conn.close()
                break
        
        if self.conn:
            self.conn.close()

    def _clientReceiveLoop(self,stopEvent):
        """
        Receives messages from the server and puts them in the incoming queue.
        """
        while not stopEvent.is_set():
            try:
                data = self.conn.recv(4096).decode('utf-8')
                if data:
                    messages = self._parseMessages(data)
                    for message in messages:
                        self.incomingQueue.put(message)
                else:
                    print("Server disconnected.")
                    break
            except socket.timeout:
                continue
            except (socket.error,ConnectionResetError):
                print("Connection to server lost.")
                break
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

    def _clientSendLoop(self,stopEvent):
        """
        Sends messages from the outgoing queue to the server.
        """
        while not stopEvent.is_set():
            try:
                message = self.outgoingQueue.get(block=True,timeout=1.0)
                json_data = json.dumps(message)
                self.conn.sendall(json_data.encode('utf-8'))
                self.outgoingQueue.task_done()
            except Empty:
                continue
            except (socket.error,ConnectionResetError):
                print("Failed to send message: connection lost.")
                break
            except Exception as e:
                print(f"Error sending message: {e}")
                break

    # --- Utility methods ---
    def _parseMessages(self,data):
        """
        Parses a raw data string into a list of JSON messages.
        Handles the case where multiple messages are received at once.
        """
        messages = []
        try:
            # Assuming one message per recv() for simplicity,
            # a more robust implementation would handle message boundaries
            # by parsing a header or a delimiter.
            messages.append(json.loads(data))
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        return messages