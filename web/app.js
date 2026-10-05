const $ = (id) => document.getElementById(id);
const letters = 'ABCDEFGHIJKLMNOPRSTUVXYZÅÄÖ';
let position = {board: Array(15).fill('.'.repeat(15)), rack: '', bonuses: Array.from({length:15},()=>Array(15).fill(''))};
let points = {}, uncertain = new Set(), moves = [], selected = null, busy = false, imageURL = null, defaultBonuses = position.bonuses;
const cells = [];
const emptyResults = $('results').innerHTML;
const mobileLayout = window.matchMedia('(max-width: 650px)');
let mobileView = 'upload', hasResults = false;

function setMobileView(view) {
  if(view==='moves' && !hasResults)return;
  mobileView=view;
  document.body.dataset.mobileView=view;
  document.querySelectorAll('.mobile-nav button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));
  if(mobileLayout.matches) {
    document.activeElement?.blur();
    document.querySelector('.workspace').scrollTop=0;
  }
  render();
}
function updateMoveNavigation() {
  const index=selected ? moves.indexOf(selected) : -1;
  $('preview-word').textContent=selected?.word || (moves.length ? 'Choose a move' : 'No moves found');
  $('preview-description').textContent=selected ? `${index+1} / ${moves.length} · ${String.fromCharCode(65+selected.col)}${selected.row+1} ${selected.direction==='horizontal'?'→':'↓'}` : (moves.length ? 'Tap a result to preview its placement.' : 'Check your board or try a different rack.');
  $('preview-score').textContent=selected ? `${selected.score} pt` : '';
  $('previous-move').disabled=busy || index<=0;
  $('next-move').disabled=busy || index<0 || index>=moves.length-1;
  $('mobile-move-count').textContent=hasResults ? String(moves.length) : '';
  document.querySelector('[data-view="moves"]').disabled=busy || !hasResults;
}
function selectMove(index, scrollToResult=false) {
  selected=moves[index] || null;
  document.querySelectorAll('.move').forEach((button,i)=>{
    button.classList.toggle('selected',i===index);
    button.setAttribute('aria-pressed',String(i===index));
    if(i===index && scrollToResult) {
      const list=$('results');
      const top=button.getBoundingClientRect().top-list.getBoundingClientRect().top+list.scrollTop;
      list.scrollTop=Math.max(0,top-(list.clientHeight-button.offsetHeight)/2);
    }
  });
  render();
}

function message(text, error = false) {
  $('message-title').textContent = text.split('. ')[0];
  $('message-detail').textContent = text;
  $('message').hidden = !text;
  $('message').open = error;
  $('message').classList.toggle('error', error);
}
function setBusy(value, action='') {
  busy=value; document.body.classList.toggle('busy',value);
  for(const id of ['solve','mobile-solve','example','clear','file','import','rack','edit-bonuses','choose-photo','paste-image']) $(id).disabled=value;
  $('paste-target').contentEditable=String(!value);
  cells.flat().forEach(({input})=>input.disabled=value);
  $('solve').textContent=value ? action : 'Find best moves ↗';
  $('mobile-solve').textContent=value ? action : 'Find best moves ↗';
  document.querySelectorAll('.mobile-nav button').forEach(button=>button.disabled=value || (button.dataset.view==='moves'&&!hasResults));
  updateMoveNavigation();
}
async function request(url, options={}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if(!response.ok) {
    const detail=Array.isArray(data.detail) ? data.detail.map(e=>e.msg).join(' ') : data.detail;
    throw new Error(detail || 'The request could not be completed.');
  }
  return data;
}
function invalidate() {
  selected=null; moves=[]; hasResults=false; $('results').innerHTML=emptyResults;
  if(mobileView==='moves')setMobileView('board');
  updateMoveNavigation();
  $('move-count').textContent='—'; $('results-summary').textContent='Position changed. Find moves to update results.';
}
function setSquare(row,col,char) {
  position.board[row]=position.board[row].slice(0,col)+char+position.board[row].slice(col+1);
}
function updateRack() {
  position.rack=$('rack').value.toUpperCase().replace(/\s/g,'');
  $('rack-count').textContent=`${position.rack.length} / 7`;
}
function render() {
  const previewTiles=mobileLayout.matches && mobileView!=='moves' ? [] : selected?.tiles || [];
  const overlay=new Map(previewTiles.map(tile=>[`${tile.row},${tile.col}`,tile]));
  let count=0;
  for(let r=0;r<15;r++) for(let c=0;c<15;c++) {
    const {cell,input,premium,value}=cells[r][c];
    const original=position.board[r][c], tile=overlay.get(`${r},${c}`);
    const char=tile ? (tile.blank ? tile.letter.toLowerCase() : tile.letter) : original;
    const occupied=char!=='.'; if(original!=='.') count++;
    cell.className=`cell ${position.bonuses[r][c]}${occupied?' occupied':''}${tile?' new':''}${uncertain.has(`${r},${c}`)?' uncertain':''}${occupied&&char!==char.toUpperCase()?' blank':''}${$('edit-bonuses').checked?' bonus-edit':''}`;
    input.value=occupied?char:'';
    const previewOnly=mobileLayout.matches && mobileView==='moves';
    input.readOnly=$('edit-bonuses').checked || previewOnly;
    input.tabIndex=previewOnly ? -1 : 0;
    premium.textContent=occupied?'':position.bonuses[r][c] || (r===7&&c===7?'✦':'');
    value.textContent=occupied && char!=='?' ? (char===char.toUpperCase()?points[char]??'':0) : '';
    input.setAttribute('aria-label',`${String.fromCharCode(65+c)}${r+1}: ${occupied?char:position.bonuses[r][c] || 'empty'}`);
  }
  $('board-summary').textContent=count?`${count} tiles on the board${uncertain.size?` · ${uncertain.size} to check`:''}`:'An empty board. A fresh start.';
  $('clear-preview').hidden=!selected;
  updateMoveNavigation();
}
function buildBoard() {
  for(let c=0;c<15;c++) { const span=document.createElement('span'); span.textContent=String.fromCharCode(65+c); document.querySelector('.column-labels').append(span); }
  for(let r=0;r<15;r++) {
    const label=document.createElement('span'); label.textContent=r+1; document.querySelector('.row-labels').append(label); cells[r]=[];
    for(let c=0;c<15;c++) {
      const cell=document.createElement('div'), input=document.createElement('input'), premium=document.createElement('span'), value=document.createElement('span');
      input.maxLength=1; input.autocomplete='off'; input.spellcheck=false; input.type='text'; input.autocapitalize='off';
      premium.className='premium'; value.className='value'; cell.append(premium,input,value); $('board').append(cell); cells[r][c]={cell,input,premium,value};
      input.addEventListener('focus',()=>{if(mobileLayout.matches&&mobileView==='moves'){input.blur();return;}if(selected){selected=null;render();} input.select();});
      input.addEventListener('input',()=>{
        const char=input.value.slice(-1); if(char && char!=='.' && !letters.includes(char.toUpperCase())){render();return;}
        setSquare(r,c,char||'.'); uncertain.delete(`${r},${c}`); invalidate(); render();
      });
      input.addEventListener('keydown',event=>{
        const delta={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]}[event.key];
        if(delta){event.preventDefault(); cells[Math.max(0,Math.min(14,r+delta[0]))][Math.max(0,Math.min(14,c+delta[1]))].input.focus();}
      });
      input.addEventListener('click',()=>{
        if(!$('edit-bonuses').checked||busy)return;
        const options=['','DL','TL','DW','TW']; position.bonuses[r][c]=options[(options.indexOf(position.bonuses[r][c])+1)%options.length]; invalidate();render();
      });
    }
  }
  render();
}
function loadPosition(data) {
  if(!Array.isArray(data.board)||data.board.length!==15||data.board.some(row=>typeof row!=='string'||row.length!==15||[...row].some(c=>c!=='.'&&c!=='?'&&!letters.includes(c.toUpperCase()))))throw new Error('Position must contain 15 board rows of 15 letters or dots.');
  if(typeof data.rack!=='string'||data.rack.length>7||[...data.rack].some(c=>!letters.includes(c.toUpperCase())&&c!=='?'))throw new Error('Invalid rack in position.');
  const bonuses=data.bonuses || defaultBonuses;
  if(!Array.isArray(bonuses)||bonuses.length!==15||bonuses.some(row=>!Array.isArray(row)||row.length!==15||row.some(c=>!['','DL','TL','DW','TW'].includes(c))))throw new Error('Invalid bonus grid.');
  position={board:[...data.board],rack:data.rack,bonuses:bonuses.map(row=>[...row])};
  uncertain=new Set((data.uncertain||[]).filter(t=>t.kind==='board').map(t=>`${t.row},${t.col}`));
  $('rack').value=position.rack;updateRack();invalidate();render();
  setMobileView('board');
}
function showSource(src) { $('source-image').hidden=false;$('preview').hidden=false;$('preview').src=src;$('toggle-image').textContent='Hide'; }
async function recognize(file=null) {
  if(busy)return;
  if(file&&file.size>12*1024*1024){message('Screenshot must be smaller than 12 MB.',true);return;}
  $('upload-feedback').hidden=true;
  $('paste-target').replaceChildren();
  $('manual-paste').hidden=true;
  setBusy(true,file?'Reading screenshot…':'Loading example…'); message(file?'Reading the board and rack locally. This can take a few seconds.':'Loading the example position.');
  try {
    let data;
    if(file) {
      const form=new FormData();form.append('image',file);
      if(imageURL)URL.revokeObjectURL(imageURL);imageURL=URL.createObjectURL(file);showSource(imageURL);
      data=await request('/api/recognize',{method:'POST',body:form});
    } else {$('source-image').hidden=true;$('preview').removeAttribute('src');data=await request('/api/example',{method:'POST'});}
    loadPosition(data);
    message(`${file?'Screenshot read.':'Example position loaded.'} ${data.warnings.join(' ')}${data.uncertain.length?` ${data.uncertain.length} tiles need a closer look (including rack tiles).`:''}`);
  } catch(error){message(error.message,true);} finally{setBusy(false);}
}
function renderMoves(data) {
  moves=data.moves; hasResults=true; $('results').replaceChildren();
  $('move-count').textContent=data.total_moves.toLocaleString();
  $('results-summary').textContent=`${data.total_moves.toLocaleString()} legal placements · ${Math.round(data.search_ms)} ms search · ${data.dictionary_words.toLocaleString()} words`;
  if(!moves.length){selected=null;const p=document.createElement('p');p.className='edit-help';p.textContent='No moves found in this dictionary. Check the recognized tiles and rack, or try a more complete word list.';$('results').append(p);setMobileView('moves');return;}
  for(const [i,move] of moves.entries()) {
    const button=document.createElement('button');button.className='move';
    const rank=document.createElement('span');rank.className='rank';rank.textContent=String(i+1).padStart(2,'0');
    const title=document.createElement('span');title.className='word';title.textContent=move.word;
    const detail=document.createElement('span');detail.className='position';detail.textContent=`${String.fromCharCode(65+move.col)}${move.row+1} ${move.direction==='horizontal'?'→':'↓'} · ${move.tiles.length} tiles${move.bingo?' · +40 bonus':''}`;title.append(detail);
    const score=document.createElement('span');score.className='score';score.textContent=move.score;const label=document.createElement('small');label.textContent='POINTS';score.append(label);
    button.append(rank,title,score);button.addEventListener('click',()=>selectMove(i));$('results').append(button);
  }
  selectMove(0);
  setMobileView('moves');
  $('results').scrollTop=0;
}
$('solve').addEventListener('click',async()=>{
  if(busy)return;updateRack();
  if(!position.rack||[...position.rack].some(c=>!letters.includes(c)&&c!=='?')){message('Enter 1–7 Swedish letters in your rack. Use ? for a blank.',true);$('rack').focus();return;}
  if(position.board.some(row=>row.includes('?'))){message('Correct the unrecognized ? squares on the board before solving.',true);return;}
  setBusy(true,'Searching…');message('');
  try{const data=await request('/api/solve',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(position)});renderMoves(data);}catch(error){message(error.message,true);}finally{setBusy(false);}
});
$('rack').addEventListener('input',()=>{updateRack();invalidate();render();});
$('mobile-solve').addEventListener('click',()=>$('solve').click());
$('example').addEventListener('click',()=>recognize());
$('choose-photo').addEventListener('click',()=>$('file').click());
$('file').addEventListener('change',event=>{if(event.target.files[0])recognize(event.target.files[0]);event.target.value='';});
function uploadFeedback(text) {
  $('upload-feedback').textContent=text;
  $('upload-feedback').hidden=!text;
}
function manualPaste(text='') {
  setMobileView('upload');
  $('manual-paste').hidden=false;
  uploadFeedback(text);
  $('paste-target').focus();
}
$('paste-image').addEventListener('click',async()=>{
  if(busy)return;
  if(!window.isSecureContext || !navigator.clipboard?.read) {
    manualPaste('Your browser needs you to paste manually on this connection.');
    return;
  }
  try {
    // Read directly in the tap handler: Safari requires the user activation.
    const items=await navigator.clipboard.read();
    for(const item of items) {
      const type=item.types.find(type=>['image/png','image/jpeg','image/webp'].includes(type));
      if(type) {
        const blob=await item.getType(type);
        await recognize(new File([blob],`clipboard.${type.split('/')[1]}`,{type}));
        return;
      }
    }
    uploadFeedback('No screenshot found in the clipboard. Copy an image first, or choose one from Photos.');
  } catch(error) {
    manualPaste('Clipboard access wasn’t available. Try pasting below, or choose from Photos.');
  }
});
document.addEventListener('paste',event=>{
  const data=event.clipboardData;
  const item=[...(data?.items || [])].find(item=>item.kind==='file' && item.type.startsWith('image/'));
  const file=item?.getAsFile() || [...(data?.files || [])].find(file=>file.type.startsWith('image/'));
  if(file) {
    event.preventDefault();
    recognize(file);
  } else if(event.target===$('paste-target') || $('paste-target').contains(event.target)) {
    // Never insert untrusted clipboard HTML into the editable paste target.
    event.preventDefault();
    uploadFeedback('That clipboard content isn’t an image. Copy the screenshot itself, or choose it from Photos.');
  }
});
$('paste-target').addEventListener('input',()=>$('paste-target').replaceChildren());
for(const event of ['dragenter','dragover'])$('dropzone').addEventListener(event,e=>{e.preventDefault();$('dropzone').classList.add('dragover');});
for(const event of ['dragleave','drop'])$('dropzone').addEventListener(event,e=>{e.preventDefault();$('dropzone').classList.remove('dragover');});
$('dropzone').addEventListener('drop',e=>{if(e.dataTransfer.files[0])recognize(e.dataTransfer.files[0]);});
$('edit-bonuses').addEventListener('change',render);
$('clear-preview').addEventListener('click',()=>{selected=null;render();document.querySelectorAll('.move').forEach(b=>b.classList.remove('selected'));});
$('clear').addEventListener('click',()=>{position.board=Array(15).fill('.'.repeat(15));uncertain.clear();invalidate();render();message('Board cleared. Your rack and bonus layout are unchanged.');});
$('toggle-image').addEventListener('click',()=>{$('preview').hidden=!$('preview').hidden;$('toggle-image').textContent=$('preview').hidden?'Show':'Hide';});
$('export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(position,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='position.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('import').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>100000)throw new Error('Position file is too large.');loadPosition(JSON.parse(await file.text()));message('Position imported.');}catch(error){message(error.message,true);}finally{event.target.value='';}});
document.querySelectorAll('.mobile-nav button').forEach(button=>button.addEventListener('click',()=>setMobileView(button.dataset.view)));
$('enter-manually').addEventListener('click',()=>setMobileView('board'));
$('previous-move').addEventListener('click',()=>selectMove(moves.indexOf(selected)-1,true));
$('next-move').addEventListener('click',()=>selectMove(moves.indexOf(selected)+1,true));
mobileLayout.addEventListener('change',()=>render());
buildBoard();
request('/api/health').then(data=>{points=data.points;defaultBonuses=data.bonuses;position.bonuses=data.bonuses.map(row=>[...row]);$('engine-status').textContent=data.engine_ready&&data.dictionary_ready?'Engine ready':'Setup required';$('dictionary-name').textContent=data.dictionary_kind;if(data.dictionary_kind==='Custom dictionary'){$('dictionary-disclaimer').textContent='Using your configured word list. Word acceptance depends on its coverage.';document.querySelector('.dictionary-note p').textContent='Using your configured word list. Word acceptance depends on its coverage.';}render();}).catch(()=>{$('engine-status').textContent='Backend unavailable';message('Could not connect to the backend. Start scripts/run.sh.',true);});
