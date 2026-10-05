import json
import os
from pathlib import Path
import subprocess
import threading
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .board import ALPHABET, POINTS, standard_bonuses
from .ocr import recognize

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get("FEUD_ENGINE", ROOT / "build/feudsolver"))
DICTIONARY = Path(os.environ.get("FEUD_DICTIONARY", ROOT / "data/swedish.txt"))
MAX_UPLOAD = 12 * 1024 * 1024
ocr_lock = threading.Lock()
solve_slots = threading.BoundedSemaphore(2)
app = FastAPI(title="Feudsolver", version="0.1.0")

class Position(BaseModel):
    board: list[str] = Field(min_length=15, max_length=15)
    rack: str = Field(min_length=1, max_length=7)
    bonuses: list[list[str]] = Field(default_factory=standard_bonuses)
    limit: int = Field(default=30, ge=1, le=100)

    @field_validator("board")
    @classmethod
    def check_board(cls, rows):
        if any(len(row)!=15 or any(c!="." and c.upper() not in ALPHABET for c in row) for row in rows):
            raise ValueError("Board needs 15 rows of 15 Swedish letters or dots. Correct any ? tiles first.")
        return rows

    @field_validator("rack")
    @classmethod
    def check_rack(cls, rack):
        if any(c not in ALPHABET+"?" for c in rack.upper()):
            raise ValueError("Rack accepts Swedish letters and ? for a blank.")
        return rack.upper()

    @field_validator("bonuses")
    @classmethod
    def check_bonuses(cls, rows):
        if len(rows)!=15 or any(len(row)!=15 or any(c not in ("","DL","TL","DW","TW") for c in row) for row in rows):
            raise ValueError("Bonuses need a 15×15 grid containing DL, TL, DW, TW or empty strings.")
        return rows

@app.get("/api/health")
def health():
    return {"engine_ready":ENGINE.is_file(), "dictionary_ready":DICTIONARY.is_file(),
            "dictionary_name":DICTIONARY.name, "dictionary_kind":"DSSO spelling entries (not SAOL)" if DICTIONARY.name=="swedish.txt" else "Custom dictionary",
            "bonuses":standard_bonuses(), "points":POINTS}

def image_position(data):
    if not ocr_lock.acquire(blocking=False):
        raise HTTPException(429,"Another screenshot is being read. Try again shortly.")
    try:
        return recognize(data)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504,"Screenshot recognition timed out. Try a smaller screenshot.") from exc
    finally:
        ocr_lock.release()

@app.post("/api/recognize")
def upload_image(image: Annotated[UploadFile, File()]):
    data = image.file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD:
        raise HTTPException(413,"Screenshot must be smaller than 12 MB.")
    return image_position(data)

@app.post("/api/example")
def example():
    path=ROOT/"examples/screenshot.json"
    if not path.is_file():
        raise HTTPException(404,"Example position not found in the project folder.")
    position=Position.model_validate_json(path.read_text(encoding="utf-8"))
    return {**position.model_dump(exclude={"limit"}), "warnings":[], "uncertain":[]}

@app.post("/api/solve")
def solve(position: Position):
    if not ENGINE.is_file() or not DICTIONARY.is_file():
        raise HTTPException(503,"Run scripts/setup.sh to build the engine and install a dictionary.")
    if not solve_slots.acquire(blocking=False):
        raise HTTPException(429,"The engine is busy. Try again shortly.")
    try:
        result = subprocess.run([str(ENGINE), "--dictionary", str(DICTIONARY), "--limit", str(position.limit)],
                                input=position.model_dump_json(exclude={"limit"}), capture_output=True, text=True, timeout=30)
        if result.returncode:
            try: message=json.loads(result.stderr).get("error","Engine rejected the position.")
            except json.JSONDecodeError: message="Engine failed to read this position."
            raise HTTPException(422,message)
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504,"Search exceeded 30 seconds. Try a smaller dictionary.") from exc
    finally:
        solve_slots.release()

app.mount("/", StaticFiles(directory=ROOT/"web", html=True), name="web")
