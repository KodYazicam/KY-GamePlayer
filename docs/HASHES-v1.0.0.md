# v1.0.0 Windows hashes

Built **2026-09-17** on GitHub Actions `windows-latest` (PyInstaller onedir). Same bytes as the [v1.0.0 release](https://github.com/KodYazicam/KY-GamePlayer/releases/tag/v1.0.0) assets.

Verify locally:

```powershell
Get-FileHash KodYazar.exe -Algorithm SHA256
Get-FileHash KodYazar-Client-v1.0.0-windows-x64.zip -Algorithm SHA256
```

Then paste the SHA-256 into VirusTotal (or open the permalink). The zip is **55.5 MB**; VirusTotal’s anonymous web upload cap is **32 MB**, so scan **`KodYazar.exe` (2.1 MB)** first.

**This scan (2026-09-17 20:25 UTC):** zip **0/66**, exe **3/65** (Google/Kaspersky/Rising/Skyhigh *Timeout*; four mobile engines *unable to process*). Counts move as engines update.

## `KodYazar.exe`

| | |
| --- | --- |
| Path in zip | `KodYazar/KodYazar.exe` |
| Size | 2 207 827 bytes |
| SHA-256 | `aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595` |
| SHA-1 | `91ba45453ff8620096fa6e560ffab8e2d913fbef` |
| MD5 | `4a66d9f3a1fb9b2ca9246ad24fc1b612` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595) · [detection 3/65](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection) · [behavior](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior) |

## `KodYazar-Client-v1.0.0-windows-x64.zip`

| | |
| --- | --- |
| Size | 58 175 875 bytes |
| SHA-256 | `81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b` |
| SHA-1 | `274acf3f598174b1ecd67832b501c683cc4629ab` |
| MD5 | `cfff176d74b6802a3805c919b5dcb5e9` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b) · [this analysis 0/66](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection) |

## What the 3 vendors actually said

| Vendor | Label | Kind |
| --- | --- | --- |
| Microsoft | `Trojan:Win32/Wacatac.B!ml` | ML (`!ml`). Generic packed-EXE bucket. [Microsoft on Wacatac](https://www.microsoft.com/en-us/wdsi/threats/malware-encyclopedia-description?name=Trojan%3AWin32%2FWacatac.B!ml) — often unsigned / high-entropy PEs. |
| Arctic Wolf | `Unsafe` | Reputation / heuristic, no family. |
| SecureAge | `Malicious` | No family string. |

Kaspersky, ESET, BitDefender, Malwarebytes, CrowdStrike Falcon, ClamAV, Avast, AVG, Sophos, Symantec: **undetected**. Popular-threat-label `trojan.` is just VT aggregating those three rows.

## Sandbox (Behavior tab)

[CAPE + Zenbox](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior):

| Check | Result |
| --- | --- |
| Detections | **not found** |
| IDS / Sigma | **not found** |
| Dropped files | **not found** |
| Network comms | **not found** |
| Processes | only `KodYazar.exe` (twice, two sandboxes) |
| Files opened | itself, `_internal\ucrtbase.dll`, Win32 UI DLLs |
| MITRE | T1027 (overlay/obfuscated PE), T1033/T1082 (locale / `GetUserName`-class), T1071 tagged **low** — no C2 observed |
| Behavior tags | `obfuscated` (= high-entropy overlay) |

That is a GUI stub unpacking PyInstaller’s archive next to the exe, not a dropper.

## PE facts that trip heuristics

Unsigned PyInstaller onedir stub (`DetectItEasy`: MSVC 19.36 / VS 2022). Overlay starts at offset `332800`, size `1 875 027` (~the packed payload), entropy **7.999**. `.rsrc` entropy 7.91 (PNG icons). Compilation timestamp **2026-09-17 19:26:45 UTC** = the GitHub Actions job. Imports: `USER32`, `COMCTL32`, `KERNEL32`, `ADVAPI32`, `GDI32` (bootloader; Qt lives in `_internal`).

`OpenProcess` / `CreateToolhelp32Snapshot` in the **unpacked** payload are intentional (`ky_gameplayer.processes` — game detect). The stub itself does not enumerate processes in this sandbox run.

Do not treat **0/66 on the zip** as “the exe is clean.” VirusTotal scores the container separately. SmartScreen looks at the PE.

Prefer `python run.py` from source if you do not want a packed binary. This repo does **not** embed a live “0/70” badge.
