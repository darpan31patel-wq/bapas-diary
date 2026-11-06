"""Keeps the Studio's photo packs up to date (Darpan, 25 Oct 2026: 'perfect go live').

    python tools/studio_packs.py site [--days 7] [--dates 2026-12-25,...]

site is a copy of the studio branch. Makes a day pack (tools/dashboard_pack.py) for today and the next days that
don't have one yet, plus any dates asked for, drops day packs more than 3 days old (unless asked for by date, which
stay 60 days), and writes site/packs/index.json listing what the Studio can open. Read only for the daily picture.
A day the morning run makes a special picture on (Every Diwali, Every Annakut, a day in BAPS history) also gets a
special pack (tools/special_pack.py) in site/packs/special/<date>/, kept as long as its day pack (Darpan, 6 Nov 2026);
packs/special/checked.json remembers the days already looked at, so a day with no special picture isn't looked at again."""
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
        made = os.path.join(days_dir, str(d), 'pack.json')
        # a pack made before every photo of the year was kept (28 Oct 2026), or before each photo carried its album's
        # first and last day (6 Nov 2026), is made again
        if os.path.exists(made) and str(d) not in a.dates and json.load(open(made)).get('albums'):
            continue
        print('making', d, flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'tools', 'dashboard_pack.py'), str(d), days_dir])
        if r.returncode:
            print('  could not make', d)
            shutil.rmtree(os.path.join(days_dir, str(d)), ignore_errors=True)
    specials_dir = os.path.join(packs, 'special')
    os.makedirs(specials_dir, exist_ok=True)
    checked_file = os.path.join(specials_dir, 'checked.json')
    checked = json.load(open(checked_file)) if os.path.exists(checked_file) else {}
    for d in want:   # the special picture's pack, on the days the morning run makes one
        if str(d) not in a.dates and (checked.get(str(d)) == 'none' or os.path.exists(os.path.join(specials_dir, str(d), 'pack.json'))):
            continue
        print('looking for a special picture on', d, flush=True)
        shutil.rmtree(os.path.join(specials_dir, str(d)), ignore_errors=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'tools', 'special_pack.py'), str(d), specials_dir])
        if r.returncode == 2:
            checked[str(d)] = 'none'
        elif r.returncode:
            print('  could not make the special pack for', d)
            shutil.rmtree(os.path.join(specials_dir, str(d)), ignore_errors=True)
            checked.pop(str(d), None)   # tried again on the next run
        else:
            checked[str(d)] = 'made'
    for folder in (days_dir, specials_dir):   # old packs go, so the branch stays small
        for name in os.listdir(folder):
            try:
                d = datetime.date.fromisoformat(name)
            except ValueError:
                continue
            old = (today - d).days > 3
            if name in asked:
                old = (today - datetime.date.fromisoformat(asked[name])).days > 60
            if old:
                shutil.rmtree(os.path.join(folder, name))
    for name in list(asked):
        if not os.path.exists(os.path.join(days_dir, name)) and not os.path.exists(os.path.join(specials_dir, name)) \
                and (today - datetime.date.fromisoformat(asked[name])).days > 60:
            asked.pop(name)
    checked = {k: v for k, v in checked.items() if (today - datetime.date.fromisoformat(k)).days <= 3 or k in asked}
    json.dump(checked, open(checked_file, 'w'), indent=1)
    json.dump(asked, open(keep_file, 'w'), indent=1)
    idx = dict(days=sorted(n for n in os.listdir(days_dir) if os.path.exists(os.path.join(days_dir, n, 'pack.json'))),
               specials=sorted(n for n in os.listdir(specials_dir) if os.path.exists(os.path.join(specials_dir, n, 'pack.json'))),
               months=sorted(n for n in os.listdir(os.path.join(packs, 'month')) if os.path.exists(os.path.join(packs, 'month', n, 'pack.json'))),
               updated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'))
    json.dump(idx, open(os.path.join(packs, 'index.json'), 'w'), indent=1)
    print(idx)


if __name__ == '__main__':
    main()
