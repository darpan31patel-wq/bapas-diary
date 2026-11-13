"""Keeps the Studio's photo packs up to date (Darpan, 25 Oct 2026: 'perfect go live').

    python tools/studio_packs.py site [--days 7] [--dates 2026-12-25,...] [--months 2023-10,...]

site is a copy of the studio branch. Makes a day pack (tools/dashboard_pack.py) for today and the next days that
don't have one yet, plus any dates asked for, drops day packs more than 3 days old (unless asked for by date, which
stay 60 days), and writes site/packs/index.json listing what the Studio can open. Read only for the daily picture.
A day the morning run makes a special picture on (Every Diwali, Every Annakut, a day in BAPS history) also gets a
special pack (tools/special_pack.py) in site/packs/special/<date>/, kept as long as its day pack (Darpan, 6 Nov 2026);
packs/special/checked.json remembers the days already looked at, so a day with no special picture isn't looked at again.
A month poster's pack (Darpan, 13 Nov 2026: 'choose any month of any year in the Studio and make its poster') is made
for every month asked for with --months, and for this month and the next one on every run: see month_packs."""
import argparse, datetime, json, os, re, shutil, subprocess, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def month_packs(packs, asked, today):
    """packs/month/<YYYY-MM>/ for each month asked for, and for this month and the next: the month's photos are picked
    by tools/poster_photos.py and packed by tools/dashboard_month_pack.py, as January 2010, January 2012 and February
    2024 were. packs/month/status.json tells the Studio how each month went: 'made', 'none' (no photos are listed for
    it, a month still to come for one) or 'failed' (the pack made before, if any, is kept). A month asked for is made
    again; this month and the next only when the day lists hold a different number of photos than its pack was made
    from. A month made here goes 60 days after it was last asked for or made; the months put there by hand stay."""
    mdir = os.path.join(packs, 'month')
    status_file = os.path.join(mdir, 'status.json')
    status = json.load(open(status_file)) if os.path.exists(status_file) else {}
    tool = lambda name, *args, **kw: subprocess.run([sys.executable, os.path.join(HERE, 'tools', name), *args], **kw)
    nxt = (today.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    now = [f'{today:%Y-%m}', f'{nxt:%Y-%m}']
    want = []
    for m in [m.strip() for m in asked.split(',') if m.strip()] + now:
        if not re.fullmatch(r'(19|20)\d\d-(0[1-9]|1[0-2])', m):
            print('not a month (YYYY-MM):', m)
        elif m not in want:
            want.append(m)
    for m in want:
        was_asked = m in asked
        pack = os.path.join(mdir, m, 'pack.json')
        try:
            listed = int(tool('poster_photos.py', '--month', m, '--count', capture_output=True, text=True).stdout.strip() or 0)
            if not was_asked and os.path.exists(pack) and json.load(open(pack)).get('listed') == listed:
                continue
            at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')
            st = dict(status.get(m) or {}, at=at, listed=listed)
            if was_asked:
                st['asked'] = str(today)
            status[m] = st
            if not listed:
                print('no photos are listed for', m)
                st['state'] = 'none'
                continue
            print('making the month', m, f'({listed} photos listed)', flush=True)
            st['state'] = 'failed'
            work = os.path.join(HERE, 'preview', 'poster', m)
            shutil.rmtree(work, ignore_errors=True)
            new = os.path.join(mdir, '.new')
            shutil.rmtree(new, ignore_errors=True)
            if tool('poster_photos.py', '--month', m).returncode == 0 and tool('dashboard_month_pack.py', HERE, m, new).returncode == 0:
                made = json.load(open(os.path.join(new, m, 'pack.json')))
                made.update(listed=listed, made=at)
                json.dump(made, open(os.path.join(new, m, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
                shutil.rmtree(os.path.join(mdir, m), ignore_errors=True)
                shutil.move(os.path.join(new, m), os.path.join(mdir, m))
                st['state'] = 'made'
            else:
                print('  could not make the month', m)
            shutil.rmtree(new, ignore_errors=True)
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(os.path.join(HERE, '.cache', 'month'), ignore_errors=True)
        except Exception as e:   # a month never stops the day packs being saved
            print('  could not make the month', m, e)
    for m in list(status):
        last = max(status[m].get('asked', ''), status[m].get('at', '')[:10])
        if m not in now and last and (today - datetime.date.fromisoformat(last)).days > 60:
            shutil.rmtree(os.path.join(mdir, m), ignore_errors=True)
            status.pop(m)
    json.dump(status, open(status_file, 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('site')
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--dates', default='')
    ap.add_argument('--months', default='')
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
    month_packs(packs, a.months, today)
    idx = dict(days=sorted(n for n in os.listdir(days_dir) if os.path.exists(os.path.join(days_dir, n, 'pack.json'))),
               specials=sorted(n for n in os.listdir(specials_dir) if os.path.exists(os.path.join(specials_dir, n, 'pack.json'))),
               months=sorted(n for n in os.listdir(os.path.join(packs, 'month')) if os.path.exists(os.path.join(packs, 'month', n, 'pack.json'))),
               updated=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes'))
    json.dump(idx, open(os.path.join(packs, 'index.json'), 'w'), indent=1)
    print(idx)


if __name__ == '__main__':
    main()
