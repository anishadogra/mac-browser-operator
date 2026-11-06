#!/usr/bin/env python3
"""actlog.py · append-only record of every irreversible browser action (send, post, submit, upload).

Write an `intent` line before the action and `done`, `failed` or `pending` right after it. Before any retry,
`check` the key: an interrupted call may already have done the work. This log beats a live query of the app.

  actlog.py key   --channel whatsapp --to RECIPIENT (--text TEXT | --text-file FILE | --file PATH)
  actlog.py add   --key KEY --channel C --to T --status intent|done|failed|pending|skipped [--note N] [--ref R]
  actlog.py check --key KEY            exit 0 and print the latest line when the key exists, exit 1 when it does not
  actlog.py tail  [--n 20] [--channel C] [--to T]

Data: $BO_HOME/actions.jsonl (default ~/.browser-operator/actions.jsonl).
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

STATUSES = ('intent', 'done', 'failed', 'pending', 'skipped')


def home():
    h = os.environ.get('BO_HOME') or os.path.join(os.path.expanduser('~'), '.browser-operator')
    os.makedirs(h, exist_ok=True)
    return h


def path():
    return os.path.join(home(), 'actions.jsonl')


def make_key(channel, to, payload):
    """16-hex key from channel + recipient + payload bytes: the same message to the same person has the same key."""
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    inner = hashlib.sha256(payload).digest()
    return hashlib.sha256(('%s|%s|' % (channel, to)).encode('utf-8') + inner).hexdigest()[:16]


def add(key, channel, to, status, note='', ref=''):
    if status not in STATUSES:
        raise ValueError('status must be one of %s' % ', '.join(STATUSES))
    row = {'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'), 'key': key, 'channel': channel,
           'to': to, 'status': status, 'note': note, 'ref': ref}
    with open(path(), 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return row


def rows():
    if not os.path.exists(path()):
        return []
    out = []
    with open(path(), encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def latest(key):
    hit = None
    for r in rows():
        if r.get('key') == key:
            hit = r
    return hit


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('key'); s.add_argument('--channel', required=True); s.add_argument('--to', required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument('--text'); g.add_argument('--text-file'); g.add_argument('--file')
    s = sub.add_parser('add'); s.add_argument('--key', required=True); s.add_argument('--channel', required=True)
    s.add_argument('--to', required=True); s.add_argument('--status', required=True, choices=STATUSES)
    s.add_argument('--note', default=''); s.add_argument('--ref', default='')
    s = sub.add_parser('check'); s.add_argument('--key', required=True)
    s = sub.add_parser('tail'); s.add_argument('--n', type=int, default=20); s.add_argument('--channel'); s.add_argument('--to')
    a = p.parse_args(argv)
    if a.cmd == 'key':
        if a.text is not None:
            payload = a.text.encode('utf-8')
        elif a.text_file:
            t = open(a.text_file, encoding='utf-8').read()
            payload = (t[:-1] if t.endswith('\n') else t).encode('utf-8')
        else:
            payload = open(a.file, 'rb').read()
        print(make_key(a.channel, a.to, payload))
    elif a.cmd == 'add':
        print(json.dumps(add(a.key, a.channel, a.to, a.status, a.note, a.ref), ensure_ascii=False))
    elif a.cmd == 'check':
        hit = latest(a.key)
        if not hit:
            print('NONE')
            return 1
        print(json.dumps(hit, ensure_ascii=False))
    elif a.cmd == 'tail':
        sel = [r for r in rows() if (not a.channel or r.get('channel') == a.channel) and (not a.to or r.get('to') == a.to)]
        for r in sel[-a.n:]:
            print('%s  %-8s %-9s %s  %s' % (r['at'], r['status'], r['channel'], r['to'], r.get('note', '')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
