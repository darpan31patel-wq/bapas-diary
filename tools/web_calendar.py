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
import argparse, datetime, json, os, shutil, sqlite3

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


def build(db, today, photo_years):
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
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    if os.path.exists(a.photo_years):
        years = {int(x) for x in open(a.photo_years).read().split() if x.strip().isdigit()}
    else:
        years = set(range(FIRST[0], today.year + 1))
    page(a.site, a.photos_url, a.search_url)
    data = build(sqlite3.connect(a.db), today, years)
    os.makedirs(os.path.join(a.site, 'data'), exist_ok=True)
    with open(os.path.join(a.site, 'data', 'calendar.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    n = sum(1 for days in data['m'].values() for d in days if len(d) > 4)
    print(f"calendar: {len(data['m'])} months, {n} days with a photo, opens on {data['start']}")


if __name__ == '__main__':
    main()
