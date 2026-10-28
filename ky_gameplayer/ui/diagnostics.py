"""Help-tab diagnostics: copy a redacted report to the clipboard."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..diagnostics import build_report
from ..i18n import t
from ..ipc import discord_ipc_available
from ..logging_setup import current_log_path


class DiagnosticsMixin:
    def _copy_diagnostics(self) -> None:
        recent: list[str] = []
        for stamp, key, kwargs in self._log_records[-40:]:
            text = self._format_log(key, kwargs) if key else str(kwargs.get("text") or "")
            recent.append(f"[{stamp}] {text}")
        try:
            available: bool | None = discord_ipc_available()
        except Exception:
            available = None
        report = build_report(
            log_path=current_log_path(),
            catalog_size=len(self.catalog.games),
            settings=self.store.settings(),
            recent=recent,
            ipc_available=available,
        )
        QApplication.clipboard().setText(report)
        self._set_status(t("diag_copied"))
        self._log(key="log_diag_copied")
