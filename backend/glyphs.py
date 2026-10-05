"""Template OCR for the classic Wordfeud typeface, independent of board contents."""
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .board import ALPHABET
from .paths import ROOT

FONT = ROOT / "data/fonts/DroidSansMono.ttf"

def normalize(mask):
    # Discard score digits and edge noise, retaining the glyph and its diacritics.
    remaining=mask.copy(); components=[]
    for sy,sx in zip(*np.where(mask)):
        if not remaining[sy,sx]:continue
        stack=[(int(sy),int(sx))]; remaining[sy,sx]=False; component=[]
        while stack:
            y,x=stack.pop();component.append((y,x))
            for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if 0<=yy<mask.shape[0] and 0<=xx<mask.shape[1] and remaining[yy,xx]:
                    remaining[yy,xx]=False;stack.append((yy,xx))
        components.append(component)
    if not components:return None
    main=max(components,key=len); ys,xs=zip(*main)
    cleaned=np.zeros_like(mask)
    for component in components:
        cy,cx=zip(*component)
        if component is main or (max(cy)<min(ys) and min(xs)<=sum(cx)/len(cx)<=max(xs) and len(component)>=max(2,len(main)*.02)):
            for y,x in component:cleaned[y,x]=True
    mask=cleaned
    y,x = np.where(mask)
    if len(x)<4:
        return None
    mask=mask[y.min():y.max()+1,x.min():x.max()+1]
    return np.asarray(Image.fromarray((mask*255).astype('uint8')).resize((32,48), Image.Resampling.BILINEAR))/255.0

@lru_cache(maxsize=1)
def templates():
    result=[]
    for size in (45,60,90):
        font=ImageFont.truetype(str(FONT),size)
        for letter in ALPHABET:
            image=Image.new('L',(150,150),255)
            ImageDraw.Draw(image).text((15,5),letter,font=font,fill=0)
            result.append((letter,normalize(np.asarray(image)<100)))
    return result

def recognize_glyph(image):
    glyph=normalize(np.asarray(image.convert('L'))<100)
    if glyph is None:
        return '?', 0.0
    scores={}
    for letter,template in templates():
        distance=float(np.mean(np.abs(glyph-template)))
        scores[letter]=min(distance,scores.get(letter,1))
    ranked=sorted(scores,key=scores.get)
    best,second=ranked[:2]
    distance=scores[best]; margin=scores[second]-distance
    confidence=max(0.0,min(1.0,1-distance*2.5))
    if margin<.025:
        confidence=min(confidence,.65)
    return best,confidence
