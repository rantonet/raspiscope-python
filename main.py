import json
import time
from multiprocessing import Process
from analysis import Analysis
from eventManager import EventManager
from camera import Camera
from cuvetteSensor import CuvetteSensor
from lightSource import LightSource
from configLoader import loadConfig

def main():
    """
    Main entry point of the application.
    Loads the configuration, instantiates all modules, and starts the EventManager.
    """
    config = loadConfig()

    try:
        # Instantiation of modules with parameters from the configuration
        cameraModule = Camera(
            config=config.get('camera', {})
        )
        cuvetteSensorModule = CuvetteSensor(
            input_pin=config.get('cuvette_sensor', {}).get('input_pin')
        )
        lightSourceModule = LightSource(
            pin=config.get('light_source', {}).get('pin'),
            dma=config.get('light_source', {}).get('dma', 10), # Default value
            brightness=config.get('light_source', {}).get('brightness', 0.8), # Default value
            pwm_channel=config.get('light_source', {}).get('pwm_channel', 0) # Default value
        )
        analysisModule = Analysis(
            reference_spectra_path=config.get('analysis', {}).get('reference_spectra_path'),
            tolerance_nm=config.get('analysis', {}).get('tolerance_nm', 10) # Default value
        )

        # List of modules to pass to the EventManager
        modulesToRun = [
            cameraModule,
            cuvetteSensorModule,
            lightSourceModule,
            analysisModule
        ]

        # Creation and startup of the EventManager
        eventManager = EventManager(modules=modulesToRun)
        eventManager.run()

    except KeyError as e:
        print(f"Error: missing configuration key in 'config.json': {e}")
    except Exception as e:
        print(f"An unexpected error occurred during initialization: {e}")

if __name__ == "__main__":
    main()