# v1.0.0 Windows hashes

Built **2026-09-17** on GitHub Actions `windows-latest` (PyInstaller onedir). Same bytes as the [v1.0.0 release](https://github.com/KodYazicam/KY-GamePlayer/releases/tag/v1.0.0) assets.

Verify locally:

```powershell
Get-FileHash KodYazar.exe -Algorithm SHA256
Get-FileHash KodYazar-Client-v1.0.0-windows-x64.zip -Algorithm SHA256
```

Then paste the SHA-256 into VirusTotal (or open the permalink). The zip is **55.5 MB**; VirusTotal’s anonymous web upload cap is **32 MB**, so scan **`KodYazar.exe` (2.1 MB)** first. The zip still has a permalink by hash if someone already uploaded it.

## `KodYazar.exe`

| | |
| --- | --- |
| Path in zip | `KodYazar/KodYazar.exe` |
| Size | 2 207 827 bytes |
| SHA-256 | `aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595` |
| SHA-1 | `91ba45453ff8620096fa6e560ffab8e2d913fbef` |
| MD5 | `4a66d9f3a1fb9b2ca9246ad24fc1b612` |
| VirusTotal | https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595 |

## `KodYazar-Client-v1.0.0-windows-x64.zip`

| | |
| --- | --- |
| Size | 58 175 875 bytes |
| SHA-256 | `81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b` |
| SHA-1 | `274acf3f598174b1ecd67832b501c683cc4629ab` |
| MD5 | `cfff176d74b6802a3805c919b5dcb5e9` |
| VirusTotal | https://www.virustotal.com/gui/file/81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b |

## What “detections” usually mean here

This is an **unsigned PyInstaller** binary. Heuristic engines often flag:

- high-entropy overlay (the bundled archive after the PE stub)
- packer / “modified” signatures
- `OpenProcess` / `CreateToolhelp32Snapshot` (this app **lists processes** to detect running games)
- `OpenProcessToken` / `GetTokenInformation` (Windows APIs used by the frozen runtime and DPAPI cookie helper)

Those are expected for this codebase. They are **not** a clean bill of health and **not** a malware confirmation. Prefer building from source (`python run.py`) if you do not want a packed EXE.

This repo does **not** embed a live VirusTotal “0/70” badge. Counts change as engines update, and a false-positive badge would be worse than hashes + a permalink.
