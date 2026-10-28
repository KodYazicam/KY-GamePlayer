from __future__ import annotations


from threading import Thread

from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..brand import APP_TITLE, GUILD_NAME, INVITE_URL
from ..client_auth import harvest
from ..i18n import t as i18n
from ..membership import check_membership


class LockMixin:
    def _build_lock(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel(APP_TITLE)
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_text = QLabel(i18n("lock_need", guild=GUILD_NAME, invite=INVITE_URL))
        self.lock_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_text.setWordWrap(True)
        self.lock_join = QPushButton(i18n("lock_join"))
        self.lock_retry = QPushButton(i18n("lock_retry"))
        self.lock_join.clicked.connect(self._open_invite)
        self.lock_retry.clicked.connect(self._enforce_membership)
        self.lock_token = QLineEdit()
        self.lock_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.lock_token.setPlaceholderText(i18n("lock_token_ph"))
        self.lock_cookie = QLineEdit()
        self.lock_cookie.setEchoMode(QLineEdit.EchoMode.Password)
        self.lock_cookie.setPlaceholderText(i18n("lock_cookie_ph"))
        self.lock_token_btn = QPushButton(i18n("lock_token_go"))
        self.lock_token_btn.clicked.connect(self._submit_lock_token)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(self.lock_text)
        layout.addWidget(self.lock_token)
        layout.addWidget(self.lock_cookie)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.lock_join)
        row.addWidget(self.lock_retry)
        row.addWidget(self.lock_token_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _open_invite(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(INVITE_URL))

    def _submit_lock_token(self) -> None:
        from ..client_auth import ClientAuth
        from ..membership import Membership, check_membership

        raw = self.lock_token.text().strip().strip('"')
        cookie = self.lock_cookie.text().strip()
        if not raw:
            self.lock_text.setText(i18n("lock_token_ph"))
            return
        auth = ClientAuth(token=raw, cookie=cookie, client="paste")
        if not auth.cookie:
            from ..client_auth import harvest_disk_extras

            harvest_disk_extras(auth)
        try:
            membership = check_membership(raw, auth.cookie)
        except Exception as exc:
            membership = Membership(ok=False, message=str(exc))
        self._on_membership(auth, membership)

    def _enforce_membership(self) -> None:
        if self._member_busy:
            return
        self._refresh_clients()
        self._member_busy = True
        preferred = self._preferred_client
        self.member_label.setText(i18n("member_checking"))
        self.lock_text.setText(i18n("member_checking"))
        QTimer.singleShot(self._lock_timeout * 1000, self._membership_timeout)

        def work() -> None:
            from ..client_auth import ClientAuth
            from ..membership import Membership

            auth = ClientAuth()
            try:
                auth = harvest(preferred, quick=True)
                membership = check_membership(auth.token, auth.cookie or "")
            except Exception as exc:
                membership = Membership(ok=False, message=f"{type(exc).__name__}: {exc}")
            self.membership_ready.emit(auth, membership)

        Thread(target=work, name="ky-membership", daemon=True).start()

    def _membership_timeout(self) -> None:
        if not self._member_busy:
            return
        self._member_busy = False
        self.lock_text.setText(i18n("lock_timeout"))
        self.member_label.setText(i18n("lock_timeout"))
        self._set_status(i18n("lock_timeout"))

    @Slot(object, object)
    def _on_membership(self, auth, membership) -> None:
        self._member_busy = False
        self._member_ok = bool(getattr(membership, "ok", False))
        self._log(f"üyelik ok={self._member_ok} {getattr(membership, 'username', '')} {getattr(membership, 'message', '')}")
        if not self._member_ok and auth is not None and not getattr(auth, "token", ""):
            self._stack.setCurrentIndex(0)
            self.lock_text.setText(i18n("lock_no_token"))
            self.member_label.setText(i18n("lock_no_token"))
            self._set_status(i18n("member_lock"))
            return
        if self._member_ok:
            self._stack.setCurrentIndex(1)
            who = membership.username or membership.user_id
            client = auth.client or "disk"
            self.member_label.setText(f"{who}  ·  {client}  ·  {GUILD_NAME}")
            if membership.me:
                self.pages.set_account(membership.me)
            self.science.preferred = self._preferred_client
            self.quest_engine.preferred = self._preferred_client
            self.science.apply_auth(auth)
            if not self.science.state.cookie:
                from ..client_auth import harvest_disk_extras

                harvest_disk_extras(auth)
                self.science.apply_auth(auth)
            if hasattr(self, "science_token"):
                self.science_token.setText(self.science.state.token)
                self.science_cookie.setText(self.science.state.cookie)
                if auth.fingerprint:
                    self.science_fp.setText(self.science.state.fingerprint)
                self._refresh_science_status()
            self.quest_engine.refresh()
            self._refresh_account()
            self._set_status(i18n("member_ok", who=who))
            return
        self._stack.setCurrentIndex(0)
        self.lock_text.setText(membership.message or i18n("lock_not_member", guild=GUILD_NAME, invite=INVITE_URL))
        self._set_status(i18n("member_lock"))

    def _require_member(self) -> bool:
        if self._member_ok:
            return True
        if self._member_busy:
            self._set_status(i18n("member_checking"))
            return False
        self._enforce_membership()
        return False
