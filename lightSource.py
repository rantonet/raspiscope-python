import time
from rpi_ws281x import PixelStrip, Color
from module import Module

class LightSource(Module):
    """
    Gestisce un LED RGB (es. NeoPixel).
    Eredita dalla classe base Module.
    """
    def __init__(self, pin, dma, brightness, pwm_channel):
        super().__init__("LightSource")
        self.pin = pin
        self.dma = dma
        self.brightness = int(brightness * 255) # La libreria vuole un valore 0-255
        self.pwm_channel = pwm_channel
        self.led = None
        self.white_color = Color(255, 255, 255)

    def on_start(self):
        """
        Inizializza la striscia LED.
        """
        try:
            # La libreria rpi_ws281x richiede privilegi di root per essere eseguita
            self.led = PixelStrip(
                1, self.pin, 800000, self.dma, False, self.brightness, self.pwm_channel
            )
            self.led.begin()
            self.turn_off() # Assicura che il LED sia spento all'avvio
            print("Sorgente luminosa inizializzata.")
        except Exception as e:
            print(f"ERRORE: Impossibile inizializzare la sorgente luminosa. Esegui come root? Dettagli: {e}")
            self.led = None

    def handle_message(self, message):
        """
        Gestisce i messaggi in arrivo.
        """
        if not self.led:
            print("Sorgente luminosa non disponibile, ignoro il comando.")
            return

        msg_type = message.get("Message", {}).get("type")
        
        if msg_type == "CuvettePresent":
            print("Cuvetta presente, accendo la luce.")
            self.turn_on()
        elif msg_type == "CuvetteAbsent":
            print("Cuvetta assente, spengo la luce.")
            self.turn_off()
        elif msg_type == "TurnOn":
            self.turn_on()
        elif msg_type == "TurnOff":
            self.turn_off()

    def turn_on(self):
        """Accende il LED con colore bianco."""
        if self.led:
            self.led.setPixelColor(0, self.white_color)
            self.led.show()
            self.send_message("All", "LightTurnedOn")

    def turn_off(self):
        """Spegne il LED."""
        if self.led:
            self.led.setPixelColor(0, Color(0, 0, 0))
            self.led.show()
            self.send_message("All", "LightTurnedOff")

    def on_stop(self):
        """
        Assicura che il LED sia spento alla terminazione del modulo.
        """
        print("Spegnimento sorgente luminosa...")
        self.turn_off()
