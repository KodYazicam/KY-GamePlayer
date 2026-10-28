"""Visual theme for KodYazar Client.

One place for colours, palette and the Qt style sheet. ``apply_theme`` is safe
to call with either a ``QApplication`` or a single widget; applying it to the
application also styles dialogs (file pickers, message boxes) that are not
children of the main window.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

# --- design tokens ---------------------------------------------------------
BG = "#16181d"
SURFACE = "#1e2026"
SURFACE_ALT = "#262931"
SURFACE_HOVER = "#2c303a"
BORDER = "#2f333d"
BORDER_STRONG = "#3d424e"
TEXT = "#eef0f4"
MUTED = "#a3a8b3"
ACCENT = "#5865f2"
ACCENT_HOVER = "#4752c4"
ACCENT_PRESSED = "#3c45a5"
SUCCESS = "#23a559"
DANGER = "#da373c"
WARNING = "#f0b232"

STYLE_SHEET = f"""
QWidget {{
    color: {TEXT};
    font-size: 13px;
}}
QWidget:focus {{ outline: none; }}
QDialog, QMainWindow, QWidget#kyRoot {{ background: {BG}; }}

QGroupBox {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 16px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {MUTED};
    font-size: 12px;
    font-weight: 700;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit,
QTextEdit, QPlainTextEdit, QListView, QListWidget {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 5px 9px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
QDateTimeEdit:hover, QTimeEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
    border-color: {BORDER_STRONG};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QDateTimeEdit:focus, QTimeEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QListView:focus, QListWidget:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    color: {MUTED};
    background: {SURFACE};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {ACCENT};
    outline: none;
}}

QPushButton {{
    background: {ACCENT};
    color: #ffffff;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {ACCENT_HOVER}; }}
QPushButton:pressed {{ background: {ACCENT_PRESSED}; }}
QPushButton:disabled {{ background: {SURFACE_ALT}; color: {MUTED}; border-color: {BORDER}; }}
QPushButton:checked {{ background: {ACCENT_HOVER}; }}
QPushButton[variant="ghost"] {{
    background: transparent;
    color: {TEXT};
    border: 1px solid {BORDER};
}}
QPushButton[variant="ghost"]:hover {{ background: {SURFACE_HOVER}; border-color: {BORDER_STRONG}; }}
QPushButton[variant="ghost"]:pressed {{ background: {SURFACE}; }}
QPushButton[variant="ghost"]:checked {{ background: {ACCENT}; border-color: {ACCENT}; color: #ffffff; }}
QPushButton[variant="danger"] {{
    background: transparent;
    color: {DANGER};
    border: 1px solid {DANGER};
}}
QPushButton[variant="danger"]:hover {{ background: {DANGER}; color: #ffffff; }}

QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px;
}}
QToolButton:hover {{ background: {SURFACE_HOVER}; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {MUTED}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 17px;
    height: 17px;
    border: 1px solid {BORDER_STRONG};
    border-radius: 4px;
    background: {SURFACE_ALT};
}}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{ image: none; }}

QTabWidget::pane {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 9px 16px;
    margin-right: 4px;
    border: 1px solid transparent;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    font-weight: 600;
}}
QTabBar::tab:hover {{ background: {SURFACE_HOVER}; color: {TEXT}; }}
QTabBar::tab:selected {{
    background: {SURFACE};
    color: {TEXT};
    border-color: {BORDER};
    border-bottom-color: {SURFACE};
}}

QListWidget {{ background: {SURFACE_ALT}; border: 1px solid {BORDER}; border-radius: 8px; padding: 4px; }}
QListWidget::item {{ border-radius: 6px; padding: 2px; }}
QListWidget::item:hover {{ background: {SURFACE_HOVER}; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #ffffff; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER_STRONG}; border-radius: 5px; min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QProgressBar {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: {TEXT};
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {BORDER}; }}

QMenu {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {ACCENT}; color: #ffffff; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}

QToolTip {{
    background: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 5px 8px;
}}

QMessageBox {{ background: {BG}; }}
QMessageBox QLabel {{ color: {TEXT}; }}
QStatusBar {{ background: {SURFACE}; color: {MUTED}; }}

QLabel#sectionTitle {{ font-size: 19px; font-weight: 700; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#statusOn {{ color: {SUCCESS}; font-size: 16px; font-weight: 600; }}
QLabel#statusOff {{ color: {DANGER}; font-size: 16px; font-weight: 600; }}
QFrame#panelBlock {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 8px;
}}
"""


def dark_palette() -> QPalette:
    """Palette that matches :data:`STYLE_SHEET` (used before the sheet loads)."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(SURFACE_ALT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE_ALT))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    return palette


def apply_theme(target: QApplication | QWidget | None = None) -> None:
    """Apply palette + style sheet to the application (or a single widget)."""
    app = target if isinstance(target, QApplication) else QApplication.instance()
    if app is not None:
        app.setPalette(dark_palette())
        app.setStyleSheet(STYLE_SHEET)
        return
    if isinstance(target, QWidget):
        target.setPalette(dark_palette())
        target.setStyleSheet(STYLE_SHEET)
