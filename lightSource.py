import time
from rpi_ws281x import PixelStrip,Color
from module import Module

class LightSource(Module):
    """
    Manages an RGB LED (e.g.,NeoPixel).
    Inherits from the base Module class.
    """
    def __init__(self,config,networkConfig,systemConfig):
        """
        Initializes the LightSource module.

        Args:
            config (dict): Module-specific configuration.
            network_config (dict): Network configuration for the base Module.
            system_config (dict): System-wide configuration for the base Module.
        """
        super().__init__("LightSource",networkConfig,systemConfig)
        self.config     = config
        self.pin        = self.config['pin']
        self.dma        = self.config['dma']
        # The library wants a value from 0-255
        self.brightness = int(self.config['brightness'] * 255)
        self.pwmChannel = self.config['pwm_channel']
        self.led        = None
        self.whiteColor = Color(255,255,255)

    def onStart(self):
        """
        Initializes the LED strip.
        """
        try:
            # The rpi_ws281x library requires root privileges to run
            self.led = PixelStrip(
                1,self.pin,800000,self.dma,False,self.brightness,self.pwmChannel
            )
            self.led.begin()
            self.turnOff() # Ensure the LED is off on startup
            print("Light source initialized.")
        except Exception as e:
            print(f"ERROR: Could not initialize light source. Run as root? Details: {e}")
            self.led = None

    def handleMessage(self,message):
        """
        Handles incoming messages from the event system.
        Acts as a dispatcher that invokes the appropriate methods.
        """
        if not self.led:
            print("Light source not available,command ignored.")
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
                print(f"'Dim' command received with invalid payload: {payload}")
        elif msgType == "Calibrate":
            if 'r' in payload and 'g' in payload and 'b' in payload:
                self.calibrate(payload)
            else:
                print(f"'Calibrate' command received with incomplete payload: {payload}")

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
        print("Turning on light source...")
        self.sendMessage("All","TurningOn")

        finalColor = self._calculateColor()
        self.led.setPixelColor(0,finalColor)
        self.led.show()
        self.is_on = True

        self.sendMessage("All","TurnedOn")
        print("Light source turned on.")

    def turnOff(self,initial=False):
        """
        Turns the LED off. Emits events before and after the action.

        Args:
            initial (bool): If True,does not send events (used only in on_start).
        """
        if not self.led: return
        if not initial:
            print("Turning off light source...")
            self.sendMessage("All","TurningOff")

        self.led.setPixelColor(0,Color(0,0,0))
        self.led.show()
        self.is_on = False

        if not initial:
            self.sendMessage("All","TurnedOff")
            print("Light source turned off.")

    def dim(self,brightness):
        """
        Adjusts the global brightness of the LED.

        Args:
            brightness (int): New brightness level (0-255).
        """
        if not self.led: return
        print(f"Adjusting brightness to {brightness}...")
        self.sendMessage("All","Dimming",{"brightness": brightness})

        self.brightness = brightness
        self.led.setBrightness(self.brightness)
        if self.is_on:
            self.led.show() # Immediately applies the new brightness if the LED is on

        self.sendMessage("All","Dimmed",{"brightness": self.brightness})
        print(f"Brightness set to {self.brightness}.")

    def calibrate(self,factors):
        """
        Applies calibration factors to the RGB channels.

        Args:
            factors (dict): A dictionary with 'r','g','b' factors.
        """
        if not self.led: return
        print(f"Applying calibration: {factors}...")
        self.sendMessage("All","Calibrating",factors)

        self.rgb_calibration = (
            float(factors.get('r',1.0)),
            float(factors.get('g',1.0)),
            float(factors.get('b',1.0))
        )

        if self.is_on:
            # If the LED is on,immediately apply the new calibrated color
            finalColor = self._calculateColor()
            self.led.setPixelColor(0,finalColor)
            self.led.show()

        self.sendMessage("All","Calibrated",{
            "r": self.rgb_calibration,
            "g": self.rgb_calibration[1],
            "b": self.rgb_calibration
        })
        print(f"Calibration applied. New factors: {self.rgb_calibration}")

    def onStop(self):
        """
        Ensures the LED is turned off when the module terminates.
        """
        print("Stopping LightSource module...")
        if self.led:
            self.turnOff(initial=True) # Turns off without sending events