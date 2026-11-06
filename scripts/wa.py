#!/usr/bin/env python3
"""wa.py · personal WhatsApp Web in Safari, through WhatsApp Web's own modules (no UI clicks, no read receipts).

  wa.py open                                   add web.whatsapp.com as a Safari tab (ask the person first)
  wa.py status                                 socket, chat count, visibility, the self chat
  wa.py wake                                   front the tab, reload when DISCONNECTED, wait for CONNECTED
  wa.py find "NAME REGEX" [--groups] [--limit 25]
  wa.py self                                   the "Message yourself" chat
  wa.py recent --chat ID|self [--n 15]         last messages, chat left unopened
  wa.py send-text --to ID|self|+DIGITS --text-file FILE [--preview] [--show] [--expect-name X] [--again] [--yes]
  wa.py send-file --to ID|self|+DIGITS --file PATH [--caption TEXT] [--expect-name X] [--again] [--yes]
  wa.py download --chat ID|self --match "FILENAME REGEX" --out DIR [--older 0]

Sends are dry runs until --yes is given. Pass --yes only after the person's go in this session.
Every send is gated (identity, not a group, no identical earlier copy, one shot per page), verified by ack,
and recorded in the action log (actlog.py). After any interruption, run `wa.py recent` before trying again.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import actlog  # noqa: E402
from safari import SafariError, front, js_raw, open_url, push, run, safari_running  # noqa: E402

PART = 'web.whatsapp.com'
URL = 'https://web.whatsapp.com/'

PRELUDE = r'''
const R = window.require;
if (typeof R !== 'function') throw new Error('NO_REQUIRE: WhatsApp Web is still loading or signed out (QR screen)');
const C = R('WAWebCollections');
const __me = () => {
  const ids = [];
  let M = null;
  try { M = R('WAWebUserPrefsMeUser'); } catch (e) {}
  if (M) for (const fn of ['getMaybeMeLidUser', 'getMeLidUser', 'getMaybeMeUser', 'getMeUser', 'getMaybeMePnUser']) {
    try { const w = M[fn] && M[fn](); const s = w && w._serialized; if (s && !ids.includes(s)) ids.push(s); } catch (e) {}
  }
  try { C.Contact.getModelsArray().forEach(c => { const s = c.isMe && c.id && c.id._serialized; if (s && !ids.includes(s)) ids.push(s); }); } catch (e) {}
  const chat = ids.map(id => C.Chat.get(id)).find(Boolean) || null;
  return {ids, chat};
};
const __who = chat => ({id: chat.id._serialized, title: chat.formattedTitle || '', name: (chat.contact && chat.contact.name) || '',
  push: (chat.contact && chat.contact.pushname) || '', group: !!chat.isGroup, unread: chat.unreadCount || 0});
const __target = async (to, create) => {
  if (!C.Chat.getModelsArray().length) throw new Error('NO_CHATS_LOADED: run wa.py wake; a QR screen means the person relinks from their phone');
  if (to === 'self') { const me = __me(); if (!me.chat) throw new Error('SELF_CHAT_NOT_FOUND ' + JSON.stringify(me.ids)); return me.chat; }
  if (/^\+?\d{8,15}$/.test(to)) {
    const digits = to.replace(/\D/g, '');
    const wid = R('WAWebWidFactory').createWid(digits + '@c.us');
    const ex = await R('WAWebQueryExistsJob').queryWidExists(wid);
    if (!ex) throw new Error('NOT_ON_WHATSAPP ' + to);
    const known = C.Chat.get(digits + '@c.us');
    if (known || !create) return known || null;
    const res = await R('WAWebFindChatAction').findOrCreateLatestChat(wid);
    return (res && res.chat) || res;
  }
  const chat = C.Chat.get(to);
  if (!chat) throw new Error('NO_CHAT ' + to + ' (copy ids whole from wa.py find)');
  return chat;
};
'''


def page(body, timeout=90, **tokens):
    """Run PRELUDE + body in the WhatsApp tab; __NAME__ placeholders become JSON values in one pass."""
    body = re.sub(r'__([A-Z]+)__', lambda m: json.dumps(tokens[m.group(1).lower()], ensure_ascii=False)
                  if m.group(1).lower() in tokens else m.group(0), body)
    out = run(PART, PRELUDE + body, timeout=timeout)
    try:
        return json.loads(out)
    except ValueError:
        return out


def emit(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    return code


def status():
    try:
        return page('''
const S = R('WAWebSocketModel').Socket;
const me = __me();
return {ok: true, stream: S.stream, state: S.state, chats: C.Chat.getModelsArray().length, hidden: document.hidden,
  self: me.chat ? __who(me.chat) : null, me_ids: me.ids};''', timeout=30)
    except SafariError as e:
        return {'ok': False, 'err': str(e)}


def wake():
    front(PART)
    st = {}
    for _ in range(10):
        st = status()
        if st.get('ok') and st.get('stream') == 'CONNECTED' and st.get('chats', 0) > 0:
            return st
        time.sleep(1.5)
    js_raw(PART, '(function(){ setTimeout(function(){ location.reload(); }, 50); return "reloading"; })()')
    time.sleep(8)
    for _ in range(20):
        st = status()
        if st.get('ok') and st.get('stream') == 'CONNECTED' and st.get('chats', 0) > 0:
            return st
        time.sleep(2)
    try:
        txt = js_raw(PART, '(document.body && document.body.innerText || "").slice(0, 400)')
    except SafariError:
        txt = ''
    if any(w in txt for w in ('Scan', 'scan', 'Log in', 'Link with phone')):
        st['signed_out'] = 'WhatsApp Web shows the QR screen: the person relinks from their phone (Settings > Linked devices).'
    return st


def resolve(to, text=None, filehash=None):
    """Who `to` is, plus earlier copies of the same text or file in that chat. Creates nothing."""
    return page('''
const chat = await __target(__TO__, false);
if (!chat) return {who: null, same: 0, live: []};
const T = __TEXT__, H = __HASH__;
const msgs = chat.msgs.getModelsArray().filter(m => m.id && m.id.fromMe);
const same = T === null ? 0 : msgs.filter(m => m.type === 'chat' && String(m.body || '').trim() === T.trim()).length;
const live = H === null ? [] : msgs.filter(m => m.mediaData && m.mediaData.filehash === H).map(m => ({ack: m.ack, fail: !!m.isSendFailure, stage: m.mediaData.mediaStage}));
return {who: __who(chat), same, live};''', timeout=60, to=to, text=text, hash=filehash)


def identity_problems(info, args):
    who = info.get('who')
    problems = []
    if who and who['group'] and not getattr(args, 'groups', False):
        problems.append('GROUP_CHAT (sending to groups needs --groups and the person\'s explicit go)')
    if args.expect_name:
        hay = ' '.join([who.get('title', ''), who.get('name', ''), who.get('push', '')]).lower() if who else ''
        if args.expect_name.lower() not in hay:
            problems.append('NAME_MISMATCH: expected %r, chat shows %r' % (args.expect_name, who))
    return problems


def guard_log(key, args):
    last = actlog.latest(key)
    if last and not args.again:
        if last['status'] == 'done':
            return 'ALREADY_SENT at %s (actlog). Use --again only when the person asks for a second copy.' % last['at']
        if last['status'] in ('intent', 'pending'):
            return ('AN EARLIER ATTEMPT (%s, %s) may have gone through. Run `wa.py recent --chat %s` and check before '
                    'retrying; record the outcome with actlog.py add.' % (last['status'], last['at'], last['to']))
    return None


def send_text(args):
    text = open(args.text_file, encoding='utf-8').read()
    text = text[:-1] if text.endswith('\n') else text
    if not text.strip():
        return emit({'ok': False, 'err': 'EMPTY_TEXT'}, 1)
    info = resolve(args.to, text=text)
    who = info.get('who')
    target_label = who['id'] if who else args.to
    key = actlog.make_key('whatsapp', target_label, text.encode('utf-8'))
    problems = identity_problems(info, args)
    if info.get('same') and not args.again:
        problems.append('SAME_TEXT_ALREADY_IN_CHAT (%d copies)' % info['same'])
    blocked = guard_log(key, args)
    if blocked:
        problems.append(blocked)
    preview = {'to': who or args.to, 'chars': len(text), 'sha12': hashlib.sha256(text.encode('utf-8')).hexdigest()[:12],
               'first_line': text.split('\n')[0][:80], 'key': key}
    if problems:
        return emit({'ok': False, 'refused': problems, **preview}, 2)
    if not args.yes:
        return emit({'ok': True, 'dry_run': 'nothing sent; pass --yes after the person\'s go', **preview})
    actlog.add(key, 'whatsapp', target_label, 'intent', note='text ' + preview['sha12'])
    try:
        res = page('''
const T = __TEXT__;
const chat = await __target(__TO__, true);
const who = __who(chat);
const expect = __EXPECT__;
if (expect && who.id !== expect) throw new Error('TARGET_CHANGED ' + who.id);
window.__boOnce = window.__boOnce || {};
if (window.__boOnce[__KEY__]) throw new Error('ONE_SHOT: already sent from this page');
const mine = () => chat.msgs.getModelsArray().filter(m => m.id && m.id.fromMe && m.type === 'chat' && String(m.body || '').trim() === T.trim());
const before = mine().length;
window.__boOnce[__KEY__] = Date.now();
let opts = {};
if (__PREVIEW__) {
  try { const link = R('WALinkify').findLink(T); if (link) { const pv = await R('WAWebLinkPreviewChatAction').getLinkPreview(link); if (pv && pv.data) opts = {linkPreview: pv.data}; } } catch (e) {}
}
if (__SHOW__) R('WAWebCmd').Cmd.openChatBottom({chat});
const res = await R('WAWebSendTextMsgChatAction').sendTextMsgToChat(chat, T, opts);
let last = null;
for (let k = 0; k < 40; k++) {
  await new Promise(r => setTimeout(r, 500));
  const a = mine();
  if (a.length > before) { last = a[a.length - 1]; if (last.ack >= 1) break; }
}
return {result: res && res.messageSendResult, ack: last ? last.ack : null, copies: mine().length - before, who, link_card: !!opts.linkPreview};''',
                   timeout=60, text=text, to=args.to, expect=who['id'] if who else None, key=key,
                   preview=bool(args.preview), show=bool(args.show))
    except SafariError as e:
        actlog.add(key, 'whatsapp', target_label, 'pending', note='error: %s' % str(e)[:200])
        return emit({'ok': False, 'err': str(e), 'next': 'run wa.py recent before any retry'}, 1)
    ok = isinstance(res, dict) and res.get('copies') == 1 and (res.get('ack') or 0) >= 1
    actlog.add(key, 'whatsapp', res.get('who', {}).get('id', target_label) if isinstance(res, dict) else target_label,
               'done' if ok else 'pending', note='ack %s copies %s' % (res.get('ack'), res.get('copies')) if isinstance(res, dict) else str(res)[:200])
    return emit({'ok': ok, **(res if isinstance(res, dict) else {'raw': res}), 'key': key}, 0 if ok else 1)


def send_file(args):
    data = open(args.file, 'rb').read()
    digest = hashlib.sha256(data).digest()
    hash_b64 = base64.b64encode(digest).decode('ascii')
    name = os.path.basename(args.file)
    info = resolve(args.to, filehash=hash_b64)
    who = info.get('who')
    target_label = who['id'] if who else args.to
    key = actlog.make_key('whatsapp', target_label, data)
    problems = identity_problems(info, args)
    live = [c for c in info.get('live', []) if not c.get('fail')]
    if live and not args.again:
        problems.append('FILE_ALREADY_IN_CHAT (%d live copies, ack %s)' % (len(live), [c['ack'] for c in live]))
    blocked = guard_log(key, args)
    if blocked:
        problems.append(blocked)
    preview = {'to': who or args.to, 'file': name, 'bytes': len(data), 'sha12': digest.hex()[:12], 'caption': args.caption, 'key': key}
    if problems:
        return emit({'ok': False, 'refused': problems, **preview}, 2)
    if not args.yes:
        return emit({'ok': True, 'dry_run': 'nothing sent; pass --yes after the person\'s go', **preview})
    st = status()
    if not (st.get('ok') and st.get('stream') == 'CONNECTED'):
        return emit({'ok': False, 'err': 'NOT_CONNECTED', 'status': st, 'next': 'wa.py wake'}, 1)
    if st.get('hidden'):
        front(PART)  # a covered tab stalls document uploads in PREPARING
    pushed = push(PART, args.file, var='__boFile')
    actlog.add(key, 'whatsapp', target_label, 'intent', note='file %s %s' % (name, digest.hex()[:12]))
    try:
        sent = page('''
const chat = await __target(__TO__, true);
const expect = __EXPECT__;
if (expect && chat.id._serialized !== expect) throw new Error('TARGET_CHANGED ' + chat.id._serialized);
const file = window.__boFile;
if (!file) throw new Error('NO_FILE_IN_PAGE');
window.__boOnce = window.__boOnce || {};
if (window.__boOnce[__KEY__]) throw new Error('ONE_SHOT: already sent from this page');
window.__boOnce[__KEY__] = Date.now();
window.__boSendT = Math.floor(Date.now() / 1000) - 5;
const od = await R('WAWebMediaOpaqueData').createFromData(file, file.type || 'application/octet-stream');
const prep = R('WAWebPrepRawMedia').prepRawMedia(od, {asDocument: true});
await prep.waitForPrep();
await prep.sendToChat({chat, options: __CAPTION__ ? {caption: __CAPTION__} : {}});
return {sent: true, chat: chat.id._serialized};''', timeout=180, to=args.to, expect=who['id'] if who else None,
             key=key, caption=args.caption or '')
    except SafariError as e:
        actlog.add(key, 'whatsapp', target_label, 'pending', note='error: %s' % str(e)[:200])
        return emit({'ok': False, 'err': str(e), 'next': 'run wa.py recent before any retry'}, 1)
    chat_id = sent.get('chat') if isinstance(sent, dict) else None
    limit = 60 + 2 * len(data) / 1_000_000
    t0, copies = time.time(), []
    while time.time() - t0 < limit:
        time.sleep(3)
        copies = page('''
const chat = await __target(__TO__, false);
const T0 = window.__boSendT || 0;
return chat.msgs.getModelsArray().filter(m => m.id && m.id.fromMe && ((m.mediaData && m.mediaData.filehash === __HASH__) || (m.filename === __NAME__ && m.t >= T0)))
  .map(m => ({id: m.id._serialized, ack: m.ack, fail: !!m.isSendFailure, stage: m.mediaData && m.mediaData.mediaStage, name: m.filename}));''',
                      timeout=30, to=chat_id or target_label, hash=hash_b64, name=name)
        live = [c for c in copies if not c['fail']] if isinstance(copies, list) else []
        if live and all((c['ack'] or 0) >= 1 for c in live):
            break
    try:
        js_raw(PART, '(function(){ window.__boFile = null; return "ok"; })()')
    except SafariError:
        pass
    live = [c for c in copies if not c['fail']] if isinstance(copies, list) else []
    ok = len(live) == 1 and (live[0]['ack'] or 0) >= 1
    actlog.add(key, 'whatsapp', target_label, 'done' if ok else 'pending',
               note='%s ack %s copies %d' % (name, [c['ack'] for c in live], len(live)))
    out = {'ok': ok, 'file': name, 'bytes': pushed['size'], 'sha12': pushed['sha12'], 'copies': copies, 'key': key}
    if not ok:
        out['next'] = 'keep Safari in front; check `wa.py recent` in a minute; never resend while a live copy exists'
    return emit(out, 0 if ok else 1)


def download(args):
    out = page('''
const chat = await __target(__TO__, false);
if (!chat) throw new Error('NO_CHAT');
for (let i = 0; i < __OLDER__; i++) { try { await R('WAWebChatLoadMessages').loadEarlierMsgs({chat}); } catch (e) { break; } }
const re = new RegExp(__PATTERN__, 'i');
const m = chat.msgs.getModelsArray().filter(x => x.type === 'document' && re.test(x.filename || '')).pop();
if (!m) throw new Error('NO_DOCUMENT_MATCH');
await m.downloadMedia({downloadEvenIfExpensive: true, rmrReason: 1, isUserInitiated: true});
const blob = R('WAWebMediaInMemoryBlobCache').InMemoryMediaBlobCache.get(m.mediaData.filehash);
if (!blob) throw new Error('NOT_IN_CACHE: try again in a few seconds');
const d = await new Promise((res, rej) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.onerror = () => rej(fr.error); fr.readAsDataURL(blob); });
return JSON.stringify({name: m.filename, hash: m.mediaData.filehash, size: blob.size}) + '\\n' + d;''',
               timeout=300, to=args.chat, older=int(args.older), pattern=args.match)
    meta_line, data_url = out.split('\n', 1)
    meta = json.loads(meta_line)
    raw = base64.b64decode(data_url.split(',', 1)[1])
    if base64.b64encode(hashlib.sha256(raw).digest()).decode('ascii') != meta['hash']:
        return emit({'ok': False, 'err': 'HASH_MISMATCH', **meta}, 1)
    os.makedirs(args.out, exist_ok=True)
    base, ext = os.path.splitext(os.path.basename(meta['name'] or 'document'))
    path, n = os.path.join(args.out, base + ext), 2
    while os.path.exists(path):
        path, n = os.path.join(args.out, '%s (%d)%s' % (base, n, ext)), n + 1
    with open(path, 'wb') as f:
        f.write(raw)
    return emit({'ok': True, 'saved': path, 'bytes': len(raw)})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('open'); sub.add_parser('status'); sub.add_parser('wake'); sub.add_parser('self')
    s = sub.add_parser('find'); s.add_argument('pattern'); s.add_argument('--groups', action='store_true'); s.add_argument('--limit', type=int, default=25)
    s = sub.add_parser('recent'); s.add_argument('--chat', required=True); s.add_argument('--n', type=int, default=15)
    for name in ('send-text', 'send-file'):
        s = sub.add_parser(name)
        s.add_argument('--to', required=True)
        s.add_argument('--expect-name'); s.add_argument('--groups', action='store_true')
        s.add_argument('--again', action='store_true'); s.add_argument('--yes', action='store_true')
        if name == 'send-text':
            s.add_argument('--text-file', required=True); s.add_argument('--preview', action='store_true'); s.add_argument('--show', action='store_true')
        else:
            s.add_argument('--file', required=True); s.add_argument('--caption')
    s = sub.add_parser('download'); s.add_argument('--chat', required=True); s.add_argument('--match', required=True)
    s.add_argument('--out', required=True); s.add_argument('--older', type=int, default=0)
    a = p.parse_args(argv)
    try:
        if a.cmd == 'open':
            if safari_running():
                try:
                    front(PART)
                    return emit({'ok': True, 'note': 'WhatsApp tab already open; brought it forward'})
                except SafariError:
                    pass
            open_url(URL, bring_front=True)
            return emit({'ok': True, 'note': 'opened web.whatsapp.com; wait ~20 s, then wa.py status'})
        if a.cmd == 'status':
            st = status()
            return emit(st, 0 if st.get('ok') else 1)
        if a.cmd == 'wake':
            st = wake()
            return emit(st, 0 if st.get('stream') == 'CONNECTED' else 1)
        if a.cmd == 'self':
            st = status()
            return emit({'ok': bool(st.get('self')), 'self': st.get('self'), 'me_ids': st.get('me_ids'), 'err': st.get('err')})
        if a.cmd == 'find':
            rows = page('''
const re = new RegExp(__PATTERN__, 'i');
return C.Chat.getModelsArray().filter(c => __GROUPS__ || !c.isGroup).map(c => Object.assign(__who(c), {t: c.t || 0}))
  .filter(r => re.test([r.title, r.name, r.push, r.id].join(' '))).sort((a, b) => b.t - a.t).slice(0, __LIMIT__);''',
                        pattern=a.pattern, groups=bool(a.groups), limit=int(a.limit))
            return emit(rows)
        if a.cmd == 'recent':
            if not (a.chat == 'self' or '@' in a.chat):
                return emit({'ok': False, 'err': 'recent takes a chat id (from wa.py find) or self'}, 2)
            res = page('''
const chat = await __target(__CHAT__, false);
const ms = chat.msgs.getModelsArray().slice(-__N__).map(m => ({me: !!(m.id && m.id.fromMe), type: m.type, t: m.t, ack: m.ack,
  text: String((m.type === 'chat' ? m.body : m.caption) || '').slice(0, 400), file: m.filename || null, fail: !!m.isSendFailure}));
return {chat: __who(chat), msgs: ms};''', chat=a.chat, n=int(a.n))
            return emit(res)
        if a.cmd == 'send-text':
            return send_text(a)
        if a.cmd == 'send-file':
            return send_file(a)
        if a.cmd == 'download':
            return download(a)
    except SafariError as e:
        return emit({'ok': False, 'err': str(e)}, 3 if 'BO_SAFARI_CLOSED' in str(e) else 1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
