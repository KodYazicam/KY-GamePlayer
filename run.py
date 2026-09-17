#!/usr/bin/env python3
import os

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false;qt.qpa.fonts=false")

from ky_gameplayer.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
