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

## Antivirus / VirusTotal

This zip is **unsigned PyInstaller**. SmartScreen will likely warn. That is the same class of warning you get from any random GitHub EXE, not a special KodYazar finding.

We scanned both files (17 Sep 2026):

- **Zip — 0/66.** VirusTotal looked at the container. [analysis](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection)
- **`KodYazar.exe` — 3/65.** Microsoft `Trojan:Win32/Wacatac.B!ml` (machine learning, generic packed-PE bucket), Arctic Wolf `Unsafe`, SecureAge `Malicious`. Kaspersky, ESET, Bitdefender, Malwarebytes, CrowdStrike: clean. [detection](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection)

The sandboxes then ran the exe: **no dropped files, no network**, only `KodYazar.exe` itself. [behavior](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior)

**0/66 on the zip is not “the exe is clean.”** Windows looks at the PE. If you do not want a packed binary, clone the repo and run `python run.py`.

Hashes: [`docs/HASHES-v1.0.0.md`](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/HASHES-v1.0.0.md) and `HASHES.txt` on this release. Longer write-up: [README](https://github.com/KodYazicam/KY-GamePlayer#windows-exe-and-antivirus).

## Notes

- Unsigned PyInstaller binary. Windows SmartScreen / Defender may warn until you “Run anyway”.
- Chrome App-Bound cookies (`v20`) are not decrypted; paste cookie on the lock screen if harvest fails.
- Official Discord shows one Playing activity. Extra IPC pins need Vesktop/arRPC.

Docs: [README](https://github.com/KodYazicam/KY-GamePlayer#readme) · [Türkçe](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/README.tr.md) · [Install](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/install.md)
