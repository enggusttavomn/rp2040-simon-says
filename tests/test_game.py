"""Host checks of game logic; hardware behavior still requires an RP2040."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, Mock, patch


def load_game():
    machine = ModuleType("machine")
    for name in ("PWM", "Pin", "SoftI2C", "ADC"):
        setattr(machine, name, MagicMock())
    machine.Pin.side_effect = lambda *args, **kwargs: MagicMock()
    ssd1306 = ModuleType("ssd1306")
    ssd1306.SSD1306_I2C = MagicMock()
    neopixel = ModuleType("neopixel")  # Native RP2 module, supplied by MicroPython.
    neopixel.NeoPixel = MagicMock()
    path = Path(__file__).resolve().parents[1] / "main.py"
    spec = importlib.util.spec_from_file_location("simon_game", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"machine": machine, "ssd1306": ssd1306, "neopixel": neopixel}):
        spec.loader.exec_module(module)
    return module


class GameTests(unittest.TestCase):
    def setUp(self):
        self.app = load_game()
        self.game = self.app.SimonGame.__new__(self.app.SimonGame)

    def test_waiting_for_start_uses_command_value(self):
        class Command(str):
            pass

        class Started(Exception):
            pass

        self.game.get_player_input = Mock(side_effect=["B", Command("A")])
        self.game.start_game = Mock(side_effect=Started)
        with patch.object(self.app.time, "sleep"), self.assertRaises(Started):
            self.game.run()
        self.game.start_game.assert_called_once_with()

    def test_joystick_switch_does_not_emit_unsupported_command(self):
        self.app.button_a.value.return_value = 1
        self.app.button_b.value.return_value = 1
        self.app.joystick_button.value.return_value = 0
        with patch.object(self.app.time, "sleep"):
            self.assertIsNone(self.game.get_player_input())

    def test_generated_sequences_use_only_supported_commands(self):
        for length in range(2, 9):
            self.game.generate_sequence(length)
            self.assertEqual(len(self.game.sequence), length)
            self.assertTrue(set(self.game.sequence).issubset(self.app.COMMANDS))
            self.assertTrue(set(self.game.sequence).issubset(self.app.COMMAND_SOUNDS))

    def test_local_libraries_do_not_shadow_native_neopixel(self):
        lib = Path(__file__).resolve().parents[1] / "lib"
        self.assertFalse((lib / "neopixel.py").exists())


if __name__ == "__main__":
    unittest.main()
