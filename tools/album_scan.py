"""Finds the baps.org vicharan photos that no day page lists (Darpan, 22 Oct 2026: download every single picture).

A day page doesn't always show every photo in its album (his screensaver project found 3 extra in album 37036), so
this checks every photo number each album could hold. Vicharan photos are named <YYYY>_<MM>_<DD>_<NNN>_<Place>.jpg,
so for each album it asks baps.org for the numbers the page skipped and 20 past the last one (more after each find),
and it looks past the newest album known for days the database doesn't have yet (the same trick as the
screensaver's update.py). Only the photos are asked for, never the pages, which sit behind a Cloudflare check.

    python tools/album_scan.py --db bapas.db --scan scan.json --hours 5

scan.json keeps what it found and which albums are done, so the next run carries on. Albums from before about 2012
use other names (01_TP_1999_01_03.jpg) that can't be guessed, so only their pages' photos are known.
"""
import argparse, collections, concurrent.futures, datetime, json, os, re, sqlite3, time, urllib.error, urllib.parse, urllib.request

PHOTO = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/{size}/{file}'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
NAME = re.compile(r'^(\d{4}_\d{2}_\d{2})_(\d{3,4})_(.+)\.jpe?g$', re.I)
NUMBER = re.compile(r'^\d{4}_\d{2}_\d{2}_(\d{3,4})')
PAST_LAST = 20     # numbers to try after the last photo of an album
GIVE_UP = 30       # errors in a row that aren't "not there": baps.org is struggling, stop for now


class Stop(Exception):
    pass


errors = 0


def exists(album, file, size='WebImages'):
    global errors
    req = urllib.request.Request(PHOTO.format(album=album, size=size, file=urllib.parse.quote(file)), method='HEAD',
                                 headers={'User-Agent': UA, 'Accept': 'image/*'})
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                errors = 0
                return r.headers.get('Content-Type', '').startswith('image')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                errors = 0
                return False
        except Exception:
            pass
        time.sleep(2)
    errors += 1
    if errors >= GIVE_UP:
        raise Stop(f'{GIVE_UP} errors in a row from baps.org')
    return False


def name(day, n, place):
    return f'{day}_{n:03d}_{place}.jpg'


def albums(db):
    """{album: (numbers known, [(day, place) most used first])} for every album with guessable names."""
    known, names = collections.defaultdict(set), collections.defaultdict(collections.Counter)
    for album, file in db.execute('SELECT album, file FROM photos'):
        m = NUMBER.match(file)
        if m:
            known[album].add(int(m[1]))
        m = NAME.match(file)
        if m:
            names[album][(m[1], m[3])] += 1
    return {a: (known[a], [p for p, _ in names[a].most_common(3)]) for a in names}


def scan_album(album, nums, prefixes, pool, past=PAST_LAST):
    """Photos in the album that the page didn't list."""
    found, n, top = [], 1, max(nums)
    while n <= top + past:
        batch = [k for k in range(n, min(n + 24, top + past + 1)) if k not in nums]
        n += 24
        for k, hit in zip(batch, pool.map(lambda k: next((name(d, k, p) for d, p in prefixes if exists(album, name(d, k, p))), None), batch)):
            if hit:
                found.append(hit)
                top = max(top, k)
    return found


def new_albums(db, state, pool, today):
    """Albums newer than any the database knows, found by trying recent days and places (like the screensaver)."""
    last = max(int(a) for a, in db.execute('SELECT DISTINCT album FROM photos'))
    last = max(last, state.get('newest_album', 0), *(int(x['album']) for x in state['extra'] if x.get('how') == 'new album'))
    newest = db.execute('SELECT max(date) FROM photos').fetchone()[0]
    since = (datetime.date.fromisoformat(newest) - datetime.timedelta(30)).isoformat()
    places = [p for p, _ in collections.Counter(
        NAME.match(f)[3] for f, in db.execute('SELECT file FROM photos WHERE date >= ?', (since,)) if NAME.match(f)).most_common(8)]
    start = datetime.date.fromisoformat(newest) - datetime.timedelta(1)
    days = [(start + datetime.timedelta(k)).strftime('%Y_%m_%d') for k in range((today - start).days + 1)]
    have = {(x['album']) for x in state['extra']}
    print(f'Looking for new albums after {last}: days {days[0]} to {days[-1]}, places {places}', flush=True)

    def first(a):
        for d in days:
            for p in places:
                if exists(a, name(d, 1, p)) or exists(a, name(d, 2, p)):
                    return a, d, p
        return None

    out = []
    for a, d, p in [r for r in pool.map(first, range(last + 1, last + 121)) if r]:
        if str(a) in have:
            continue
        files = scan_album(str(a), {0}, [(d, p)], pool, past=45)   # a whole album: numbers can skip a lot
        print(f'  new album {a}: {d} {p}, {len(files)} photos', flush=True)
        out += [dict(album=str(a), file=f, how='new album') for f in files]
        state['newest_album'] = max(state.get('newest_album', 0), a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--scan', required=True, help='scan.json, read and written')
    ap.add_argument('--hours', type=float, default=5)
    a = ap.parse_args()
    stop_at = time.time() + a.hours * 3600
    state = json.load(open(a.scan)) if os.path.exists(a.scan) else {}
    state.setdefault('extra', []); state.setdefault('done', {})
    db = sqlite3.connect(a.db)

    def keep():
        state['checked'] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        json.dump(state, open(a.scan, 'w'), indent=0)

    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        try:
            if 'full_size' not in state:   # does baps.org keep the original uploads? (the Mac script asks for them first)
                sample = db.execute('SELECT album, file FROM photos WHERE year >= 2012 ORDER BY random() LIMIT 40').fetchall()
                hits = sum(exists(al, re.sub(r'\.JPE?G$', '.jpg', f, flags=re.I), 'FullSizeImages') for al, f in sample)
                state['full_size'] = dict(tried=len(sample), found=hits)
                print(f'Full size originals: {hits} of {len(sample)} tried', flush=True)
            todo = [(al, v) for al, v in sorted(albums(db).items(), key=lambda kv: -int(kv[0])) if al not in state['done']]
            print(f'{len(todo)} albums left to check', flush=True)
            for k, (album, (nums, prefixes)) in enumerate(todo):
                if time.time() > stop_at:
                    print('Out of time, the next run carries on'); break
                found = scan_album(album, nums, prefixes, pool)
                state['extra'] += [dict(album=album, file=f, how='album scan') for f in found]
                state['done'][album] = len(found)
                if found:
                    print(f'  album {album}: {len(found)} not on its page', flush=True)
                if k % 50 == 0:
                    keep(); print(f'{k} of {len(todo)} albums checked, {len(state["extra"])} extra photos so far', flush=True)
            else:
                state['extra'] += new_albums(db, state, pool, datetime.date.today())
        except Stop as e:
            print('Stopped:', e)
    keep()
    print(f'{len(state["done"])} albums checked in all, {len(state["extra"])} photos found that no page lists')


if __name__ == '__main__':
    main()
