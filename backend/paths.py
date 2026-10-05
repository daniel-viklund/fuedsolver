"""Locations shared by a source checkout and a portable application folder."""
import os
from pathlib import Path
import sys

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
ENGINE_NAME = "feudsolver.exe" if os.name == "nt" else "feudsolver"
ENGINE_CANDIDATES = [ROOT / "bin" / ENGINE_NAME, ROOT / "build/Release" / ENGINE_NAME, ROOT / "build" / ENGINE_NAME]
ENGINE = Path(os.environ["FEUD_ENGINE"]) if "FEUD_ENGINE" in os.environ else next(
    (path for path in ENGINE_CANDIDATES if path.is_file()), ENGINE_CANDIDATES[-1]
)
