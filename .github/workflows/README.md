# Workflows

| File | Trigger | What |
| --- | --- | --- |
| `ci.yml` | push/PR to `main` | `compileall` + `unittest` on Python 3.11–3.14, `ruff`, offscreen Qt coverage with a 60 % gate, Windows smoke job. No external network, Discord client or real credentials. |
| `release.yml` | tag `v*`, manual dispatch | Native Windows, macOS arm64/Intel, Debian/Ubuntu, Fedora/RHEL, Arch and generic Linux builds; one `publish` job creates the release with per-file SHA-256 and `HASHES.txt`. A manual dispatch on `main` builds and uploads artifacts but skips `publish`; use it to validate runners before tagging. |

Release jobs need `contents: write` (the default `GITHUB_TOKEN` is enough).
Notes body: [`docs/release-notes.md`](../../docs/release-notes.md).

## Release matrix

| Job | Runner | Output |
| --- | --- | --- |
| `windows` | `windows-latest` | `…-windows-x64.zip` |
| `macos-arm64` | `macos-15` | `…-macos-arm64.zip` |
| `macos-x64` | `macos-15-intel` | `…-macos-x64.zip` |
| `linux` | `ubuntu-22.04` + `fedora:latest` container for RPM | `…-linux-x64.deb`, `.rpm`, `.tar.gz` |
| `arch` | `ubuntu-22.04` + `archlinux:base-devel` container | `…-arch-x64.pkg.tar.zst` |
| `publish` | `ubuntu-latest` | checksums + `HASHES.txt` + GitHub Release |

The tag must match `project.version` in `pyproject.toml`; the `publish` job
fails before uploading if they differ.

Local equivalents: [`packaging/windows/`](../../packaging/windows/),
[`packaging/macos/`](../../packaging/macos/) and
[`packaging/linux/`](../../packaging/linux/).
