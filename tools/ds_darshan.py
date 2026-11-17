"""baps.org's daily darshan photo ("Swamishri's Darshan" on each Daily Satsang page) onto Through the years (baps.org find 2;
Darpan, 13 Nov 2026 "Yes to all"; mockup 17 Nov 2026). Each page gives one photo of Bapa with its month, year and place
("Param Pujya Pramukh Swami MaharajJune 1995, Tithal India"), so years before 1999 get darshan too.

Website only: nothing here touches the daily 2pm picture or the shared database release.

    python3 tools/ds_darshan.py rows  --ds dailysatsang.json --out ds-rows.json
    python3 tools/ds_darshan.py store --rows ds-rows.json --have have.txt --send CMD     (on a GitHub runner)
    python3 tools/ds_darshan.py add   --rows ds-rows.json --db bapas.db --have have.txt  (the build's copy only)

rows   one row per photo: album 'bapsds-YYYY-MM-DD' (the baps.org page's date), file 'YYMMDDS.jpg', the month as a date
       range (date_from the 1st, date_to the last day: baps.org gives only the month), place, guru, and everything
       baps.org said (caption line, page link, photo link) for the database (Darpan, 13 Nov 2026: full detail).
store  fetches each photo file from baps.org (image files only, one at a time, a pause between, never 04:30 to 07:30 UTC,
       stops at once if baps.org asks for a check: never past Cloudflare), makes the website's sizes
       (tools/hires_photos.py: o, l, m, s, t) and sends them to the photo store (R2).
add    puts the rows into the build's copy of the database (source 'baps.org daily darshan'), only those in the photo
       store. Through the years then lines up his eyes in them like every other photo (tools/faces_years.py).
"""
import argparse, calendar, json, os, re, shutil, sqlite3, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LINE = re.compile(r"Swamishri'?s Darshan\s*\n\s*(?:Param Pujya |HDH |Pragat Brahmaswarup )*(Pramukh|Mahant) Swami Maharaj\s*"
                  r"([A-Z][a-z]+)\s+(\d{4})\s*,?\s*([^\n]*)")
MONTHS = {m: i for i, m in enumerate(calendar.month_name) if m}
PSM_UNTIL = '2016-08-13'
SOURCE = 'baps.org daily darshan'
FIX = {'Saranpur': 'Sarangpur'}   # a spelling slip on one baps.org page


def place_of(s):
    s = re.sub(r'\s+', ' ', s).strip(' ,.')
    parts = [p.strip() for p in re.split(r',\s*', s) if p.strip()]
    if len(parts) == 1 and ' ' in parts[0]:   # "Tithal India"
        w = parts[0].rsplit(' ', 1)
        if w[1] in ('India', 'UK', 'USA', 'Kenya', 'Canada', 'Uganda', 'Tanzania', 'Australia', 'ME', 'UAE'):
            parts = w
    town = FIX.get(parts[0], parts[0]) if parts else ''
    return town, ', '.join([town] + parts[1:]) if parts else ''


def rows(a):
    ds = json.load(open(a.ds, encoding='utf-8'))
    if isinstance(ds, dict):
        ds = [dict(v, date=k) for k, v in ds.items()]
    out, why = [], {'kept': 0, 'no darshan line': 0, 'no photo': 0, 'guru and date disagree': 0}
    for d in ds:
        m = LINE.search(d.get('text') or '')
        if not m:
            why['no darshan line'] += 1; continue
        guru, mon, year, where = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if mon not in MONTHS:
            why['no darshan line'] += 1; continue
        mo = MONTHS[mon]
        src = [p['src'] for p in d.get('photos') or d.get('imgs') or [] if isinstance(p, dict) and re.search(r'/dailysatsang/\d{4}/\d{6}S\.jpe?g$', p.get('src', ''), re.I)]
        if not src:
            why['no photo'] += 1; continue
        date_from = f'{year}-{mo:02d}-01'
        date_to = f'{year}-{mo:02d}-{calendar.monthrange(year, mo)[1]:02d}'
        if (guru == 'Pramukh') != (date_from < PSM_UNTIL):
            why['guru and date disagree'] += 1; continue
        town, full = place_of(where)
        out.append(dict(album=f"bapsds-{d['date']}", file=src[0].rsplit('/', 1)[1], year=year, date=None, date_from=date_from,
                        date_to=date_to, month=f'{mon} {year}', place=town, place_full=full,
                        guru=f'{guru} Swami Maharaj', caption="Swamishri's darshan", is_bapa=1,
                        baps_line=m.group(0).split('\n', 1)[1].strip(), photo_url=src[0], page_url=d.get('url') or '',
                        page_date=d['date'], source=SOURCE))
        why['kept'] += 1
    out.sort(key=lambda r: (r['date_from'], r['page_date']))
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    years = sorted({r['year'] for r in out})
    print(f'{a.out}: {len(out)} darshan photos, years {" ".join(map(str, years))}; {why}')


def store(a):
    import hires_photos as H
    import requests
    rs = json.load(open(a.rows, encoding='utf-8'))
    have = set(open(a.have).read().split('\n')) if a.have and os.path.exists(a.have) else set()
    todo = [r for r in rs if f"o/{r['album']}/{r['file']}" not in have]
    print(f'{len(todo)} of {len(rs)} photos to put in the photo store', flush=True)
    S = requests.Session()
    S.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
    inbox, out = os.path.join(a.work, 'in'), os.path.join(a.work, 'out')
    end, sent = time.time() + a.minutes * 60, 0
    for i in range(0, len(todo), a.chunk):
        shutil.rmtree(a.work, ignore_errors=True); os.makedirs(inbox)
        jobs, stop = [], False
        for r in todo[i:i + a.chunk]:
            if time.time() > end or H.quiet_now():
                print('Stopping for now (out of time, or 04:30 to 07:30 UTC); the next run carries on.'); stop = True; break
            time.sleep(a.gap)
            try:
                g = S.get(r['photo_url'], timeout=40)
            except Exception as e:
                print('  could not fetch', r['photo_url'], e); continue
            if g.status_code in (403, 429, 503) or not g.headers.get('content-type', '').startswith('image'):
                print(f"  baps.org said {g.status_code} ({g.headers.get('content-type', '')}): stopping, never past a check"); stop = True; break
            p = os.path.join(inbox, r['album'], r['file']); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(g.content)
            jobs.append((p, out, f"{r['album']}/{r['file']}"))
        for j in jobs:
            err = H.make(j)
            if err:
                print('  could not use', err)
        if jobs and H.send(a.send, out):
            sent += len(jobs)
        print(f'  {sent} sent so far', flush=True)
        if stop:
            break
    shutil.rmtree(a.work, ignore_errors=True)
    print(f'{sent} photos now in the photo store')


def add(a):
    text = open(a.rows, encoding='utf-8').read().strip() if os.path.exists(a.rows) else ''
    rs = json.loads(text) if text else []
    if a.have:
        have = set(open(a.have).read().split('\n')) if os.path.exists(a.have) else set()
        rs = [r for r in rs if f"m/{r['album']}/{r['file']}" in have or f"o/{r['album']}/{r['file']}" in have]
    db = sqlite3.connect(a.db)
    cols = {c[1] for c in db.execute('PRAGMA table_info(photos)')}
    want = ['year', 'date', 'date_from', 'date_to', 'place', 'album', 'file', 'caption', 'is_bapa', 'source']
    use = [c for c in want if c in cols]
    before = db.execute('SELECT count(*) FROM photos').fetchone()[0]
    db.executemany(f'INSERT OR IGNORE INTO photos ({", ".join(use)}) VALUES ({", ".join("?" * len(use))})',
                   [tuple(r[c] for c in use) for r in rs])
    db.commit()
    print(f'baps.org daily darshan photos in this build: {db.execute("SELECT count(*) FROM photos").fetchone()[0] - before} (of {len(rs)} in the photo store)')
    if a.years:
        print('\n'.join(str(y) for y in sorted({r['year'] for r in rs})), file=open(a.years, 'a'))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('rows'); r.add_argument('--ds', required=True); r.add_argument('--out', required=True)
    s = sub.add_parser('store'); s.add_argument('--rows', required=True); s.add_argument('--have'); s.add_argument('--send', required=True)
    s.add_argument('--work', default='work'); s.add_argument('--chunk', type=int, default=100)
    s.add_argument('--minutes', type=float, default=120); s.add_argument('--gap', type=float, default=3)
    p = sub.add_parser('add'); p.add_argument('--rows', required=True); p.add_argument('--db', required=True); p.add_argument('--have')
    p.add_argument('--years', help='add their years to this list (faces_years --years)')
    a = ap.parse_args()
    {'rows': rows, 'store': store, 'add': add}[a.cmd](a)


if __name__ == '__main__':
    main()
