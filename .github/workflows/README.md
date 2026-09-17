# Workflows

| File | Trigger | What |
| --- | --- | --- |
| `ci.yml` | push/PR to `main` | `compileall` + `unittest` on Python 3.11/3.12/3.13. No PySide6. |
| `release.yml` | tag `v*` | Windows PyInstaller onedir zip + SHA-256, `gh release create`. |

Release job needs `contents: write` (default `GITHUB_TOKEN` is enough). Notes body: [`docs/release-notes.md`](../../docs/release-notes.md).

Local Windows equivalent: `packaging\windows\build.bat`.
