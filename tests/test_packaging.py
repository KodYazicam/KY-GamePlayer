from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from ky_gameplayer import __version__

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_version_matches_pyproject(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], __version__)

    def test_linux_spec_and_launcher_are_present(self) -> None:
        spec = (ROOT / "packaging" / "linux" / "KodYazar-linux.spec").read_text(encoding="utf-8")
        self.assertIn('name="KodYazar"', spec)
        self.assertIn("tomllib", spec)
        self.assertTrue((ROOT / "packaging" / "linux" / "kodyazar").is_file())
        self.assertTrue((ROOT / "packaging" / "linux" / "PKGBUILD.in").is_file())

    def test_desktop_entry_uses_installed_launcher(self) -> None:
        body = (ROOT / "packaging" / "linux" / "kodyazar.desktop").read_text(encoding="utf-8")
        self.assertIn("Exec=/usr/bin/kodyazar", body)
        self.assertIn("Icon=kodyazar", body)

    def test_macos_bundle_version_comes_from_project(self) -> None:
        spec = (ROOT / "packaging" / "macos" / "KodYazar-macOS.spec").read_text(encoding="utf-8")
        self.assertIn('"CFBundleShortVersionString": version', spec)
        self.assertNotIn("1.1.0", spec)

    def test_release_workflow_creates_combined_hashes(self) -> None:
        body = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("HASHES.txt", body)
        for job in ("windows", "macos-arm64", "macos-x64", "linux", "arch", "publish"):
            self.assertIn(f"  {job}:", body)


if __name__ == "__main__":
    unittest.main()
