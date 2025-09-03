import sys
from eventManager import EventManager
from configLoader import ConfigLoader # <-- Modificato: Importa ConfigLoader

def main():
    """
    Main entry point of the application.
    Loads the configuration and starts the EventManager,
    which will handle module instantiation and orchestration.
    """
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    try:
        # L'instanziazione dei moduli viene delegata all'EventManager.
        # Il main si occupa solo di avviare l'EventManager con il file
        # di configurazione corretto.
        print(f"Loading configuration from '{config_path}'...")
        event_manager = EventManager(configPath=config_path)
        event_manager.run()

    except Exception as e:
        # Gli errori critici di configurazione (es. file non trovato)
        # vengono già gestiti da ConfigLoader, che termina l'applicazione.
        # Questa clausola cattura altre eccezioni impreviste.
        print(f"An unexpected error occurred during initialization: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()