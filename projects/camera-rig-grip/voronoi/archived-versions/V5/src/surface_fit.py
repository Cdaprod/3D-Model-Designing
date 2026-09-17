#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
raise SystemExit(subprocess.call([sys.executable,str(ROOT/"src"/"solid_loft_fit.py"),*sys.argv[1:]],cwd=ROOT))
