import unittest
from unittest.mock import MagicMock, patch
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

    def test_handleMessage_turnOn(self):
        """Verifica che il messaggio 'TurnOn' attivi la luce."""
        self.light_source_module.led = self.mock_pixelstrip
        with patch.object(self.light_source_module, 'turnOn') as mock_turn_on:
            self.light_source_module.handleMessage({"Message": {"type": "TurnOn"}})
            mock_turn_on.assert_called_once()

    def test_handleMessage_dim(self):
        """Verifica che il messaggio 'Dim' regoli la luminosità."""
        self.light_source_module.led = self.mock_pixelstrip
        with patch.object(self.light_source_module, 'dim') as mock_dim:
            self.light_source_module.handleMessage({"Message": {"type": "Dim", "payload": {"brightness": 100}}})
            mock_dim.assert_called_once_with(100)
    
    def test_turnOn(self):
        """Verifica che turnOn imposti il colore e mostri il risultato."""
        self.light_source_module.led = self.mock_pixelstrip
        self.light_source_module.base_color = (255, 255, 255)
        self.light_source_module.rgb_calibration = (1, 1, 1)

        self.light_source_module.turnOn()
        self.mock_pixelstrip.setPixelColor.assert_called_with(0, 'Color(255,255,255)')
        self.mock_pixelstrip.show.assert_called_once()
        self.assertTrue(self.light_source_module.is_on)
        self.mock_module.sendMessage.assert_has_calls([
            call("All", "TurningOn"),
            call("All", "TurnedOn")
        ])

    def test_onStop(self):
        """Verifica che onStop spenga la luce."""
        self.light_source_module.led = self.mock_pixelstrip
        with patch.object(self.light_source_module, 'turnOff') as mock_turn_off:
            self.light_source_module.onStop()
            mock_turn_off.assert_called_once_with(initial=True)