# v1.0.0 Windows hashes

Built **2026-09-17** on GitHub Actions `windows-latest` (PyInstaller onedir). Same bytes as the [v1.0.0 release](https://github.com/KodYazicam/KY-GamePlayer/releases/tag/v1.0.0) assets.

Verify locally:

```powershell
Get-FileHash KodYazar.exe -Algorithm SHA256
Get-FileHash KodYazar-Client-v1.0.0-windows-x64.zip -Algorithm SHA256
```

Then paste the SHA-256 into VirusTotal (or open the permalink). The zip is **55.5 MB**; VirusTotal’s anonymous web upload cap is **32 MB**, so scan **`KodYazar.exe` (2.1 MB)** first.

**This scan (2026-09-17):** zip **0/66**, exe **3/66**. Counts move as engines update. The 3 exe hits are the usual unsigned-PyInstaller heuristics (see below), not a named family.

## `KodYazar.exe`

| | |
| --- | --- |
| Path in zip | `KodYazar/KodYazar.exe` |
| Size | 2 207 827 bytes |
| SHA-256 | `aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595` |
| SHA-1 | `91ba45453ff8620096fa6e560ffab8e2d913fbef` |
| MD5 | `4a66d9f3a1fb9b2ca9246ad24fc1b612` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595) · [this analysis 3/66](https://www.virustotal.com/gui/file-analysis/NGE2NmQ5ZjNhMWZiOWIyY2E5MjQ2YWQyNGZjMWI2MTI6MTc4OTY3Njc1OQ==/detection) |

## `KodYazar-Client-v1.0.0-windows-x64.zip`

| | |
| --- | --- |
| Size | 58 175 875 bytes |
| SHA-256 | `81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b` |
| SHA-1 | `274acf3f598174b1ecd67832b501c683cc4629ab` |
| MD5 | `cfff176d74b6802a3805c919b5dcb5e9` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b) · [this analysis 0/66](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection) |

## What “detections” usually mean here

This is an **unsigned PyInstaller** binary. Heuristic engines often flag:

- high-entropy overlay (the bundled archive after the PE stub)
- packer / “modified” signatures
- `OpenProcess` / `CreateToolhelp32Snapshot` (this app **lists processes** to detect running games)
- `OpenProcessToken` / `GetTokenInformation` (Windows APIs used by the frozen runtime and DPAPI cookie helper)

Those are expected for this codebase. They are **not** a clean bill of health and **not** a malware confirmation. Prefer building from source (`python run.py`) if you do not want a packed EXE.

Do not treat **0/66 on the zip** as “the exe is clean.” VirusTotal scans the zip container separately from the PE inside it. The number that matters for SmartScreen / Defender is the **exe** row (3/66 here).

This repo does **not** embed a live “0/70” badge. Counts change; permalinks + SHA-256 do not.
