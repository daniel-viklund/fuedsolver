"""Detect an unzoomed dark-theme Wordfeud board and recognize tiles locally.

Geometry is inferred from the 15-cell grid, never from screenshot-specific text.
macOS uses Vision; other platforms can install Tesseract with Swedish language data.
"""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageOps
from .board import ALPHABET, standard_bonuses
from .glyphs import recognize_glyph
from .paths import ROOT


def runs(mask):
    edges = np.diff(np.r_[False, mask, False].astype(int))
    return list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))

def detect_geometry(image):
    # Wordfeud's unzoomed board spans the screenshot width. Find its colored cells.
    a = np.asarray(image)
    h, w = a.shape[:2]
    colorful = (a.max(axis=2).astype(int) - a.min(axis=2).astype(int) > 45) & (a.max(axis=2) > 90)
    # Sample the left padding, away from the TB/TO/DB label that splits a run.
    rows = colorful[:, max(2,int(w/15*.12))]
    cell = w / 15
    candidates = []
    for start, end in runs(rows):
        if .5 * cell < end - start < 1.2 * cell and start + w <= h:
            top = max(0, start - int(cell * .05))
            # A grid has a dark horizontal gutter every cell, bright cell interiors.
            scores = []
            for r in range(15):
                y = int(top + (r + .5) * cell)
                if y < h:
                    centers = [a[y, min(w-1, int((c+.5)*cell))].mean() for c in range(15)]
                    scores.append(np.std(centers))
            candidates.append((float(np.mean(scores)), top))
    if not candidates:
        raise ValueError("Could not find a full board. Use an uncropped, unzoomed dark-theme screenshot, or enter the board manually.")
    _, top = max(candidates)
    # Rack: a horizontal run of large pale tiles below the board.
    pale = (a.min(axis=2) > 145)
    rack_rows = pale.mean(axis=1) > .5
    rack_candidates = [(s,e) for s,e in runs(rack_rows) if s > top+w and e-s > w*.04]
    rack_box = None
    if rack_candidates:
        start,end = max(rack_candidates, key=lambda x:x[1]-x[0])
        bands = runs(pale[start+int((end-start)*.97)])
        bands = [(x,y) for x,y in bands if y-x > w*.075]
        if 1 <= len(bands) <= 7:
            rack_box = [(x,start,y,end) for x,y in bands]
    return (0, top, w, top+w), rack_box

def read_tiles(paths):
    helper = ROOT / "build/vision-ocr"
    if helper.exists():
        result = subprocess.run([str(helper)], input=json.dumps([str(p) for p in paths]), text=True, encoding="utf-8", capture_output=True, timeout=90)
        if result.returncode:
            raise ValueError("The local OCR helper failed: " + result.stderr[:300])
        return json.loads(result.stdout)
    if shutil.which("tesseract"):
        results = []
        for path in paths:
            result = subprocess.run(["tesseract", str(path), "stdout", "-l", "swe", "--psm", "10"], capture_output=True, text=True, encoding="utf-8", timeout=5)
            if result.returncode:
                raise ValueError("Tesseract failed. Install the Swedish (swe) language data.")
            results.append([{"text":result.stdout.strip(), "confidence":.5}])
        return results
    raise ValueError("OCR is not installed. Run scripts/setup.sh (macOS), or install Tesseract with Swedish language data.")

def recognize(data):
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Please upload a valid PNG, JPEG or WebP screenshot.") from exc
    if image.width < 300 or image.height < image.width or image.width * image.height > 20_000_000:
        raise ValueError("Use a portrait screenshot, at least 300 pixels wide and under 20 megapixels.")
    if image.width > 1200:
        image = image.resize((1200, round(image.height * 1200/image.width)))
    board_box, rack_boxes = detect_geometry(image)
    left,top,right,bottom = board_box
    cell = (right-left)/15
    array = np.asarray(image)
    board = [["."]*15 for _ in range(15)]
    bonuses = standard_bonuses()
    specs = []
    # Color references from the classic dark board; only empty visible bonuses are read.
    colors = {"TL":np.array([35,100,137]), "TW":np.array([147,40,48]), "DL":np.array([107,144,78]), "DW":np.array([199,114,7])}
    for r in range(15):
        for c in range(15):
            x,y = left+c*cell, top+r*cell
            crop = array[int(y+cell*.12):int(y+cell*.88), int(x+cell*.12):int(x+cell*.88)]
            # Pale tiles and yellow last-move tiles both have bright red/green channels.
            bright = (crop[:,:,0]>165) & (crop[:,:,1]>165)
            if bright.mean() > .45:
                specs.append(("board",r,c,(x,y,x+cell,y+cell)))
            else:
                color = np.median(crop.reshape(-1,3),axis=0)
                nearest = min(colors,key=lambda k:np.linalg.norm(color-colors[k]))
                bonuses[r][c] = nearest if np.linalg.norm(color-colors[nearest])<65 else ""
    for i,box in enumerate(rack_boxes or []):
        specs.append(("rack",0,i,box))
    if not specs:
        raise ValueError("No tiles found. Check the screenshot or enter a position manually.")
    uncertain = []
    rack = ["?"]*len(rack_boxes or [])
    with tempfile.TemporaryDirectory(prefix="feud-ocr-") as directory:
        paths = []
        template_results = []
        for i,(_,_,_,box) in enumerate(specs):
            x,y,x2,y2 = box; w,h=x2-x,y2-y
            # Exclude the small value in the upper-right, retaining Å/Ä/Ö marks.
            tile = image.crop((round(x+w*.12),round(y+h*.08),round(x+w*.73),round(y2-h*.12)))
            char,confidence=recognize_glyph(tile)
            template_results.append([{"text":char,"confidence":confidence}])
            gray = np.asarray(tile.convert("L"))
            tile = Image.fromarray(np.where(gray<100,0,255).astype("uint8"))
            tile = tile.resize((round(tile.width*4),round(tile.height*4)))
            tile = ImageOps.expand(tile, border=40, fill=255)
            path=Path(directory)/f"{i}.png"; tile.save(path); paths.append(path)
        # The known tile font is much more reliable for isolated glyphs than text OCR.
        # Optional system OCR is only a fallback for poorly matching fonts/crops.
        recognized = template_results
        fallback_indices=[i for i,candidates in enumerate(recognized) if candidates[0]['confidence']<.6]
        if fallback_indices and ((ROOT/'build/vision-ocr').exists() or shutil.which('tesseract')):
            fallback=read_tiles([paths[i] for i in fallback_indices])
            for i,candidates in zip(fallback_indices,fallback):
                if candidates:
                    recognized[i]=candidates
    for (kind,r,c,_), candidates in zip(specs,recognized):
        choices = []
        for candidate in candidates:
            text = candidate["text"].upper().strip().replace("0","O").replace("1","I").replace("|","I")
            letters = "".join(ch for ch in text if ch in ALPHABET)
            if len(letters)==1:
                choices.append((letters,float(candidate["confidence"])))
        char, confidence = choices[0] if choices else ("?",0)
        if kind=="board": board[r][c]=char
        else: rack[c]=char
        if confidence<.85 or not choices:
            uncertain.append({"kind":kind,"row":r,"col":c,"letter":char,"confidence":confidence})
    warnings = ["Review every tile before solving. OCR cannot reliably identify zero-point blanks; enter those board letters in lowercase."]
    if not rack_boxes:
        warnings.append("Rack not found. Enter your tiles manually.")
    # Hidden premiums cannot be inferred for a random board. Their values are irrelevant
    # for existing tiles, but the UI must not claim they were observed.
    return {"board":["".join(row) for row in board], "rack":"".join(rack), "bonuses":bonuses,
            "uncertain":uncertain, "warnings":warnings, "board_box":[int(v) for v in board_box]}
