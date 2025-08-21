import time
from gpiozero import InputDevice, GPIOZeroError
from threading import Thread
from module import Module
import statistics

class CuvetteSensor(Module):
    """
    Rileva la presenza della cuvetta tramite un sensore a effetto Hall.
    Eredita dalla classe base Module.
    """
    def __init__(self, input_pin):
        super().__init__("CuvetteSensor")
        self.input_pin = input_pin
        self.sensor = None
        self.presence_threshold = 0
        self.threshold_span = 0.1
        self.is_present = False

    def on_start(self):
        """
        Inizializza il sensore e avvia la calibrazione.
        """
        try:
            self.sensor = InputDevice(self.input_pin)
            print(f"Sensore cuvetta inizializzato sul pin {self.input_pin}.")
            self.calibrate()
        except GPIOZeroError as e:
            print(f"ERRORE: Impossibile inizializzare il sensore sul pin {self.input_pin}. Controlla i collegamenti e i permessi. Dettagli: {e}")
            self.sensor = None

    def main_loop(self):
        """
        Sovrascrive il loop principale per controllare continuamente la presenza.
        """
        if not self.sensor:
            # Se il sensore non è stato inizializzato, non fare nulla.
            time.sleep(1)
            return

        while not self.stop_event.is_set():
            self.check_presence()
            time.sleep(0.1) # Controlla ogni 100ms

    def check_presence(self):
        """
        Controlla il valore del sensore e invia un segnale se lo stato cambia.
        """
        try:
            current_value = self.sensor.value
            currently_present = current_value < self.presence_threshold
            
            if currently_present and not self.is_present:
                self.is_present = True
                print("Cuvetta inserita.")
                self.send_message("All", "CuvettePresent")
            elif not currently_present and self.is_present:
                self.is_present = False
                print("Cuvetta rimossa.")
                self.send_message("All", "CuvetteAbsent")
        except Exception as e:
            print(f"Errore durante la lettura del sensore: {e}")
            # Potrebbe essere utile fermare il loop o tentare di reinizializzare
            self.stop_event.set()


    def calibrate(self, num_samples=100):
        """
        Esegue la calibrazione per impostare la soglia di presenza.
        Assume che la cuvetta NON sia presente durante la calibrazione.
        """
        if not self.sensor:
            print("Impossibile calibrare: sensore non inizializzato.")
            return

        print("Avvio calibrazione sensore cuvetta... (assicurarsi che non ci sia la cuvetta)")
        samples = []
        try:
            for _ in range(num_samples):
                samples.append(self.sensor.value)
                time.sleep(0.01)
            
            if samples:
                # La soglia è la media delle letture a vuoto meno un margine
                mean_value = statistics.mean(samples)
                self.presence_threshold = mean_value - self.threshold_span
                print(f"Calibrazione completata. Soglia impostata a: {self.presence_threshold:.4f}")
            else:
                raise ValueError("Nessun campione raccolto.")
        except Exception as e:
            print(f"ERRORE durante la calibrazione del sensore: {e}")
