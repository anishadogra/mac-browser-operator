#!/usr/bin/env python3
"""doctor.py · check this Mac for Mac Browser Operator and say exactly what to fix.

  doctor.py           quick check; touches no browser
  doctor.py --init    also create the data folder (~/.browser-operator or $BO_HOME) and profile.md from the template
  doctor.py --live    also ask an already running Safari for 1+1, which proves "Allow JavaScript from Apple Events";
                      Safari is never launched by this check
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def home():
    return os.environ.get('BO_HOME') or os.path.join(os.path.expanduser('~'), '.browser-operator')


def sh(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or '').strip(), (r.stderr or '').strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, '', str(e)


def running(name):
    return sh(['pgrep', '-x', name])[0] == 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--init', action='store_true')
    p.add_argument('--live', action='store_true')
    a = p.parse_args(argv)
    results = []

    def item(ok, label, fix=''):
        results.append((ok, label, fix))

    is_mac = platform.system() == 'Darwin'
    item(is_mac, 'macOS %s' % (platform.mac_ver()[0] or '?') if is_mac else 'macOS (found %s)' % platform.system(),
         'Safari control and real clicks need a Mac; Chrome via the extension still works elsewhere.')
    item(sys.version_info >= (3, 8), 'Python %s' % platform.python_version(), 'Install Python 3.8 or newer (the macOS python3 is fine).')
    item(bool(shutil.which('osascript')), 'osascript available', 'osascript ships with macOS.')
    for f in ('SKILL.md', 'scripts/safari.py', 'scripts/wa.py', 'scripts/actlog.py', 'scripts/learn.py', 'scripts/js/bo_core.js'):
        if not os.path.exists(os.path.join(SKILL, f)):
            item(False, 'skill file %s' % f, 'Copy the whole skill folder again from the repository.')
            break
    else:
        item(True, 'skill files complete in %s' % SKILL)

    safari_app = os.path.exists('/Applications/Safari.app') or os.path.exists('/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app')
    item(safari_app, 'Safari installed' + (' (running)' if running('Safari') else ' (closed)'), 'Safari comes with macOS.')
    chrome_app = os.path.exists('/Applications/Google Chrome.app') or os.path.exists(os.path.expanduser('~/Applications/Google Chrome.app'))
    item(chrome_app, 'Google Chrome installed' + (' (running)' if running('Google Chrome') else ' (closed)') if chrome_app else 'Google Chrome installed',
         'Install Chrome and the Claude in Chrome extension for Gmail, LinkedIn, Instagram and forms.')

    code, out, err = sh(['osascript', '-l', 'JavaScript', '-e', "ObjC.import('ApplicationServices'); $.AXIsProcessTrusted()"])
    trusted = code == 0 and out.strip() == 'true'
    item(trusted, 'Accessibility granted for real clicks and keys',
         'System Settings > Privacy & Security > Accessibility: turn on the app that runs Claude (Claude, Terminal or iTerm). Needed only for real clicks.')

    if a.live:
        if running('Safari'):
            code, out, err = sh(['osascript', '-e', 'tell application "Safari" to if (count of windows) > 0 then do JavaScript "1+1" in current tab of front window'], timeout=20)
            if code == 0 and out.strip() in ('2', '2.0'):
                item(True, 'Safari answers JavaScript from Apple Events')
            elif 'JavaScript from Apple Events' in err:
                item(False, 'Safari JavaScript from Apple Events is off', 'Safari > Settings > Advanced > "Show features for web developers", then Settings > Developer > "Allow JavaScript from Apple Events".')
            elif '-1743' in err or 'Not authorized' in err:
                item(False, 'Automation permission for Safari is missing', 'System Settings > Privacy & Security > Automation: allow the app running Claude to control Safari.')
            elif code == 0:
                item(True, 'Safari reachable (no window open to test JavaScript)')
            else:
                item(False, 'Safari JavaScript test failed: %s' % (err or out)[:160], 'Run again with a normal web page open in Safari.')
        else:
            item(True, 'Safari live test skipped: Safari is closed (open it yourself, then rerun with --live)')

    h = home()
    profile = os.path.join(h, 'profile.md')
    if a.init:
        os.makedirs(h, exist_ok=True)
        if not os.path.exists(profile):
            shutil.copyfile(os.path.join(SKILL, 'templates', 'profile.md'), profile)
            item(True, 'created %s from the template' % profile)
    item(os.path.isdir(h), 'data folder %s' % h, 'Run doctor.py --init.')
    item(os.path.exists(profile), 'profile.md present', 'Run doctor.py --init, then fill in accounts and standing permissions with the person.')
    for name, label in (('actions.jsonl', 'action log'), ('learnings.jsonl', 'learning ledger'), ('runs.jsonl', 'pace history')):
        f = os.path.join(h, name)
        n = sum(1 for _ in open(f, encoding='utf-8')) if os.path.exists(f) else 0
        item(True, '%s: %d lines' % (label, n))

    node = shutil.which('node')
    item(True, 'node %s' % ('found (optional, for `node --check` on JS helpers)' if node else 'not found (optional)'))

    bad = 0
    for ok, label, fix in results:
        print(('  ok   ' if ok else '  FIX  ') + label)
        if not ok:
            bad += 1
            if fix:
                print('       -> ' + fix)
    print('\nChrome extension: Claude checks for mcp__claude-in-chrome__* tools in its own tool list; install the "Claude in Chrome" extension if they are missing.')
    print('%s' % ('All set.' if not bad else '%d item(s) to fix.' % bad))
    return 0 if not bad else 1


if __name__ == '__main__':
    sys.exit(main())
