"""Year in review: one page for each whole year of Bapa's Diary, with the year's best darshan, every town Bapa stayed in
on a map, the big moments (murti pratishthas, festivals, new mandirs), the year in numbers and the year month by month
(Darpan, 29 Oct 2026: "at New Year, a lovely page with the best photos and places from the whole year. Also maybe
showing everything he has done, all the big events").

Website only: nothing here touches the daily 2pm picture chain and nothing is fetched from baps.org. Photos come from
R2 (photos.bapas-diary.com), chosen from bapa.db (only photos where Bapa is recognised by face, tools/web_faces.py),
so the page shows Bapa in person only. The towns and their order come from the Travels page, so both pages agree.
Pramukh Swami Maharaj and Mahant Swami Maharaj are side by side at the top of every year.

    python3 tools/web_year.py --db bapa.db --faces faces --travels out/travels/index.html --out out [--years 2025] [--keys keys.txt]

Writes out/year/YYYY/index.html for every whole year with photos (the year just ended appears on 1 January) and
out/year/index.html, which opens the latest one.
"""
import argparse, datetime, glob, gzip, html, json, math, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_bapa_rules as R

PHOTOS = 'https://photos.bapas-diary.com/'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
PSM_UNTIL = R.PSM_UNTIL
# the festivals worth a place among the year's big moments whenever Bapa has darshan photos that day; any other festival
# gets in only when a caption that day names it (he celebrated it, not just that it fell on the calendar)
MAJOR = re.compile(r'diwali|annakut|guru purnima|janma jayanti|pramukh swami maharaj\'s jayanti|ramnavmi|hari-nom|janmashtami|'
                   r'pushpadol|yogi jayanti|gunatitanand swami\'s birthday|vasant panchami', re.I)
CELEBRATE = re.compile(r'arti|procession|pujan|celebrat|assembly|utsav|abhishek|annakut|swings|hindol', re.I)
# murti pratishtha rituals for mandirs far and wide are nearly every week, so one gets a card of its own only when the
# caption names the mandir; the rest are counted in the year in numbers
PRATISHTHA = re.compile(r'(?<!details of the )murti[- ]pratishtha (?:rituals|mahapuja)', re.I)
MOMENT = [   # what a caption says happened, and the title the moment gets
    (re.compile(r'murti[- ]pratishtha (?:rituals )?(?:of|for) .*\bmandirs?\b', re.I), 'Murti pratishtha'),
    (re.compile(r'inaugurat\w* (?:the |a )?(?:new )?(?:\w+ )?mandir', re.I), 'A new mandir opens'),
    (re.compile(r'diksha (?:rituals|mantra)|newly initiated', re.I), 'New swamis take diksha'),
    (re.compile(r'shilanyas', re.I), 'Shilanyas'),
    (re.compile(r'patotsav', re.I), 'Patotsav'),
]
NOT_PHOTO = re.compile(r'portrait|painting|framed|banner|poster|cut-?out|image of|picture of|video|screen|murti of (?:param pujya )?'
                       r'(?:pramukh|mahant|swamishri)', re.I)   # his picture, not him (Darpan, 25 and 26 Oct 2026)


def esc(s):
    return html.escape(s or '', quote=True)


def fmt_date(d, weekday=True):
    t = datetime.date.fromisoformat(d)
    return (t.strftime('%A ') if weekday else '') + f'{t.day} {MONTHS[t.month - 1]}'


def span(a, b):
    ta, tb = datetime.date.fromisoformat(a), datetime.date.fromisoformat(b)
    if a == b:
        return f'{ta.day} {MONTHS[ta.month - 1][:3]}'
    if ta.month == tb.month:
        return f'{ta.day} to {tb.day} {MONTHS[ta.month - 1][:3]}'
    return f'{ta.day} {MONTHS[ta.month - 1][:3]} to {tb.day} {MONTHS[tb.month - 1][:3]}'


def km(a, b):
    (x1, y1), (x2, y2) = [(math.radians(p[0]), math.radians(p[1])) for p in (a, b)]
    h = math.sin((y2 - y1) / 2) ** 2 + math.cos(y1) * math.cos(y2) * math.sin((x2 - x1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def load_faces(folder, years):
    faces = {}
    for f in glob.glob(os.path.join(folder, 'face2-*.json.gz')):
        if int(os.path.basename(f)[6:10]) in years:
            faces.update(json.load(gzip.open(f, 'rt')))
    return faces


def travels(path):
    """The Travels page's own stops (one per stay, in order) and where each town is."""
    s = open(path, encoding='utf-8').read()
    trips = json.loads(re.search(r'<script id="trips" type="application/json">(.*?)</script>', s, re.S).group(1))
    land = json.loads(re.search(r'<script id="land" type="application/json">(.*?)</script>', s, re.S).group(1))
    return trips, land


def land_rings(topo):
    """The world's coastlines from the Travels page's TopoJSON, as rings of [lon, lat]."""
    sx, sy = topo['transform']['scale']
    tx, ty = topo['transform']['translate']
    arcs = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ids):
        out = []
        for i in ids:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out += pts[1:] if out else pts
        return out
    rings = []
    for g in topo['objects']['land']['geometries']:
        polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
        for poly in polys:
            rings += [ring(r) for r in poly]
    return rings


def map_svg(stops, places, rings, numbers, label):
    """A flat map of the year's journey: the land round the towns, the route in gold, a numbered dot for each town
    (numbers: the town's number in the list beside the map)."""
    lls = [places[s['p']]['ll'] for s in stops if s['p'] in places]
    if not lls:
        return ''
    lo0, lo1 = min(p[0] for p in lls), max(p[0] for p in lls)
    la0, la1 = min(p[1] for p in lls), max(p[1] for p in lls)
    c = math.cos(math.radians((la0 + la1) / 2))
    w, h = (lo1 - lo0) * c, la1 - la0
    want = 1.55   # wide map: a long way round the world stays readable, a year in Gujarat is not a thin strip
    if w < 5 * want:
        w = 5 * want
    if h < w / want:
        h = w / want
    if w < h * want:
        w = h * want
    cx, cy = (lo0 + lo1) / 2, (la0 + la1) / 2
    pad = .12
    W = 1000
    sc = W / (w * (1 + 2 * pad))
    H = round(h * (1 + 2 * pad) * sc)

    def xy(p):
        return ((p[0] - cx) * c * sc + W / 2, (cy - p[1]) * sc + H / 2)
    paths = []
    for r in rings:
        if max(p[1] for p in r) < -60:   # Antarctica
            continue
        u = [r[0]]   # a coast across the date line stays in one piece, on the side of the world the map shows
        for x, y in r[1:]:
            x += 360 * round((u[-1][0] - x) / 360)
            u.append((x, y))
        k = 360 * round((cx - sum(x for x, _ in u) / len(u)) / 360)
        r = [(x + k, y) for x, y in u]
        if not any(-W < x < 2 * W and -H < y < 2 * H for x, y in map(xy, r[::4] or r)):
            continue
        paths.append('M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in map(xy, r)) + 'Z')
    route, dots = [], {}
    for s in stops:
        if s['p'] not in places:
            continue
        x, y = xy(places[s['p']]['ll'])
        route.append(f'{x:.1f} {y:.1f}')
        dots.setdefault(s['p'], (numbers[s['p']], x, y))
    days = {}
    for s in stops:
        days[s['p']] = days.get(s['p'], 0) + (datetime.date.fromisoformat(s['b']) - datetime.date.fromisoformat(s['a'])).days + 1
    labels, out = [], []
    for p, (n, x, y) in sorted(dots.items(), key=lambda d: -days.get(d[0], 0)):   # longest stays named first, none on top of another
        anchor = 'end' if x > W * .78 else 'start'
        x0 = x - 16 - 11 * len(places[p]['name']) if anchor == 'end' else x + 14
        x1 = x0 + 16 + 11 * len(places[p]['name'])
        if all(x1 < a or x0 > b or abs(y - ly) > 26 for a, b, ly in labels) and all(abs(x - dx) > 12 or abs(y - dy) > 12 or q == p
                                                                                     for q, (m, dx, dy) in dots.items()):
            labels.append((x0, x1, y))
            out.append(f'<text x="{x + (-14 if anchor == "end" else 14):.0f}" y="{y + 6:.0f}" text-anchor="{anchor}">{esc(places[p]["name"])}</text>')
    dot = ''.join(f'<g class="dot"><circle cx="{x:.1f}" cy="{y:.1f}" r="11"/><text x="{x:.1f}" y="{y + 4:.1f}">{n}</text></g>'
                  for p, (n, x, y) in sorted(dots.items(), key=lambda d: -d[1][0]))
    return (f'<figure class="mapf"><svg class="map" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}: map of the towns Bapa stayed in">'
            f'<path class="land" d="{" ".join(paths)}"/>'
            f'<polyline class="route" points="{" ".join(route)}"/>{dot}<g class="names">{"".join(out)}</g></svg>'
            f'<figcaption class="mapnote">{esc(label)}</figcaption></figure>')


def maps(stays, places, rings):
    """The whole year's journey, and when it went far and wide, a closer map of the country with most of the towns."""
    numbers = {}
    for s in stays:
        if s['p'] in places:
            numbers.setdefault(s['p'], len(numbers) + 1)
    if not numbers:
        return '', numbers
    countries = []
    for p in numbers:
        if places[p]['country'] not in countries:
            countries.append(places[p]['country'])
    lls = [places[p]['ll'] for p in numbers]
    span = max(p[0] for p in lls) - min(p[0] for p in lls)
    out = map_svg(stays, places, rings, numbers, ', '.join(countries) if len(countries) > 1 else countries[0])
    home = max(countries, key=lambda k: sum(1 for p in numbers if places[p]['country'] == k))
    near = [p for p in numbers if places[p]['country'] == home]
    nl = [places[p]['ll'] for p in near]
    if len(countries) > 1 and len(near) >= 4 and max(p[0] for p in nl) - min(p[0] for p in nl) < span / 4:
        out += map_svg([s for s in stays if s['p'] in near], places, rings, numbers, f'Across {home}')
    return out, numbers


class Year:
    def __init__(self, db, faces, year):
        self.db, self.faces, self.year = db, faces, year
        self.rows = []   # every photo of Bapa this year, best of each day first
        for al, fi, d, d0, place, cap, rank, fx, fy, close in db.execute(
                'SELECT p.album, p.file, p.date, p.date_from, p.place, p.caption, b.rank, b.fx, b.fy, b.close FROM photos p '
                'JOIN bapa_pick b USING (album, file) WHERE p.year = ? ORDER BY coalesce(p.date, p.date_from), b.rank', (year,)):
            day = d or d0
            if not day or NOT_PHOTO.search(cap or ''):
                continue
            rec = faces.get(f'{al}/{fi}') or []
            self.rows.append(dict(key=f'{al}/{fi}', day=day, place=place or '', cap=R.tidy(cap or ''), raw=cap or '', rank=rank,
                                  fx=fx if fx is not None else .5, fy=fy if fy is not None else .3, close=close, rec=rec))
        self.used = set()

    def score(self, r, close=True):
        """A clear darshan: recognised for sure, front on, a big sharp face."""
        rec = r['rec']
        if len(rec) < 8:
            return -1 if close else 0
        sim, w, front, sharp, bright = rec[0], rec[3], rec[5], rec[6], rec[7]
        if sharp < R.SHARP_MIN or bright < R.BRIGHT_MIN:
            return -1
        if close:
            return sim + .4 * front + min(sharp, 400) / 700 + min(w, .22) * 3 - r['rank'] * .05 + (.25 if r['close'] else 0)
        if w < .03:   # Bapa too small to see in an activity photo
            return -1
        return sim + .2 * front + min(sharp, 300) / 900 + min(w, .15) * 2 + (.5 if R.is_special(r['raw']) else 0) - r['rank'] * .03

    def best(self, rows, n=1, close=True, one_a_day=True):
        out, days, caps = [], set(), set()
        for r in sorted(rows, key=lambda r: -self.score(r, close)):
            if self.score(r, close) < 0 or r['key'] in self.used:
                continue
            ck = frozenset(R.caption_key(r['cap'])) if r['cap'] else r['key']
            if (one_a_day and r['day'] in days) or ck in caps:
                continue
            out.append(r)
            days.add(r['day'])
            caps.add(ck)
            if len(out) == n:
                break
        for r in out:
            self.used.add(r['key'])
        return out

    def on(self, a, b=None):
        b = b or a
        return [r for r in self.rows if a <= r['day'] <= b]


def moments(y, db, stays):
    """The year's big moments, in date order: the history posts about Bapa's own day, the festivals he celebrated and
    the days a caption tells of a pratishtha, a new mandir or diksha."""
    year = str(y.year)
    where = {}   # day -> the town Bapa was in
    for s in stays:
        t = datetime.date.fromisoformat(s['a'])
        while t.isoformat() <= s['b']:
            where[t.isoformat()] = s['p']
            t += datetime.timedelta(days=1)
    days = {}
    for d, place, line, data in db.execute("SELECT date, place, line, data FROM tg_events WHERE date LIKE ? ORDER BY date", (year + '%',)):
        info = json.loads(data or '{}')
        town = (place or '').split(',')[0].lower()
        if not town or not any(town in (r['place'] + ' ' + where.get(d, '')).lower() for r in y.on(d)):   # Bapa was there that day
            continue
        text = info.get('whatsapp') or info.get('story') or line
        text = re.sub(r'^On this day in \d{4},?\s*', '', text or '')
        text = text[:1].upper() + text[1:]
        title = re.sub(r'^(?:HH |His Holiness )?(?:Param Pujya )?(?:Mahant|Pramukh) Swami Maharaj (?=[a-z])', '', line or '')
        if d not in days and title:
            days[d] = dict(day=d, title=title[:1].upper() + title[1:], text=text, why='history')
    for d, fest, about in db.execute("SELECT date, festivals, festival_about FROM calendar WHERE date LIKE ? AND festivals != ''", (year + '%',)):
        rows = y.on(d)
        if len(rows) < 8 or d in days:
            continue
        names = [f.strip() for f in fest.split(';')]
        words = [w.lower()[:6] for w in re.findall(r'[A-Za-z]{4,}', fest) if w.lower() not in ('swami', 'maharaj', 'shri', 'start', 'birthday')]
        said = [r for r in rows if any(w in r['raw'].lower() for w in words) and CELEBRATE.search(r['raw'])]
        if said or MAJOR.search(fest):
            text = said[0]['cap'] if said else re.split(r'(?<=\.)\s', about or '')[0]
            days[d] = dict(day=d, title=' and '.join(re.sub(r'\s*\(.*?\)', '', n) for n in names), text=text, why='festival')
    for r in y.rows:
        if r['day'] in days or r['day'][:4] != year:
            continue
        for rx, title in MOMENT:
            if rx.search(r['raw']):
                near = [k for k in days if days[k]['title'] == title and
                        abs((datetime.date.fromisoformat(k) - datetime.date.fromisoformat(r['day'])).days) <= 3]
                if not near:   # one card for a pratishtha that runs over a few days
                    days[r['day']] = dict(day=r['day'], title=title, text=r['cap'], why='caption')
                break
    out = []
    for d in sorted(days):
        m = days[d]
        rows = y.on(d)
        special = [r for r in rows if R.is_special(r['raw'])]
        pick = y.best(special, 1, close=False) or y.best(rows, 1, close=False) or y.best(rows, 1)
        if not pick:
            continue
        m['photo'] = pick[0]
        m['place'] = where.get(d) or pick[0]['place'].split(',')[0]
        if not m['text']:
            m['text'] = pick[0]['cap']
        out.append(m)
    return out


def img(r, size='m', cls='', alt=None):
    fx, fy = max(0, min(1, r['fx'])), max(0, min(1, r['fy']))
    return (f'<img class="{cls}" src="{PHOTOS}{size}/{esc(r["key"])}" loading="lazy" decoding="async" '
            f'style="object-position:{fx * 100:.0f}% {fy * 100:.0f}%" alt="{esc(alt if alt is not None else r["cap"])}" '
            f'data-cap="{esc(r["cap"])}" data-day="{r["day"]}" data-big="{PHOTOS}m/{esc(r["key"])}">')


def page(y, db, trips, rings, years, cal):
    year = y.year
    guru = 'Pramukh Swami Maharaj' if year < 2016 else 'Mahant Swami Maharaj' if year > 2016 else 'Pramukh Swami Maharaj and Mahant Swami Maharaj'
    stays = [s for s in trips['years'].get(str(year), [])]
    places = trips['places']
    map_html, numbered = maps(stays, places, rings)
    dist = sum(km(places[a['p']]['ll'], places[b['p']]['ll']) for a, b in zip(stays, stays[1:]) if a['p'] in places and b['p'] in places)
    countries = sorted({places[s['p']]['country'] for s in stays if s['p'] in places})
    mo = moments(y, db, stays)
    mandirs = len({r['day'] for r in y.rows if PRATISHTHA.search(r['raw'])})
    darshan_days = len({r['day'] for r in y.rows})

    # the year's twelve best darshan, one a month, for the top of the page
    heroes = []
    for m in range(1, 13):
        a = f'{year}-{m:02d}-01'
        b = f'{year}-{m:02d}-31'
        heroes += y.best(y.on(a, b), 1)

    nums = [(f'{darshan_days}', 'days of darshan'), (f'{len(numbered)}', 'towns' if len(numbered) != 1 else 'town'),
            (f'{len(countries)}', 'countries' if len(countries) != 1 else 'country')]
    if dist >= 50:
        nums.append((f'{round(dist, -2):,.0f}', 'km travelled'))
    if mandirs:
        nums.append((f'{mandirs}', 'days of murti pratishtha' if mandirs != 1 else 'day of murti pratishtha'))
    nums.append((f'{len(mo)}', 'big moments'))
    nums_html = ''.join(f'<div class="num"><b>{esc(n)}</b><span>{esc(t)}</span></div>' for n, t in nums)

    stays_html = []
    for s in stays:
        n = numbered.get(s['p'])
        photo = y.best(y.on(s['a'], s['b']), 1)
        nm = places.get(s['p'], {}).get('name', s['p'])
        ct = places.get(s['p'], {}).get('country', '')
        d = (datetime.date.fromisoformat(s['b']) - datetime.date.fromisoformat(s['a'])).days + 1
        stays_html.append(
            f'<li><span class="n">{n or ""}</span>{img(photo[0], "s", "th", "") if photo else "<i class=th></i>"}'
            f'<div><b>{esc(nm)}</b><small>{esc(ct)}</small><em>{esc(span(s["a"], s["b"]))} · {d} day{"s" if d != 1 else ""}</em></div></li>')

    mo_html = []
    for m in mo:
        c = cal.get(m['day'], {})
        indian = c.get('indian_date', '')
        mo_html.append(
            f'<article class="moment"><figure>{img(m["photo"], "m", "ph")}</figure><div class="mt">'
            f'<p class="when">{esc(fmt_date(m["day"]))}{" · " + esc(indian) if indian else ""}</p>'
            f'<p class="where">{esc(m["place"])}</p><h3>{esc(m["title"])}</h3><p class="what">{esc(m["text"])}</p>'
            f'<a class="see" href="/search/#date={m["day"]}">See more</a></div></article>')

    months_html = []
    for i in range(12):
        a, b = f'{year}-{i + 1:02d}-01', f'{year}-{i + 1:02d}-31'
        rows = y.on(a, b)
        if not rows:
            continue
        here = []
        for s in stays:
            if s['a'] <= b and s['b'] >= a:
                nm = places.get(s['p'], {}).get('name', s['p'])
                if nm not in here:
                    here.append(nm)
        fests = [m['title'] for m in mo if a <= m['day'] <= b]
        big = y.best(rows, 1)
        small = y.best(rows, 4, close=False)
        if len(small) < 4:
            small += y.best(rows, 4 - len(small))
        pics = big + small
        if not pics:
            continue
        last = max(r['day'] for r in rows)
        months_html.append(
            f'<section class="month"><div class="mh"><h3>{MONTHS[i]}</h3><p class="towns">{esc(" · ".join(here))}</p>'
            + (f'<p class="fests">{esc(" · ".join(fests))}</p>' if fests else '')
            + f'<p class="cnt">{len({r["day"] for r in rows})} days of darshan</p>'
            f'<a class="see" href="/search/#from={a}&amp;to={last}">See more</a></div>'
            f'<div class="mosaic">{"".join(f"<figure>{img(r, "m" if k == 0 else "s", "ph")}</figure>" for k, r in enumerate(pics))}</div></section>')

    best_html = ''.join(f'<figure>{img(r, "m", "ph")}<figcaption>{MONTHS[int(r["day"][5:7]) - 1]}</figcaption></figure>' for r in heroes)
    others = ''.join(f'<a href="/year/{x}/"{" class=on aria-current=page" if x == year else ""}>{x}</a>' for x in years)
    title = f'{year} with Bapa'
    return fill(
        title=esc(title), year=year, guru=esc(guru), lead=esc(
            f'Every town, every festival and the best darshan of {guru}’s {year}, from {len(y.rows):,} photos.'),
        nums=nums_html, map=map_html, stays=''.join(stays_html), moments=''.join(mo_html), months=''.join(months_html),
        best=best_html, others=others)


TEMPLATE = os.path.join(R.HERE, 'site', 'year', 'year.html')   # the page's look; @@name@@ marks where each part goes


def fill(**parts):
    s = open(TEMPLATE, encoding='utf-8').read()
    return re.sub(r'@@(\w+)@@', lambda m: str(parts[m.group(1)]), s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--faces', required=True)
    ap.add_argument('--travels', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--years', default='')
    ap.add_argument('--photos-url', default='https://photos.bapas-diary.com/')
    ap.add_argument('--keys', help='write the photo keys the pages use here (for a mockup)')
    a = ap.parse_args()
    global PHOTOS
    PHOTOS = a.photos_url
    db = sqlite3.connect(a.db)
    last = datetime.date.today().year - 1   # whole years only: the year just ended appears on 1 January
    have = [r[0] for r in db.execute('SELECT DISTINCT p.year FROM photos p JOIN bapa_pick USING (album, file) WHERE p.year <= ? '
                                     'ORDER BY p.year', (last,))]
    want = [int(x) for x in a.years.split(',') if x] or have
    trips, land = travels(a.travels)
    rings = land_rings(land)
    faces = load_faces(a.faces, set(want))
    cal = {r[0]: dict(indian_date=r[1]) for r in db.execute('SELECT date, indian_date FROM calendar')}
    keys = set()
    for year in want:
        y = Year(db, faces, year)
        if not y.rows:
            continue
        d = os.path.join(a.out, 'year', str(year))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'index.html'), 'w', encoding='utf-8').write(page(y, db, trips, rings, have, cal))
        keys |= y.used
        print(f'year in review {year}: {len(y.rows)} photos, {len(y.used)} on the page')
    if have:
        os.makedirs(os.path.join(a.out, 'year'), exist_ok=True)
        open(os.path.join(a.out, 'year', 'index.html'), 'w', encoding='utf-8').write(
            f'<!doctype html><meta charset="utf-8"><title>Year in review</title><meta http-equiv="refresh" content="0; url=/year/{have[-1]}/">'
            f'<link rel="canonical" href="/year/{have[-1]}/"><a href="/year/{have[-1]}/">{have[-1]} with Bapa</a>')
    if a.keys:
        open(a.keys, 'w').write('\n'.join(sorted(keys)) + '\n')


if __name__ == '__main__':
    main()
