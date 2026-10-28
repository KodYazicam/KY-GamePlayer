from __future__ import annotations

import unittest
from unittest import mock

try:  # theme imports Qt for the system-scheme probe
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - CI unit matrix
    raise unittest.SkipTest("PySide6 not installed") from exc

from ky_gameplayer.ui import theme


def _luminance(color: str) -> float:
    value = color.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast(foreground: str, background: str) -> float:
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class TokenTests(unittest.TestCase):
    def tearDown(self) -> None:
        theme.set_mode("dark")

    def test_text_tokens_meet_wcag_aa(self) -> None:
        pairs = (
            (theme.DARK.TEXT, theme.DARK.BG),
            (theme.DARK.TEXT, theme.DARK.SURFACE),
            (theme.DARK.MUTED, theme.DARK.SURFACE),
            (theme.DARK.ROW_TEXT, theme.DARK.SURFACE),
            (theme.LIGHT.TEXT, theme.LIGHT.BG),
            (theme.LIGHT.TEXT, theme.LIGHT.SURFACE),
            (theme.LIGHT.MUTED, theme.LIGHT.SURFACE),
            (theme.LIGHT.ROW_TEXT, theme.LIGHT.SURFACE),
        )
        for foreground, background in pairs:
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(_contrast(foreground, background), 4.5)

    def test_white_on_accent_is_readable(self) -> None:
        self.assertGreaterEqual(_contrast("#ffffff", theme.DARK.ACCENT), 4.5)
        self.assertGreaterEqual(_contrast("#ffffff", theme.LIGHT.ACCENT), 4.5)

    def test_style_sheet_follows_tokens(self) -> None:
        dark = theme.build_style_sheet(theme.DARK)
        light = theme.build_style_sheet(theme.LIGHT)
        self.assertIn(theme.DARK.SURFACE, dark)
        self.assertIn(theme.LIGHT.SURFACE, light)
        self.assertNotIn(theme.DARK.BG, light)
        self.assertIn(theme.LIGHT.ACCENT, light)

    def test_mode_resolution_and_alias(self) -> None:
        theme.set_mode("light")
        self.assertEqual(theme.tokens(), theme.LIGHT)
        theme.set_mode("nonsense")
        self.assertEqual(theme.mode(), "dark")
        with mock.patch.object(theme, "system_is_dark", return_value=False):
            theme.set_mode("system")
            self.assertEqual(theme.active_mode(), "light")
            self.assertEqual(theme.tokens(), theme.LIGHT)
        with mock.patch.object(theme, "system_is_dark", return_value=True):
            theme.set_mode("system")
            self.assertEqual(theme.active_mode(), "dark")


class ApplyThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self) -> None:
        theme.apply_theme(self.app, "dark")

    def test_palette_switches(self) -> None:
        theme.apply_theme(self.app, "light")
        palette = self.app.palette()
        self.assertEqual(palette.color(QPalette.ColorRole.Window).name(), theme.LIGHT.BG)
        self.assertIn(theme.LIGHT.BG, self.app.styleSheet())

        theme.apply_theme(self.app, "dark")
        palette = self.app.palette()
        self.assertEqual(palette.color(QPalette.ColorRole.Window).name(), theme.DARK.BG)
        self.assertIn(theme.DARK.BG, self.app.styleSheet())


if __name__ == "__main__":
    unittest.main()
