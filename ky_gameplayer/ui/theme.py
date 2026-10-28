"""Visual theme for KodYazar Client.

One place for colours, palette and the Qt style sheet. ``apply_theme`` is safe
to call with either a ``QApplication`` or a single widget; applying it to the
application also styles dialogs (file pickers, message boxes) that are not
children of the main window.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


@dataclass(frozen=True)
class Tokens:
    """Colour tokens shared by the style sheet and the custom-painted widgets."""

    BG: str
    SURFACE: str
    SURFACE_ALT: str
    SURFACE_HOVER: str
    BORDER: str
    BORDER_STRONG: str
    TEXT: str
    MUTED: str
    ACCENT: str
    ACCENT_HOVER: str
    ACCENT_PRESSED: str
    SUCCESS: str
    DANGER: str
    WARNING: str
    SELECTED: str
    HOVER: str
    ROW_TEXT: str


DARK = Tokens(
    BG="#16181d",
    SURFACE="#1e2026",
    SURFACE_ALT="#262931",
    SURFACE_HOVER="#2c303a",
    BORDER="#2f333d",
    BORDER_STRONG="#3d424e",
    TEXT="#eef0f4",
    MUTED="#a3a8b3",
    ACCENT="#5865f2",
    ACCENT_HOVER="#4752c4",
    ACCENT_PRESSED="#3c45a5",
    SUCCESS="#23a559",
    DANGER="#da373c",
    WARNING="#f0b232",
    SELECTED="#404249",
    HOVER="#35373c",
    ROW_TEXT="#dbdee1",
)

LIGHT = Tokens(
    BG="#f4f5f8",
    SURFACE="#ffffff",
    SURFACE_ALT="#eef0f5",
    SURFACE_HOVER="#e5e8ef",
    BORDER="#d7dbe3",
    BORDER_STRONG="#b9c0cd",
    TEXT="#181a1f",
    MUTED="#5b6270",
    ACCENT="#5865f2",
    ACCENT_HOVER="#4752c4",
    ACCENT_PRESSED="#3c45a5",
    SUCCESS="#1a7f37",
    DANGER="#c9372c",
    WARNING="#a86300",
    SELECTED="#d9def0",
    HOVER="#e8ebf2",
    ROW_TEXT="#20232a",
)

TOKEN_NAMES = tuple(DARK.__dataclass_fields__)

_MODES = ("system", "dark", "light")
_mode = "dark"
_active = DARK


def system_is_dark() -> bool:
    app = QGuiApplication.instance()
    if app is None:
        return True
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Light:
        return False
    return True


def resolve_mode(mode: str) -> str:
    if mode == "light":
        return "light"
    if mode == "system":
        return "dark" if system_is_dark() else "light"
    return "dark"


def set_mode(mode: str) -> None:
    global _mode, _active
    _mode = mode if mode in _MODES else "dark"
    _active = LIGHT if resolve_mode(_mode) == "light" else DARK


def mode() -> str:
    """Configured mode: ``system``, ``dark`` or ``light``."""
    return _mode


def active_mode() -> str:
    """Concrete mode after resolving ``system``."""
    return resolve_mode(_mode)


def tokens() -> Tokens:
    return _active


def build_style_sheet(t: Tokens) -> str:
    return f"""
    QWidget {{
        color: {t.TEXT};
        font-size: 13px;
    }}
    QWidget:focus {{ outline: none; }}
    QDialog, QMainWindow, QWidget#kyRoot {{ background: {t.BG}; }}

    QGroupBox {{
        background: {t.SURFACE};
        border: 1px solid {t.BORDER};
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
        color: {t.MUTED};
        font-size: 12px;
        font-weight: 700;
    }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QTimeEdit,
    QTextEdit, QPlainTextEdit, QListView, QListWidget {{
        background: {t.SURFACE_ALT};
        border: 1px solid {t.BORDER};
        border-radius: 7px;
        padding: 5px 9px;
        selection-background-color: {t.ACCENT};
        selection-color: #ffffff;
    }}
    QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover,
    QDateTimeEdit:hover, QTimeEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
        border-color: {t.BORDER_STRONG};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QDateTimeEdit:focus, QTimeEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QListView:focus, QListWidget:focus {{
        border: 1px solid {t.ACCENT};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled,
    QDoubleSpinBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
        color: {t.MUTED};
        background: {t.SURFACE};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox QAbstractItemView {{
        background: {t.SURFACE_ALT};
        border: 1px solid {t.BORDER_STRONG};
        border-radius: 8px;
        padding: 4px;
        selection-background-color: {t.ACCENT};
        outline: none;
    }}

    QPushButton {{
        background: {t.ACCENT};
        color: #ffffff;
        border: 1px solid transparent;
        border-radius: 7px;
        padding: 7px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {t.ACCENT_HOVER}; }}
    QPushButton:pressed {{ background: {t.ACCENT_PRESSED}; }}
    QPushButton:disabled {{ background: {t.SURFACE_ALT}; color: {t.MUTED}; border-color: {t.BORDER}; }}
    QPushButton:checked {{ background: {t.ACCENT_HOVER}; }}
    QPushButton[variant="ghost"] {{
        background: transparent;
        color: {t.TEXT};
        border: 1px solid {t.BORDER};
    }}
    QPushButton[variant="ghost"]:hover {{ background: {t.SURFACE_HOVER}; border-color: {t.BORDER_STRONG}; }}
    QPushButton[variant="ghost"]:pressed {{ background: {t.SURFACE}; }}
    QPushButton[variant="ghost"]:checked {{ background: {t.ACCENT}; border-color: {t.ACCENT}; color: #ffffff; }}
    QPushButton[variant="danger"] {{
        background: transparent;
        color: {t.DANGER};
        border: 1px solid {t.DANGER};
    }}
    QPushButton[variant="danger"]:hover {{ background: {t.DANGER}; color: #ffffff; }}

    QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px;
    }}
    QToolButton:hover {{ background: {t.SURFACE_HOVER}; }}

    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QCheckBox:disabled, QRadioButton:disabled {{ color: {t.MUTED}; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 17px;
        height: 17px;
        border: 1px solid {t.BORDER_STRONG};
        border-radius: 4px;
        background: {t.SURFACE_ALT};
    }}
    QRadioButton::indicator {{ border-radius: 9px; }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {t.ACCENT}; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {t.ACCENT};
        border-color: {t.ACCENT};
    }}
    QCheckBox::indicator:checked {{ image: none; }}

    QTabWidget::pane {{
        background: {t.SURFACE};
        border: 1px solid {t.BORDER};
        border-radius: 10px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {t.MUTED};
        padding: 9px 16px;
        margin-right: 4px;
        border: 1px solid transparent;
        border-top-left-radius: 9px;
        border-top-right-radius: 9px;
        font-weight: 600;
    }}
    QTabBar::tab:hover {{ background: {t.SURFACE_HOVER}; color: {t.TEXT}; }}
    QTabBar::tab:selected {{
        background: {t.SURFACE};
        color: {t.TEXT};
        border-color: {t.BORDER};
        border-bottom-color: {t.SURFACE};
    }}

    QListWidget {{ background: {t.SURFACE_ALT}; border: 1px solid {t.BORDER}; border-radius: 8px; padding: 4px; }}
    QListWidget::item {{ border-radius: 6px; padding: 2px; }}
    QListWidget::item:hover {{ background: {t.SURFACE_HOVER}; }}
    QListWidget::item:selected {{ background: {t.ACCENT}; color: #ffffff; }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {t.BORDER_STRONG}; border-radius: 5px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: {t.MUTED}; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle:horizontal {{ background: {t.BORDER_STRONG}; border-radius: 5px; min-width: 28px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QProgressBar {{
        background: {t.SURFACE_ALT};
        border: 1px solid {t.BORDER};
        border-radius: 7px;
        height: 14px;
        text-align: center;
        color: {t.TEXT};
    }}
    QProgressBar::chunk {{ background: {t.ACCENT}; border-radius: 6px; }}

    QSplitter::handle {{ background: transparent; }}
    QSplitter::handle:hover {{ background: {t.BORDER}; }}

    QMenu {{
        background: {t.SURFACE_ALT};
        border: 1px solid {t.BORDER_STRONG};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t.ACCENT}; color: #ffffff; }}
    QMenu::separator {{ height: 1px; background: {t.BORDER}; margin: 5px 8px; }}

    QToolTip {{
        background: {t.SURFACE_ALT};
        color: {t.TEXT};
        border: 1px solid {t.BORDER_STRONG};
        border-radius: 6px;
        padding: 5px 8px;
    }}

    QMessageBox {{ background: {t.BG}; }}
    QMessageBox QLabel {{ color: {t.TEXT}; }}
    QStatusBar {{ background: {t.SURFACE}; color: {t.MUTED}; }}

    QLabel#sectionTitle {{ font-size: 19px; font-weight: 700; }}
    QLabel#muted {{ color: {t.MUTED}; }}
    QLabel#statusOn {{ color: {t.SUCCESS}; font-size: 16px; font-weight: 600; }}
    QLabel#statusOff {{ color: {t.DANGER}; font-size: 16px; font-weight: 600; }}
    QFrame#panelBlock {{
        background: {t.SURFACE};
        border: 1px solid {t.BORDER};
        border-radius: 12px;
        padding: 8px;
    }}"""


def build_palette(t: Tokens) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(t.BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(t.TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(t.SURFACE_ALT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t.SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(t.TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(t.SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.SURFACE_ALT))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t.TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(t.MUTED))
    palette.setColor(QPalette.ColorRole.Link, QColor(t.ACCENT))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.MUTED))
    return palette


def dark_palette() -> QPalette:
    """Backwards-compatible dark palette."""
    return build_palette(DARK)


def apply_theme(target: QApplication | QWidget | None = None, mode: str | None = None) -> None:
    """Apply palette + style sheet to the application (or a single widget).

    ``mode`` is ``system``, ``dark`` or ``light``; omitted it keeps the current
    selection. Applying to the application also styles dialogs that are not
    children of the main window.
    """
    if mode is not None:
        set_mode(mode)
    tokens_now = tokens()
    style = build_style_sheet(tokens_now)
    palette = build_palette(tokens_now)
    app = target if isinstance(target, QApplication) else QApplication.instance()
    if app is not None:
        app.setPalette(palette)
        app.setStyleSheet(style)
        return
    if isinstance(target, QWidget):
        target.setPalette(palette)
        target.setStyleSheet(style)
