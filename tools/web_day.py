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
import argparse, datetime, io, json, os, re, sqlite3, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'tools')]
from web_places import town_of   # never a year as the town: '2004, Los Angeles' is Los Angeles (Darpan's Today, 19 June)

TRIP_DAYS = 14   # photos dated "24 to 27 Oct" show on those days; a longer range only on its first day (Darpan, 26 Oct
                 # 2026: 14 days, not 7). Each day of a trip gets its own share of the trip's photos, in the album's order,
                 # so no photo is shown on two days of the same trip
SMALL = 320


def day_data(db, mmdd):
    day = datetime.date(2000, *map(int, mmdd.split('-')))   # 2000 has 29 February
    years = {}

    def year(y, place):
        return years.setdefault(y, {'y': y, 'place': town_of(place), 'p': []})

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

    stories, seen = [], {}
    for ch, d, place, line, headline, data in db.execute(
            "SELECT channel, date, place, line, headline, data FROM tg_events WHERE substr(date, 6) = ? ORDER BY date", (mmdd,)):
        if not (line or headline):
            continue
        s = [int(d[:4]), town_of(place), line or headline or '']
        more = post_more(db, ch, data, d, line or headline)
        if more:
            s.append(more)
        # the same story told twice (both channels, or a post shared again in other words): keep the one that says more
        old = next((o for o in seen.get(s[0], []) if same_story(o, s)), None)
        if old:
            if len(json.dumps(s[2:])) > len(json.dumps(old[2:])):
                old[2:] = s[2:]
            continue
        seen.setdefault(s[0], []).append(s)
        stories.append(s)
    return {'date': mmdd, 'title': f'{day.day} {day:%B}', 'years': [years[y] for y in sorted(years)], 'cal': cal,
            'stories': stories}


# Darpan, 29 Oct 2026: "there's lots more information on the Telegram group for each post that we're not using". The
# site showed only each post's one line summary; the post itself also gives the day's Indian date, its title and the
# whole story (or, in the UK diary, everything Bapa did that day). post_more() reads those out, with no links, no
# channel names and nothing that names where the words come from (the public site never names its sources).
MONTH = {'kartik': 'Kartak', 'kartak': 'Kartak', 'magshar': 'Magshar', 'magsar': 'Magshar', 'margshirsh': 'Magshar',
         'posh': 'Posh', 'paush': 'Posh', 'maha': 'Maha', 'magh': 'Maha', 'fagan': 'Fagan', 'fagun': 'Fagan',
         'falgun': 'Fagan', 'phagun': 'Fagan', 'chaitra': 'Chaitra', 'chaitar': 'Chaitra', 'vaishakh': 'Vaishakh',
         'vaishakh': 'Vaishakh', 'jeth': 'Jeth', 'jeshth': 'Jeth', 'ashadh': 'Ashadh', 'ashad': 'Ashadh',
         'shravan': 'Shravan', 'bhadarvo': 'Bhadarvo', 'bhadrapad': 'Bhadarvo', 'aso': 'Aso', 'ashvin': 'Aso'}
TITHI = ['', 'Padvo', 'Bij', 'Trij', 'Choth', 'Pancham', 'Chhath', 'Satam', 'Atham', 'Nom', 'Dasham', 'Ekadashi',
         'Baras', 'Teras', 'Chaudas']
TITHI_WORDS = {'punam': 15, 'purnima': 15, 'poonam': 15, 'amas': 30, 'amavasya': 30, 'ekadashi': 11, 'agiyaras': 11}
NOT_SAID = re.compile(r'https?://|www\.|t\.me|telegram|(this|our|the|join) channel|whatsapp|instagram|^\W*(smruti (photos|video)|'
                      r'full program|highlights|video|watch|photos|join|follow|subscribe|link|click)\b|#\w|[🎥📹📸📷🔗👉▶]', re.I)
LINK_NAME = re.compile(r'\b(full program(me)?|playlist|video|watch|live|highlights|bhajan|kirtan|prarthna|prarthana)\b', re.I)


def same_story(a, b):
    """Two stories of one year tell the same thing: their lines, or their first paragraphs, share most of their words."""
    words = lambda t: set(re.findall(r'[a-z]{3,}', (t or '').lower())) - {'the', 'and', 'for', 'with', 'from', 'his', 'swami', 'maharaj'}
    first = lambda s: ((s[3] if len(s) > 3 else {}).get('w') or [''])[0]
    for x, y in ((a[2], b[2]), (first(a), first(b))):
        x, y = words(x), words(y)
        if x and y and len(x & y) / min(len(x), len(y)) >= .6:
            return True
    return False


EMOJI = re.compile('[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]')


def tithi(text):
    """'Aso vad 4', '(Fagun vad 5, VS 1856)', 'Kartik sud Punam' -> 'Aso Vad Choth', as the BAPS calendar writes it."""
    m = re.search(r'\b(adhik\s+)?([a-z]+)\s+(sud|vad|sudi|vadi)\s+(\d{1,2}|[a-z]+)\b', text or '', re.I)
    if not m or m.group(2).lower() not in MONTH:
        return ''
    n = m.group(4).lower()
    n = int(n) if n.isdigit() else TITHI_WORDS.get(n, 0)
    side = 'Sud' if m.group(3).lower().startswith('s') else 'Vad'
    if not 1 <= n <= 30:
        return ''
    name = 'Punam' if n == 15 and side == 'Sud' else 'Amas' if n in (15, 30) else TITHI[n] if n < 15 else ''
    return name and ' '.join(filter(None, ['Adhik' if m.group(1) else '', MONTH[m.group(2).lower()], side, name]))


def post_more(db, ch, data, date, line):
    """{'ti': Indian date, 'h': the post's own title, 'w': [what it says, a paragraph or a line each], 'l': 1 for a UK
    diary day (a list of what Bapa did)} from the story's own post, or None."""
    import web_bapa_rules as R
    try:
        e = json.loads(data or '{}')
        n = int(str(e.get('url') or '').rstrip('/').rsplit('/', 1)[-1])
    except ValueError:
        return None
    row = db.execute('SELECT text FROM tg_posts WHERE channel = ? AND id = ?', (ch, n)).fetchone()
    text = (row and row[0] or '').replace('\r', '')
    if not text.strip() or text.rstrip().endswith('…'):   # a cut short copy of a post says nothing new
        return None
    blocks = [[l.strip() for l in b.split('\n') if l.strip()] for b in re.split(r'\n\s*\n', text)]
    lines = [l for b in blocks for l in b]
    out = {}
    head = lines[:4]   # the date, the Indian date, the place(s) and the title come first, in that order
    for l in head:
        if not out.get('ti') and len(l) < 60:
            out['ti'] = tithi(l)
    if not out.get('ti'):
        out.pop('ti', None)
    place = (e.get('place') or '').split(',')[0].strip().lower()
    said, title = [], ''
    for b in blocks:
        keep = []
        for l in b:
            short = len(l) < 70 and not re.search(r'[.!?]["’”]?$', l)
            if short and (re.match(r'^\(?\w*,?\s*\d{1,2}(st|nd|rd|th)?\s+\w+,?\s+\d{4}', l) or tithi(l) or
                          re.fullmatch(r'\(?(VS|Samvat)\s*\d*\)?', l, re.I)):
                continue   # the date and Indian date lines
            if short and not said and not keep and (l.split(',')[0].strip().lower() == place or re.search(
                    r',\s*(India|UK|USA|Kenya|Canada|Australia|Uganda|Tanzania|UAE|France|Belgium|Germany|Switzerland|'
                    r'Netherlands|Italy|Portugal|Sweden|New Zealand|Singapore|South Africa)\b', l) or ch == 'satpurush'):
                continue   # the place line(s): the card shows the place already
            if NOT_SAID.search(l):
                # the name of the link that follows goes with it ('Smruti Bhajan: Kem Re Tolay', then the link)
                if re.search(r'https?://|www\.', l) and keep and len(keep[-1]) < 70 and not re.search(r'[.!?]$', keep[-1]):
                    keep.pop()
                continue
            if len(l) < 80 and LINK_NAME.search(l) and not re.search(r'[.!?]$', l) and ch != 'satpurush':
                continue   # 'Grand Dedication Playlist': a link's name, its link already gone
            keep.append(l)
        if keep:
            said.append(' '.join(keep) if ch != 'satpurush' else keep)
    if ch == 'satpurush':   # a diary day: each thing Bapa did is its own line
        said = [l.rstrip('.').strip() for b in said for l in b]
        out['l'] = 1
    if said and ch != 'satpurush' and len(said[0]) < 90 and not re.search(r'[.!?]$', said[0]):
        title = said.pop(0)   # a short first line with no full stop is the post's title
    d = datetime.date.fromisoformat(date)
    own = rf'(?:{d.day}(?:st|nd|rd|th)?\s+{d:%B}|{d:%B}\s+{d.day}(?:st|nd|rd|th)?),?\s+{d.year}'
    said = [EMOJI.sub('', s).strip() for s in said]   # the posts' little pictures ('🛕 In 1984, ...') stay with the posts
    said = [re.sub(rf'^On\s+{own},?\s+', 'On this day, ', s) for s in said]   # the card shows the date already
    said = [re.sub(rf',?\s+on\s+(?:the\s+(?:morning|afternoon|evening|night)\s+of\s+)?{own}\b', '', s) for s in said]
    said = [re.sub(r'\s+', ' ', R.undate(s, date) if s else s).strip() for s in said]
    said = [re.sub(r'([.!?])\s*:\s+', r'\1 ', s) for s in said]   # '...children.: He has written' (a list run together)
    told = {(line or '').lower().rstrip('.'), (line or '').split(': ', 1)[-1].lower().rstrip('.')}   # 'in London: Dhanteras'
    # a diary day keeps every line (the page leaves out the one its summary already says); a story drops its summary
    said = [s for s in said if s and (ch == 'satpurush' or s.lower().rstrip('.') not in told)]
    title = re.sub(r',\s*(India|UK|USA|Kenya|Canada|Australia|UAE)$', '', EMOJI.sub('', title)).strip()
    if title and title.lower() not in (line or '').lower():
        out['h'] = title
    while said and len(' '.join(said)) > 1600:   # a long story: its first part, never a cut sentence
        said.pop()
    if said:
        out['w'] = said
    else:
        out.pop('l', None)
    return out or None


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
