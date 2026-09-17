from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path


def _linux_path() -> Path:
    config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return config / "autostart" / "kodyazar.desktop"


def _win_path() -> Path:
    appdata = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "KodYazar.bat"


def _mac_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "dev.kodyazar.client.plist"


def enabled() -> bool:
    if sys.platform == "win32":
        return _win_path().exists()
    if sys.platform == "darwin":
        return _mac_path().exists()
    return _linux_path().exists()


def _python() -> Path:
    exe = Path(sys.executable)
    if sys.platform == "win32":
        candidate = exe.with_name("pythonw.exe")
        if candidate.exists():
            return candidate
    return exe


def _launch(run_py: Path) -> tuple[Path, Path | None, Path]:
    run_py = run_py.resolve()
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return exe, None, exe.parent
    python = _python()
    return python, run_py, run_py.parent


def set_enabled(on: bool, run_py: Path) -> None:
    python, script, workdir = _launch(run_py)
    if sys.platform == "win32":
        path = _win_path()
        if not on:
            if path.exists():
                path.unlink()
            vbs = path.with_suffix(".vbs")
            if vbs.exists():
                vbs.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if script is None:
            cmd = f'start "" /D "{workdir}" "{python}"'
        else:
            cmd = f'start "" /D "{workdir}" "{python}" "{script}"'
        vbs = path.with_suffix(".vbs")
        py = str(python).replace("\\", "\\\\")
        wd = str(workdir).replace("\\", "\\\\")
        extra = f' & """{str(script).replace(chr(92), chr(92)+chr(92))}"""' if script else ""
        vbs.write_text(
            "\r\n".join(
                [
                    'Set sh = CreateObject("Wscript.Shell")',
                    f'sh.CurrentDirectory = "{wd}"',
                    f'sh.Run """{py}"""{extra}, 0, False',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        path.write_text(
            "\r\n".join(
                [
                    "@echo off",
                    f'cd /d "{workdir}"',
                    cmd,
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return
    if sys.platform == "darwin":
        path = _mac_path()
        if not on:
            if path.exists():
                path.unlink()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
                    '<plist version="1.0"><dict>',
                    "<key>Label</key><string>dev.kodyazar.client</string>",
                    "<key>ProgramArguments</key><array>",
                    f"<string>{python}</string>",
                    *([f"<string>{script}</string>"] if script else []),
                    "</array>",
                    f"<key>WorkingDirectory</key><string>{workdir}</string>",
                    "<key>RunAtLoad</key><true/>",
                    "</dict></plist>",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return
    path = _linux_path()
    if not on:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    icon = workdir / "assets" / "icon.png"
    exec_line = f"{shlex.quote(str(python))}" + (f" {shlex.quote(str(script))}" if script else "")
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=KodYazar Client",
        f"Exec={exec_line}",
        f"Path={workdir}",
        "X-GNOME-Autostart-enabled=true",
        "Hidden=false",
        "Terminal=false",
    ]
    if icon.exists():
        lines.append(f"Icon={icon}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    install_desktop(run_py)


def install_desktop(run_py: Path) -> None:
    run_py = run_py.resolve()
    python = _python()
    icon = run_py.parent / "assets" / "icon.png"
    body = "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            "Name=KodYazar Client",
            f"Exec={shlex.quote(str(python))} {shlex.quote(str(run_py))}",
            f"Path={run_py.parent}",
            f"Icon={icon if icon.exists() else 'applications-games'}",
            "Terminal=false",
            "Categories=Game;Utility;",
            "StartupNotify=true",
            "StartupWMClass=KodYazar Client",
            "",
        ]
    )
    local = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "applications" / "kodyazar.desktop"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(body, encoding="utf-8")
    (run_py.parent / "KY-GamePlayer.desktop").write_text(body, encoding="utf-8")
