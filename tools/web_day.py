"""Day page data for the website bapas-diary.com (Darpan, 23 Oct 2026: the On this day picture as a living page,
every year card fading through all of that year's photos and captions, for all 366 days).

Website only: nothing here touches the daily 2pm picture.

    python3 tools/web_day.py --db bapas.db --out day                      every day of the year, data only
    python3 tools/web_day.py --db bapas.db --out day --days 10-24 --photos   one day, with small photos (mockups)
    python3 tools/web_day.py --db bapas.db --site out --photos-url https://photos.bapas-diary.com/   the home page, ready to put live

--site writes the home page as the website wants it: out/index.html (site/day.html), out/fonts/ and out/data/day/MM-DD.json.

Writes day/MM-DD.json for each day:
  {"date": "10-24", "title": "24 October",
   "years": [{"y": 2014, "place": "Sarangpur",
              "p": [[album, file, caption, bapa], ...],          every photo dated that day, in the day's order
              "trip": [from, to], "t": [[album, file, caption, bapa], ...]}],   photos dated a few days around it
   "cal": {"2014": [indian date, festivals, notes], ...},        the BAPS calendar for this date in every year it has
   "stories": [[year, place, line], ...]}                        On this day stories, older years included
The page loads photos from R2 by album and file (s/ALBUM/FILE, made by tools/web_photos.py).

--photos also saves day/s/ALBUM/FILE (320 px) straight from baps.org, with where the face is ("f": [x, y] after the
bapa flag) so a card centres on it. That is only for mockups: the cloud can't reach R2, the real site uses R2.
"""
import argparse, datetime, io, json, os, sqlite3, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'tools')]

TRIP_DAYS = 14   # photos dated "24 to 27 Oct" show on those days; a longer range only on its first day (Darpan, 26 Oct
                 # 2026: 14 days, not 7). Each day of a trip gets its own share of the trip's photos, in the album's order,
                 # so no photo is shown on two days of the same trip
SMALL = 320


def day_data(db, mmdd):
    day = datetime.date(2000, *map(int, mmdd.split('-')))   # 2000 has 29 February
    years = {}

    def year(y, place):
        return years.setdefault(y, {'y': y, 'place': (place or '').split(',')[0].strip(), 'p': []})

    rows = db.execute("SELECT year, place, album, file, caption, is_bapa FROM photos WHERE substr(date, 6) = ? "
                      "ORDER BY date, album, file", (mmdd,))
    for y, place, album, file, cap, bapa in rows:
        year(y, place)['p'].append([album, file, cap or '', bapa])

    rows = db.execute("SELECT year, place, album, file, caption, is_bapa, date_from, date_to FROM photos "
                      "WHERE date IS NULL ORDER BY date_from, album, file")
    trips = {}
    for y, place, album, file, cap, bapa, d0, d1 in rows:
        trips.setdefault((y, d0, d1), []).append((place, album, file, cap, bapa))
    for (y, d0, d1), photos in trips.items():
        a, b = datetime.date.fromisoformat(d0), datetime.date.fromisoformat(d1 or d0)
        here = None
        for yr in {a.year, b.year}:   # a trip can run over New Year
            try:
                d = datetime.date(yr, day.month, day.day)
            except ValueError:   # 29 February in a year without one
                continue
            if a <= d <= b:
                here = d
        if not here or ((b - a).days > TRIP_DAYS and here != a):
            continue
        days = (b - a).days + 1
        if days <= TRIP_DAYS + 1:   # this day's share: the k-th of as many equal parts as the trip has days
            k = (here - a).days
            photos = photos[k * len(photos) // days:(k + 1) * len(photos) // days]
        if not photos:
            continue
        Y = year(y, photos[0][0])
        Y.setdefault('trip', [d0, d1 or d0])
        Y.setdefault('t', []).extend([album, file, cap or '', bapa] for _, album, file, cap, bapa in photos)

    # the photo the 2pm picture showed that year goes first on its card
    for date, y, url in db.execute("SELECT date, year, photo_url FROM diary WHERE substr(date, 6) = ?", (mmdd,)):
        Y = years.get(y)
        if Y and url:
            album, file = url.split('/GalleryImages/')[-1].split('/')[0], url.rsplit('/', 1)[-1]
            for k, p in enumerate(Y['p']):
                if p[0] == album and p[1] == file:
                    Y['p'].insert(0, Y['p'].pop(k))
                    break

    cal = {d[:4]: [v or '' for v in row] for d, *row in db.execute(
        "SELECT date, indian_date, festivals, notes FROM calendar WHERE substr(date, 6) = ? ORDER BY date", (mmdd,))}

    stories = [[int(d[:4]), (place or '').split(',')[0].strip(), line or headline or '']
               for d, place, line, headline in db.execute(
                   "SELECT date, place, line, headline FROM tg_events WHERE substr(date, 6) = ? ORDER BY date", (mmdd,))
               if line or headline]
    return {'date': mmdd, 'title': f'{day.day} {day:%B}', 'years': [years[y] for y in sorted(years)], 'cal': cal,
            'stories': stories}


def save_photos(data, out, gap):
    """Small copies for a mockup, and where the face is, so the card centres on it."""
    from archive_download import SITE, get
    from PIL import Image, ImageOps
    import make
    for Y in data['years']:
        when = f"{Y['y']}-{data['date']}"
        for p in Y['p'] + Y.get('t', []):
            path = os.path.join(out, 's', p[0], p[1])
            if not os.path.exists(path):
                body, _ = get(SITE.format(album=p[0], size='WebImages', file=p[1]))
                time.sleep(gap)
                if not body:
                    continue
                im = ImageOps.exif_transpose(Image.open(io.BytesIO(body))).convert('RGB')
                face, sim = make.bapa_face(im, when, need=0)
                if face:
                    p.append([round((face[0] + face[2] / 2) / im.width, 3), round((face[1] + face[3] / 2) / im.height, 3)])
                im.thumbnail((SMALL, SMALL * 2), Image.LANCZOS)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                im.save(path, 'JPEG', quality=70, optimize=True, progressive=True)
        print(f"  {Y['y']}: {len(Y['p'])} photos, {len(Y.get('t', []))} from the trip", flush=True)


FONTS = {'G5': 'eb-garamond-latin-500-normal.woff2', 'G6': 'eb-garamond-latin-600-normal.woff2',
         'G7': 'eb-garamond-latin-700-normal.woff2', 'A7': 'arimo-latin-700-normal.woff2'}


def page(site, photos, search):
    """site/day.html as the website's home page, with its fonts."""
    import shutil
    os.makedirs(os.path.join(site, 'fonts'), exist_ok=True)
    body = open(os.path.join(HERE, 'site', 'day.html'), encoding='utf-8').read()
    body = body.replace('<meta charset="utf-8">\n', '')
    for k, f in FONTS.items():
        shutil.copy(os.path.join(HERE, 'fonts', f), os.path.join(site, 'fonts', f))
        body = body.replace('{{FONT_%s}}' % k, '/fonts/' + f)
    body = body.replace('{{MENU_CSS}}', '/menu.css').replace('{{DATA}}', '/data/day/').replace('{{PHOTOS}}', photos).replace('{{SEARCH}}', search)
    head, body = body.split('</style>\n', 1)   # title, menu link and styles go in the head
    with open(os.path.join(site, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '<meta name="description" content="Bapa on this day, every year: darshan photos from 1999 to today, with the BAPS calendar.">\n'
                + head + '</style>\n</head>\n<body>\n' + body.lstrip() + '\n</body>\n</html>\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='day')
    ap.add_argument('--days', nargs='*', help='MM-DD; every day of the year when left out')
    ap.add_argument('--photos', action='store_true', help='also save small photos from baps.org (mockups only)')
    ap.add_argument('--gap', type=float, default=1.0, help='seconds between photos')
    ap.add_argument('--site', help='write the whole home page into this folder (index.html, fonts/, data/day/)')
    ap.add_argument('--photos-url', default='https://photos.bapas-diary.com/', help='where the s/ and m/ photos are (R2)')
    ap.add_argument('--search-url', default='/search/')
    a = ap.parse_args()
    if a.site:
        page(a.site, a.photos_url, a.search_url)
        a.out = os.path.join(a.site, 'data', 'day')
    os.makedirs(a.out, exist_ok=True)
    db = sqlite3.connect(a.db)
    days = a.days or [f'{d:%m-%d}' for d in (datetime.date(2000, 1, 1) + datetime.timedelta(n) for n in range(366))]
    for mmdd in days:
        data = day_data(db, mmdd)
        if a.photos:
            save_photos(data, a.out, a.gap)
        with open(os.path.join(a.out, f'{mmdd}.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        n = sum(len(Y['p']) + len(Y.get('t', [])) for Y in data['years'])
        print(f"{mmdd}: {len(data['years'])} years, {n} photos, {len(data['stories'])} stories", flush=True)


if __name__ == '__main__':
    main()
