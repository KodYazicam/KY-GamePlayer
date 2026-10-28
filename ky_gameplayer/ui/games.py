from __future__ import annotations

import random
from collections import deque


from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QMessageBox,
)

from ..games import Game
from ..i18n import t as i18n
from ..store import game_store_links


class GamesMixin:
    def _schedule_filter(self) -> None:
        self._update_filter_badge()
        self._filter_timer.start()

    def _filter_bool(self, combo: QComboBox) -> bool | None:
        value = combo.currentData()
        if value == "yes":
            return True
        if value == "no":
            return False
        return None

    def _set_scope(self, value: str) -> None:
        self._scope = value
        button = self.scope_buttons.get(value)
        if button is not None and not button.isChecked():
            button.setChecked(True)
        self._schedule_filter()

    def _toggle_filters(self, checked: bool) -> None:
        self.filter_drawer.setVisible(bool(checked))
        self._update_filter_badge()

    def _filter_combos(self) -> tuple[QComboBox, ...]:
        return (
            self.theme_filter,
            self.dist_filter,
            self.os_filter,
            self.icon_filter,
            self.cover_filter,
            self.overlay_filter,
        )

    def _active_filter_count(self) -> int:
        return sum(1 for combo in self._filter_combos() if combo.currentData() not in (None, "", "all"))

    def _active_filter_summary(self) -> str:
        return " · ".join(
            combo.currentText()
            for combo in self._filter_combos()
            if combo.currentData() not in (None, "", "all")
        )

    def _update_filter_badge(self) -> None:
        if not hasattr(self, "btn_filters"):
            return
        count = self._active_filter_count()
        text = i18n("filters")
        if count:
            text = f"{text} · {count}"
        self.btn_filters.setText(text)
        summary = self._active_filter_summary()
        if hasattr(self, "filter_summary"):
            self.filter_summary.setText(summary or i18n("filters_none"))
        self.btn_filters.setToolTip(summary or i18n("filters_tip"))
        self.btn_filters.setProperty("active", bool(count))
        style = self.btn_filters.style()
        style.unpolish(self.btn_filters)
        style.polish(self.btn_filters)

    def _clear_filters(self) -> None:
        for combo in self._filter_combos():
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._update_filter_badge()
        self._schedule_filter()

    def _sync_markers(self) -> None:
        if not hasattr(self, "model"):
            return
        self.model.set_markers(
            set(self.store.favorites()),
            set(self.store.playlist()),
            set(self.store.excluded()),
        )

    def _set_selection_controls(self, enabled: bool) -> None:
        if not hasattr(self, "btn_fav"):
            return
        for button in (self.btn_fav, self.btn_playlist, self.btn_exclude):
            button.setEnabled(enabled)
        self.weight_box.setEnabled(enabled)
        if not enabled:
            self.selection_name.setText(i18n("select_game"))
            self.selection_meta.setText(i18n("select_game_hint"))

    def _toggle_details(self, checked: bool) -> None:
        self.details_panel.setVisible(bool(checked))
        self.btn_details.setText(i18n("details_hide" if checked else "details_show"))

    def _reload_list(self) -> None:
        current_id = self._game.id if self._game else None
        games = self.catalog.filter(
            query=self.search.text(),
            theme=self.theme_filter.currentData() or None,
            distributor=self.dist_filter.currentData() or None,
            os_name=self.os_filter.currentData() or None,
            has_icon=self._filter_bool(self.icon_filter),
            has_cover=self._filter_bool(self.cover_filter),
            overlay=self._filter_bool(self.overlay_filter),
        )
        scope = getattr(self, "_scope", "all")
        if scope == "favorites":
            allow = set(self.store.favorites())
            games = [game for game in games if game.id in allow]
        elif scope == "recents":
            order = {game_id: i for i, game_id in enumerate(self.store.recents())}
            games = [game for game in games if game.id in order]
            games.sort(key=lambda game: order.get(game.id, 999))
        elif scope == "playlist":
            allow = set(self.store.playlist())
            games = [game for game in games if game.id in allow]
        elif scope == "excluded":
            allow = set(self.store.excluded())
            games = [game for game in games if game.id in allow]
        self.model.reset_games(games)
        self._sync_markers()
        self.count_label.setText(i18n("games_count_filter", shown=len(games), n=len(self.catalog.games)))
        if hasattr(self, "empty_label"):
            self.empty_label.setVisible(not games)
            self.list_view.setVisible(bool(games))
        self._update_filter_badge()
        if current_id:
            row = self.model.index_for_id(current_id)
            if row >= 0:
                self.list_view.setCurrentIndex(self.model.index(row))

    def _select_game_id(self, game_id: str) -> None:
        row = self.model.index_for_id(game_id)
        if row >= 0:
            self.list_view.setCurrentIndex(self.model.index(row))
            self.list_view.scrollTo(self.model.index(row))
            return
        game = self.catalog.get(game_id)
        if game is not None:
            self._apply_game(game)

    def _on_app_id_entered(self) -> None:
        game_id = self.app_id.text().strip()
        if not game_id:
            return
        game = self.catalog.get(game_id)
        if game is None:
            self._game = None
            self._set_selection_controls(False)
            self.selection_name.setText(i18n("custom_app", id=game_id))
            self.selection_meta.setText(i18n("custom_app_hint"))
            self.game_meta.setPlainText(i18n("custom_app", id=game_id))
            self._update_preview()
            return
        if self._game and self._game.id == game_id:
            return
        self._select_game_id(game_id)

    def _on_game_changed(self, current, _previous) -> None:
        game = self.model.game_at(current.row())
        if game is not None:
            self._apply_game(game)

    def _apply_game(self, game: Game) -> None:
        same = self._game is not None and self._game.id == game.id
        self._game = game
        self._set_selection_controls(True)
        if same:
            self._update_preview()
            return
        self.app_id.setText(game.id)
        self.activity_name.setText(game.name)
        if self.auto_assets.isChecked():
            image = game.cover_image_hash or game.icon_hash or ""
            small = ""
            if game.cover_image_hash and game.icon_hash and game.icon_hash != game.cover_image_hash:
                small = game.icon_hash
            self.large_image.setText(image)
            self.large_text.setText(game.name)
            self.small_image.setText(small)
        self.store.last_game_id = game.id
        self.store.add_recent(game.id)
        if self.template_box is not None and self.template_box.isChecked():
            template = self.store.game_template(game.id)
            if template is not None:
                self.apply_config(game.id, template)
                self._log(key="log_template_applied", name=game.name)
        self._fill_game_meta(game)
        self._fill_assets(game)
        self._refresh_fav_buttons()
        self._update_preview()
        self._queue_icon(game)

    def _fill_game_meta(self, game: Game) -> None:
        theme = f" · {game.themes[0]}" if game.themes else ""
        self.selection_name.setText(game.name)
        self.selection_meta.setText(f"{game.id}{theme}")
        lines = [
            f"{game.name}",
            f"ID: {game.id}",
        ]
        if game.aliases:
            lines.append("Alias: " + ", ".join(game.aliases[:12]))
        if game.themes:
            lines.append(i18n("theme") + ": " + ", ".join(game.themes))
        lines.append(
            f"hook={game.hook} overlay={game.overlay} "
            f"compat_hook={game.overlay_compatibility_hook} "
            f"methods={game.overlay_methods} warn={game.overlay_warn}"
        )
        if game.executables:
            exe = ", ".join(
                f"{e.get('name')} ({e.get('os')}"
                + (" launcher" if e.get("is_launcher") else "")
                + ")"
                for e in game.executables[:12]
            )
            lines.append("Exe: " + exe)
        if game.third_party_skus:
            skus = ", ".join(
                f"{s.get('distributor')}:{s.get('id')}"
                for s in game.third_party_skus[:16]
                if s.get("distributor")
            )
            lines.append("SKU: " + skus)
        cc = game.content_classification or {}
        ratings = (cc.get("agency_ratings") or {}) if isinstance(cc, dict) else {}
        if ratings:
            bits = []
            for agency, payload in ratings.items():
                if isinstance(payload, dict):
                    bits.append(f"{agency}={payload.get('rating')}")
            if bits:
                lines.append("Rating: " + ", ".join(bits))
        classes = cc.get("discord_classifications") if isinstance(cc, dict) else None
        if classes:
            lines.append("Discord class: " + ", ".join(str(x) for x in classes))
        links = game_store_links(game)
        if links:
            lines.append(i18n("store") + ": " + ", ".join(f"{dist}:{url}" for dist, _sku, url in links[:6]))
        flags = []
        if self.store.is_favorite(game.id):
            flags.append(i18n("tag_fav"))
        if game.id in self.store.playlist():
            flags.append(i18n("tag_pl"))
        if game.id in self.store.excluded():
            flags.append(i18n("tag_ex"))
        if flags:
            lines.append(i18n("tag_line") + ": " + ", ".join(flags))
        self.game_meta.setPlainText("\n".join(lines))

    def _queue_icon(self, game: Game) -> None:
        if game is None or not game.icon_hash:
            return
        if game.id in self._icon_requested:
            return
        self._icon_requested.add(game.id)
        self._icon_queue.append(game)
        if not self._icon_timer.isActive():
            self._icon_timer.start()

    def _pump_icons(self) -> None:
        started = 0
        while self._icon_queue and started < 2:
            game = self._icon_queue.pop(0)
            url = game.icon_url(64)
            if not url:
                continue
            started += 1

            def done(pixmap: QPixmap, game_id: str = game.id) -> None:
                if not pixmap.isNull():
                    self.model.set_icon(game_id, pixmap)

            self.images.get(url, done)
        if not self._icon_queue:
            self._icon_timer.stop()

    def _games_by_ids(self, ids: list[str]) -> list[Game]:
        games: list[Game] = []
        for game_id in ids:
            game = self.catalog.get(game_id)
            if game is not None:
                games.append(game)
        return games

    def _random_pool(self) -> list[Game]:
        source = self.random_source.currentData()
        if source == "favorites":
            pool = self._games_by_ids(self.store.favorites())
        elif source == "playlist":
            pool = self._games_by_ids(self.store.playlist())
        elif source == "filter":
            pool = list(self.model.games())
        else:
            pool = list(self.catalog.games)
        excluded = set(self.store.excluded())
        pool = [game for game in pool if game.id not in excluded]
        return pool

    def _pick_weighted(self, games: list[Game]) -> Game:
        blocked = set(self._random_history)
        blocked.update(self.store.excluded())
        current = self._game.id if self._game else None
        if current:
            blocked.add(current)
        candidates = [game for game in games if game.id not in blocked] or list(games)
        weights = [self.store.weight(game.id) for game in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _random_switch(self, _checked: bool = False) -> None:
        pool = self._random_pool()
        if not pool:
            self._set_status(i18n("status_random_none"))
            return
        norepeat = int(self.random_norepeat.value())
        self._random_history = deque(self._random_history, maxlen=max(1, norepeat or 1))
        if norepeat <= 0:
            self._random_history.clear()
        game = pool[0] if len(pool) == 1 else self._pick_weighted(pool)
        if norepeat > 0:
            self._random_history.append(game.id)
        self._select_game_id(game.id)
        self._stamp_now()
        if self.random_enabled.isChecked():
            self._random_timer.start(int(self.random_interval.value()) * 1000)
        self._update_rpc(silent=True)
        self._set_status(i18n("status_random", name=game.name))
        self._refresh_random_countdown()
        if self.science_enabled.isChecked() and self.science_on_random.isChecked():
            self._run_science(reason=f"random:{game.id}", games=[game])

    def _refresh_random_countdown(self) -> None:
        if not self.random_enabled.isChecked() or not self._random_timer.isActive():
            self.random_countdown.setText("")
            return
        remaining = max(0, int(self._random_timer.remainingTime() / 1000))
        name = self._game.name if self._game else "—"
        self.random_countdown.setText(i18n("countdown", name=name, s=remaining))

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+R"), self, self._random_switch)
        QShortcut(QKeySequence("Ctrl+U"), self, lambda: self._update_rpc())
        QShortcut(QKeySequence("Ctrl+L"), self, self._clear_rpc)
        QShortcut(QKeySequence("Ctrl+P"), self, self._pin_current)
        QShortcut(QKeySequence("Ctrl+D"), self, self._scan_running)
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)
        QShortcut(QKeySequence("Escape"), self, self._clear_search)
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, self._toggle_favorite)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self._fill_store_button)
        QShortcut(QKeySequence("F1"), self, self._show_shortcuts)

    def _focus_search(self) -> None:
        self.search.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search.selectAll()

    def _clear_search(self) -> None:
        if self.search.text():
            self.search.clear()  # textChanged schedules a debounced reload
        else:
            self.search.setFocus()

    def _show_shortcuts(self) -> None:
        QMessageBox.information(self, i18n("shortcuts_title"), i18n("shortcuts_text"))

    def _refresh_fav_buttons(self) -> None:
        game = self._game
        if game is None:
            return
        self.btn_fav.setText(i18n("fav_on") if self.store.is_favorite(game.id) else i18n("fav_off"))
        self.btn_playlist.setText(
            i18n("pl_on") if game.id in self.store.playlist() else i18n("pl_off")
        )
        self.btn_exclude.setText(
            i18n("ex_on") if game.id in self.store.excluded() else i18n("ex_off")
        )
        self.weight_box.blockSignals(True)
        self.weight_box.setValue(self.store.weight(game.id))
        self.weight_box.blockSignals(False)

    def _toggle_favorite(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_favorite(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._schedule_filter()
        self._set_status(i18n("status_fav_on" if on else "status_fav_off", name=self._game.name))

    def _toggle_playlist(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_playlist(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._schedule_filter()
        self._set_status(i18n("status_pl_on" if on else "status_pl_off", name=self._game.name))

    def _toggle_excluded(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_excluded(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._schedule_filter()
        self._set_status(i18n("status_ex_on" if on else "status_ex_off", name=self._game.name))

    def _on_weight_changed(self, value: int) -> None:
        if self._game is None:
            return
        self.store.set_weight(self._game.id, int(value))
