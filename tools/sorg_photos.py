"""Photos from the old BAPS website, swaminarayan.org, onto the website's days (Darpan, 13 Nov 2026: "Older years on
Today and the Calendar. swaminarayan.org has Bapa's vicharan from 1999 to 2011 and festivals from 1981 to 1995. Once
it is in, those days can show on Today, the Calendar and Through the years, so far more dates have a photo").

Website only: nothing here touches the daily 2pm picture or the shared database release, and nothing is fetched
from swaminarayan.org. The photos come from the copy the "Collect other BAPS websites" thread saved in Drive
("Bapa's Archive/sites/swaminarayan.org/<site path>") and its detail list (swaminarayan-org-photos.jsonl).

    python3 tools/sorg_photos.py rows  --photos swaminarayan-org-photos.jsonl --db bapas.db --out sorg-rows.json
    python3 tools/sorg_photos.py store --rows sorg-rows.json --have have.txt --remote "gdrive:Bapa's Archive/sites/swaminarayan.org" --send CMD
    python3 tools/sorg_photos.py db    --rows sorg-rows.json --out sorg.db          (only these photos, for the face check)
    python3 tools/sorg_photos.py add   --rows sorg-rows.json --db bapas.db [--have have.txt]   (the website build's copy only)

rows   one row per photo with a day: the full size copy only (the small copy is the same photo), its English date,
       place, caption and where it came from. A photo baps.org already gave us (same day, same caption) is left out,
       so no day shows the same darshan twice. Album: 'sorg-' and the page's folder ('sorg-vicharan-2004-04-02-photo-london').
store  makes the same five sizes every website photo has (tools/hires_photos.py: o, l, m, s, t) and sends them to the
       photo store (R2), skipping those already there. Keeps 04:30 to 07:30 UTC free.
add    puts the rows into the build's copy of the database (source 'swaminarayan.org'), only those whose photo is in the
       store, so no page ever shows an empty square. Today, the Calendar and Through the years then take them only
       when the face check finds Bapa (tools/web_faces.py, faces file face2-YEAR-sorg.json.gz); a clicked Calendar day and
       Search show every one.
"""
import argparse, json, os, re, shutil, sqlite3, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DECOR = re.compile(r'^(title|home|news|line\d*|dot|spacer|logo|banner|bullet|arrow|back|next|prev|top|bottom|head(er)?|'
                   r'menu|button|bg|border|corner|blank|clear|print|mp3|zip|download|map)\b', re.I)
BAPA = re.compile(r'\b(swamishri|pramukh swami|bapa|swami ?bapa|hdh|guruhari|his holiness)\b', re.I)


def norm(c):
    return re.sub(r'[^a-z0-9]+', ' ', (c or '').lower()).strip()


def album_of(page_url):
    path = re.sub(r'^https?://[^/]+/', '', page_url or '')
    path = re.sub(r'/(index|default)\.html?$', '', path)
    path = re.sub(r'\.html?$', '', path)
    return 'sorg-' + re.sub(r'[^A-Za-z0-9]+', '-', path).strip('-').lower()


def rows(a):
    have = set()
    if a.db and os.path.exists(a.db):
        db = sqlite3.connect(a.db)
        for d, c in db.execute("SELECT coalesce(date, date_from), caption FROM photos WHERE coalesce(source, '') != 'swaminarayan.org'"):
            if d and c:
                have.add((d[:10], norm(c)))
    out, seen, why = [], set(), {'kept': 0, 'small copy': 0, 'no day': 0, 'baps.org has it': 0, 'twice': 0}
    for line in open(a.photos, encoding='utf-8'):
        try:
            p = json.loads(line)
        except ValueError:
            continue
        if p.get('content_type') and not str(p['content_type']).startswith('image/'):   # the site's "File Not Found" page
            why['not a photo'] = why.get('not a photo', 0) + 1
            continue
        if p.get('size') == 'small' and p.get('other_size_url'):
            why['small copy'] += 1
            continue
        url = p.get('photo_url', '')
        file = url.rsplit('/', 1)[-1]
        if DECOR.match(file) or '/images/' in url and not (p.get('caption') or p.get('alt')):
            why['site decoration'] = why.get('site decoration', 0) + 1   # the site's own titles, lines and buttons
            continue
        d = p.get('date') or ''
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
            why['no day'] += 1
            continue
        album = album_of(p.get('page_url', ''))
        if (album, file) in seen:
            why['twice'] += 1
            continue
        seen.add((album, file))
        cap = re.sub(r'\s+', ' ', p.get('caption') or p.get('alt') or '').strip()
        if cap and (d, norm(cap)) in have:
            why['baps.org has it'] += 1
            continue
        d1 = p.get('date_to') if re.fullmatch(r'\d{4}-\d{2}-\d{2}', p.get('date_to') or '') else d
        out.append(dict(album=album, file=file, year=int(d[:4]), date=d if d1 == d else None,
                        date_from=d, date_to=d1, place=(p.get('place') or '').strip(), caption=cap,
                        is_bapa=1 if BAPA.search(cap) else 0, drive_path=p.get('drive_path', ''), photo_url=url,
                        page_url=p.get('page_url', ''), date_from_why=p.get('date_from', ''), place_from=p.get('place_from', '')))
        why['kept'] += 1
    out = same_as_baps(out, a.db, why, a.captions)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
    years = {}
    for r in out:
        years[r['year']] = years.get(r['year'], 0) + 1
    print(f'swaminarayan.org photos: {json.dumps(why)}; by year: {json.dumps(dict(sorted(years.items())))}')


def same_as_baps(out, dbpath, why, captions_out=None):
    """baps.org moved the old site's news onto its own pages, keeping the file names (news/2001/06/bhuj/photo/07f.jpg
    is baps.org album 3681's 07f.jpg, 21 June 2001). A page whose photos are mostly in one baps.org album dated within
    15 days is that album: those photos are left out, and the old site's own caption for each is kept in --captions,
    because baps.org often gave every photo of the album the story's title."""
    if not dbpath or not os.path.exists(dbpath):
        return out
    import collections, datetime
    db = sqlite3.connect(dbpath)
    by_name = collections.defaultdict(list)   # file name -> [(date, album, caption)]
    for d, al, f, c in db.execute("SELECT coalesce(date, date_from), album, file, caption FROM photos "
                                  "WHERE year < 2012 AND coalesce(source, '') != 'swaminarayan.org'"):
        if d:
            by_name[f.lower()].append((d[:10], al, c or ''))
    pages = collections.defaultdict(list)
    for r in out:
        pages[r['album']].append(r)
    drop, better = set(), {}
    for album, rs in pages.items():
        votes = collections.Counter()
        for r in rs:
            d0 = datetime.date.fromisoformat(r['date_from'])
            for d, al, c in by_name.get(r['file'].lower(), []):
                if abs((datetime.date.fromisoformat(d) - d0).days) <= 15:
                    votes[al] += 1
        if not votes:
            continue
        al, n = votes.most_common(1)[0]
        if n < min(3, len(rs)):
            continue
        for r in rs:
            hit = next(((d, c) for d, a2, c in by_name.get(r['file'].lower(), []) if a2 == al), None)
            if hit:
                drop.add((r['album'], r['file']))
                if r['caption'] and norm(r['caption']) != norm(hit[1]):
                    better[f"{al}/{r['file']}"] = dict(baps_org=hit[1], swaminarayan_org=r['caption'], page_url=r['page_url'])
    why['baps.org has it'] += len(drop)
    why['kept'] -= len(drop)
    if captions_out:
        json.dump(better, open(captions_out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(f'old site captions for {len(better):,} photos baps.org also has: {captions_out}')
    return [r for r in out if (r['album'], r['file']) not in drop]


def drive_rel(r):
    """the photo's path inside the Drive copy (the site path)"""
    p = r.get('drive_path') or ''
    m = re.search(r'swaminarayan\.org/(.+)$', p)
    if m:
        return m.group(1)
    return re.sub(r'^https?://[^/]+/', '', r['photo_url'])


def store(a):
    import hires_photos as H
    rs = json.load(open(a.rows, encoding='utf-8'))
    have = set(open(a.have).read().split('\n')) if a.have and os.path.exists(a.have) else set()
    todo = [r for r in rs if f"o/{r['album']}/{r['file']}" not in have]
    print(f'{len(todo):,} of {len(rs):,} photos to put in the photo store', flush=True)
    end = time.time() + a.minutes * 60
    inbox, out = os.path.join(a.work, 'in'), os.path.join(a.work, 'out')
    from concurrent.futures import ProcessPoolExecutor
    sent = 0
    with ProcessPoolExecutor() as pool:
        for i in range(0, len(todo), a.chunk):
            if time.time() > end or H.quiet_now():
                print('Stopping for now (out of time, or 04:30 to 07:30 UTC); the next run carries on.')
                break
            part = todo[i:i + a.chunk]
            shutil.rmtree(a.work, ignore_errors=True)
            os.makedirs(inbox)
            with open(os.path.join(a.work, 'list.txt'), 'w') as f:
                f.write('\n'.join(drive_rel(r) for r in part) + '\n')
            subprocess.run(['rclone', 'copy', a.remote, inbox, '--files-from-raw', os.path.join(a.work, 'list.txt'),
                            '--transfers', '4', '--checkers', '4', '--ignore-errors'], check=False)
            jobs = [(os.path.join(inbox, drive_rel(r)), out, f"{r['album']}/{r['file']}") for r in part
                    if os.path.exists(os.path.join(inbox, drive_rel(r)))]
            for err in pool.map(H.make, jobs, chunksize=8):
                if err:
                    print('  could not use', err)
            if jobs and H.send(a.send, out):
                sent += len(jobs)
            print(f'  {min(i + a.chunk, len(todo)):,} of {len(todo):,} ({len(part) - len(jobs)} not in Drive yet)', flush=True)
    shutil.rmtree(a.work, ignore_errors=True)
    print(f'{sent:,} photos now in the photo store')


COLS = ('year', 'date', 'date_from', 'date_to', 'place', 'album', 'file', 'caption', 'is_bapa')


def put(db, rs):
    db.executemany('INSERT OR IGNORE INTO photos (year, date, date_from, date_to, place, album, file, caption, is_bapa, '
                   'source, local_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   [tuple(r[c] for c in COLS) + ('swaminarayan.org', 'sites/swaminarayan.org/' + drive_rel(r)) for r in rs])
    db.commit()


def make_db(a):
    rs = json.load(open(a.rows, encoding='utf-8'))
    if os.path.exists(a.out):
        os.remove(a.out)
    db = sqlite3.connect(a.out)
    db.execute('CREATE TABLE photos (year INTEGER, date TEXT, date_from TEXT, date_to TEXT, place TEXT, album TEXT, file TEXT, '
               'caption TEXT, is_bapa INTEGER, source TEXT, local_path TEXT, PRIMARY KEY (album, file))')
    put(db, rs)
    print(f'{a.out}: {len(rs):,} photos; years {" ".join(str(y) for (y,) in db.execute("SELECT DISTINCT year FROM photos ORDER BY year"))}')


def add(a):
    rs = json.load(open(a.rows, encoding='utf-8'))
    if a.have:
        have = set(open(a.have).read().split('\n')) if os.path.exists(a.have) else set()
        rs = [r for r in rs if f"s/{r['album']}/{r['file']}" in have or f"o/{r['album']}/{r['file']}" in have]
    db = sqlite3.connect(a.db)
    before = db.execute('SELECT count(*) FROM photos').fetchone()[0]
    put(db, rs)
    n = db.execute('SELECT count(*) FROM photos').fetchone()[0] - before
    print(f'swaminarayan.org photos in this build: {n:,} (of {len(rs):,} in the photo store)')
    if a.captions and os.path.exists(a.captions):
        # baps.org gave many old News photos only the story's title ("Divya Satsang Parva Pachmarhi, MP, India" on all
        # eight); where the old site says what is in that very photo ("Swamishri lights the divo to inaugurate the
        # convention"), the build uses those words, so Today's rules can read what Bapa is doing
        better = json.load(open(a.captions, encoding='utf-8'))
        done = 0
        for k, v in better.items():
            al, f = k.split('/', 1)
            same = db.execute('SELECT count(*) FROM photos WHERE album = ? AND caption = ?', (al, v['baps_org'])).fetchone()[0]
            if same >= 3:
                done += db.execute('UPDATE photos SET caption = ? WHERE album = ? AND file = ? AND caption = ?',
                                   (v['swaminarayan_org'], al, f, v['baps_org'])).rowcount
        db.commit()
        print(f"baps.org photos given the old site's own caption: {done:,}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('rows'); r.add_argument('--photos', required=True); r.add_argument('--db'); r.add_argument('--out', required=True)
    r.add_argument('--captions', help="the old site's caption for photos baps.org also has, for the database")
    s = sub.add_parser('store'); s.add_argument('--rows', required=True); s.add_argument('--have')
    s.add_argument('--remote', default="gdrive:Bapa's Archive/sites/swaminarayan.org"); s.add_argument('--send', required=True)
    s.add_argument('--work', default='work'); s.add_argument('--chunk', type=int, default=300); s.add_argument('--minutes', type=float, default=300)
    d = sub.add_parser('db'); d.add_argument('--rows', required=True); d.add_argument('--out', required=True)
    p = sub.add_parser('add'); p.add_argument('--rows', required=True); p.add_argument('--db', required=True); p.add_argument('--have')
    p.add_argument('--captions', help='from rows --captions')
    a = ap.parse_args()
    {'rows': rows, 'store': store, 'db': make_db, 'add': add}[a.cmd](a)


if __name__ == '__main__':
    main()
