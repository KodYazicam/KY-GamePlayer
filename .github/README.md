# `.github/` — CI and templates

| Path | Role |
| --- | --- |
| `workflows/ci.yml` | On push/PR to `main`: Python 3.11, 3.12, 3.13 — `compileall`, `unittest discover`, `games.json` is a non-empty list |
| `ISSUE_TEMPLATE/bug.yml` | Bug form (OS, Discord client, redacted logs) |
| `ISSUE_TEMPLATE/feature.yml` | Feature form (area dropdown) |
| `PULL_REQUEST_TEMPLATE.md` | Compile/tests/docs/license/no-secrets checklist |

CI does **not** install PySide6. Unit tests import only helpers that do not need Qt. Do not add `from ky_gameplayer.window import MainWindow` to tests without splitting a Qt-free module first.

Private security reports: GitHub Security Advisories, not the public bug form. See [`../SECURITY.md`](../SECURITY.md).
