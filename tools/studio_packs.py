"""Keeps the Studio's photo packs up to date (Darpan, 25 Oct 2026: 'perfect go live').

    python tools/studio_packs.py site [--days 7] [--dates 2026-12-25,...]

site is a copy of the studio branch. Makes a day pack (tools/dashboard_pack.py) for today and the next days that
don't have one yet, plus any dates asked for, drops day packs more than 3 days old (unless asked for by date, which
stay 60 days), and writes site/packs/index.json listing what the Studio can open. Read only for the daily picture."""
import argparse, datetime, json, os, shutil, subprocess, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--dates', default='')
    a = ap.parse_args()
    packs = os.path.join(a.site, 'packs')
    days_dir = os.path.join(packs, 'day')
    os.makedirs(days_dir, exist_ok=True)
    os.makedirs(os.path.join(packs, 'month'), exist_ok=True)
    keep_file = os.path.join(packs, 'asked.json')
    asked = json.load(open(keep_file)) if os.path.exists(keep_file) else {}
    today = datetime.datetime.now(ZoneInfo('Europe/London')).date()
    want = [today + datetime.timedelta(days=i) for i in range(a.days)]
    for d in filter(None, a.dates.split(',')):
        d = datetime.date.fromisoformat(d.strip())
        want.append(d); asked[str(d)] = str(today)
    for d in want:
        if os.path.exists(os.path.join(days_dir, str(d), 'pack.json')) and str(d) not in a.dates:
            continue
        print('making', d, flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'tools', 'dashboard_pack.py'), str(d), days_dir])
        if r.returncode:
            print('  could not make', d)
            shutil.rmtree(os.path.join(days_dir, str(d)), ignore_errors=True)
    for name in os.listdir(days_dir):   # old packs go, so the branch stays small
        try:
            d = datetime.date.fromisoformat(name)
        except ValueError:
            continue
        old = (today - d).days > 3
        if name in asked:
            old = (today - datetime.date.fromisoformat(asked[name])).days > 60
        if old:
            shutil.rmtree(os.path.join(days_dir, name)); asked.pop(name, None)
    json.dump(asked, open(keep_file, 'w'), indent=1)
    idx = dict(days=sorted(n for n in os.listdir(days_dir) if os.path.exists(os.path.join(days_dir, n, 'pack.json'))),
               months=sorted(n for n in os.listdir(os.path.join(packs, 'month')) if os.path.exists(os.path.join(packs, 'month', n, 'pack.json'))),
               updated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'))
    json.dump(idx, open(os.path.join(packs, 'index.json'), 'w'), indent=1)
    print(idx)


if __name__ == '__main__':
    main()
