// bo_core.js · Mac Browser Operator in-page helpers. Inject once per page load:
//   Chrome (extension): send this file's text through javascript_tool.
//   Safari: python3 scripts/safari.py jsf -t <url-part> scripts/js/bo_core.js
// Everything lives on window.__bo, so injecting twice is harmless. The last line is the result.
(() => {
  const bo = window.__bo = window.__bo || {};
  bo.version = '1.0';

  // ---- timing ----
  bo.sleep = ms => new Promise(r => setTimeout(r, ms));
  bo.waitFor = async (fn, {timeout = 10000, every = 200, label = 'condition'} = {}) => {
    const t0 = Date.now(); let last = null;
    while (Date.now() - t0 < timeout) {
      try { const v = await fn(); if (v) return v; } catch (e) { last = e; }
      await bo.sleep(every);
    }
    throw new Error('TIMEOUT ' + label + (last ? ' (' + (last.message || last) + ')' : ''));
  };
  // Sleeps that keep time in a background tab (Worker clock; falls back to setTimeout).
  bo.wait = ms => {
    if (!bo._clock) {
      try {
        let url = URL.createObjectURL(new Blob(['onmessage=e=>setTimeout(()=>postMessage(e.data),e.data.ms)'], {type: 'text/javascript'}));
        if (window.trustedTypes && trustedTypes.createPolicy) {
          bo._tt = bo._tt || trustedTypes.createPolicy('bo-clock', {createScriptURL: s => s});
          url = bo._tt.createScriptURL(url);
        }
        const w = new Worker(url), waiting = {}; let n = 0;
        w.onmessage = e => { const cb = waiting[e.data.id]; delete waiting[e.data.id]; if (cb) cb(); };
        bo._clock = t => new Promise(r => { const id = ++n; waiting[id] = r; w.postMessage({id, ms: t}); });
      } catch (e) { bo._clock = bo.sleep; }
    }
    return Promise.race([bo._clock(ms), bo.sleep(ms + 1500)]);
  };

  // ---- finding and gating ----
  bo.vis = (sel, root = document) => [...root.querySelectorAll(sel)].filter(e => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden');
  bo.one = (sel, root) => { const a = bo.vis(sel, root); if (a.length !== 1) throw new Error('EXPECTED ONE ' + sel + ', FOUND ' + a.length); return a[0]; };
  bo.label = e => ((e.innerText || e.textContent || '').trim() || e.getAttribute('aria-label') || e.value || '').trim();
  bo.byText = (sel, text, {exact = true, root} = {}) => bo.vis(sel, root).filter(e => exact ? bo.label(e) === text : bo.label(e).includes(text));
  bo.gate = checks => {
    const bad = Object.keys(checks).filter(k => !checks[k]);
    if (bad.length) throw new Error('GATE FAILED: ' + bad.join(', '));
    return 'gate ok: ' + Object.keys(checks).join(', ');
  };
  bo.account = () => [...document.querySelectorAll('[aria-label]')].map(e => e.getAttribute('aria-label')).find(x => /Google Account/.test(x)) || null;
  bo.at = (x, y) => { const e = document.elementFromPoint(x, y); if (!e) return null; const a = e.closest('[aria-label]'); return a ? a.getAttribute('aria-label') : bo.label(e).slice(0, 40); };
  bo.center = el => { const r = el.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; };

  // ---- hashing (compare text by hash: JS length counts an emoji as 2) ----
  bo.hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
  bo.sha = async (text, n = 12) => bo.hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))).slice(0, n);
  bo.shaFile = async blob => bo.hex(await crypto.subtle.digest('SHA-256', await blob.arrayBuffer()));

  // ---- typing ----
  bo.focus = el => {
    el.focus();
    const a = document.activeElement;
    if (a !== el && !el.contains(a)) throw new Error('NOT FOCUSED: ' + (el.getAttribute('aria-label') || el.id || el.tagName));
    return el;
  };
  // React-controlled inputs and textareas: the native setter plus input and change events.
  bo.setValue = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    el.focus();
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    return el.value;
  };
  bo.caretEnd = el => { el.focus(); const s = getSelection(); s.selectAllChildren(el); s.collapseToEnd(); return el; };
  // contenteditable editors such as Gmail's body and Flow's prompt box.
  bo.insertText = (el, text, {replace = false} = {}) => {
    bo.focus(el);
    if (replace) document.execCommand('selectAll'); else bo.caretEnd(el);
    return document.execCommand('insertText', false, text);
  };
  // Lexical (WhatsApp, Instagram DMs) and Tiptap (LinkedIn) take a synthetic paste.
  bo.paste = (el, text, {html} = {}) => {
    bo.caretEnd(el);
    const dt = new DataTransfer();
    dt.setData('text/plain', text);
    if (html) dt.setData('text/html', html);
    el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    return true;
  };
  bo.pasteFiles = (el, files) => {
    el.focus();
    const dt = new DataTransfer();
    [...files].forEach(f => dt.items.add(f));
    el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: dt, bubbles: true, cancelable: true}));
    return dt.files.length;
  };
  bo.linesToHtml = text => text.split('\n').map(l => '<p>' + l.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</p>').join('');
  // Read an editor back the way it renders: one <p> per line, emoji images as their plain text.
  bo.readEditor = el => {
    const one = node => {
      let s = '';
      const walk = n => {
        if (n.nodeType === 3) s += n.textContent;
        else if (n.tagName === 'IMG') s += n.getAttribute('data-plain-text') || n.alt || '';
        else n.childNodes.forEach(walk);
      };
      walk(node);
      return s;
    };
    const ps = [...el.querySelectorAll('p')];
    return (ps.length ? ps : [el]).map(one).join('\n');
  };

  // ---- clicking ----
  bo.fire = el => {
    for (const t of ['mousedown', 'mouseup', 'click']) el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window}));
    return bo.label(el).slice(0, 40);
  };

  // ---- files ----
  bo.fileInput = (id = 'bo-file', {multiple = true, accept = ''} = {}) => {
    const old = document.getElementById(id);
    if (old) old.remove();
    const inp = document.createElement('input');
    inp.type = 'file'; inp.id = id; inp.multiple = multiple;
    if (accept) inp.accept = accept;
    inp.setAttribute('aria-label', id + ' upload');
    inp.style.cssText = 'position:fixed;left:0;top:0;width:10px;height:10px;opacity:0.01;z-index:2147483647';
    document.body.appendChild(inp);
    return 'ready: find "' + id + ' upload", then file_upload';
  };
  // Run before clicking an app's upload button: its file input is kept in the page instead of opening the macOS picker.
  bo.parkPickers = () => {
    if (bo._parking) return 'already parking';
    const park = el => {
      if (!el || el.type !== 'file') return false;
      el.setAttribute('aria-label', 'bo parked file input');
      if (!el.isConnected) { el.style.display = 'none'; document.body.appendChild(el); }
      bo.parked = el;
      return true;
    };
    const oc = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function () { if (park(this)) return; return oc.apply(this, arguments); };
    const osp = HTMLInputElement.prototype.showPicker;
    if (osp) HTMLInputElement.prototype.showPicker = function () { if (park(this)) return; return osp.apply(this, arguments); };
    bo._parking = true;
    return 'pickers parked: the next upload click leaves its input in __bo.parked';
  };
  bo.feed = (input, files) => {
    const dt = new DataTransfer();
    [...files].forEach(f => dt.items.add(f));
    input.files = dt.files;
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
    return input.files.length;
  };
  // Over the 10 MB file_upload cap: split on the Mac, upload part by part, assemble and hash-check here.
  bo.chunkInput = () => { bo.parts = []; bo.fileInput('bo-chunk', {multiple: false}); return 'ready: find "bo-chunk upload"; after each file_upload run __bo.takePart()'; };
  bo.takePart = () => {
    const f = document.getElementById('bo-chunk').files[0];
    const l = bo.parts[bo.parts.length - 1];
    if (f && !(l && l.name === f.name && l.size === f.size)) bo.parts.push(f);
    return bo.parts.map(p => p.name + ' ' + p.size);
  };
  bo.assemble = async (name, type, expectSha) => {
    const file = new File(bo.parts, name, {type: type || 'application/octet-stream'});
    const sha = await bo.shaFile(file);
    if (expectSha && sha !== String(expectSha).toLowerCase()) throw new Error('ASSEMBLY SHA MISMATCH ' + sha.slice(0, 12));
    bo.file = file;
    return {name, size: file.size, sha12: sha.slice(0, 12)};
  };
  // Capture the blob behind an app's own download click (nothing lands in Downloads).
  bo.hookDownloads = () => {
    if (bo._dl) return 'already hooked';
    bo.downloads = []; bo.blobs = {};
    const oa = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      if (this.hasAttribute('download') && this.href) { bo.downloads.push({href: this.href, name: this.getAttribute('download') || ''}); return; }
      return oa.apply(this, arguments);
    };
    const cou = URL.createObjectURL, rou = URL.revokeObjectURL;
    URL.createObjectURL = function (b) { const u = cou.call(URL, b); bo.blobs[u] = b; return u; };
    URL.revokeObjectURL = function (u) { if (bo.blobs[u]) return; return rou.call(URL, u); };
    bo._dl = true;
    return 'downloads hooked: read __bo.downloads';
  };

  // ---- reading out ----
  // The extension blocks text that looks like key=value, query URLs or tokens, and truncates long strings.
  bo.safe = s => String(s).replace(/https?:\/\//g, '').replace(/=/g, ' :: ').replace(/[?&]/g, ' ');
  bo.stash = (key, value) => { bo.store = bo.store || {}; bo.store[key] = typeof value === 'string' ? value : JSON.stringify(value); return key + ' ' + bo.store[key].length; };
  bo.slice = (key, i = 0, n = 900) => bo.store[key].slice(i * n, (i + 1) * n);
  bo.fiber = (el, prop, depth = 25) => {
    const k = Object.keys(el).find(x => x.startsWith('__reactFiber$') || x.startsWith('__reactInternalInstance$'));
    let f = k && el[k];
    for (let i = 0; f && i < depth; i++, f = f.return) {
      const p = f.memoizedProps;
      if (p && p[prop] !== undefined) return p[prop];
    }
    return undefined;
  };
  // Replaces the page with plain paragraphs so get_page_text can read a long text. Reload afterwards.
  bo.showForReading = paragraphs => {
    const main = document.createElement('main'), art = document.createElement('article');
    paragraphs.forEach(t => { const p = document.createElement('p'); p.textContent = t; art.appendChild(p); });
    main.appendChild(art);
    document.body.replaceChildren(main);
    return paragraphs.length + ' paragraphs ready for get_page_text';
  };

  // ---- long jobs: run inside the page, poll from outside ----
  bo.runs = bo.runs || {};
  bo.run = (name, fn) => {
    const cur = bo.runs[name];
    if (cur && cur.busy) return 'BUSY ' + name;
    const st = bo.runs[name] = {busy: true, started: new Date().toISOString(), log: [], err: null, result: null, stop: false};
    Promise.resolve()
      .then(() => fn(st))
      .then(v => { st.result = v === undefined ? null : v; }, e => { st.err = String((e && e.message) || e); })
      .then(() => { st.busy = false; st.ended = new Date().toISOString(); });
    return 'started ' + name;
  };
  bo.status = name => {
    const r = bo.runs[name];
    if (!r) return 'NO RUN ' + name;
    return JSON.stringify({busy: r.busy, err: r.err, steps: r.log.length, last: r.log.slice(-3), result: r.result}).slice(0, 900);
  };
  bo.stop = name => { const r = bo.runs[name]; if (r) r.stop = true; return 'stop requested for ' + name; };
})();
'bo_core ' + window.__bo.version + ' ready on ' + location.host;
