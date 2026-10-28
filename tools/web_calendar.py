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


def months(last):
    y, m = FIRST
    while (y, m) <= (last.year, last.month):
        yield y, m
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)


# ---------------------------------------------------------------- the future (Darpan, 26 Oct 2026)
# "Carry the calendar on past today": the coming months show the BAPS calendar for each day, and where Bapa is going
# (his upcoming vicharan), clearly marked FUTURE CALENDAR and FUTURE VICHARAN. The vicharan comes from the baps.org
# schedule page his Chrome helper saves daily (crawl/schedule/latest.json on the database branch); nothing here
# fetches baps.org. Only that page's text is used: its list of stays, then each place's days and what happens.
FUTURE_MONTHS = 18          # at most this far ahead (the BAPS calendar table is usually filled to the end of next year)
EVERY_DAY = re.compile(r'^(No Events|Puja Darshan|Evening Sabha|Morning Sabha|-+|Date & Day|Morning|Evening)$', re.I)
DAY_LINE = re.compile(r'^(\d{1,2} [A-Z][a-z]{2} \d{4}), [A-Z][a-z]+day$')
STAY_LINE = re.compile(r'^(\d{1,2} [A-Z][a-z]{2} \d{4}) to (\d{1,2} [A-Z][a-z]{2} \d{4})$')


def _date(s):
    return datetime.datetime.strptime(s, '%d %b %Y').date()


def schedule(path, today):
    """{date: [place, what happens]} for the days after today, from the saved vicharan schedule page."""
    try:
        lines = [x.strip() for x in json.load(open(path, encoding='utf-8'))['text'].splitlines() if x.strip()]
    except Exception as e:
        print(f'vicharan: no schedule ({e})')
        return {}
    out, events = {}, {}
    for i, x in enumerate(lines):          # the stays: a place, then "20 Oct 2026 to 4 Nov 2026"
        m = STAY_LINE.match(x)
        if m and i:
            d, b = _date(m[1]), _date(m[2])
            while d <= b:
                out[d.isoformat()] = [lines[i - 1], '']   # a later stay's first day wins (he arrives that day)
                d += datetime.timedelta(1)
    place, day = None, None
    for i, x in enumerate(lines):          # each place's days: "Schedule of Swamishri's Vicharan", the place, the days
        if x.startswith('Schedule of Swamishri') and i + 1 < len(lines):
            place, day = lines[i + 1], None
        elif x.startswith('\u00a9') or x.startswith('©'):
            place, day = None, None
        elif place and DAY_LINE.match(x):
            day = _date(DAY_LINE.match(x)[1]).isoformat()
        elif place and day and not EVERY_DAY.match(x) and not re.match(r'^(Morning|Evening)\s*:', x):
            events.setdefault(day, {}).setdefault(place, []).append(x)
    for d, by in events.items():
        if d in out:
            out[d][1] = ' · '.join(x for e in by.values() for x in e)   # a moving day: "Viday · Aagman"
    out = {d: v for d, v in out.items() if d > today.isoformat()}
    print(f'vicharan: {len(out)} days ahead, {sum(1 for v in out.values() if v[1])} with something happening')
    return out


def build(db, today, photo_years, vary=None, ahead=None):
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

    # the future: every day the BAPS calendar has, up to FUTURE_MONTHS ahead; a day after today has no photo, and
    # where Bapa is going (ahead) instead of where he was
    last = today
    if ahead is not None and cal:
        cap = datetime.date(today.year + (today.month + FUTURE_MONTHS - 1) // 12, (today.month + FUTURE_MONTHS - 1) % 12 + 1, 1)
        last = max(today, min(datetime.date.fromisoformat(max(cal)), cap - datetime.timedelta(1)))
    out, vich = {}, {}
    for y, m in months(last):
        days = []
        d = datetime.date(y, m, 1)
        while d.month == m and d <= last:
            k = d.isoformat()
            if d > today:
                pl, what = (ahead or {}).get(k, ['', ''])
                days.append(cal.get(k, ['', '', '']) + [pl])
                if what:
                    vich[k] = what
            else:
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
    data = {'start': start, 'm': out}
    if last > today:
        data['fut'] = (today + datetime.timedelta(1)).isoformat()   # the first day of the FUTURE CALENDAR
        data['v'] = vich                                           # what happens on a FUTURE VICHARAN day
    return data


# ---------------------------------------------------------------- variety from day to day
# Darpan, 26 Oct 2026: "all these images are all the same, have some variety so the calendar doesn't look so similar".
# Each day takes one of its best few photos of Bapa (from --pool, the Bapa only database), choosing the one that looks
# least like the days around it: the day before, two days before, and the days above it in the calendar (a week
# earlier). "Looks like" = a tiny 8 x 6 colour picture of each photo (the backdrop, the light, how close the shot is),
# kept in --sigs between runs so each photo is only fetched once; the same event (album) the day before counts too.
# Darpan, 26 Oct 2026 (late): "choose the best picture for the day, the same as On this day, a mix of close ups and
# activity pictures". So the day's candidates are On this day's own ranking (bapa_pick in --pool: a close darshan
# first, unless a special action shot), only its best few, and the best one wins unless it looks much like the days
# around it; a close up the day after a close up (or an activity after an activity) costs a little, so the two mix.
# No rule of his own about faces: only a photo the square would cut his head off in costs more.
NOT_BAPA = re.compile(r'murti|portrait|framed|photo of|painting|statue|image of', re.I)
CANDIDATES = 4
RANK = .3        # each step down On this day's ranking
LOOK = .6        # how much looking like the days around it counts
SAME_KIND = .45  # close up after close up, activity after activity
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
        self.kind = {}   # 'ALBUM/FILE': 1 a close up, 0 an activity (On this day's own word for it)
        try:
            self.kind = {f'{a}/{f}': c for a, f, c in pool.execute('SELECT album, file, close FROM bapa_pick')}
            self.order = ('SELECT p.album, p.file, p.caption FROM photos p JOIN bapa_pick b USING (album, file) '
                          'WHERE p.date = ? ORDER BY b.rank, p.rowid')
        except sqlite3.Error:   # an older pool without On this day's ranking
            self.order = 'SELECT album, file, caption FROM photos WHERE date = ? AND is_bapa = 1 ORDER BY rowid'

    def candidates(self, date, first):
        out = [first] if first else []
        for album, file, cap in self.pool.execute(self.order, (date,)):
            if NOT_BAPA.search(cap or '') or any(o[0] == album and o[1] == file for o in out):
                continue
            out.append([album, file, cap or ''])
        # On this day's best few, and its best activity picture when those are all close ups (or the other way round)
        best = out[:CANDIDATES - 1]
        other = [c for c in out[CANDIDATES - 1:] if {self.kind.get(f'{c[0]}/{c[1]}')} - {self.kind.get(f'{b[0]}/{b[1]}') for b in best}]
        return best[:1] + other[:1] + best[1:] if other else out[:CANDIDATES]

    def darshan(self, c, date):
        """0 = fine in a square; more where the square would cut his head (only in years whose faces are looked at)."""
        if not self.faces or date[:4] not in self.face_years:
            return 0
        rec = self.faces.get(f'{c[0]}/{c[1]}')
        if not rec or not rec[0]:
            return 0
        x, h = rec[1] + rec[3] / 2, rec[4]
        return .6 if h > .42 or not .1 < x < .9 else 0

    def fetch(self, keys):
        errors = []

        def one(k):
            try:
                if self.local:
                    data = open(os.path.join(self.local, k), 'rb').read()
                else:
                    a, f = k.split('/', 1)
                    # a browser's name: Cloudflare turns away Python's own (the first live run read no photo at all)
                    req = urllib.request.Request(f'{self.url}s/{a}/{urllib.parse.quote(f)}',
                                                 headers={'User-Agent': 'Mozilla/5.0 (bapas-diary calendar)'})
                    data = urllib.request.urlopen(req, timeout=20).read()
                return k, signature(data)
            except Exception as e:
                errors.append(f'{k}: {e}')
                return k, ''
        with concurrent.futures.ThreadPoolExecutor(16) as ex:   # every year's photos once, then kept
            for k, sig in ex.map(one, keys):
                self.sigs[k] = sig
        print(f'looks: {len(keys) - len(errors)} of {len(keys)} photos read' + (f', first miss {errors[0]}' if errors else ''))

    def __call__(self, photo, photo_years):
        days = sorted(d for d in photo if int(d[:4]) in photo_years)
        cands = {d: self.candidates(d, photo[d]) for d in days}
        self.fetch(sorted({f'{c[0]}/{c[1]}' for L in cands.values() for c in L} - {k for k, v in self.sigs.items() if v}))   # misses are tried again
        changed = 0
        for d in days:
            day = datetime.date.fromisoformat(d)
            near = [(w, photo.get((day - datetime.timedelta(k)).isoformat())) for k, w in NEIGHBOURS]
            best, cost = None, None
            for r, c in enumerate(cands[d]):
                sig = self.sigs.get(f'{c[0]}/{c[1]}', '')
                if not sig and r:
                    continue   # couldn't be looked at (not copied yet?): keep to the photos we know are there
                x = RANK * r + self.darshan(c, d) + LOOK * sum(w * likeness(sig, self.sigs.get(f'{n[0]}/{n[1]}', '')) for w, n in near if n)
                if near[0][1] and near[0][1][0] == c[0]:
                    x += .3   # the same event as yesterday: likely the same stage
                kind, before = self.kind.get(f'{c[0]}/{c[1]}'), near[0][1] and self.kind.get(f'{near[0][1][0]}/{near[0][1][1]}')
                if kind is not None and kind == before:
                    x += SAME_KIND
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
    ap.add_argument('--schedule', help='the saved baps.org vicharan schedule (crawl/schedule/latest.json); '
                    'with it the calendar carries on into the coming months')
    ap.add_argument('--sig-dir', help='read photos from this folder (ALBUM/FILE) instead of --photos-url')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    if os.path.exists(a.photo_years):
        years = {int(x) for x in open(a.photo_years).read().split() if x.strip().isdigit()}
    else:
        years = set(range(FIRST[0], today.year + 1))
    page(a.site, a.photos_url, a.search_url)
    vary = Variety(sqlite3.connect(a.pool), a.sigs, a.photos_url, a.sig_dir, a.faces) if a.pool else None
    ahead = schedule(a.schedule, today) if a.schedule else None
    data = build(sqlite3.connect(a.db), today, years, vary, ahead)
    os.makedirs(os.path.join(a.site, 'data'), exist_ok=True)
    with open(os.path.join(a.site, 'data', 'calendar.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    n = sum(1 for days in data['m'].values() for d in days if len(d) > 4)
    print(f"calendar: {len(data['m'])} months, {n} days with a photo, opens on {data['start']}")


if __name__ == '__main__':
    main()
