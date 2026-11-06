// wa_business.js · gated helpers for WhatsApp Business Web in Chrome (proven: paste, hash gate, own file input for photos).
// Set before injecting:
//   window.__WA_ACCOUNT_DIGITS = '<country code + number of the sending account>';
//   window.__WA_OURS = /<words that only your own earlier outreach contains>/i;   (optional)
// Nothing here clicks Send. Sending is a separate real click on the Send button after the gates pass.
window.__waSleep = ms => new Promise(r => setTimeout(r, ms));
window.__waSha = async (t, n) => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(t)))].map(b => b.toString(16).padStart(2, '0')).join('').slice(0, n || 12);
window.__waEd = () => document.querySelector('footer div[contenteditable="true"]');
// Read the composer the way WhatsApp renders it: one <p> per line, emoji as <img data-plain-text>.
window.__waRead = () => {
  const ed = window.__waEd(); if (!ed) return null;
  const ps = [...ed.querySelectorAll('p')];
  const one = p => { let s = ''; const walk = n => { if (n.nodeType === 3) s += n.textContent; else if (n.tagName === 'IMG') s += n.getAttribute('data-plain-text') || n.alt || ''; else n.childNodes.forEach(walk); }; p.childNodes.forEach(walk); return s; };
  return (ps.length ? ps : [ed]).map(one).join('\n');
};
// Before pasting: the right account, the right chat, no dialog, no earlier message of ours, an empty composer.
window.__waGate = (digits, name) => {
  const want = String(window.__WA_ACCOUNT_DIGITS || '').replace(/\D/g, '');
  if (!want) throw new Error('SET window.__WA_ACCOUNT_DIGITS FIRST');
  const wid = (localStorage.getItem('last-wid-md') || '').replace(/\D/g, '');
  if (!wid.startsWith(want)) throw new Error('WRONG ACCOUNT ' + wid.slice(0, 12));
  if (document.querySelector('[role="dialog"]')) throw new Error('A DIALOG IS OPEN');
  const main = document.querySelector('#main'); if (!main) throw new Error('NO CHAT OPEN');
  const head = (main.querySelector('header') || {}).innerText || '';
  const d = String(digits || '').replace(/\D/g, '');
  const okNum = d.length >= 7 && head.replace(/\D/g, '').includes(d.slice(-10));
  const okName = !!name && head.toLowerCase().includes(String(name).toLowerCase());
  if (!(okNum || okName)) throw new Error('WRONG CHAT: ' + head.split('\n')[0]);
  if (window.__WA_OURS && window.__WA_OURS.test(main.innerText)) throw new Error('THIS CHAT ALREADY HAS OUR MESSAGE');
  if (!window.__waEd()) throw new Error('NO COMPOSER');
  if ((window.__waRead() || '').trim()) throw new Error('COMPOSER NOT EMPTY');
  return 'gate ok: ' + head.split('\n')[0];
};
// Paste the approved text and return the composer's sha12 for comparison with the draft's hash.
window.__waPaste = async text => {
  const ed = window.__waEd(); if (!ed) throw new Error('NO COMPOSER');
  ed.focus();
  const dt = new DataTransfer(); dt.setData('text/plain', text);
  ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  await window.__waSleep(700);
  return await window.__waSha(window.__waRead());
};
// The link card: look inside the card itself (the composer's emoji are images too).
window.__waCard = () => {
  const c = document.querySelector('#main [aria-label="Cancel"]');
  if (!c) return {card: false, image: false};
  const m = (window.__waRead() || '').match(/https?:\/\/([^\/\s]+)/);
  const host = m ? m[1].replace(/^www\./, '') : '';
  let box = c.parentElement;
  for (let i = 0; box && i < 10; i++, box = box.parentElement) { if (host && (box.innerText || '').includes(host)) break; }
  if (!box) box = c.parentElement;
  const image = !!box.querySelector('img:not([data-plain-text]), [style*="background-image"]');
  return {card: true, image, host};
};
// A card without an image only repeats the URL: drop it, keep cards with a picture.
window.__waDropBareCard = async () => {
  const s = window.__waCard();
  if (s.card && !s.image) { document.querySelector('#main [aria-label="Cancel"]').click(); await window.__waSleep(500); }
  return window.__waCard();
};
// Label and centre of the Send button; require the expected label before the real click (click it by ref from find).
window.__waSendRect = () => {
  const b = document.querySelector('[aria-label^="Send"][aria-label*="selected"]') || document.querySelector('footer [aria-label="Send"]');
  if (!b) return {label: null};
  const r = b.getBoundingClientRect(), x = r.x + r.width / 2, y = r.y + r.height / 2;
  const under = document.elementFromPoint(x, y);
  const u = under && under.closest('[aria-label]');
  return {label: b.getAttribute('aria-label'), x: Math.round(x), y: Math.round(y), under: u ? u.getAttribute('aria-label') : null};
};
// Photos: our own file input (the attach menu opens a macOS picker), then paste its files into the composer.
window.__waPhotoInput = () => {
  const old = document.getElementById('bo-photos'); if (old) old.remove();
  const inp = document.createElement('input');
  inp.type = 'file'; inp.multiple = true; inp.accept = 'image/*'; inp.id = 'bo-photos';
  inp.setAttribute('aria-label', 'bo photos upload');
  inp.style.cssText = 'position:fixed;left:0;top:0;width:10px;height:10px;opacity:0.01;z-index:2147483647';
  document.body.appendChild(inp);
  return 'ready: find "bo photos upload", then file_upload';
};
window.__waPastePhotos = async n => {
  const inp = document.getElementById('bo-photos');
  if (!inp || inp.files.length !== n) throw new Error('PHOTOS NOT LOADED: ' + (inp ? inp.files.length : 0) + ' of ' + n);
  const ed = window.__waEd(); if (!ed) throw new Error('NO COMPOSER');
  ed.focus();
  const dt = new DataTransfer(); [...inp.files].forEach(f => dt.items.add(f));
  ed.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
  for (let k = 0; k < 60; k++) {
    await window.__waSleep(250);
    const b = document.querySelector('[aria-label^="Send"][aria-label*="selected"]');
    if (b) return 'media editor open: ' + b.getAttribute('aria-label');
  }
  throw new Error('MEDIA EDITOR DID NOT OPEN');
};
'wa_business helpers ready on ' + location.host;
