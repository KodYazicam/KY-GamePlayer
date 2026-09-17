from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .badges import CATALOG_BADGES, GIFT_BADGES, NITRO_MONTHS, badge_icon_url, decode_flags
from .brand import APP_TITLE, GUILD_NAME, INVITE_URL, REQUIRED_GUILD_ID
from .discord_rest import HOUSES, QuestTask, house_from_flags
from .i18n import t
from .images import ImageCache


def _scroll(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(inner)
    return area


class ImageCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("imageCard")
        self._selected = False
        self.setMinimumSize(132, 168)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setMinimumHeight(72)
        self.image.setStyleSheet("background:#111214; border-radius:10px;")
        self.title = QLabel("")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("muted")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.image, 1)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        self._apply()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected: bool, color: str = "#5865f2") -> None:
        self._selected = selected
        self.setProperty("accent", color if selected else "")
        self._apply()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.image.setPixmap(
            pixmap.scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def set_mark(self, text: str, color: str) -> None:
        self.image.setText(text)
        self.image.setStyleSheet(
            f"background:{color}; color:#ffffff; border-radius:10px; font-weight:700; font-size:22px;"
        )

    def _apply(self) -> None:
        accent = self.property("accent") or "#3f4147"
        border = accent if self._selected else "#3f4147"
        glow = accent if self._selected else "transparent"
        self.setStyleSheet(
            f"""
            QFrame#imageCard {{
                background: #1e1f22;
                border: 2px solid {border};
                border-radius: 12px;
            }}
            QFrame#imageCard:hover {{
                border: 2px solid {glow if self._selected else '#5865f2'};
            }}
            """
        )


class QuestCard(QFrame):
    def __init__(self, task: QuestTask, images: ImageCache, parent=None) -> None:
        super().__init__(parent)
        self.task = task
        self.setObjectName("questCard")
        self.setStyleSheet(
            "QFrame#questCard { background:#1e1f22; border:1px solid #3f4147; border-radius:12px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        self.icon = QLabel("🎯")
        self.icon.setFixedSize(52, 52)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet("background:#111214; border-radius:10px;")
        url = task.icon_url(64)
        if url:
            images.get(url, self._set_icon)
        col = QVBoxLayout()
        self.name = QLabel(task.name)
        self.name.setFont(QFont("", 10, QFont.Weight.DemiBold))
        self.meta = QLabel(f"{task.task_type}  ·  {task.progress}/{task.target}s")
        self.meta.setObjectName("muted")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(task.percent)
        self.bar.setTextVisible(True)
        self.bar.setFormat(f"%{task.percent}")
        self.bar.setMaximumHeight(14)
        col.addWidget(self.name)
        col.addWidget(self.meta)
        col.addWidget(self.bar)
        layout.addWidget(self.icon)
        layout.addLayout(col, 1)
        if task.completed:
            badge_text = t("quest_done")
        elif task.enrolled:
            badge_text = t("quest_enrolled")
        else:
            badge_text = t("quest_wait")
        self.badge = QLabel(badge_text)
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = "#23a559" if task.completed else ("#f0b232" if task.enrolled else "#949ba4")
        self.badge.setStyleSheet(f"color:{color}; font-weight:700;")
        layout.addWidget(self.badge)

    def _set_icon(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.icon.setPixmap(
            pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def update_progress(self, progress: int, target: int, completed: bool) -> None:
        self.task.progress = progress
        self.task.target = target
        self.task.completed = completed
        percent = 100 if completed or target <= 0 else min(100, int(progress * 100 / target))
        self.bar.setValue(percent)
        self.bar.setFormat(f"%{percent}")
        self.meta.setText(f"{self.task.task_type}  ·  {progress}/{target}s")
        self.badge.setText(t("quest_done") if completed else t("quest_run"))
        self.badge.setStyleSheet("color:#23a559; font-weight:700;" if completed else "color:#f0b232; font-weight:700;")


class KodYazarPages(QWidget):
    house_chosen = Signal(int)
    house_leave = Signal()
    privacy_chosen = Signal(int)
    quests_refresh = Signal()
    quests_start = Signal()
    quests_stop = Signal()
    status_apply = Signal(str)
    clan_apply = Signal(str)
    account_refresh = Signal()

    def __init__(self, images: ImageCache, parent=None) -> None:
        super().__init__(parent)
        self.images = images
        self._house = 2
        self._privacy = 3
        self._quest_cards: dict[str, QuestCard] = {}
        self._house_cards: dict[int, ImageCard] = {}
        self._privacy_cards: dict[int, ImageCard] = {}
        self.account = QLabel(t("account_waiting"))
        self.account.setObjectName("muted")
        self._me: dict | None = None
        self._account_payload: tuple | None = None
        self._last_quests: list[QuestTask] = []
        self.house_page = _scroll(self._house_block())
        self.badge_page = _scroll(self._badge_block())
        self.privacy_page = _scroll(self._privacy_block())
        self.quest_page = _scroll(self._quest_block())
        self.account_page = _scroll(self._account_block())
        self.help_page = _scroll(self._help_block())

    def _house_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.house_head = QLabel(t("house_head"))
        self.house_head.setObjectName("sectionTitle")
        self.house_sub = QLabel(t("house_sub"))
        self.house_sub.setObjectName("muted")
        self.house_sub.setWordWrap(True)
        layout.addWidget(self.house_head)
        layout.addWidget(self.account)
        layout.addWidget(self.house_sub)
        grid = QHBoxLayout()
        desc = {1: t("house_brave"), 2: t("house_brill"), 3: t("house_bal")}
        for house_id, name, color, url in HOUSES:
            card = ImageCard()
            card.title.setText(name)
            card.title.setStyleSheet(f"color:{color}; font-weight:700;")
            card.subtitle.setText(desc[house_id])
            card.clicked.connect(lambda hid=house_id: self._pick_house(hid))
            self.images.get(url, card.set_pixmap)
            self._house_cards[house_id] = card
            grid.addWidget(card)
        layout.addLayout(grid)
        row = QHBoxLayout()
        self.house_apply = QPushButton(t("house_apply"))
        self.house_leave_btn = QPushButton(t("house_leave"))
        self.house_apply.clicked.connect(lambda: self.house_chosen.emit(self._house))
        self.house_leave_btn.clicked.connect(self.house_leave.emit)
        row.addWidget(self.house_apply)
        row.addWidget(self.house_leave_btn)
        layout.addLayout(row)
        self.house_hint = QLabel(t("house_hint"))
        self.house_hint.setObjectName("muted")
        self.house_hint.setWordWrap(True)
        layout.addWidget(self.house_hint)
        layout.addStretch(1)
        self._pick_house(2)
        return box

    def _privacy_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.privacy_head = QLabel(t("privacy_head"))
        self.privacy_head.setObjectName("sectionTitle")
        self.privacy_sub = QLabel(t("privacy_sub"))
        self.privacy_sub.setObjectName("muted")
        layout.addWidget(self.privacy_head)
        layout.addWidget(self.privacy_sub)
        grid = QHBoxLayout()
        items = (
            (1, t("privacy_private"), t("privacy_private_sub"), "1", "#f472b6"),
            (2, t("privacy_limited"), t("privacy_limited_sub"), "2", "#fbbf24"),
            (3, t("privacy_public"), t("privacy_public_sub"), "3", "#34d399"),
        )
        for level, title, caption, mark, color in items:
            card = ImageCard()
            card.title.setText(title)
            card.title.setStyleSheet(f"color:{color}; font-weight:700;")
            card.subtitle.setText(caption)
            card.set_mark(mark, color)
            card.clicked.connect(lambda lv=level: self._pick_privacy(lv))
            self._privacy_cards[level] = card
            grid.addWidget(card)
        layout.addLayout(grid)
        self.privacy_apply = QPushButton(t("privacy_apply"))
        self.privacy_apply.clicked.connect(lambda: self.privacy_chosen.emit(self._privacy))
        layout.addWidget(self.privacy_apply)
        layout.addStretch(1)
        self._pick_privacy(3)
        return box

    def _quest_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.quests_head = QLabel(t("quests_head"))
        self.quests_head.setObjectName("sectionTitle")
        self.quests_sub = QLabel(t("quests_sub"))
        self.quests_sub.setObjectName("muted")
        self.quests_sub.setWordWrap(True)
        self.quest_meta = QLabel(t("quests_none_meta"))
        self.quest_meta.setObjectName("muted")
        layout.addWidget(self.quests_head)
        layout.addWidget(self.quests_sub)
        layout.addWidget(self.quest_meta)
        self.quest_host = QVBoxLayout()
        empty = QLabel(t("quests_empty"))
        empty.setObjectName("muted")
        empty.setWordWrap(True)
        self.quest_host.addWidget(empty)
        layout.addLayout(self.quest_host)
        row = QHBoxLayout()
        self.quest_enroll = QPushButton(t("quests_enroll"))
        self.quest_refresh = QPushButton(t("btn_scan"))
        self.quest_start = QPushButton(t("quests_start"))
        self.quest_stop = QPushButton(t("quests_stop"))
        self.quest_enroll.clicked.connect(self.quests_start.emit)
        self.quest_refresh.clicked.connect(self.quests_refresh.emit)
        self.quest_start.clicked.connect(self.quests_start.emit)
        self.quest_stop.clicked.connect(self.quests_stop.emit)
        row.addWidget(self.quest_refresh)
        row.addWidget(self.quest_enroll)
        row.addWidget(self.quest_start)
        row.addWidget(self.quest_stop)
        layout.addLayout(row)
        layout.addStretch(1)
        return box

    def _badge_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.badges_head = QLabel(t("badges_head"))
        self.badges_head.setObjectName("sectionTitle")
        self.badges_sub = QLabel(t("badges_sub"))
        self.badges_sub.setObjectName("muted")
        self.badges_sub.setWordWrap(True)
        layout.addWidget(self.badges_head)
        layout.addWidget(self.badges_sub)
        self.gift_head = QLabel(t("gift_head"))
        self.gift_head.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(self.gift_head)
        gifts = QGridLayout()
        self._gift_cards: list[tuple[ImageCard, str, int]] = []
        for i, (title, need, icon_hash) in enumerate(GIFT_BADGES):
            card = ImageCard()
            card.setMinimumSize(110, 140)
            card.title.setText(title)
            card.subtitle.setText(t("gift_need", n=need))
            url = badge_icon_url(icon_hash)
            if url:
                self.images.get(url, card.set_pixmap)
            else:
                card.set_mark(title[:1], "#5865f2")
            gifts.addWidget(card, i // 3, i % 3)
            self._gift_cards.append((card, title, need))
        layout.addLayout(gifts)
        self.owned_host = QVBoxLayout()
        self.owned_title = QLabel(t("owned_head"))
        self.owned_title.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(self.owned_title)
        layout.addLayout(self.owned_host)
        self.nitro_head = QLabel(t("nitro_head"))
        self.nitro_head.setFont(QFont("", 11, QFont.Weight.DemiBold))
        layout.addWidget(self.nitro_head)
        grid = QGridLayout()
        self._catalog_labels: list[tuple[QLabel, str]] = []
        catalog: list[tuple[str, str | None]] = [
            (key, None) for key, _months in NITRO_MONTHS
        ]
        catalog.extend(CATALOG_BADGES)
        nitro_lookup = {key: months for key, months in NITRO_MONTHS}
        for i, (title, icon_hash) in enumerate(catalog):
            wrap = QFrame()
            wrap.setStyleSheet("background:#111214; border-radius:8px;")
            inner = QHBoxLayout(wrap)
            inner.setContentsMargins(6, 4, 6, 4)
            pic = QLabel()
            pic.setFixedSize(36, 36)
            pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pic.setStyleSheet("background:#1e1f22; border-radius:8px; color:#f2f3f5; font-weight:700;")
            url = badge_icon_url(icon_hash)
            if url:
                self.images.get(url, lambda pix, target=pic: self._set_catalog_icon(target, pix))
            else:
                mark = t("nitro_month", n=nitro_lookup[title]) if title in nitro_lookup else title
                pic.setText(mark[:1])
            shown = t("nitro_month", n=nitro_lookup[title]) if title in nitro_lookup else title
            label = QLabel(shown)
            inner.addWidget(pic)
            inner.addWidget(label, 1)
            grid.addWidget(wrap, i // 3, i % 3)
            self._catalog_labels.append((label, title))
        layout.addLayout(grid)
        layout.addStretch(1)
        return box

    def _set_catalog_icon(self, target: QLabel, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        target.setPixmap(
            pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def _account_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.acc_head = QLabel(t("account_head"))
        self.acc_head.setObjectName("sectionTitle")
        self.acc_sub = QLabel(t("account_sub"))
        self.acc_sub.setObjectName("muted")
        self.acc_sub.setWordWrap(True)
        layout.addWidget(self.acc_head)
        layout.addWidget(self.acc_sub)
        self.account_meta = QLabel("—")
        self.account_meta.setWordWrap(True)
        layout.addWidget(self.account_meta)
        self.status_edit = QLineEdit()
        self.status_edit.setPlaceholderText(t("ph_status"))
        status_row = QHBoxLayout()
        self.status_btn = QPushButton(t("btn_status"))
        self.status_btn.clicked.connect(lambda: self.status_apply.emit(self.status_edit.text()))
        status_row.addWidget(self.status_edit, 1)
        status_row.addWidget(self.status_btn)
        layout.addLayout(status_row)
        self.clan_box = QComboBox()
        self.clan_box.setEditable(True)
        self.clan_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.clan_box.setMaxVisibleItems(18)
        completer = QCompleter(self.clan_box.model(), self.clan_box)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.clan_box.setCompleter(completer)
        self.clan_meta = QLabel(t("clan_none"))
        self.clan_meta.setObjectName("muted")
        clan_row = QHBoxLayout()
        self.clan_btn = QPushButton(t("btn_clan"))
        self.clan_btn.clicked.connect(self._emit_clan)
        clan_row.addWidget(self.clan_box, 1)
        clan_row.addWidget(self.clan_btn)
        layout.addLayout(clan_row)
        layout.addWidget(self.clan_meta)
        self.orbs_label = QLabel(t("orbs_none"))
        self.orbs_label.setObjectName("muted")
        self.orbs_label.setWordWrap(True)
        layout.addWidget(self.orbs_label)
        self.account_refresh_btn = QPushButton(t("btn_account_refresh"))
        self.account_refresh_btn.clicked.connect(self.account_refresh.emit)
        layout.addWidget(self.account_refresh_btn)
        layout.addStretch(1)
        return box

    def _help_block(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        self.help_head = QLabel(t("help_head"))
        self.help_head.setObjectName("sectionTitle")
        self.help_body = QLabel(
            t("help_body", app=APP_TITLE, guild=GUILD_NAME, invite=INVITE_URL)
        )
        self.help_body.setWordWrap(True)
        self.help_body.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.help_head)
        layout.addWidget(self.help_body)
        self.help_invite = QPushButton(t("help_join", invite=INVITE_URL))
        self.help_invite.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(INVITE_URL)))
        layout.addWidget(self.help_invite)
        self.help_meta = QLabel(t("help_id", id=REQUIRED_GUILD_ID))
        self.help_meta.setObjectName("muted")
        layout.addWidget(self.help_meta)
        layout.addStretch(1)
        return box

    def _pick_house(self, house_id: int) -> None:
        self._house = house_id
        colors = {1: "#9C84EF", 2: "#F47B67", 3: "#45DDC0"}
        for hid, card in self._house_cards.items():
            card.set_selected(hid == house_id, colors[hid])

    def _pick_privacy(self, level: int) -> None:
        self._privacy = level
        colors = {1: "#f472b6", 2: "#fbbf24", 3: "#34d399"}
        for lv, card in self._privacy_cards.items():
            card.set_selected(lv == level, colors[lv])

    def set_account(self, me: dict) -> None:
        name = me.get("global_name") or me.get("username") or "?"
        flags = int(me.get("public_flags") or me.get("flags") or 0)
        house = house_from_flags(flags)
        names = {1: "Bravery", 2: "Brilliance", 3: "Balance"}
        house_txt = names.get(house or 0, t("house_none"))
        self._me = me
        self.account.setText(f"{name}  ·  {house_txt}")
        if house:
            self._pick_house(house)
        self.set_owned_badges(me)

    def set_owned_badges(self, me: dict) -> None:
        if not hasattr(self, "owned_host"):
            return
        flags = int(me.get("public_flags") or me.get("flags") or 0)
        premium = int(me.get("premium_type") or 0)
        while self.owned_host.count():
            item = self.owned_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for badge in decode_flags(flags, premium):
            mark = t("owned_yes") if badge.owned else t("owned_no")
            color = "#23a559" if badge.owned else "#949ba4"
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 2, 0, 2)
            icon = QLabel()
            icon.setFixedSize(22, 22)
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if badge.icon_url:
                self.images.get(badge.icon_url, lambda pix, target=icon: self._set_catalog_icon(target, pix))
            text = QLabel(f"{badge.name}  ·  {mark}  ·  {badge.how}")
            text.setStyleSheet(f"color:{color};")
            line.addWidget(icon)
            line.addWidget(text, 1)
            self.owned_host.addWidget(row)

    def set_account_details(self, me: dict, settings: dict | None, entitlements: list | None, guilds: list | None) -> None:
        self._account_payload = (me, settings, entitlements, guilds)
        self.set_account(me)
        clan = me.get("clan") or me.get("primary_guild") or {}
        tag = clan.get("tag") or "—"
        nitro = me.get("premium_type")
        self.account_meta.setText(
            f"{me.get('global_name') or me.get('username')}  ·  @{me.get('username')}  ·  "
            f"Nitro {nitro}  ·  clan {tag}"
        )
        if isinstance(settings, dict):
            custom = settings.get("custom_status") or {}
            self.status_edit.setText(str(custom.get("text") or ""))
        self._fill_clans(guilds or [], clan)
        count = len(entitlements or [])
        self.orbs_label.setText(t("orbs_count", n=count))

    def _emit_clan(self) -> None:
        self.clan_apply.emit(str(self.clan_box.currentData() or ""))

    def _fill_clans(self, guilds: list, clan: dict) -> None:
        current = str(clan.get("identity_guild_id") or clan.get("id") or "")
        current_tag = str(clan.get("tag") or "").strip()
        tagged: list[tuple[str, str, str]] = []
        rest: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for guild in guilds:
            if not isinstance(guild, dict):
                continue
            gid = str(guild.get("id") or "")
            if not gid or gid in seen:
                continue
            seen.add(gid)
            name = str(guild.get("name") or gid)
            features = {str(item) for item in (guild.get("features") or [])}
            tag = ""
            extra = guild.get("clan") or guild.get("profile") or {}
            if isinstance(extra, dict):
                tag = str(extra.get("tag") or extra.get("identity_tag") or "").strip()
            if "GUILD_TAGS" in features or tag:
                tagged.append((gid, name, tag))
            else:
                rest.append((gid, name, tag))
        tagged.sort(key=lambda item: item[1].casefold())
        rest.sort(key=lambda item: item[1].casefold())
        self.clan_box.blockSignals(True)
        self.clan_box.clear()
        self.clan_box.addItem(t("clan_off"), "")
        for gid, name, tag in tagged + rest:
            label = f"{name}  [{tag}]" if tag else name
            if gid == current and current_tag and not tag:
                label = f"{name}  [{current_tag}]"
            self.clan_box.addItem(label, gid)
        if current:
            idx = self.clan_box.findData(current)
            if idx < 0:
                shown = current_tag or current
                self.clan_box.insertItem(1, f"{shown}  ·  {current}", current)
                idx = 1
            self.clan_box.setCurrentIndex(idx)
        self.clan_box.blockSignals(False)
        total = len(tagged) + len(rest)
        if hasattr(self, "clan_meta"):
            self.clan_meta.setText(t("clan_meta", n=total, tagged=len(tagged)))

    def set_quests(self, tasks: list[QuestTask]) -> None:
        self._last_quests = tasks
        while self.quest_host.count():
            item = self.quest_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._quest_cards.clear()
        if not tasks:
            empty = QLabel(t("quests_empty2"))
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            self.quest_host.addWidget(empty)
            self.quest_meta.setText(t("quests_count", n=0))
            return
        self.quest_meta.setText(t("quests_count", n=len(tasks)))
        for task in tasks:
            card = QuestCard(task, self.images, self)
            self._quest_cards[task.quest_id] = card
            self.quest_host.addWidget(card)

    def update_quest(self, quest_id: str, progress: int, target: int, completed: bool) -> None:
        card = self._quest_cards.get(quest_id)
        if card is not None:
            card.update_progress(progress, target, completed)

    def retranslate(self) -> None:
        self.account.setText(t("account_waiting") if self._me is None else self.account.text())
        self.house_head.setText(t("house_head"))
        self.house_sub.setText(t("house_sub"))
        self.house_apply.setText(t("house_apply"))
        self.house_leave_btn.setText(t("house_leave"))
        self.house_hint.setText(t("house_hint"))
        desc = {1: t("house_brave"), 2: t("house_brill"), 3: t("house_bal")}
        for house_id, card in self._house_cards.items():
            card.subtitle.setText(desc.get(house_id, ""))
        self.privacy_head.setText(t("privacy_head"))
        self.privacy_sub.setText(t("privacy_sub"))
        self.privacy_apply.setText(t("privacy_apply"))
        privacy = {
            1: (t("privacy_private"), t("privacy_private_sub")),
            2: (t("privacy_limited"), t("privacy_limited_sub")),
            3: (t("privacy_public"), t("privacy_public_sub")),
        }
        for level, card in self._privacy_cards.items():
            title, sub = privacy[level]
            card.title.setText(title)
            card.subtitle.setText(sub)
        self.quests_head.setText(t("quests_head"))
        self.quests_sub.setText(t("quests_sub"))
        self.quest_enroll.setText(t("quests_enroll"))
        self.quest_refresh.setText(t("btn_scan"))
        self.quest_start.setText(t("quests_start"))
        self.quest_stop.setText(t("quests_stop"))
        self.badges_head.setText(t("badges_head"))
        self.badges_sub.setText(t("badges_sub"))
        self.gift_head.setText(t("gift_head"))
        for card, _title, need in self._gift_cards:
            card.subtitle.setText(t("gift_need", n=need))
        self.owned_title.setText(t("owned_head"))
        self.nitro_head.setText(t("nitro_head"))
        nitro_lookup = {key: months for key, months in NITRO_MONTHS}
        for label, key in self._catalog_labels:
            if key in nitro_lookup:
                label.setText(t("nitro_month", n=nitro_lookup[key]))
        self.acc_head.setText(t("account_head"))
        self.acc_sub.setText(t("account_sub"))
        self.status_edit.setPlaceholderText(t("ph_status"))
        self.status_btn.setText(t("btn_status"))
        self.clan_btn.setText(t("btn_clan"))
        if hasattr(self, "clan_meta") and self._account_payload is None:
            self.clan_meta.setText(t("clan_none"))
        self.account_refresh_btn.setText(t("btn_account_refresh"))
        self.help_head.setText(t("help_head"))
        self.help_body.setText(t("help_body", app=APP_TITLE, guild=GUILD_NAME, invite=INVITE_URL))
        self.help_invite.setText(t("help_join", invite=INVITE_URL))
        self.help_meta.setText(t("help_id", id=REQUIRED_GUILD_ID))
        if self._me is not None:
            self.set_account(self._me)
        if self._account_payload is not None:
            self.set_account_details(*self._account_payload)
        self.set_quests(self._last_quests)


Pages = KodYazarPages
