#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parent
    launcher = root / "start_local.sh"
    print("run_gui.py is deprecated. Launching the supported local web app instead.")
    return subprocess.call([str(launcher)])


if __name__ == "__main__":
    sys.exit(main())
