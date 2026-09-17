Windows **onedir** build from `packaging/windows/KodYazar.spec`.

## Download

1. Get `KodYazar-Client-v*-windows-x64.zip` from this release.
2. Unzip the whole folder. Do **not** copy only `KodYazar.exe`.
3. Run `KodYazar\KodYazar.exe`.
4. Start Discord / Vesktop first, join [KodYazar Client](https://discord.gg/rS42FCPfKZ), then connect.

`games.json` (~12 MB catalog) and `assets/` are inside `_internal`.

## Also in this tree

- Source: clone and `python run.py` (Linux / macOS / Windows)
- Windows from source: `kurulum.bat` then `windows.bat`

## Verify

Hashes for **this tag** (`v1.0.0`): [`docs/HASHES-v1.0.0.md`](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/HASHES-v1.0.0.md) and the `HASHES.txt` asset on the release.

| File | SHA-256 | VirusTotal |
| --- | --- | --- |
| `KodYazar.exe` | `aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595` | [gui/file/…](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595) |
| zip | `81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b` | [gui/file/…](https://www.virustotal.com/gui/file/81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b) |

Upload **`KodYazar.exe`** (2.1 MB) if VirusTotal has no report yet. The zip is 55 MB (over the anonymous 32 MB web cap). Unsigned PyInstaller often trips heuristics (packer overlay, process-enumeration APIs). That is expected; it is not a “clean” badge and not proof of malware.

## Notes

- Unsigned PyInstaller binary. Windows SmartScreen / Defender may warn until you “Run anyway”.
- Chrome App-Bound cookies (`v20`) are not decrypted; paste cookie on the lock screen if harvest fails.
- Official Discord shows one Playing activity. Extra IPC pins need Vesktop/arRPC.

Docs: [README](https://github.com/KodYazicam/KY-GamePlayer#readme) · [Türkçe](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/README.tr.md) · [Install](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/install.md)
