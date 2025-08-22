# config_loader.py
import json
import sys

_config = None

def loadConfig(config_path="config.json"):
    """
    Carica, analizza e restituisce la configurazione da un file JSON.
    Il risultato viene memorizzato nella cache per evitare letture multiple.

    Args:
        config_path (str): Il percorso del file di configurazione JSON.

    Returns:
        dict: Un dizionario che rappresenta la configurazione.

    Raises:
        SystemExit: Se il file non viene trovato, non è un JSON valido,
                    o mancano chiavi essenziali.
    """
    global _config
    if _config is not None:
        return _config

    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
    except FileNotFoundError:
        print(f"ERRORE CRITICO: Il file di configurazione '{config_path}' non è stato trovato.", file=sys.stderr)
        sys.exit(1) # Termina l'applicazione con un codice di errore
    except json.JSONDecodeError as e:
        print(f"ERRORE CRITICO: Il file di configurazione '{config_path}' non è un file JSON valido.", file=sys.stderr)
        print(f"Dettagli dell'errore: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERRORE CRITICO: Si è verificato un errore imprevisto durante la lettura di '{config_path}'.", file=sys.stderr)
        print(f"Dettagli: {e}", file=sys.stderr)
        sys.exit(1)

    # Validazione di base per la presenza di chiavi principali
    required_keys = ["network", "system", "modules"]
    for key in required_keys:
        if key not in config_data:
            print(f"ERRORE CRITICO: La chiave obbligatoria '{key}' manca nel file di configurazione.", file=sys.stderr)
            sys.exit(1)

    _config = config_data
    return _config