// gmail_runner.js · gated Gmail web sender for an APPROVED list.
// Per row: open compose → To by insertText, focus the subject so it blurs into a chip → gate chip, subject, body →
// 3 s → re-gate → Send (dispatched events) → wait for "Message sent" → verify exactly one row in Sent.
// Setup, in one javascript_tool call each:
//   window.__ACCOUNT = 'you@company.com';   then inject this file;   then __dataInput()
//   find "bo send list upload" → file_upload the JSON [{"to", "s", "T"}] → await __load('<sha256 of the file>')
// Run: __chunk(0, 25), then poll __RUN and __col(0, 25) (read-only) every ~2 minutes. Any throw stops before the next compose.
// Keep this tab in front for the whole run. The runner paces itself at about 11 s per email; faster sends vanished.
window.__sleep = ms => new Promise(r => setTimeout(r, ms));
window.__vis = sel => [...document.querySelectorAll(sel)].filter(e => e.offsetParent !== null);
window.__SENT = window.__SENT || {}; window.__OK = window.__OK || {}; window.__STOP = false;
if (!window.__AFTER) { const d = new Date(); d.setHours(0, 0, 0, 0); window.__AFTER = Math.floor(d.getTime() / 1000); }  // Sent checks start at local midnight today
window.__e2008 = () => /#2008|system encountered a problem/i.test(document.body.innerText);
window.__banner = () => /could not be sent|Check your network/i.test(document.body.innerText);
window.__dataInput = () => {
  const old = document.getElementById('bo-data'); if (old) old.remove();
  const inp = document.createElement('input');
  inp.type = 'file'; inp.id = 'bo-data'; inp.accept = '.json,application/json';
  inp.setAttribute('aria-label', 'bo send list upload');
  inp.style.cssText = 'position:fixed;left:0;top:0;width:10px;height:10px;opacity:0.01;z-index:2147483647';
  document.body.appendChild(inp);
  return 'ready: find "bo send list upload", then file_upload the JSON';
};
// Load the list from the uploaded file (never retype it): byte hash, row shape, one row per address.
window.__load = async expectSha => {
  const inp = document.getElementById('bo-data');
  if (!inp || !inp.files.length) throw new Error('NO LIST FILE: run __dataInput(), then file_upload the JSON');
  const buf = await inp.files[0].arrayBuffer();
  const sha = [...new Uint8Array(await crypto.subtle.digest('SHA-256', buf))].map(b => b.toString(16).padStart(2, '0')).join('');
  if (expectSha && sha !== String(expectSha).toLowerCase()) throw new Error('LIST SHA MISMATCH ' + sha.slice(0, 12));
  const rows = JSON.parse(new TextDecoder().decode(buf));
  if (!Array.isArray(rows) || !rows.length) throw new Error('LIST EMPTY');
  const bad = rows.findIndex(r => !r || typeof r.to !== 'string' || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(r.to.trim()) || typeof r.s !== 'string' || !r.s || typeof r.T !== 'string' || !r.T);
  if (bad >= 0) throw new Error('BAD ROW ' + bad);
  const seen = new Set();
  const dup = rows.findIndex(r => { const k = r.to.trim().toLowerCase(); if (seen.has(k)) return true; seen.add(k); return false; });
  if (dup >= 0) throw new Error('SAME ADDRESS TWICE, ROW ' + dup);
  window.__D = rows.map(r => ({to: r.to.trim().toLowerCase(), s: r.s, T: r.T}));
  return {n: window.__D.length, sha12: sha.slice(0, 12), after: window.__AFTER};
};
window.__search = async q => {
  window.__vis('div[role="main"] tr.zA').forEach(r => r.setAttribute('data-bo-stale', '1'));
  location.hash = '#search/' + encodeURIComponent(q);
  await window.__sleep(1200);
  for (let k = 0; k < 64; k++) {
    if (window.__e2008()) throw new Error('GMAIL 2008');
    const box = document.querySelector('input[name="q"]');
    const main = window.__vis('div[role="main"]')[0];
    const rows = window.__vis('div[role="main"] tr.zA');
    const stale = rows.some(r => r.hasAttribute('data-bo-stale'));
    const subj = rows.map(r => ((r.querySelector('.bog') || {}).innerText || '').trim());
    if (box && box.value.trim() === q && main && !stale && (rows.length ? subj.every(s => s) : /No messages matched/i.test(main.innerText))) return {n: rows.length, subj};
    await window.__sleep(250);
  }
  return {n: -1, subj: []};
};
window.__prep = async i => {
  const d = window.__D[i];
  if (!window.__ACCOUNT) throw new Error('SET window.__ACCOUNT FIRST');
  for (let k = 0; k < 60 && window.__banner(); k++) await window.__sleep(500);
  if (window.__banner()) throw new Error('NETWORK BANNER STILL SHOWING');
  if (window.__e2008()) throw new Error('GMAIL 2008');
  for (let k = 0; k < 25 && !document.title.includes(window.__ACCOUNT); k++) await window.__sleep(200);
  if (!document.title.includes(window.__ACCOUNT)) throw new Error('WRONG ACCOUNT ' + document.title);
  if (window.__SENT[d.to]) throw new Error('ALREADY SENT THIS RUN ' + d.to);
  if (window.__vis('input[name="subjectbox"]').length) throw new Error('A COMPOSE IS ALREADY OPEN');
  location.hash = '#inbox?compose=new';
  for (let k = 0; k < 60; k++) {
    await window.__sleep(200);
    const s = window.__vis('input[name="subjectbox"]');
    if (s.length > 1) throw new Error('TWO COMPOSES');
    if (s.length === 1) {
      const to = window.__vis('input[aria-label="To recipients"]');
      if (to.length === 1) {
        const dlg = s[0].closest('[role="dialog"]');
        if (dlg && dlg.getBoundingClientRect().height < 300) throw new Error('COMPOSE MINIMIZED');
        to[0].focus();
        if (document.activeElement !== to[0]) throw new Error('TO FIELD NOT FOCUSED');
        return 'ready ' + i + ' ' + d.to;
      }
    }
  }
  throw new Error('COMPOSE DID NOT OPEN');
};
// Real chips only: suggestion dropdown entries also carry [email] and must not satisfy the gate.
window.__chips = dlg => {
  const a = [...new Set([...dlg.querySelectorAll('[email][data-hovercard-id]')]
    .filter(e => e.offsetParent !== null && !e.closest('[role=listbox],[role=option]'))
    .map(e => e.getAttribute('email').toLowerCase()))];
  if (a.length) return a;
  const box = [...dlg.querySelectorAll('div[aria-label="To"]')].filter(e => e.offsetParent !== null)[0];
  if (!box) return [];
  return [...new Set((box.innerText.match(/[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}/g) || []).map(x => x.toLowerCase()))];
};
window.__to = async i => {
  const d = window.__D[i];
  const to = window.__vis('input[aria-label="To recipients"]');
  if (to.length !== 1) throw new Error('TO COUNT ' + to.length);
  to[0].focus(); if (document.activeElement !== to[0]) throw new Error('TO FIELD NOT FOCUSED');
  if (to[0].value) throw new Error('TO NOT EMPTY');
  document.execCommand('insertText', false, d.to);
  await window.__sleep(500);
  const s = window.__vis('input[name="subjectbox"]')[0]; s.focus();
  const dlg = s.closest('[role="dialog"]') || document;
  // Up to 75 s: a background tab runs Gmail's timers about once a minute, so the chip can be that late.
  for (let k = 0; k < 375; k++) {
    await window.__sleep(200);
    const c = window.__chips(dlg); if (c.length) return c;
    if (k === 10 || k === 60) { to[0].dispatchEvent(new FocusEvent('blur', {relatedTarget: s})); to[0].dispatchEvent(new FocusEvent('focusout', {bubbles: true, relatedTarget: s})); }
  }
  return [];
};
window.__fill = async i => {
  const d = window.__D[i];
  const subj = window.__vis('input[name="subjectbox"]');
  if (subj.length !== 1) throw new Error('COMPOSE COUNT ' + subj.length);
  const dlg = subj[0].closest('[role="dialog"]') || subj[0].closest('table') || document;
  let chips = [];
  for (let k = 0; k < 25; k++) { chips = window.__chips(dlg); if (chips.length) break; await window.__sleep(200); }
  if (chips.length !== 1 || chips[0] !== d.to) throw new Error('CHIP MISMATCH ' + JSON.stringify(chips) + ' vs ' + d.to);
  const s = subj[0]; s.focus(); if (document.activeElement !== s) throw new Error('SUBJECT NOT FOCUSED');
  s.select(); document.execCommand('insertText', false, d.s);
  const b = dlg.querySelector('div[aria-label="Message Body"]') || window.__vis('div[aria-label="Message Body"]')[0];
  b.focus(); if (!b.contains(document.activeElement) && document.activeElement !== b) throw new Error('BODY NOT FOCUSED');
  document.execCommand('selectAll'); document.execCommand('insertText', false, d.T);
  await window.__sleep(350);
  const bt = b.innerText.replace(/\n{3,}/g, '\n\n').trim();
  if (s.value !== d.s) throw new Error('SUBJECT MISMATCH ' + s.value);
  if (bt !== d.T.trim()) throw new Error('BODY MISMATCH ' + bt.length + ' vs ' + d.T.length);
  if (window.__chips(dlg).join() !== d.to) throw new Error('CHIP CHANGED');
  b.focus();
  return 'gated ' + i + ' ' + d.to;
};
window.__regate = i => {
  const d = window.__D[i];
  const s = window.__vis('input[name="subjectbox"]');
  if (s.length !== 1) throw new Error('COMPOSE COUNT ' + s.length);
  if (s[0].value !== d.s) throw new Error('SUBJECT CHANGED');
  const dlg = s[0].closest('[role="dialog"]') || document;
  if (window.__chips(dlg).join() !== d.to) throw new Error('CHIP CHANGED');
  const b = dlg.querySelector('div[aria-label="Message Body"]');
  if (b.innerText.replace(/\n{3,}/g, '\n\n').trim() !== d.T.trim()) throw new Error('BODY CHANGED');
  return dlg;
};
window.__send = async i => {
  const dlg = window.__regate(i);
  const b = [...dlg.querySelectorAll('div[role="button"]')].filter(e => e.offsetParent !== null && /^Send\b/.test(e.getAttribute('aria-label') || e.getAttribute('data-tooltip') || ''));
  if (b.length !== 1) throw new Error('SEND BUTTON COUNT ' + b.length);
  for (const t of ['mousedown', 'mouseup', 'click']) b[0].dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window}));
  return 'clicked send ' + i;
};
window.__done = async i => {
  const d = window.__D[i];
  let closed = false;
  for (let k = 0; k < 50; k++) {
    await window.__sleep(200);
    if (window.__banner()) throw new Error('NETWORK ' + i + ' ' + d.to);
    if (window.__vis('input[name="subjectbox"]').length === 0) { closed = true; break; }
  }
  if (!closed) throw new Error('STILL OPEN ' + i + ' ' + d.to);
  window.__SENT[d.to] = new Date().toISOString();
  for (let k = 0; k < 40; k++) {
    await window.__sleep(250);
    const t = document.body.innerText;
    if (/could not be sent|Check your network/i.test(t)) throw new Error('NETWORK AFTER CLOSE ' + i + ' ' + d.to);
    if (/Message sent/i.test(t) && !/Sending\.\.\./.test(t)) break;
  }
  return 'closed ' + i + ' ' + d.to;
};
// Each retry moves after: by one second, because Gmail does not re-run a search it is already showing.
window.__verify = async i => {
  const d = window.__D[i];
  const qs = [0, 1, 2, 3].map(k => 'in:sent to:' + d.to + ' after:' + (Number(window.__AFTER) + k));
  for (let attempt = 0; attempt < 4; attempt++) {
    const r = await window.__search(qs[attempt]);
    if (r.n === 1 && r.subj[0] === d.s) { window.__OK[d.to] = window.__SENT[d.to]; return 'VERIFIED ' + i + ' ' + d.to; }
    if (r.n > 1) throw new Error('DUPLICATE IN SENT ' + i + ' ' + d.to + ' ' + r.n);
    await window.__sleep(2500 * (attempt + 1));
  }
  throw new Error('NOT IN SENT ' + i + ' ' + d.to);
};
window.__one = async i => {
  const d = window.__D[i];
  if (window.__OK[d.to]) return 'skip ' + i;
  await window.__prep(i);
  const c = await window.__to(i);
  if (c.length !== 1 || c[0] !== d.to) throw new Error('CHIP MISMATCH AFTER TO ' + JSON.stringify(c) + ' vs ' + d.to);
  await window.__fill(i);
  await window.__sleep(3000);
  await window.__send(i);
  await window.__done(i);
  await window.__verify(i);
  return 'ok ' + i;
};
window.__chunk = (from, to) => {
  if (window.__RUN && window.__RUN.busy) return 'BUSY';
  if (!Array.isArray(window.__D)) return 'LOAD THE LIST FIRST';
  window.__STOP = false;
  window.__RUN = {busy: true, from, to, at: null, err: null, n: 0};
  (async () => {
    try {
      for (let i = from; i < to && i < window.__D.length; i++) {
        if (window.__STOP) { window.__RUN.err = 'STOPPED BEFORE ' + i; break; }
        window.__RUN.at = i;
        const r = await window.__one(i);
        if (r.startsWith('ok')) { window.__RUN.n++; await window.__sleep(4000); }  // with the gates this paces ~11 s per email
      }
    } catch (e) { window.__RUN.err = String((e && e.message) || e); }
    window.__RUN.busy = false;
  })();
  return 'started ' + from + '-' + to;
};
// Read-only progress: [[row, "hh:mm:ss.mmm"], …] for verified rows in the range.
window.__col = (from, to) => JSON.stringify(window.__D.slice(from, to).map((d, k) => [from + k, window.__OK[d.to] ? window.__OK[d.to].slice(11, 23) : null]).filter(x => x[1]));
JSON.stringify({ok: 'gmail runner ready', title: document.title, account: window.__ACCOUNT || 'SET window.__ACCOUNT', after: window.__AFTER});
