# v1.0.0 Windows hashes

Built **17 September 2026** on GitHub Actions (`windows-latest`, PyInstaller onedir). Same bytes as the [v1.0.0 release](https://github.com/KodYazicam/KY-GamePlayer/releases/tag/v1.0.0).

Check on your machine before you run it:

```powershell
Get-FileHash KodYazar.exe -Algorithm SHA256
Get-FileHash KodYazar-Client-v1.0.0-windows-x64.zip -Algorithm SHA256
```

The numbers below must match. If they do not, you do not have our file.

The zip is ~55 MB. VirusTotal’s anonymous web upload stops at 32 MB, so upload **`KodYazar.exe`** (2.1 MB) if you scan it yourself.

The English story (SmartScreen, what 0/66 vs 3/65 means, sandbox): [README — Windows EXE and antivirus](../README.md#windows-exe-and-antivirus). Turkish: [`README.tr.md`](README.tr.md#windows-exe-ve-antivirüs).

## `KodYazar.exe`

| | |
| --- | --- |
| Path in the zip | `KodYazar/KodYazar.exe` |
| Size | 2 207 827 bytes |
| SHA-256 | `aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595` |
| SHA-1 | `91ba45453ff8620096fa6e560ffab8e2d913fbef` |
| MD5 | `4a66d9f3a1fb9b2ca9246ad24fc1b612` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595) · [detection 3/65](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection) · [behavior](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior) |

## Zip

| | |
| --- | --- |
| Name | `KodYazar-Client-v1.0.0-windows-x64.zip` |
| Size | 58 175 875 bytes |
| SHA-256 | `81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b` |
| SHA-1 | `274acf3f598174b1ecd67832b501c683cc4629ab` |
| MD5 | `cfff176d74b6802a3805c919b5dcb5e9` |
| VirusTotal | [file](https://www.virustotal.com/gui/file/81cc6d4ca19fe83835d61f264fbb45bc93aacdb7bf609cb884e310ebb79ad18b) · [0/66](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection) |

Scan of **17 Sep 2026, 20:25 UTC**. Google / Kaspersky / Rising / Skyhigh *timeout* on the exe; four mobile engines cannot process a Win64 GUI. The count will move if you click Reanalyze.

## The three vendor rows (exe)

| Vendor | What they wrote | What that usually means |
| --- | --- | --- |
| Microsoft | `Trojan:Win32/Wacatac.B!ml` | `!ml` = machine learning. Generic bucket for unsigned / packed PEs. Not “we identified this as the Wacatac family.” |
| Arctic Wolf | `Unsafe` | Reputation / heuristic. No family name. |
| SecureAge | `Malicious` | No family name. |

Kaspersky, ESET, Bitdefender, Malwarebytes, CrowdStrike Falcon, ClamAV, Avast, AVG, Sophos, Symantec: **undetected**. VirusTotal’s “trojan” headline is those three rows added together.

## What the sandbox did

[CAPE + Zenbox](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior) actually ran the exe:

- no dropped files
- no network
- no IDS / Sigma
- only process: `KodYazar.exe`
- files opened: itself, `_internal\ucrtbase.dll`, normal Win32 UI DLLs
- tag `obfuscated` = the PyInstaller overlay (high-entropy blob at the end of the PE), not a hidden second program

That is a GUI stub looking for its `_internal` folder. In the sandbox the folder was not there (they uploaded the exe alone), so it could not load Qt. At home, unzip the **whole** zip.

## Why static engines twitch

Unsigned PyInstaller stub (DetectItEasy: MSVC 19.36 / Visual Studio 2022). Overlay starts at byte `332800`, size `1 875 027`, entropy **7.999**. That *is* the packed Python. Compile timestamp **2026-09-17 19:26:45 UTC** matches the Actions job. Stub imports: `USER32`, `COMCTL32`, `KERNEL32`, `ADVAPI32`, `GDI32`. Qt and the game catalog live in `_internal`, not in those five DLLs.

`CreateToolhelp32Snapshot` / `OpenProcess` exist in the **unpacked** app on purpose (`ky_gameplayer.processes` — “which game is running?”). The stub did not enumerate processes in this sandbox run.

Do not quote the zip’s 0/66 as if the exe were clean. Windows cares about the PE.
