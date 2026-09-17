# `assets/` — window and desktop icons

Used by:

- `ky_gameplayer.__main__` → `QApplication.setWindowIcon`
- `ky_gameplayer.autostart.install_desktop` → Linux `.desktop` `Icon=`
- `packaging/windows/KodYazar.spec` → PyInstaller `icon=` (PNG fallback; `.ico` is preferred if you add one)

| File | Size | Role |
| --- | --- | --- |
| `icon.png` | 256×256 RGBA | Canonical app icon. Copied as `icon256.png`. |
| `icon256.png` | 256×256 | Same pixels as `icon.png`. |
| `icon128.png` | 128×128 | Task switchers / about dialogs. |
| `icon64.png` | 64×64 | Desktop environments that pick mid-size. |
| `icon48.png` | 48×48 | GNOME/KDE app grid. |
| `icon32.png` | 32×32 | Title bar / small launchers. |
| `icon16.png` | 16×16 | Favicon-scale. |

There is **no** `icon.ico` in the tree. Windows EXE build falls back to `icon.png`. To get a proper multi-size ICO:

```bash
# ImageMagick example
magick assets/icon16.png assets/icon32.png assets/icon48.png assets/icon64.png assets/icon128.png assets/icon256.png assets/icon.ico
```

Then `KodYazar.spec` picks `assets/icon.ico` automatically.

Do not put screenshots, banners, or the 12 MB `games.json` here. CDN game art is downloaded at runtime into the cache dir (`docs/data.md`).
