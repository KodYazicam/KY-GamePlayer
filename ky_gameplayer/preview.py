from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget

from .activity import ActivityConfig
from .games import Game
from .i18n import t


def _type_prefix(activity_type: int, name: str) -> str:
    mapping = {
        0: f"Playing {name}",
        1: f"Streaming {name}",
        2: f"Listening to {name}",
        3: f"Watching {name}",
        4: name or "Custom Status",
        5: f"Competing in {name}",
    }
    return mapping.get(activity_type, f"Playing {name}")


def _elapsed_text(config: ActivityConfig) -> str | None:
    import time

    if config.start and config.end:
        remaining = max(0, int(config.end - time.time()))
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d} {t('preview_left')}"
        return f"{mins}:{secs:02d} {t('preview_left')}"
    if config.start:
        elapsed = max(0, int(time.time() - config.start))
        mins, secs = divmod(elapsed, 60)
        hours, mins = divmod(mins, 60)
        if hours:
            return f"{hours}:{mins:02d}:{secs:02d} {t('preview_elapsed')}"
        return f"{mins}:{secs:02d} {t('preview_elapsed')}"
    return None


class PresencePreview(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._config = ActivityConfig()
        self._game: Game | None = None
        self._large = QPixmap()
        self._small = QPixmap()
        self.setMinimumHeight(210)
        self.setMaximumHeight(260)

    def set_game(self, game: Game | None) -> None:
        self._game = game
        self.update()

    def set_config(self, config: ActivityConfig) -> None:
        self._config = config
        self.update()

    def set_large(self, pixmap: QPixmap) -> None:
        self._large = pixmap
        self.update()

    def set_small(self, pixmap: QPixmap) -> None:
        self._small = pixmap
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111214"))
        card = self.rect().adjusted(8, 8, -8, -8)
        path = QPainterPath()
        path.addRoundedRect(card, 12, 12)
        painter.fillPath(path, QColor("#1e1f22"))

        game_name = (self._game.name if self._game else None) or self._config.name or t("preview_game")
        status_line = _type_prefix(self._config.type, game_name)
        if self._config.status_display_type == 1 and self._config.state:
            status_line = _type_prefix(self._config.type, self._config.state)
        elif self._config.status_display_type == 2 and self._config.details:
            status_line = _type_prefix(self._config.type, self._config.details)

        painter.setPen(QColor("#b5bac1"))
        font = QFont(self.font())
        font.setPointSize(8)
        font.setBold(True)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        painter.setFont(font)
        painter.drawText(card.adjusted(16, 12, -16, 0), Qt.AlignmentFlag.AlignLeft, status_line.upper())

        icon_box = card.adjusted(16, 40, 0, 0)
        icon_box.setWidth(72)
        icon_box.setHeight(72)
        icon_path = QPainterPath()
        icon_path.addRoundedRect(icon_box, 10, 10)
        painter.fillPath(icon_path, QColor("#2b2d31"))
        if not self._large.isNull():
            scaled = self._large.scaled(
                icon_box.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.setClipPath(icon_path)
            painter.drawPixmap(icon_box, scaled)
            painter.setClipping(False)

        if not self._small.isNull():
            badge = icon_box.adjusted(48, 48, 8, 8)
            badge.setWidth(28)
            badge.setHeight(28)
            painter.setBrush(QColor("#1e1f22"))
            painter.setPen(QColor("#1e1f22"))
            painter.drawEllipse(badge.adjusted(-3, -3, 3, 3))
            small = self._small.scaled(
                badge.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            clip = QPainterPath()
            clip.addEllipse(badge)
            painter.setClipPath(clip)
            painter.drawPixmap(badge, small)
            painter.setClipping(False)

        text_left = icon_box.right() + 14
        y = icon_box.top() + 4
        painter.setPen(QColor("#f2f3f5"))
        title = QFont(self.font())
        title.setPointSize(12)
        title.setBold(True)
        painter.setFont(title)
        painter.drawText(text_left, y + 16, game_name)
        y += 22

        body = QFont(self.font())
        body.setPointSize(10)
        painter.setFont(body)
        painter.setPen(QColor("#dbdee1"))
        if self._config.details:
            painter.drawText(text_left, y + 16, self._config.details[:64])
            y += 18
        if self._config.state:
            party = ""
            if self._config.party_size and self._config.party_max:
                party = f" ({self._config.party_size} of {self._config.party_max})"
            painter.drawText(text_left, y + 16, f"{self._config.state[:48]}{party}")
            y += 18
        elapsed = _elapsed_text(self._config)
        if elapsed:
            painter.setPen(QColor("#b5bac1"))
            painter.drawText(text_left, y + 16, elapsed)
            y += 18

        buttons = self._config.buttons()
        bx = text_left
        by = max(y + 10, icon_box.bottom() - 8)
        for button in buttons[:2]:
            bw, bh = 118, 28
            r = icon_box.adjusted(0, 0, 0, 0)
            r.setLeft(bx)
            r.setTop(by)
            r.setWidth(bw)
            r.setHeight(bh)
            bpath = QPainterPath()
            bpath.addRoundedRect(r, 6, 6)
            painter.fillPath(bpath, QColor("#4e5058"))
            painter.setPen(QColor("#f2f3f5"))
            smallf = QFont(self.font())
            smallf.setPointSize(8)
            smallf.setBold(True)
            painter.setFont(smallf)
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, button["label"][:16])
            bx += bw + 8
