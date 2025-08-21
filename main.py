import json
import time
from multiprocessing import Process
from analysis import Analysis
from eventManager import EventManager
from camera import Camera
from cuvetteSensor import CuvetteSensor
from lightSource import LightSource

def load_config():
    """Carica la configurazione dal file config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Errore: file 'config.json' non trovato. Creane uno basato su 'config.example.json'")
        exit(1)
    except json.JSONDecodeError:
        print("Errore: 'config.json' non è un file JSON valido.")
        exit(1)

def main():
    """
    Punto di ingresso principale dell'applicazione.
    Carica la configurazione, istanzia tutti i moduli e avvia l'EventManager.
    """
    config = load_config()

    try:
        # Istanziazione dei moduli con i parametri dalla configurazione
        camera_module = Camera(
            config=config.get('camera', {})
        )
        cuvette_sensor_module = CuvetteSensor(
            input_pin=config.get('cuvette_sensor', {}).get('input_pin')
        )
        light_source_module = LightSource(
            pin=config.get('light_source', {}).get('pin'),
            dma=config.get('light_source', {}).get('dma', 10), # Valore di default
            brightness=config.get('light_source', {}).get('brightness', 0.8), # Valore di default
            pwm_channel=config.get('light_source', {}).get('pwm_channel', 0) # Valore di default
        )
        analysis_module = Analysis(
            reference_spectra_path=config.get('analysis', {}).get('reference_spectra_path'),
            tolerance_nm=config.get('analysis', {}).get('tolerance_nm', 10) # Valore di default
        )

        # Lista dei moduli da passare all'EventManager
        modules_to_run = [
            camera_module,
            cuvette_sensor_module,
            light_source_module,
            analysis_module
        ]

        # Creazione e avvio dell'EventManager
        event_manager = EventManager(modules=modules_to_run)
        event_manager.run()

    except KeyError as e:
        print(f"Errore: chiave di configurazione mancante in 'config.json': {e}")
    except Exception as e:
        print(f"Si è verificato un errore imprevisto durante l'inizializzazione: {e}")

if __name__ == "__main__":
    main()
