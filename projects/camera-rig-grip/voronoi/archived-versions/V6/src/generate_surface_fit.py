#!/usr/bin/env python3
"""Optional post-stage launcher for the adjustable pipeline."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
cmd = [sys.executable, str(ROOT / "src" / "surface_fit.py"), *sys.argv[1:]]
raise SystemExit(subprocess.call(cmd, cwd=ROOT))
