import unittest
from unittest.mock import MagicMock, patch, call
from rpi_ws281x import PixelStrip, Color
from lightSource import LightSource

class TestLightSource(unittest.TestCase):
    def setUp(self):
        self.mock_config =  {
                                "pin"         : 18,
                                "dma"         : 10,
                                "brightness"  : 0.5,
                                "pwm_channel" : 0
                            }
        self.mock_network_config = {}
        self.mock_system_config  = {}
        
        self.mock_pixelstrip = MagicMock(spec=PixelStrip)
        self.mock_pixelstrip_patcher = patch('lightSource.PixelStrip', return_value=self.mock_pixelstrip)
        self.mock_pixelstrip_patcher.start()
        
        self.mock_module_patcher = patch('lightSource.Module', MagicMock(spec=True))
        self.mock_module = self.mock_module_patcher.start()
        
        with patch('lightSource.Color', MagicMock(side_effect=lambda r, g, b: f"Color({r},{g},{b})")):
            self.light_source_module = LightSource(self.mock_config, self.mock_network_config, self.mock_system_config)

    def tearDown(self):
        self.mock_pixelstrip_patcher.stop()
        self.mock_module_patcher.stop()

    def test_onStart_success(self):
        """Verifica la corretta inizializzazione della striscia LED."""
        self.light_source_module.onStart()
        self.mock_pixelstrip.begin.assert_called_once()
        self.mock_pixelstrip.setPixelColor.assert_called_once_with(0, "Color(0,0,0)")
        self.mock_module.log.assert_called_once_with("INFO", "Light source initialized.")

    def test_onStart_error(self):
        """Verifica la gestione di un errore di inizializzazione."""
        self.mock_pixelstrip.begin.side_effect = Exception("Test Error")
        self.light_source_module.onStart()
        self.mock_module.log.assert_called_once_with("ERROR", "Could not initialize light source. Run as root? Details: Test Error")
        self.assertIsNone(self.light_source_module.led)

    def test_turnOn(self):
        """Verifica che turnOn imposti il colore e mostri il risultato."""
        self.light_source_module.led = self.mock_pixelstrip
        self.light_source_module.is_on = False
        self.light_source_module.turnOn()
        self.mock_pixelstrip.setPixelColor.assert_called_with(0, 'Color(255,255,255)')
        self.mock_pixelstrip.show.assert_called_once()
        self.assertTrue(self.light_source_module.is_on)
        self.mock_module.sendMessage.assert_has_calls([
            call("All", "TurningOn"),
            call("All", "TurnedOn")
        ])
        self.mock_module.log.assert_has_calls([
            call("INFO", "Turning on light source..."),
            call("INFO", "Light source turned on.")
        ])

    def test_dim(self):
        """Verifica che dim regoli la luminosità e invii i messaggi di log."""
        self.light_source_module.led = self.mock_pixelstrip
        self.light_source_module.is_on = True
        self.light_source_module.dim(100)
        self.mock_pixelstrip.setBrightness.assert_called_once_with(100)
        self.mock_pixelstrip.show.assert_called_once()
        self.assertEqual(self.light_source_module.brightness, 100)
        self.mock_module.log.assert_has_calls([
            call("INFO", "Adjusting brightness to 100..."),
            call("INFO", "Brightness set to 100.")
        ])

    def test_onStop(self):
        """Verifica che onStop spenga la luce e invii il log."""
        self.light_source_module.led = self.mock_pixelstrip
        with patch.object(self.light_source_module, 'turnOff') as mock_turn_off:
            self.light_source_module.onStop()
            mock_turn_off.assert_called_once_with(initial=True)
            self.mock_module.log.assert_called_once_with("INFO", "Stopping LightSource module...")