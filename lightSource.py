"""
Author: Antlampas
CC BY-SA 4.0
https://creativecommons.org/licenses/by-sa/4.0/
"""

import time
from rpi_ws281x import PixelStrip,Color
from module     import Module
from configLoader import ConfigLoader

class LightSource(Module):
    """
    Manages an RGB LED (e.g.,NeoPixel).
    Inherits from the base Module class.
    """
    def __init__(self,networkConfig,systemConfig):
        """
        Initializes the LightSource module.
        """
        config_loader = ConfigLoader()
        full_config = config_loader.get_config()

        super().__init__("LightSource",networkConfig,systemConfig)
        self.pin        = full_config['pin']
        self.dma        = full_config['dma']
        # The library wants a value from 0-255
        self.brightness = int(full_config['brightness'] * 255)
        self.pwmChannel = full_config['pwm_channel']
        self.led        = None
        self.whiteColor = Color(255,255,255)

    def onStart(self):
        """
        Initializes the LED strip.
        """
        self.sendMessage("EventManager", "Register")
        try:
            # The rpi_ws281x library requires root privileges to run
            self.led = PixelStrip(
                1,self.pin,800000,self.dma,False,self.brightness,self.pwmChannel
            )
            self.led.begin()
            self.turnOff() # Ensure the LED is off on startup
            self.log("INFO","Light source initialized.")
        except Exception as e:
            self.log("ERROR",f"Could not initialize light source. Run as root? Details: {e}")
            self.led = None

    def handleMessage(self,message):
        """
        Handles incoming messages from the event system.
        Acts as a dispatcher that invokes the appropriate methods.
        """
        if not self.led:
            self.log("WARNING","Light source not available,command ignored.")
            return

        msgType = message.get("Message",{}).get("type")
        payload = message.get("Message",{}).get("payload",{})

        if msgType == "TurnOn" or msgType == "CuvettePresent":
            self.turnOn()
        elif msgType == "TurnOff" or msgType == "CuvetteAbsent":
            self.turnOff()
        elif msgType == "Dim":
            newBrightness = payload.get("brightness")
            if isinstance(newBrightness,int) and 0 <= newBrightness <= 255:
                self.dim(newBrightness)
            else:
                self.log("WARNING",f"'Dim' command received with invalid payload: {payload}")
        elif msgType == "Calibrate":
            if 'r' in payload and 'g' in payload and 'b' in payload:
                self.calibrate(payload)
            else:
                self.log("WARNING",f"'Calibrate' command received with incomplete payload: {payload}")

    def _calculateColor(self):
        """
        Helper method to calculate the final color to apply to the LED,
        taking RGB calibration into account.
        """
        r = int(self.base_color * self.rgb_calibration)
        g = int(self.base_color[1] * self.rgb_calibration[1])
        b = int(self.base_color * self.rgb_calibration)

        # Ensures the values are within the  range
        r = max(0,min(255,r))
        g = max(0,min(255,g))
        b = max(0,min(255,b))

        return Color(r,g,b)

    def turnOn(self):
        """
        Turns the LED on. Emits events before and after the action.
        """
        if not self.led: return
        self.log("INFO","Turning on light source...")
        self.sendMessage("All","TurningOn")

        finalColor = self._calculateColor()
        self.led.setPixelColor(0,finalColor)
        self.led.show()
        self.is_on = True

        self.sendMessage("All","TurnedOn")
        self.log("INFO","Light source turned on.")

    def turnOff(self,initial=False):
        """
        Turns the LED off. Emits events before and after the action.

        Args:
            initial (bool): If True,does not send events (used only in on_start).
        """
        if not self.led: return
        if not initial:
            self.log("INFO","Turning off light source...")
            self.sendMessage("All","TurningOff")

        self.led.setPixelColor(0,Color(0,0,0))
        self.led.show()
        self.is_on = False

        if not initial:
            self.sendMessage("All","TurnedOff")
            self.log("INFO","Light source turned off.")

    def dim(self,brightness):
        """
        Adjusts the global brightness of the LED.

        Args:
            brightness (int): New brightness level (0-255).
        """
        if not self.led: return
        self.log("INFO",f"Adjusting brightness to {brightness}...")
        self.sendMessage("All","Dimming",{"brightness": brightness})

        self.brightness = brightness
        self.led.setBrightness(self.brightness)
        if self.is_on:
            self.led.show() # Immediately applies the new brightness if the LED is on

        self.sendMessage("All","Dimmed",{"brightness": self.brightness})
        self.log("INFO",f"Brightness set to {self.brightness}.")

    def setColor(self, r, g, b):
        """
        Sets the RGB color of the LED.

        Args:
            r (int): The red color component (0-255).
            g (int): The green color component (0-255).
            b (int): The blue color component (0-255).
        """
        if not self.led:
            self.log("WARNING", "Cannot set color, light source not available.")
            return

        self.log("INFO", f"Setting LED color to R:{r}, G:{g}, B:{b}...")
        self.led.setPixelColor(0, Color(r, g, b))
        self.led.show()
        self.is_on = True

        self.sendMessage("All", "ColorSet", {"r": r, "g": g, "b": b})
        self.log("INFO", "LED color set successfully.")

    def onStop(self):
        """
        Ensures the LED is turned off when the module terminates.
        """
        self.log("INFO","Stopping LightSource module...")
        if self.led:
            self.turnOff(initial=True) # Turns off without sending events