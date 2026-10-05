"""Check trie generation against an independent, exhaustive word-placement oracle."""
from collections import Counter
from itertools import product
import json
from pathlib import Path
import random
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
VALUES=dict(zip("ABCDEFGHIJKLMNOPRSTUVXYZÅÄÖ",[1,3,8,1,1,3,2,3,1,7,3,2,3,1,2,4,1,1,1,4,3,8,7,8,4,4,4]))

def position(rack, tiles=()):
    grid=[list('.'*15) for _ in range(15)]
    for r,c,char in tiles: grid[r][c]=char
    return {'board':[''.join(row) for row in grid], 'rack':rack, 'bonuses':[['']*15 for _ in range(15)]}

def run_engine(tmp_path, pos, words):
    dictionary=tmp_path/'words.txt';dictionary.write_text('\n'.join(words)+'\n')
    result=subprocess.run([str(ROOT/'build/feudsolver'),'--dictionary',str(dictionary),'--limit','1000'],input=json.dumps(pos),text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout)

def key(tiles):
    return tuple(sorted((t['row'],t['col'],t['letter'],t['blank']) for t in tiles))

def oracle(pos, words):
    board=pos['board'];bonuses=pos['bonuses'];rack=Counter(pos['rack']);found={}
    inside=lambda r,c:0<=r<15 and 0<=c<15
    occupied=lambda r,c:inside(r,c) and board[r][c]!='.'
    value=lambda char:VALUES[char] if char.isupper() else 0
    nonempty=any(char!='.' for row in board for char in row)
    for word in words:
        for dr,dc in [(0,1),(1,0)]:
            for r in range(15):
                for c in range(15):
                    if not inside(r+dr*(len(word)-1),c+dc*(len(word)-1)):continue
                    if occupied(r-dr,c-dc) or occupied(r+dr*len(word),c+dc*len(word)):continue
                    squares=[(r+dr*i,c+dc*i,ch) for i,ch in enumerate(word)]
                    if any(occupied(y,x) and board[y][x].upper()!=ch for y,x,ch in squares):continue
                    new=[(y,x,ch) for y,x,ch in squares if not occupied(y,x)]
                    if not new or len(new)>len(pos['rack']):continue
                    connected=any(occupied(y+dy,x+dx) for y,x,_ in new for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)])
                    if nonempty and not connected:continue
                    if not nonempty and not any((y,x)==(7,7) for y,x,_ in new):continue
                    for blank_bits in product([False,True],repeat=len(new)):
                        used=Counter('?' if blank else ch for (_,_,ch),blank in zip(new,blank_bits))
                        if used-rack:continue
                        blanks={(y,x):blank for (y,x,_),blank in zip(new,blank_bits)}
                        total=0;multiplier=1;cross_total=0;valid=True
                        for y,x,ch in squares:
                            if occupied(y,x):total+=value(board[y][x]);continue
                            bonus=bonuses[y][x];lm={'DL':2,'TL':3}.get(bonus,1);wm={'DW':2,'TW':3}.get(bonus,1)
                            v=0 if blanks[y,x] else VALUES[ch]
                            total+=v*lm;multiplier*=wm
                            prefix='';suffix='';cross_points=0
                            yy,xx=y-dc,x-dr
                            while occupied(yy,xx):prefix=board[yy][xx].upper()+prefix;cross_points+=value(board[yy][xx]);yy-=dc;xx-=dr
                            yy,xx=y+dc,x+dr
                            while occupied(yy,xx):suffix+=board[yy][xx].upper();cross_points+=value(board[yy][xx]);yy+=dc;xx+=dr
                            if prefix or suffix:
                                if prefix+ch+suffix not in words:valid=False;break
                                cross_total+=(cross_points+v*lm)*wm
                        if valid:
                            k=tuple(sorted((y,x,ch,blank) for (y,x,ch),blank in zip(new,blank_bits)))
                            found[k]=total*multiplier+cross_total+(40 if len(new)==7 else 0)
    return found

@pytest.mark.parametrize('seed',range(8))
def test_all_moves_and_scores_match_oracle(tmp_path,seed):
    rng=random.Random(seed)
    words={'AB','BA','AA','BB','ABA','BAB','AAB','BAA','ABB','BBA'}
    tiles=[] if seed==0 else [(7,7,'A'),(7,8,'B')]
    if seed>3:tiles += [(6,7,'b'),(6,8,'A')]
    pos=position('AB?' if seed%2 else 'AAB',tiles)
    for r in range(4,11):
        for c in range(4,11):pos['bonuses'][r][c]=rng.choice(['','','','DL','TL','DW','TW'])
    expected=oracle(pos,words);result=run_engine(tmp_path,pos,words)
    actual={key(move['tiles']):move['score'] for move in result['moves']}
    assert actual==expected
    assert result['total_moves']==len(expected)
    assert [m['score'] for m in result['moves']]==sorted((m['score'] for m in result['moves']),reverse=True)

def test_swedish_letters_and_seven_tile_bonus(tmp_path):
    result=run_engine(tmp_path,position('SMÖRGÅS'),{'SMÖRGÅS'})
    assert result['moves']
    assert all(m['score']==56 and m['bingo'] for m in result['moves'])
    assert all(len(m['tiles'])==7 for m in result['moves'])

def test_repeated_letters_cannot_exceed_rack(tmp_path):
    assert not run_engine(tmp_path,position('AB'),{'AAA'})['moves']

def test_existing_blank_does_not_score_or_reuse_bonus(tmp_path):
    pos=position('T',[(7,7,'å')]);pos['bonuses'][7][7]='TW'
    moves=run_engine(tmp_path,pos,{'ÅT'})['moves']
    assert moves and all(m['score']==1 for m in moves)

def test_board_edge_and_word_extension(tmp_path):
    pos=position('T',[(0,13,'Å')])
    moves=run_engine(tmp_path,pos,{'ÅT'})['moves']
    assert any(m['tiles']==[{'row':0,'col':14,'letter':'T','blank':False}] for m in moves)

def test_invalid_positions_fail_cleanly(tmp_path):
    dictionary=tmp_path/'words.txt';dictionary.write_text('ÅT\n')
    result=subprocess.run([str(ROOT/'build/feudsolver'),'--dictionary',str(dictionary)],input='{"board":[],"rack":"A"}',text=True,capture_output=True)
    assert result.returncode==1
    assert 'error' in json.loads(result.stderr)
