#!/usr/bin/env python3
"""learn.py · the learning ledger that makes every browser run faster than the last.

  learn.py add --site gmail --kind trap|fix|speed|limit|rule --text "what happened -> what works" [--evidence E]
  learn.py show [SITE] [--n 15]          newest first; "•" = waiting to be folded into a playbook, "✓" = folded
  learn.py run  --site gmail --items 200 --ok 200 --minutes 37 [--note N]
  learn.py pace [SITE]                   recent runs per site: seconds per item and success rate, trend
  learn.py pending [SITE]                lines not yet folded into references/sites/SITE.md
  learn.py promote SITE [--ids 3,4]      mark lines as folded in (all pending lines of SITE without --ids)

Data (append-only): $BO_HOME/learnings.jsonl and $BO_HOME/runs.jsonl (default ~/.browser-operator/).
"""
import argparse
import datetime
import json
import os
import sys

KINDS = ('trap', 'fix', 'speed', 'limit', 'rule')


def home():
    h = os.environ.get('BO_HOME') or os.path.join(os.path.expanduser('~'), '.browser-operator')
    os.makedirs(h, exist_ok=True)
    return h


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def read(name):
    p = os.path.join(home(), name)
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def append(name, row):
    with open(os.path.join(home(), name), 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def lessons():
    """Fold the event stream into the current lessons: {id: row with 'promoted' set}."""
    items, order = {}, []
    for r in read('learnings.jsonl'):
        if r.get('event') == 'promote':
            for i in r.get('ids', []):
                if i in items:
                    items[i]['promoted'] = r['at']
        elif 'id' in r:
            r.setdefault('promoted', None)
            items[r['id']] = r
            order.append(r['id'])
    return [items[i] for i in order]


def fmt(r):
    mark = '✓' if r.get('promoted') else '•'
    ev = ('  [%s]' % r['evidence']) if r.get('evidence') else ''
    return '%s #%d %s %-9s %-6s %s%s' % (mark, r['id'], r['at'][:10], r['site'], r['kind'], r['text'], ev)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('add'); s.add_argument('--site', required=True); s.add_argument('--kind', required=True, choices=KINDS)
    s.add_argument('--text', required=True); s.add_argument('--evidence', default='')
    s = sub.add_parser('show'); s.add_argument('site', nargs='?'); s.add_argument('--n', type=int, default=15)
    s = sub.add_parser('run'); s.add_argument('--site', required=True); s.add_argument('--items', type=int, required=True)
    s.add_argument('--ok', type=int, required=True); s.add_argument('--minutes', type=float, required=True); s.add_argument('--note', default='')
    s = sub.add_parser('pace'); s.add_argument('site', nargs='?')
    s = sub.add_parser('pending'); s.add_argument('site', nargs='?')
    s = sub.add_parser('promote'); s.add_argument('site'); s.add_argument('--ids', default='')
    a = p.parse_args(argv)

    if a.cmd == 'add':
        ls = lessons()
        new_id = (max([r['id'] for r in ls]) + 1) if ls else 1
        row = append('learnings.jsonl', {'id': new_id, 'at': now(), 'site': a.site.lower(), 'kind': a.kind,
                                         'text': a.text.strip(), 'evidence': a.evidence.strip()})
        print('saved #%d (%s, %s)' % (row['id'], row['site'], row['kind']))
    elif a.cmd in ('show', 'pending'):
        ls = [r for r in lessons() if not a.site or r['site'] == a.site.lower()]
        if a.cmd == 'pending':
            ls = [r for r in ls if not r.get('promoted')]
            for r in ls:
                print(fmt(r))
            print('%d pending%s' % (len(ls), (' for ' + a.site) if a.site else ''))
        else:
            for r in list(reversed(ls))[:a.n]:
                print(fmt(r))
            if not ls:
                print('no lessons yet%s' % ((' for ' + a.site) if a.site else ''))
    elif a.cmd == 'run':
        if a.items <= 0 or a.minutes <= 0:
            print('items and minutes must be positive', file=sys.stderr)
            return 2
        row = append('runs.jsonl', {'at': now(), 'site': a.site.lower(), 'items': a.items, 'ok': a.ok,
                                    'minutes': a.minutes, 'note': a.note})
        print('run saved: %s, %.1f s per item, %d%% ok' % (row['site'], 60 * a.minutes / a.items, round(100 * a.ok / a.items)))
    elif a.cmd == 'pace':
        runs = [r for r in read('runs.jsonl') if not a.site or r['site'] == a.site.lower()]
        if not runs:
            print('no runs recorded yet')
            return 0
        for site in sorted(set(r['site'] for r in runs)):
            rs = [r for r in runs if r['site'] == site][-5:]
            spi = [60 * r['minutes'] / r['items'] for r in rs]
            trend = ''
            if len(spi) > 1:
                trend = '  faster by %.0f%%' % (100 * (spi[0] - spi[-1]) / spi[0]) if spi[-1] < spi[0] else '  slower by %.0f%%' % (100 * (spi[-1] - spi[0]) / spi[0])
            print('%s: ' % site + ', '.join('%s %.1fs/item %d%%ok' % (r['at'][:10], s, round(100 * r['ok'] / r['items'])) for r, s in zip(rs, spi)) + trend)
    elif a.cmd == 'promote':
        ls = [r for r in lessons() if r['site'] == a.site.lower() and not r.get('promoted')]
        ids = [int(x) for x in a.ids.split(',') if x.strip()] if a.ids else [r['id'] for r in ls]
        ids = [i for i in ids if any(r['id'] == i for r in ls)]
        if not ids:
            print('nothing pending for %s' % a.site)
            return 0
        append('learnings.jsonl', {'event': 'promote', 'at': now(), 'site': a.site.lower(), 'ids': ids})
        print('marked %d lines as folded into references/sites/%s.md: %s' % (len(ids), a.site.lower(), ', '.join('#%d' % i for i in ids)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
