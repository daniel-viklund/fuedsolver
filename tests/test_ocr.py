import io
import json
from pathlib import Path
from PIL import Image
import pytest
from backend.ocr import recognize
from backend.board import standard_bonuses

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('width',[1206,900,600])
def test_provided_screenshot_matches_human_transcription(width):
    source=ROOT/'IMG_3527.PNG'
    if not source.exists():pytest.skip('User screenshot not present')
    expected=json.loads((ROOT/'examples/screenshot.json').read_text(encoding='utf-8'))
    image=Image.open(source);image=image.resize((width,round(image.height*width/image.width)))
    data=io.BytesIO();image.save(data,format='PNG')
    actual=recognize(data.getvalue())
    assert actual['board']==expected['board']
    assert actual['rack']==expected['rack']
    standard=standard_bonuses()
    for r,row in enumerate(expected['board']):
        for c,char in enumerate(row):
            if char=='.':assert actual['bonuses'][r][c]==standard[r][c]
