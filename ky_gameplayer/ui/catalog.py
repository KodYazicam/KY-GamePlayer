"""Catalog download/update workflow for the Games tab.

Everything here is user-initiated: the window only downloads when the update
button is clicked, and nothing is written until the preview is confirmed.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from ..catalog_sync import (
    CatalogDiff,
    CatalogError,
    backup_path,
    bundled_catalog_path,
    catalog_timestamp,
    diff_catalogs,
    download_catalog,
    restore_backup,
    safe_minimum,
    sync,
    validate_games,
)
from ..detect import ProcessIndex
from ..games import GameCatalog
from ..i18n import t as i18n


class CatalogMixin:
    def _update_catalog(self) -> None:
        if self._catalog_busy:
            return
        self._set_catalog_busy(True, "catalog_downloading")
        self.tasks.submit(
            lambda: download_catalog(timeout=60),
            on_done=self._on_catalog_downloaded,
            on_error=self._on_catalog_error,
            name="catalog-download",
        )

    def _on_catalog_downloaded(self, rows: list[dict]) -> None:
        try:
            minimum = safe_minimum(len(self.catalog.games))
            validate_games(rows, minimum=minimum)
        except CatalogError as exc:
            self._on_catalog_error(exc)
            return

        old = [game.raw for game in self.catalog.games]
        diff = diff_catalogs(old, rows)
        answer = QMessageBox.question(
            self,
            i18n("catalog_confirm_title"),
            self._catalog_diff_message(diff),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            self._set_catalog_busy(False, "catalog_cancelled")
            return

        previous = len(self.catalog.games)
        target = self._catalog_user_path

        def install() -> tuple[int, GameCatalog]:
            written, _ = sync(
                target,
                rows,
                minimum=minimum,
                previous_count=previous,
                fallback=bundled_catalog_path(),
            )
            return written, GameCatalog.load(target)

        self._set_catalog_busy(True, "catalog_installing")
        self.tasks.submit(
            install,
            on_done=self._on_catalog_installed,
            on_error=self._on_catalog_error,
            name="catalog-install",
        )

    def _on_catalog_installed(self, result: tuple[int, GameCatalog]) -> None:
        written, catalog = result
        self._apply_catalog(catalog, self._catalog_user_path)
        self._set_catalog_busy(False)
        self._log(key="log_catalog_updated", n=written)
        self._set_status(i18n("catalog_updated", n=written))

    def _restore_catalog(self) -> None:
        if self._catalog_busy:
            return
        backup = backup_path(self._catalog_user_path)
        if not backup.exists():
            QMessageBox.information(self, i18n("catalog_confirm_title"), i18n("catalog_none"))
            return
        answer = QMessageBox.question(
            self,
            i18n("catalog_restore_title"),
            i18n("catalog_restore_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        target = self._catalog_user_path

        def restore() -> tuple[int, GameCatalog]:
            written, _ = restore_backup(target)
            return written, GameCatalog.load(target)

        self._set_catalog_busy(True, "catalog_installing")
        self.tasks.submit(
            restore,
            on_done=self._on_catalog_restored,
            on_error=self._on_catalog_error,
            name="catalog-restore",
        )

    def _on_catalog_restored(self, result: tuple[int, GameCatalog]) -> None:
        written, catalog = result
        self._apply_catalog(catalog, self._catalog_user_path)
        self._set_catalog_busy(False)
        self._log(key="log_catalog_restored", n=written)
        self._set_status(i18n("catalog_restored", n=written))

    def _on_catalog_error(self, exc: BaseException) -> None:
        self._set_catalog_busy(False)
        self._log(f"CATALOG {exc}")
        QMessageBox.warning(self, i18n("catalog_confirm_title"), i18n("catalog_failed", error=exc))

    def _apply_catalog(self, catalog: GameCatalog, path: Path) -> None:
        """Swap the in-memory catalog and refresh everything that depends on it."""
        current_id = self._game.id if self._game else self.app_id.text().strip()
        self.catalog = catalog
        self._catalog_path = path
        self._catalog_source = "user" if path == self._catalog_user_path else "bundled"
        self._detector = ProcessIndex(catalog)
        self._icon_queue.clear()
        self._icon_requested.clear()
        self._rebuild_catalog_filters()
        self._game = None
        self._reload_list()
        if current_id and catalog.get(current_id) is not None:
            self._select_game_id(current_id)
        elif self.app_id.text().strip():
            self._on_app_id_entered()
        else:
            self.game_meta.clear()
        self._refresh_catalog_actions()
        self._update_catalog_status()

    def _rebuild_catalog_filters(self) -> None:
        for combo, values in (
            (self.theme_filter, self.catalog.themes),
            (self.dist_filter, self.catalog.distributors),
        ):
            current = combo.currentData()
            combo.blockSignals(True)
            while combo.count() > 1:
                combo.removeItem(1)
            for value in values:
                combo.addItem(value, value)
            index = combo.findData(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _catalog_diff_message(self, diff: CatalogDiff) -> str:
        lines = [
            i18n("catalog_diff_counts", current=diff.current, new=diff.new),
            i18n(
                "catalog_diff_changes",
                added=diff.added_count,
                removed=diff.removed_count,
                changed=diff.changed_count,
            ),
        ]
        if diff.added_examples:
            lines.append(i18n("catalog_diff_added", names=", ".join(diff.added_examples)))
        if diff.removed_examples:
            lines.append(i18n("catalog_diff_removed", names=", ".join(diff.removed_examples)))
        lines.extend(("", i18n("catalog_diff_warning")))
        return "\n".join(lines)

    def _set_catalog_busy(self, busy: bool, text_key: str = "") -> None:
        self._catalog_busy = busy
        if hasattr(self, "catalog_status"):
            if text_key:
                self.catalog_status.setText(i18n(text_key))
            elif not busy:
                self._update_catalog_status()
        self._refresh_catalog_actions()

    def _refresh_catalog_actions(self) -> None:
        if not hasattr(self, "btn_catalog_update"):
            return
        backup_ready = backup_path(self._catalog_user_path).exists()
        self.btn_catalog_update.setEnabled(not self._catalog_busy)
        self.btn_catalog_restore.setVisible(backup_ready)
        self.btn_catalog_restore.setEnabled(not self._catalog_busy and backup_ready)
        if not backup_ready:
            self.btn_catalog_restore.setToolTip(i18n("catalog_none"))
        else:
            self.btn_catalog_restore.setToolTip("")

    def _update_catalog_status(self) -> None:
        if not hasattr(self, "catalog_status") or getattr(self, "_catalog_busy", False):
            return
        stamp = catalog_timestamp(self._catalog_path) or "—"
        key = "catalog_status_user" if getattr(self, "_catalog_source", "bundled") == "user" else "catalog_status_bundled"
        self.catalog_status.setText(i18n(key, date=stamp))
        self.catalog_status.setToolTip(str(self._catalog_path))
