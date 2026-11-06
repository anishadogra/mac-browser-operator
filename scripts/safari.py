#!/usr/bin/env python3
"""safari.py · drive the person's Safari from Claude Code (macOS).

Tabs are chosen by a URL fragment (-t), because other sessions add tabs and windows.
Every command except `open` refuses to run while Safari is closed, so nothing launches by surprise.

  safari.py tabs [--json]
  safari.py js    -t PART 'expression'          evaluate one expression (no trailing semicolon); objects print as JSON
  safari.py jsf   -t PART FILE.js               run a whole file; its last expression is the result
  safari.py run   -t PART BODY.js [--timeout 90]   async body (may use await, must `return`); prints the result
  safari.py run   -t PART --code 'return document.title' [--timeout 90]
  safari.py open  URL [--front]                 new tab at the end of window 1 (a window only when none exists)
  safari.py front -t PART                       unminimise, select the tab, bring Safari forward
  safari.py click -t PART 'CSS' [--index N] [--text EXACT | --contains TEXT]    real mouse click
  safari.py clickxy -t PART X Y                 real click at a screen point
  safari.py key   -t PART KEY [--mods cmd,shift]   KEY: one character, or return tab escape space delete up down left right
  safari.py push  -t PART FILE [--var NAME]     local file -> window[NAME] as a File, SHA-256 checked in the page
  safari.py pull  -t PART URL OUT               fetch URL inside the page (its cookies; blob: URLs too) and save it
  safari.py shot  -t PART OUT.png [--maxw 1600] screenshot of that Safari window

One-time setup by the person: Safari > Settings > Advanced > "Show features for web developers", then Settings >
Developer > "Allow JavaScript from Apple Events". Real clicks and keys also need Accessibility for the app running this.
"""
import argparse
import base64
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import uuid

SLICE = 900_000      # characters per read-back call
CHUNK = 1_000_000    # base64 characters per push call (a multiple of 4)


class SafariError(RuntimeError):
    pass


HINTS = (
    ('JavaScript from Apple Events', 'The person turns on Safari > Settings > Developer > "Allow JavaScript from Apple Events".'),
    ('-1743', 'System Settings > Privacy & Security > Automation: allow the app running Claude to control Safari and System Events.'),
    ('Not authorized to send Apple events', 'System Settings > Privacy & Security > Automation: allow the app running Claude to control Safari and System Events.'),
    ('assistive access', 'System Settings > Privacy & Security > Accessibility: turn on the app running Claude.'),
    ('-25211', 'System Settings > Privacy & Security > Accessibility: turn on the app running Claude.'),
)


def safari_running():
    return subprocess.run(['pgrep', '-x', 'Safari'], capture_output=True).returncode == 0


def require_running():
    if not safari_running():
        raise SafariError('BO_SAFARI_CLOSED: Safari is not running. Ask the person before opening it, then `safari.py open URL`.')


def osa(script, *args, lang=None, timeout=60):
    """Run an AppleScript (or JXA with lang='JavaScript') from a temp file and return stdout."""
    fd, path = tempfile.mkstemp(suffix='.js' if lang else '.applescript')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(script)
    try:
        cmd = ['osascript'] + (['-l', lang] if lang else []) + [path] + [str(a) for a in args]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise SafariError('BO_TIMEOUT: osascript ran past %ss; the page may still be working, so check before re-running' % timeout)
    finally:
        os.unlink(path)
    if r.returncode != 0:
        err = r.stderr.strip()
        for needle, hint in HINTS:
            if needle in err:
                err += '\n-> ' + hint
                break
        raise SafariError(err)
    out = r.stdout
    return out[:-1] if out.endswith('\n') else out


AS_RUN_JS = r'''
on run argv
  set jsPath to item 1 of argv
  set needle to item 2 of argv
  set js to read (POSIX file jsPath) as «class utf8»
  tell application "Safari"
    repeat with w in windows
      repeat with t in tabs of w
        set u to ""
        try
          set u to URL of t
        end try
        if u is missing value then set u to ""
        if u contains needle then
          try
            set r to do JavaScript js in t
          on error errMsg number errNum
            if errNum is -2763 then return "BO_UNDEFINED"
            error errMsg number errNum
          end try
          try
            if r is missing value then return "BO_UNDEFINED"
            return r as text
          on error
            return "BO_UNDEFINED"
          end try
        end if
      end repeat
    end repeat
  end tell
  return "BO_NO_TAB"
end run
'''

AS_TABS = r'''
on run argv
  set TB to ASCII character 9
  set LF to ASCII character 10
  set out to ""
  tell application "Safari"
    set wi to 0
    repeat with w in windows
      set wi to wi + 1
      set cur to 0
      try
        set cur to index of current tab of w
      end try
      set mini to false
      try
        set mini to miniaturized of w
      end try
      set ti to 0
      repeat with t in tabs of w
        set ti to ti + 1
        set u to ""
        set n to ""
        try
          set u to URL of t
        end try
        try
          set n to name of t
        end try
        if u is missing value then set u to ""
        if n is missing value then set n to ""
        set out to out & wi & TB & ti & TB & (ti = cur) & TB & mini & TB & u & TB & n & LF
      end repeat
    end repeat
  end tell
  return out
end run
'''

AS_FRONT = r'''
on run argv
  set needle to item 1 of argv
  tell application "Safari"
    repeat with w in windows
      repeat with t in tabs of w
        set u to ""
        try
          set u to URL of t
        end try
        if u is missing value then set u to ""
        if u contains needle then
          set theWin to contents of w
          set theTab to contents of t
          try
            if miniaturized of theWin then set miniaturized of theWin to false
          end try
          set current tab of theWin to theTab
          set index of theWin to 1
          activate
          delay 0.3
          return (name of theWin) as text
        end if
      end repeat
    end repeat
  end tell
  return "BO_NO_TAB"
end run
'''

AS_RAISE = r'''
on run argv
  set wname to item 1 of argv
  tell application "System Events" to tell process "Safari"
    set frontmost to true
    try
      perform action "AXRaise" of (first window whose name is wname)
    on error
      try
        perform action "AXRaise" of window 1
      end try
    end try
  end tell
  return "ok"
end run
'''

AS_OPEN = r'''
on run argv
  set theURL to item 1 of argv
  tell application "Safari"
    if (count of windows) is 0 then
      make new document with properties {URL:theURL}
    else
      tell window 1 to make new tab at end of tabs with properties {URL:theURL}
    end if
  end tell
  return "opened"
end run
'''

AS_FRONTMOST = 'tell application "System Events" to get name of first application process whose frontmost is true'

JXA_CLICK = r'''
ObjC.import('CoreGraphics');
function run(argv) {
  const x = parseFloat(argv[0]), y = parseFloat(argv[1]);
  const p = $.CGPointMake(x, y);
  const here = $.CGEventGetLocation($.CGEventCreate(null));
  const post = (type, at) => { const e = $.CGEventCreateMouseEvent(null, type, at, 0); $.CGEventPost(0, e); };
  post(5, p); delay(0.06); post(1, p); delay(0.07); post(2, p); delay(0.08);
  post(5, here);
  return 'clicked ' + x + ',' + y;
}
'''

JXA_WINID = r'''
ObjC.import('CoreGraphics');
function run(argv) {
  const want = argv[0] || '';
  const arr = ObjC.castRefToObject($.CGWindowListCopyWindowInfo(1, 0));
  let first = '';
  for (let i = 0; i < arr.count; i++) {
    const d = arr.objectAtIndex(i);
    if (ObjC.unwrap(d.objectForKey('kCGWindowOwnerName')) !== 'Safari') continue;
    if (ObjC.unwrap(d.objectForKey('kCGWindowLayer')) !== 0) continue;
    const id = String(ObjC.unwrap(d.objectForKey('kCGWindowNumber')));
    const name = ObjC.unwrap(d.objectForKey('kCGWindowName')) || '';
    if (!first) first = id;
    if (want && name === want) return id;
  }
  return first;
}
'''

KEYCODES = {'return': 36, 'enter': 76, 'tab': 48, 'space': 49, 'delete': 51, 'escape': 53,
            'left': 123, 'right': 124, 'down': 125, 'up': 126}
MODS = {'cmd': 'command', 'command': 'command', 'shift': 'shift', 'opt': 'option', 'alt': 'option',
        'option': 'option', 'ctrl': 'control', 'control': 'control'}


# ---------------------------------------------------------------- JavaScript

def js_raw(part, code, timeout=60):
    """Run code in the first tab whose URL contains `part`; return its result as text."""
    require_running()
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(code)
    try:
        out = osa(AS_RUN_JS, path, part, timeout=timeout)
    finally:
        os.unlink(path)
    if out == 'BO_NO_TAB':
        raise SafariError('BO_NO_TAB: no Safari tab URL contains %r (see `safari.py tabs`)' % part)
    return out


def js_expr(part, expr, timeout=60):
    code = ('(function(){ try { var __v = (%s); return (typeof __v === "string") ? __v : JSON.stringify(__v); }'
            ' catch (e) { return "BO_ERR " + ((e && e.message) || e); } })()') % expr
    return js_raw(part, code, timeout)


def run(part, body, timeout=90):
    """Run an async body in the page, wait for it to settle, return its value (strings raw, the rest as JSON)."""
    rid = uuid.uuid4().hex[:12]
    rid_js = json.dumps(rid)
    start = ('(function(){ window.__boRes = window.__boRes || {}; var id = %s; window.__boRes[id] = {s: "pending"};\n'
             '(async function(){\n%s\n})().then(function(v){ window.__boRes[id] = {s: "ok", v: (typeof v === "string") ? v :'
             ' JSON.stringify(v === undefined ? null : v)}; }, function(e){ window.__boRes[id] = {s: "err",'
             ' v: String((e && (e.message || e)) || e)}; });\nreturn "started"; })()') % (rid_js, body)
    out = js_raw(part, start)
    if out != 'started':
        raise SafariError('the script did not start (syntax error?): %s' % out[:300])
    t0, delay = time.time(), 0.2
    while True:
        st = js_raw(part, '(function(){ var r = (window.__boRes || {})[%s]; if (!r) return "BO_GONE";'
                          ' if (r.s === "pending") return "BO_PENDING"; return r.s + ":" + r.v.length; })()' % rid_js)
        if st == 'BO_GONE':
            raise SafariError('the page reloaded or navigated while the script ran')
        if st != 'BO_PENDING':
            break
        if time.time() - t0 > timeout:
            raise SafariError('BO_TIMEOUT after %ss: the page may still finish, so check its state before re-running' % timeout)
        time.sleep(delay)
        delay = min(delay * 1.5, 2.0)
    kind, n = st.split(':', 1)
    n = int(n)
    parts = [js_raw(part, 'window.__boRes[%s].v.slice(%d, %d)' % (rid_js, k, k + SLICE)) for k in range(0, n, SLICE)]
    js_raw(part, '(function(){ delete window.__boRes[%s]; return "ok"; })()' % rid_js)
    val = ''.join(parts) if n else ''
    if kind == 'err':
        raise SafariError('page error: ' + val)
    return val


# ---------------------------------------------------------------- windows, focus, clicks

def tabs():
    require_running()
    rows = []
    for line in osa(AS_TABS).splitlines():
        f = line.split('\t')
        if len(f) >= 6:
            rows.append({'window': int(f[0]), 'tab': int(f[1]), 'current': f[2] == 'true', 'minimised': f[3] == 'true',
                         'url': f[4], 'title': '\t'.join(f[5:])})
    return rows


def frontmost():
    try:
        return osa(AS_FRONTMOST, timeout=10)
    except SafariError:
        return ''


def give_back(app):
    if app and app != 'Safari':
        time.sleep(0.3)
        try:
            osa('tell application "System Events" to set frontmost of process %s to true' % json.dumps(app, ensure_ascii=False), timeout=10)
        except SafariError:
            pass


def front(part):
    require_running()
    name = osa(AS_FRONT, part)
    if name == 'BO_NO_TAB':
        raise SafariError('BO_NO_TAB: no Safari tab URL contains %r' % part)
    return name


def raise_window(name):
    try:
        osa(AS_RAISE, name, timeout=15)
    except SafariError:
        pass


def rect_js(sel, index=0, text=None, contains=None):
    return ('(function(){ var lab = function(e){ return ((e.innerText || "").trim() || e.getAttribute("aria-label") || "").trim(); };\n'
            'var els = Array.prototype.slice.call(document.querySelectorAll(%s)).filter(function(e){ var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; });\n'
            'var exact = %s, part = %s;\n'
            'if (exact !== null) els = els.filter(function(e){ return lab(e) === exact; });\n'
            'if (part !== null) els = els.filter(function(e){ return lab(e).indexOf(part) >= 0; });\n'
            'var e = els[%d]; if (!e) return JSON.stringify({err: "nomatch", n: els.length});\n'
            'e.scrollIntoView({block: "nearest", inline: "nearest"}); var r = e.getBoundingClientRect();\n'
            'return JSON.stringify({n: els.length, x: window.screenX + (window.outerWidth - window.innerWidth) + r.x + r.width / 2,'
            ' y: window.screenY + (window.outerHeight - window.innerHeight) + r.y + r.height / 2, w: r.width, h: r.height,'
            ' focus: document.hasFocus(), hidden: document.hidden, txt: lab(e).slice(0, 60)}); })()'
            ) % (json.dumps(sel), json.dumps(text), json.dumps(contains), index)


def click(part, sel, index=0, text=None, contains=None, tries=4):
    """Real click on a visible element: front the tab, raise the window, require focus, CGEvent click, hand focus back."""
    require_running()
    prev = frontmost()
    try:
        for k in range(tries):
            wname = front(part)
            raise_window(wname)
            time.sleep(0.35)
            r = json.loads(js_raw(part, rect_js(sel, index, text, contains)))
            if 'err' in r:
                return {'ok': False, **r}
            if not r.get('focus'):
                time.sleep(0.4)
                raise_window(wname)
                time.sleep(0.3)
                r = json.loads(js_raw(part, rect_js(sel, index, text, contains)))
            if frontmost() != 'Safari' or not r.get('focus'):
                time.sleep(0.6)
                continue
            osa(JXA_CLICK, r['x'], r['y'], lang='JavaScript', timeout=15)
            return {'ok': True, 'try': k + 1, **r}
        return {'ok': False, 'err': 'Safari never held focus (the person may be working in another app)'}
    finally:
        give_back(prev)


def clickxy(part, x, y):
    prev = frontmost()
    try:
        raise_window(front(part))
        time.sleep(0.35)
        if frontmost() != 'Safari':
            raise SafariError('Safari lost focus; nothing clicked')
        return osa(JXA_CLICK, x, y, lang='JavaScript', timeout=15)
    finally:
        give_back(prev)


def key(part, k, mods=''):
    prev = frontmost()
    try:
        raise_window(front(part))
        time.sleep(0.3)
        if frontmost() != 'Safari':
            raise SafariError('Safari lost focus; nothing typed')
        names = [MODS[m.strip().lower()] for m in mods.split(',') if m.strip()]
        using = (' using {%s}' % ', '.join(n + ' down' for n in names)) if names else ''
        if k.lower() in KEYCODES:
            osa('tell application "System Events" to key code %d%s' % (KEYCODES[k.lower()], using), timeout=15)
        else:
            osa('tell application "System Events" to keystroke %s%s' % (json.dumps(k, ensure_ascii=False), using), timeout=15)
        return 'ok'
    finally:
        give_back(prev)


def open_url(url, bring_front=False):
    out = osa(AS_OPEN, url)
    if bring_front:
        host = urllib.parse.urlparse(url).netloc or url
        for _ in range(20):
            try:
                front(host)
                break
            except SafariError:
                time.sleep(0.5)
    return out


def shot(part, out, maxw=None):
    name = front(part)
    raise_window(name)
    time.sleep(0.5)
    wid = osa(JXA_WINID, name, lang='JavaScript', timeout=15)
    if not wid:
        raise SafariError('no on-screen Safari window found')
    subprocess.run(['screencapture', '-x', '-o', '-l', wid, out], check=True)
    if maxw:
        subprocess.run(['sips', '-Z', str(maxw), out], capture_output=True)
    return out


# ---------------------------------------------------------------- files

def push(part, path, var='__boFile'):
    """Send a local file into the page as window[var] (a File) and prove its bytes with SHA-256."""
    data = open(path, 'rb').read()
    sha = hashlib.sha256(data).hexdigest()
    b64 = base64.b64encode(data).decode('ascii')
    name = os.path.basename(path)
    mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    js_raw(part, '(function(){ window.__boPush = []; return "ok"; })()')
    for k in range(0, len(b64), CHUNK):
        js_raw(part, '(function(){ window.__boPush.push(%s); return "ok"; })()' % json.dumps(b64[k:k + CHUNK]))
    body = '''
      const parts = window.__boPush.map(s => { const bin = atob(s); const a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return a; });
      const file = new File(parts, %s, {type: %s});
      const hex = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer()))].map(b => b.toString(16).padStart(2, '0')).join('');
      window.__boPush = null;
      window[%s] = file;
      return {name: file.name, size: file.size, type: file.type, sha: hex};
    ''' % (json.dumps(name), json.dumps(mime), json.dumps(var))
    res = json.loads(run(part, body, timeout=120))
    if res['sha'] != sha or res['size'] != len(data):
        js_raw(part, '(function(){ window[%s] = null; return "ok"; })()' % json.dumps(var))
        raise SafariError('SHA MISMATCH after push: page %s vs local %s' % (res['sha'][:12], sha[:12]))
    res['var'] = var
    res['sha12'] = sha[:12]
    del res['sha']
    return res


def pull(part, url, out, timeout=180):
    """Fetch a URL inside the page (cookies included, blob: works) and write the bytes to `out`."""
    body = '''
      const r = await fetch(%s, {credentials: 'include'});
      if (!r.ok) throw new Error('http ' + r.status);
      const b = await r.blob();
      return await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = () => rej(fr.error); fr.readAsDataURL(b); });
    ''' % json.dumps(url)
    data_url = run(part, body, timeout=timeout)
    head, b64 = data_url.split(',', 1)
    raw = base64.b64decode(b64)
    if os.path.exists(out):
        raise SafariError('refusing to overwrite %s' % out)
    with open(out, 'wb') as f:
        f.write(raw)
    return {'out': out, 'bytes': len(raw), 'type': head[5:].split(';')[0], 'sha12': hashlib.sha256(raw).hexdigest()[:12]}


# ---------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('tabs'); s.add_argument('--json', action='store_true')
    for name in ('js', 'jsf'):
        s = sub.add_parser(name); s.add_argument('-t', '--tab', required=True); s.add_argument('code'); s.add_argument('--timeout', type=int, default=60)
    s = sub.add_parser('run'); s.add_argument('-t', '--tab', required=True); s.add_argument('file', nargs='?')
    s.add_argument('--code'); s.add_argument('--timeout', type=int, default=90)
    s = sub.add_parser('open'); s.add_argument('url'); s.add_argument('--front', action='store_true')
    s = sub.add_parser('front'); s.add_argument('-t', '--tab', required=True)
    s = sub.add_parser('click'); s.add_argument('-t', '--tab', required=True); s.add_argument('selector')
    s.add_argument('--index', type=int, default=0); s.add_argument('--text'); s.add_argument('--contains')
    s = sub.add_parser('clickxy'); s.add_argument('-t', '--tab', required=True); s.add_argument('x', type=float); s.add_argument('y', type=float)
    s = sub.add_parser('key'); s.add_argument('-t', '--tab', required=True); s.add_argument('key'); s.add_argument('--mods', default='')
    s = sub.add_parser('push'); s.add_argument('-t', '--tab', required=True); s.add_argument('file'); s.add_argument('--var', default='__boFile')
    s = sub.add_parser('pull'); s.add_argument('-t', '--tab', required=True); s.add_argument('url'); s.add_argument('out')
    s.add_argument('--timeout', type=int, default=180)
    s = sub.add_parser('shot'); s.add_argument('-t', '--tab', required=True); s.add_argument('out'); s.add_argument('--maxw', type=int)
    a = p.parse_args(argv)
    try:
        if a.cmd == 'tabs':
            rows = tabs()
            if a.json:
                print(json.dumps(rows, ensure_ascii=False))
            else:
                for r in rows:
                    print('%d.%d%s%s  %s  |  %s' % (r['window'], r['tab'], ' *' if r['current'] else '  ',
                                                   ' (min)' if r['minimised'] else '', r['url'], r['title']))
        elif a.cmd == 'js':
            print(js_expr(a.tab, a.code, a.timeout))
        elif a.cmd == 'jsf':
            print(js_raw(a.tab, open(a.code, encoding='utf-8').read(), a.timeout))
        elif a.cmd == 'run':
            body = a.code if a.code is not None else open(a.file, encoding='utf-8').read()
            print(run(a.tab, body, a.timeout))
        elif a.cmd == 'open':
            print(open_url(a.url, a.front))
        elif a.cmd == 'front':
            print(front(a.tab))
        elif a.cmd == 'click':
            print(json.dumps(click(a.tab, a.selector, a.index, a.text, a.contains), ensure_ascii=False))
        elif a.cmd == 'clickxy':
            print(clickxy(a.tab, a.x, a.y))
        elif a.cmd == 'key':
            print(key(a.tab, a.key, a.mods))
        elif a.cmd == 'push':
            print(json.dumps(push(a.tab, a.file, a.var), ensure_ascii=False))
        elif a.cmd == 'pull':
            print(json.dumps(pull(a.tab, a.url, a.out, a.timeout), ensure_ascii=False))
        elif a.cmd == 'shot':
            print(shot(a.tab, a.out, a.maxw))
    except SafariError as e:
        print('ERROR: %s' % e, file=sys.stderr)
        return 3 if 'BO_SAFARI_CLOSED' in str(e) else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
