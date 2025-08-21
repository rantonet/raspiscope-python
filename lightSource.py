import time
from rpi_ws281x import PixelStrip, Color
from module import Module

class LightSource(Module):
    """
    Manages an RGB LED (e.g., NeoPixel).
    Inherits from the base Module class.
    """
    def __init__(self, pin, dma, brightness, pwm_channel):
        super().__init__("LightSource")
        self.pin = pin
        self.dma = dma
        self.brightness = int(brightness * 255) # The library wants a value from 0-255
        self.pwm_channel = pwm_channel
        self.led = None
        self.white_color = Color(255, 255, 255)

    def on_start(self):
        """
        Initializes the LED strip.
        """
        try:
            # The rpi_ws281x library requires root privileges to run
            self.led = PixelStrip(
                1, self.pin, 800000, self.dma, False, self.brightness, self.pwm_channel
            )
            self.led.begin()
            self.turn_off() # Ensure the LED is off on startup
            print("Light source initialized.")
        except Exception as e:
            print(f"ERROR: Could not initialize light source. Run as root? Details: {e}")
            self.led = None

    def handle_message(self, message):
        """
        Handles incoming messages.
        """
        if not self.led:
            print("Light source not available, ignoring command.")
            return

        msg_type = message.get("Message", {}).get("type")
        
        if msg_type == "CuvettePresent":
            print("Cuvette present, turning on the light.")
            self.turn_on()
        elif msg_type == "CuvetteAbsent":
            print("Cuvette absent, turning off the light.")
            self.turn_off()
        elif msg_type == "TurnOn":
            self.turn_on()
        elif msg_type == "TurnOff":
            self.turn_off()

    def turn_on(self):
        """Turns the LED on with a white color."""
        if self.led:
            self.led.setPixelColor(0, self.white_color)
            self.led.show()
            self.send_message("All", "LightTurnedOn")

    def turn_off(self):
        """Turns the LED off."""
        if self.led:
            self.led.setPixelColor(0, Color(0, 0, 0))
            self.led.show()
            self.send_message("All", "LightTurnedOff")

    def on_stop(self):
        """
        Ensures the LED is turned off when the module terminates.
        """
        print("Shutting down light source...")
        self.turn_off()