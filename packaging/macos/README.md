# macOS packaging

Produces `dist/KodYazar.app` with PyInstaller. Build on the architecture you
ship for: `macos-15` is Apple Silicon (arm64), `macos-15-intel` is Intel (x64).
The current PySide6 6.12 wheels require macOS 14 (Sonoma) or newer.

## Prereqs

```bash
python3 -m pip install -r requirements.txt pyinstaller
```

## Build

```bash
./packaging/macos/build.sh
# -> dist/KodYazar.app
open dist/KodYazar.app
```

`build.sh` first creates `build/icon.icns` from `assets/icon.png` with
`make-icns.sh`, then runs PyInstaller. The bundle version comes from
`pyproject.toml`; do not hard-code it in the spec.

## Release zip

```bash
ditto -c -k --sequesterRsrc --keepParent dist/KodYazar.app \
  KodYazar-Client-vX.Y.Z-macos-arm64.zip
```

The release workflow creates one zip per architecture. The `.app` includes
`games.json`, `assets/` and `LICENSE` in `Contents/Resources`.

## Notes

- The `.app` is **not signed or notarized**. First launch on another Mac:
  right-click → Open, or `xattr -dr com.apple.quarantine KodYazar.app` after
  copying it off this machine. Real signing needs a Developer ID certificate
  (roadmap 2.0).
- Token/IPC paths live under `~/Library/Application Support/kodyazar`,
  `~/Library/Caches/kodyazar` and the macOS temp directories.
- `codesign -s - --deep dist/KodYazar.app` (ad-hoc) can silence some Gatekeeper
  noise; PyInstaller may already ad-hoc sign an arm64 bundle.
- Intel support is built on `macos-15-intel`; GitHub hosts that label until
  August 2027. After that, the Intel artifact will be dropped or built on a
  self-hosted runner.
