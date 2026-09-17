from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


class ImageCache(QObject):
    loaded = Signal(str, QPixmap)

    def __init__(self, cache_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._nam = QNetworkAccessManager(self)
        self._pending: dict[str, list] = {}
        self._memory: dict[str, QPixmap] = {}
        self._replies: dict[QNetworkReply, str] = {}
        self._nam.finished.connect(self._on_finished)

    def get(self, url: str, callback) -> QPixmap | None:
        if not url:
            return None
        pixmap = self._memory.get(url)
        if pixmap is not None and not pixmap.isNull():
            callback(pixmap)
            return pixmap
        disk = self._disk_path(url)
        waiters = self._pending.setdefault(url, [])
        waiters.append(callback)
        if len(waiters) == 1:
            if disk.exists():
                pixmap = QPixmap()
                if pixmap.load(str(disk)):
                    self._memory[url] = pixmap
                    self._pending.pop(url, None)
                    callback(pixmap)
                    return pixmap
            request = QNetworkRequest(QUrl(url))
            request.setAttribute(
                QNetworkRequest.Attribute.CacheLoadControlAttribute,
                QNetworkRequest.CacheLoadControl.PreferCache,
            )
            reply = self._nam.get(request)
            self._replies[reply] = url
        return None

    def _disk_path(self, url: str) -> Path:
        name = url.split("?")[0].rstrip("/").replace("https://", "").replace("/", "_")
        if not name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            name += ".png"
        return self.cache_dir / name[-180:]

    def _on_finished(self, reply: QNetworkReply) -> None:
        url = self._replies.pop(reply, reply.url().toString())
        waiters = self._pending.pop(url, [])
        pixmap = QPixmap()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll().data()
            if pixmap.loadFromData(data):
                self._memory[url] = pixmap
                disk = self._disk_path(url)
                try:
                    disk.write_bytes(bytes(data))
                except OSError:
                    pass
                self.loaded.emit(url, pixmap)
        reply.deleteLater()
        for callback in waiters:
            callback(pixmap)
