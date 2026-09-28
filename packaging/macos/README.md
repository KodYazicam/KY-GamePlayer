# macOS packaging

Produces `dist/KodYazar.app` with PyInstaller. Untested on Apple Silicon vs
Intel — build on the machine you ship for.

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

## Notes

- The `.app` is **not notarized**. First launch: right-click → Open, or
  `xattr -dr com.apple.quarantine dist/KodYazar.app` after copying it off
  this machine.
- Token/IPC paths live under `~/Library/Application Support/kodyazar`
  and `/tmp` (see README → Data on disk).
- `codesign -s - --deep dist/KodYazar.app` (ad-hoc) can silence some
  Gatekeeper noise; real signing needs a Developer ID certificate
  (roadmap 2.0).
