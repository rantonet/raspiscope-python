import json
import time
from multiprocessing import Process
from analysis import Analysis
from eventManager import EventManager
from camera import Camera
from cuvetteSensor import CuvetteSensor
from lightSource import LightSource

def load_config():
    """Loads the configuration from the config.json file."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: 'config.json' file not found. Please create one based on 'config.example.json'")
        exit(1)
    except json.JSONDecodeError:
        print("Error: 'config.json' is not a valid JSON file.")
        exit(1)

def main():
    """
    Main entry point of the application.
    Loads the configuration, instantiates all modules, and starts the EventManager.
    """
    config = load_config()

    try:
        # Instantiation of modules with parameters from the configuration
        camera_module = Camera(
            config=config.get('camera', {})
        )
        cuvette_sensor_module = CuvetteSensor(
            input_pin=config.get('cuvette_sensor', {}).get('input_pin')
        )
        light_source_module = LightSource(
            pin=config.get('light_source', {}).get('pin'),
            dma=config.get('light_source', {}).get('dma', 10), # Default value
            brightness=config.get('light_source', {}).get('brightness', 0.8), # Default value
            pwm_channel=config.get('light_source', {}).get('pwm_channel', 0) # Default value
        )
        analysis_module = Analysis(
            reference_spectra_path=config.get('analysis', {}).get('reference_spectra_path'),
            tolerance_nm=config.get('analysis', {}).get('tolerance_nm', 10) # Default value
        )

        # List of modules to pass to the EventManager
        modules_to_run = [
            camera_module,
            cuvette_sensor_module,
            light_source_module,
            analysis_module
        ]

        # Creation and startup of the EventManager
        event_manager = EventManager(modules=modules_to_run)
        event_manager.run()

    except KeyError as e:
        print(f"Error: missing configuration key in 'config.json': {e}")
    except Exception as e:
        print(f"An unexpected error occurred during initialization: {e}")

if __name__ == "__main__":
    main()