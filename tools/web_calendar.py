"""Calendar page for the website bapas-diary.com (Darpan, 24 Oct 2026: a calendar that scrolls sideways from 1999 to
today, five rows of days a month, each day with a photo of Bapa and the BAPS calendar, and where Bapa was as a
timeline along the top).

Website only: nothing here touches the daily 2pm picture.

    python3 tools/web_calendar.py --db bapas.db --site out --photos-url https://photos.bapas-diary.com/

writes out/calendar/index.html (site/calendar.html), out/fonts/ and out/data/calendar.json:
  {"start": "1999-10",                          the month the page opens on
   "m": {"1999-01": [[indian date, festivals, notes, place, album, file, caption], ...one per day], ...}}
A day's photo is the one the 2pm picture showed that year, else the first photo of Bapa that day, else any photo,
else a photo from a short trip around that day. Photos come from R2 (s/ALBUM/FILE, made by tools/web_photos.py), so
only years listed in site/photo-years.txt get one; the others show the date in big letters until they are copied.
"""
import argparse, base64, concurrent.futures, datetime, glob, gzip, io, json, os, re, shutil, sqlite3, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = (1999, 1)
TRIP_DAYS = 7
FONTS = {'G5': 'eb-garamond-latin-500-normal.woff2', 'G6': 'eb-garamond-latin-600-normal.woff2',
         'A7': 'arimo-latin-700-normal.woff2'}


def months(today):
    y, m = FIRST
    while (y, m) <= (today.year, today.month):
        yield y, m
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)


def build(db, today, photo_years, vary=None):
    place, photo = {}, {}
    rows = db.execute("SELECT date, place, album, file, caption, is_bapa FROM photos WHERE date IS NOT NULL "
                      "ORDER BY date, is_bapa DESC, album, file")
    for date, pl, album, file, cap, bapa in rows:
        pl = (pl or '').split(',')[0].strip()
        if pl:
            place.setdefault(date, pl)
        photo.setdefault(date, [album, file, cap or ''])
    for date, url in db.execute("SELECT date, photo_url FROM diary WHERE photo_url IS NOT NULL"):
        album, file = url.split('/GalleryImages/')[-1].split('/')[0], url.rsplit('/', 1)[-1]
        if db.execute("SELECT 1 FROM photos WHERE album = ? AND file = ?", (album, file)).fetchone():
            cap = db.execute("SELECT caption FROM photos WHERE album = ? AND file = ?", (album, file)).fetchone()[0]
            photo[date] = [album, file, cap or '']
    trip = {}
    for d0, d1, pl, album, file, cap in db.execute(
            "SELECT date_from, date_to, place, album, file, caption FROM photos WHERE date IS NULL AND date_from IS NOT NULL "
            "ORDER BY date_from, is_bapa DESC, album, file"):
        a = datetime.date.fromisoformat(d0)
        b = datetime.date.fromisoformat(d1 or d0)
        if (b - a).days > TRIP_DAYS:
            b = a
        pl = (pl or '').split(',')[0].strip()
        d = a
        while d <= b:
            trip.setdefault(d.isoformat(), [pl, [album, file, cap or '']])
            d += datetime.timedelta(1)
    if vary:
        vary(photo, photo_years)
    cal = {d: [i or '', f or '', n or ''] for d, i, f, n in
           db.execute("SELECT date, indian_date, festivals, notes FROM calendar")}

    out = {}
    for y, m in months(today):
        days = []
        d = datetime.date(y, m, 1)
        while d.month == m and d <= today:
            k = d.isoformat()
            pl = place.get(k) or (trip.get(k) or [''])[0]
            ph = photo.get(k) or (trip.get(k) or [None, None])[1]
            row = cal.get(k, ['', '', '']) + [pl]
            if ph and y in photo_years:
                row += ph
            days.append(row)
            d += datetime.timedelta(1)
        if days:
            out[f'{y}-{m:02d}'] = days
    # opens on this month; while R2 doesn't have this year yet, on this month in the newest year it has
    start = f'{today.year}-{today.month:02d}'
    if today.year not in photo_years and photo_years:
        y = max(photo_years)
        start = f'{y}-{today.month:02d}' if f'{y}-{today.month:02d}' in out else start
    return {'start': start, 'm': out}


# ---------------------------------------------------------------- variety from day to day
# Darpan, 26 Oct 2026: "all these images are all the same, have some variety so the calendar doesn't look so similar".
# Each day takes one of its best few photos of Bapa (from --pool, the Bapa only database), choosing the one that looks
# least like the days around it: the day before, two days before, and the days above it in the calendar (a week
# earlier). "Looks like" = a tiny 8 x 6 colour picture of each photo (the backdrop, the light, how close the shot is),
# kept in --sigs between runs so each photo is only fetched once; the same event (album) the day before counts too.
# Variety never wins over a good darshan: where Bapa's face has been looked at (--faces), a photo where his face is
# small (a wide hall, a corridor) or not recognised costs more than one where he is close and clear.
NOT_BAPA = re.compile(r'murti|portrait|framed|photo of|painting|statue|image of', re.I)
CANDIDATES = 10
NEIGHBOURS = ((1, 1.0), (2, .5), (7, .7), (6, .3), (8, .3))


def signature(data):
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert('RGB').resize((8, 6), Image.BILINEAR)
    return base64.b64encode(im.tobytes()).decode()


def likeness(a, b):
    """1 = the same look, 0 = clearly different."""
    if not a or not b:
        return 0
    x, y = base64.b64decode(a), base64.b64decode(b)
    d = sum(abs(p - q) for p, q in zip(x, y)) / (len(x) * 255)
    return max(0.0, 1 - d / .22)


class Variety:
    def __init__(self, pool, sigs, photos_url, local=None, faces=None):
        self.pool, self.sigs_path, self.url, self.local = pool, sigs, photos_url, local
        self.faces, self.face_years = {}, set()
        for f in sorted(glob.glob(os.path.join(faces or '-', 'face2-*.json.gz'))):
            self.faces.update(json.load(gzip.open(f, 'rt')))
            self.face_years.add(os.path.basename(f).split('-')[1])   # face2-YEAR-part-parts.json.gz
        self.sigs = json.load(open(sigs)) if sigs and os.path.exists(sigs) else {}

    def candidates(self, date, first):
        out = [first] if first else []
        for album, file, cap in self.pool.execute(
                'SELECT album, file, caption FROM photos WHERE date = ? AND is_bapa = 1 ORDER BY rowid', (date,)):
            if NOT_BAPA.search(cap or '') or any(o[0] == album and o[1] == file for o in out):
                continue
            out.append([album, file, cap or ''])
            if len(out) >= CANDIDATES:
                break
        return out

    def darshan(self, c, date):
        """0 = Bapa close and clear; more for a small or unrecognised face (only in years whose faces are looked at)."""
        if not self.faces or date[:4] not in self.face_years:
            return 0
        rec = self.faces.get(f'{c[0]}/{c[1]}')
        if not rec or rec[0] < .38:
            return .45
        x, h = rec[1] + rec[3] / 2, rec[4]
        if h > .42 or not .1 < x < .9:
            return .6   # so close or so near the edge that the square would cut his head
        return .7 if h < .1 else .3 if h < .16 else 0

    def fetch(self, keys):
        def one(k):
            try:
                if self.local:
                    data = open(os.path.join(self.local, k), 'rb').read()
                else:
                    a, f = k.split('/', 1)
                    data = urllib.request.urlopen(f'{self.url}s/{a}/{urllib.parse.quote(f)}', timeout=20).read()
                return k, signature(data)
            except Exception:
                return k, ''
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            for k, sig in ex.map(one, keys):
                self.sigs[k] = sig

    def __call__(self, photo, photo_years):
        days = sorted(d for d in photo if int(d[:4]) in photo_years)
        cands = {d: self.candidates(d, photo[d]) for d in days}
        self.fetch(sorted({f'{c[0]}/{c[1]}' for L in cands.values() for c in L} - set(self.sigs)))
        changed = 0
        for d in days:
            day = datetime.date.fromisoformat(d)
            near = [(w, photo.get((day - datetime.timedelta(k)).isoformat())) for k, w in NEIGHBOURS]
            best, cost = None, None
            for r, c in enumerate(cands[d]):
                sig = self.sigs.get(f'{c[0]}/{c[1]}', '')
                if not sig and r:
                    continue   # couldn't be looked at (not copied yet?): keep to the photos we know are there
                x = .08 * r + self.darshan(c, d) + sum(w * likeness(sig, self.sigs.get(f'{n[0]}/{n[1]}', '')) for w, n in near if n)
                if near[0][1] and near[0][1][0] == c[0]:
                    x += .3   # the same event as yesterday: likely the same stage
                if cost is None or x < cost:
                    best, cost = c, x
            if best and best != photo[d]:
                photo[d] = best
                changed += 1
        if self.sigs_path:
            json.dump(self.sigs, open(self.sigs_path, 'w'), separators=(',', ':'))
        print(f'variety: {changed} of {len(days)} days took a different photo, {len(self.sigs)} looks kept')


def page(site, photos, search):
    os.makedirs(os.path.join(site, 'fonts'), exist_ok=True)
    body = open(os.path.join(HERE, 'site', 'calendar.html'), encoding='utf-8').read()
    for k, f in FONTS.items():
        shutil.copy(os.path.join(HERE, 'fonts', f), os.path.join(site, 'fonts', f))
        body = body.replace('{{FONT_%s}}' % k, '/fonts/' + f)
    body = (body.replace('{{MENU_CSS}}', '/menu.css').replace('{{DATA}}', '/data/calendar.json')
            .replace('{{PHOTOS}}', photos).replace('{{SEARCH}}', search))
    head, body = body.split('</style>\n', 1)   # title, menu link and styles go in the head
    os.makedirs(os.path.join(site, 'calendar'), exist_ok=True)
    with open(os.path.join(site, 'calendar', 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + head + '</style>\n</head>\n<body>\n' + body.lstrip() + '\n</body>\n</html>\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--site', default='out')
    ap.add_argument('--photos-url', default='https://photos.bapas-diary.com/', help='where the s/ photos are (R2)')
    ap.add_argument('--search-url', default='/search/')
    ap.add_argument('--photo-years', default=os.path.join(HERE, 'site', 'photo-years.txt'),
                    help='years whose photos are on R2 (one per line); missing file = every year')
    ap.add_argument('--today', help='YYYY-MM-DD, for testing')
    ap.add_argument('--pool', help='the Bapa only database to choose each day from, for variety (bapa.db)')
    ap.add_argument('--sigs', help='where to keep each photo\'s look between runs (json)')
    ap.add_argument('--faces', help='folder of face2-*.json.gz: where Bapa\'s face is in each photo')
    ap.add_argument('--sig-dir', help='read photos from this folder (ALBUM/FILE) instead of --photos-url')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    if os.path.exists(a.photo_years):
        years = {int(x) for x in open(a.photo_years).read().split() if x.strip().isdigit()}
    else:
        years = set(range(FIRST[0], today.year + 1))
    page(a.site, a.photos_url, a.search_url)
    vary = Variety(sqlite3.connect(a.pool), a.sigs, a.photos_url, a.sig_dir, a.faces) if a.pool else None
    data = build(sqlite3.connect(a.db), today, years, vary)
    os.makedirs(os.path.join(a.site, 'data'), exist_ok=True)
    with open(os.path.join(a.site, 'data', 'calendar.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    n = sum(1 for days in data['m'].values() for d in days if len(d) > 4)
    print(f"calendar: {len(data['m'])} months, {n} days with a photo, opens on {data['start']}")


if __name__ == '__main__':
    main()
