from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QPainterPath
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from .games import Game


class GameListModel(QAbstractListModel):
    GameRole = Qt.ItemDataRole.UserRole
    IdRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self) -> None:
        super().__init__()
        self._games: list[Game] = []
        self._icons: dict[str, QPixmap] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._games)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._games)):
            return None
        game = self._games[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return game.name
        if role == Qt.ItemDataRole.ToolTipRole:
            aliases = ", ".join(game.aliases[:4])
            extra = f"\n{aliases}" if aliases else ""
            return f"{game.name}\n{game.id}{extra}"
        if role == self.GameRole:
            return game
        if role == self.IdRole:
            return game.id
        if role == Qt.ItemDataRole.DecorationRole:
            return self._icons.get(game.id)
        return None

    def games(self) -> list[Game]:
        return self._games

    def game_at(self, row: int) -> Game | None:
        if 0 <= row < len(self._games):
            return self._games[row]
        return None

    def reset_games(self, games: list[Game]) -> None:
        self.beginResetModel()
        self._games = games
        self.endResetModel()

    def set_icon(self, game_id: str, pixmap: QPixmap) -> None:
        self._icons[game_id] = pixmap
        for row, game in enumerate(self._games):
            if game.id == game_id:
                idx = self.index(row)
                self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.DecorationRole])
                break

    def index_for_id(self, game_id: str) -> int:
        for row, game in enumerate(self._games):
            if game.id == game_id:
                return row
        return -1


class GameDelegate(QStyledItemDelegate):
    icon_needed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._placeholder = QPixmap(32, 32)
        self._placeholder.fill(QColor("#1e1f22"))
        self._asked: set[str] = set()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(option.rect.width(), 52)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(6, 4, -6, -4)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        if selected:
            painter.setBrush(QColor("#404249"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 8, 8)
        elif hover:
            painter.setBrush(QColor("#35373c"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 8, 8)

        game: Game = index.data(GameListModel.GameRole)
        if game is None:
            painter.restore()
            return
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        if not isinstance(icon, QPixmap) or icon.isNull():
            icon = self._placeholder
            if game.id not in self._asked:
                self._asked.add(game.id)
                self.icon_needed.emit(game)
        else:
            icon = icon.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        icon_rect = rect.adjusted(8, 6, 0, -6)
        icon_rect.setWidth(32)
        icon_rect.setHeight(32)
        path = QPainterPath()
        path.addRoundedRect(icon_rect, 6, 6)
        painter.setClipPath(path)
        painter.drawPixmap(icon_rect, icon)
        painter.setClipping(False)

        name_font = QFont(option.font)
        name_font.setPointSize(10)
        name_font.setWeight(QFont.Weight.DemiBold)
        meta_font = QFont(option.font)
        meta_font.setPointSize(8)

        painter.setPen(QColor("#f2f3f5") if selected else QColor("#dbdee1"))
        painter.setFont(name_font)
        text_x = icon_rect.right() + 10
        painter.drawText(text_x, rect.top() + 18, game.name)

        painter.setPen(QColor("#949ba4"))
        painter.setFont(meta_font)
        meta = game.id
        if game.themes:
            meta = f"{game.id}  ·  {game.themes[0]}"
        painter.drawText(text_x, rect.top() + 36, meta)
        painter.restore()
