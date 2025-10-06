"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

import sys
import signal
from multiprocessing import Process
from threading       import Thread

from eventManager    import EventManager
from configLoader    import ConfigLoader
from logger          import Logger
from lightSource     import LightSource
from cuvetteSensor   import CuvetteSensor
from camera          import Camera
from analysis        import Analysis
from cli             import CLI
from gui             import GUI

def main():
    """
    Main entry point of the application.
    Loads the configuration, starts all enabled modules in separate processes,
    and runs the EventManager in the main thread to coordinate them.
    """
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    config_loader = ConfigLoader(config_path)
    config = config_loader.get_config()

    modules_to_start = {
        "logger"        : Logger,
        "lightSource"   : LightSource,
        "cuvetteSensor" : CuvetteSensor,
        "camera"        : Camera,
        "analysis"      : Analysis,
        "cli"           : CLI,
    }
    running_processes = []
    
    event_manager = EventManager(configPath=config_path)
    emProcess = Process(target=event_manager.run)
    emProcess.start()

    # 3. Start each enabled module in its own process
    for name, module_class in modules_to_start.items():
        if name in config['modules'] and config['modules'][name].get('enabled', False):
            print(f"Starting module: {name}")
            module_config = config['modules'][name]
            network_config = config['network']
            system_config = config['system']
            
            instance = module_class(module_config, network_config, system_config)
            
            process = Process(target=instance.run)
            process.start()
            
            running_processes.append({'name': name, 'process': process})

    def shutdown():
        print("Shutdown signal received. Terminating all processes...")
        event_manager.stop()
        for p_info in running_processes:
            print(f"Terminating {p_info['name']}...")
            p_info['process'].terminate()
            p_info['process'].join()
        # The EventManager thread will be stopped by its own signal handler
        # We just need to wait for it to finish
        emProcess.join()
        print("All processes terminated. Exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep the main thread alive to wait for signals
    emProcess.join() # Wait for event manager to finish
    # If the event manager thread finishes, it means a shutdown was requested
    # so we call shutdown() to clean up the other processes
    shutdown()

if __name__ == "__main__":
    main()
