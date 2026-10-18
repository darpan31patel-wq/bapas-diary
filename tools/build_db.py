"""Turn the per-year crawl files (bapas-diary-YYYY.json from tools/crawl.js) into archive/vicharan/MM-DD.txt,
one file per day of the year, listing every captioned photo of Bapa on that day in each year.

    python tools/build_db.py /path/to/folder/with/bapas-diary-YYYY.json [--out archive/vicharan]

A photo's date comes from its file name when it carries one (2014_10_16_..., y091016-..., 20111016-...),
otherwise from its page title or address (16 October 2014, 15 to 23 January 1999, ...).
If a year has no photo of Bapa on the exact day, the nearest day of the same trip stands in
(a range page covering the day, else the closest dated photo within NEAR days), so most years still get a photo.
"""
import argparse, collections, datetime, glob, json, os, re, sys

NEAR = 3
MONTHS = 'january february march april may june july august september october november december'.split()
MON = '(' + '|'.join(MONTHS) + ')'
ORD = r'(?:st|nd|rd|th)?'
PSM_TO_MSM = datetime.date(2016, 8, 13)          # Bapa = Pramukh Swami Maharaj before, Mahant Swami Maharaj from
URL = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{file}'

PSM = re.compile(r'Pramukh\s+Swami(\s+Maharaj)?|\bPSM\b', re.I)
MSM = re.compile(r'Mahant\s+Swami(\s+Maharaj)?|\bMSM\b', re.I)
SWAMISHRI = re.compile(r'\bSwamishri\b|\bBapa\b', re.I)
NAME_START = re.compile(r"^(?:(?:HH|HDH|Param\s+Pujya|Pujya|P\.\s*P\.)\s+)?(?:Swamishri|Pramukh\s+Swami\s+Maharaj|Mahant\s+Swami\s+Maharaj)(?:'s)?\s+", re.I)
NOT_BAPA = re.compile(r'\b(murti of|photo of|portrait of|image of|cutout of|painting of|statue of)\s+(Param\s+Pujya\s+|Brahmswarup\s+|Pujya\s+)?(Pramukh|Mahant|Swamishri)', re.I)


def d(y, m, day):
    try:
        return datetime.date(y, m, day)
    except ValueError:
        return None


def file_date(name, year):
    """The date in a photo's file name, if it has one that fits the year."""
    for pat, f in ((r'(?<!\d)(\d{4})[_-]?(\d\d)[_-]?(\d\d)(?!\d)', lambda g: (int(g[0]), int(g[1]), int(g[2]))),
                   (r'(?i)(?<![a-z0-9])y(\d\d)(\d\d)(\d\d)(?!\d)', lambda g: (2000 + int(g[0]), int(g[1]), int(g[2])))):
        for g in re.findall(pat, name):
            y, m, day = f(g)
            if abs(y - year) <= 1 and 1 <= m <= 12:
                x = d(y, m, day)
                if x:
                    return x
    return None


def page_dates(path, title, year):
    """(first, last) day a page covers, from its title or address; None if it names no day."""
    s = (path.rsplit('/', 1)[-1].replace('.aspx', '').replace('-', ' ') + ' | ' + title).lower()
    s = re.sub(r'\s+', ' ', s)
    m = re.search(rf'(\d{{1,2}}){ORD} {MON} (?:to|–|-) (\d{{1,2}}){ORD} {MON}', s)
    if m:
        a, b = d(year, MONTHS.index(m[2]) + 1, int(m[1])), d(year, MONTHS.index(m[4]) + 1, int(m[3]))
        if a and b and a <= b:
            return a, b
    m = re.search(rf'(\d{{1,2}}){ORD} (?:to|–|-|and|&) (\d{{1,2}}){ORD} {MON}', s)
    if m:
        mo = MONTHS.index(m[3]) + 1
        a, b = d(year, mo, int(m[1])), d(year, mo, int(m[2]))
        if a and b and a <= b:
            return a, b
    m = re.search(rf'(\d{{1,2}}){ORD} (?:to )?{MON}', s) or re.search(rf'{MON} (\d{{1,2}}){ORD}\b', s)
    if m:
        g = m.groups()
        day, mo = (g[0], g[1]) if g[0].isdigit() else (g[1], g[0])
        a = d(year, MONTHS.index(mo) + 1, int(day))
        if a:
            return a, a
    return None


def place_of(title):
    t = re.sub(r'\s+', ' ', title)
    if 'Vicharan, ' in t:
        t = t.split('Vicharan, ', 1)[1]
    elif ' - ' in t:
        t = t.rsplit(' - ', 1)[1]
    elif ', ' in t:
        t = t.split(', ', 1)[1]
    parts = [p.strip() for p in t.split(',') if p.strip()]
    return ', '.join(parts[:2])


def about_bapa(c, day):
    """Does the caption say the photo is of Bapa (Pramukh Swami Maharaj until 13 Aug 2016, Mahant Swami Maharaj after)?"""
    if not c or NOT_BAPA.search(c):
        return False
    if day < PSM_TO_MSM:
        return bool(SWAMISHRI.search(c) or PSM.search(c))
    return bool(SWAMISHRI.search(c) or MSM.search(c))


def short(c):
    """'Swamishri blesses devotees' -> 'blesses devotees' (a lower case caption means 'Swamishri ...' to make.py)."""
    c = re.sub(r'\s+', ' ', c).strip().replace('|', '/')
    m = NAME_START.match(c)
    if m and len(c) > m.end():
        rest = c[m.end():]
        if rest[:1].isalpha() and rest.split(' ', 1)[0].lower() not in ('and', 'with', 'at', 'in'):
            return rest[0].lower() + rest[1:]
    return c


def load(folder):
    """{year: [(date or None, (first, last) or None, album, file, caption, place)]}, one entry per photo."""
    out = {}
    for f in sorted(glob.glob(os.path.join(folder, 'bapas-diary-[12][0-9][0-9][0-9].json'))):
        data = json.load(open(f, encoding='utf-8'))
        y = data['year']
        seen = {}
        for p in data['pages']:
            span = page_dates(p['p'], p.get('t', ''), y)
            if y <= 2016 and re.search(r"Mahant Swami Maharaj'?s Vicharan", p.get('t', ''), re.I) and (y < 2016 or (span and span[1] < PSM_TO_MSM)):
                continue          # before 13 Aug 2016 'Swamishri' on Mahant Swami's own vicharan pages is not Bapa
            place = place_of(p.get('t', ''))
            for album, file, cap in p['rows']:
                key = (album, file)
                day = file_date(file, y) or (span[0] if span and span[0] == span[1] else None)
                old = seen.get(key)
                # a photo can show up on a report page and its gallery page: keep the most exact date and a caption
                if old is None or (day and not old[0]) or (span and not old[1] and not old[0]) or (cap and not old[4] and (day or not old[0])):
                    seen[key] = (day, span if span and span[0] != span[1] else None, album, file, cap or (old[4] if old else ''), place or (old[5] if old else ''))
        out[y] = list(seen.values())
    return out


def build(years):
    """{'MM-DD': {year: (actual date, [photos])}} with the exact day, else the trip's range page, else the nearest day."""
    days = collections.defaultdict(dict)
    stats = collections.Counter()
    for y, photos in years.items():
        bapa = []
        for day, span, album, file, cap, place in photos:
            ref = day or (span[0] if span else None)
            if ref and about_bapa(cap, ref):
                bapa.append((day, span, album, file, cap, place))
        stats['bapa'] += len(bapa)
        exact, ranged = collections.defaultdict(list), []
        for x in bapa:
            if x[0]:
                exact[x[0]].append(x)
            elif x[1]:
                ranged.append(x)
        dated = sorted(exact)
        for i in range(366):
            when = datetime.date(2024, 1, 1) + datetime.timedelta(i)       # 2024 has 29 February
            day = d(y, when.month, when.day)
            if not day:
                continue
            mmdd = f'{when:%m-%d}'
            if day in exact:
                days[mmdd][y] = (day, exact[day]); stats['exact'] += 1
                continue
            cover = [x for x in ranged if x[1][0] <= day <= x[1][1]]
            if cover:
                days[mmdd][y] = (day, cover); stats['range'] += 1
                continue
            near = [t for t in dated if abs((t - day).days) <= NEAR]
            gap = lambda x: min(abs((x[1][0] - day).days), abs((x[1][1] - day).days))
            near_r = [x for x in ranged if gap(x) <= NEAR]
            if near or near_r:
                tg = min((abs((t - day).days) for t in near), default=99)
                rg = min((gap(x) for x in near_r), default=99)
                if tg <= rg:
                    t = min(near, key=lambda t: (abs((t - day).days), t > day))
                    days[mmdd][y] = (t, exact[t])
                else:
                    pick = [x for x in near_r if gap(x) == rg]
                    t = pick[0][1][0] if abs((pick[0][1][0] - day).days) == rg else pick[0][1][1]
                    days[mmdd][y] = (t, pick)
                stats['near'] += 1
    return days, stats


def write(days, out):
    os.makedirs(out, exist_ok=True)
    for mmdd, per_year in sorted(days.items()):
        when = datetime.date(2024, int(mmdd[:2]), int(mmdd[3:]))
        lines = [f"# Every captioned photo of Bapa on baps.org's {when.day} {when:%B} vicharan pages, from the full crawl of every year (tools/build_db.py).",
                 '# "#year album prefix|place|date" starts a group (date only when the photo is from a nearby day of the same trip). Each line: photo ids|caption.',
                 '# A caption starting lower case means "Swamishri ...". Photos of murtis, and of devotees doing darshan, are left out.']
        for y in sorted(per_year):
            actual, photos = per_year[y]
            groups = collections.OrderedDict()
            for day, span, album, file, cap, place in photos:
                groups.setdefault((album, place), collections.OrderedDict()).setdefault(short(cap), []).append(file[:-4] if file.lower().endswith('.jpg') else file)
            for (album, place), caps in groups.items():
                note = '' if actual.strftime('%m-%d') == mmdd else '|' + actual.isoformat()
                lines.append(f'#{y} {album}|{place}{note}')
                for cap, ids in caps.items():
                    lines.append(','.join(ids) + '|' + cap)
        open(os.path.join(out, mmdd + '.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'archive', 'vicharan'))
    a = ap.parse_args()
    years = load(a.folder)
    total = sum(len(v) for v in years.values())
    undated = sum(1 for v in years.values() for x in v if not x[0] and not x[1])
    days, stats = build(years)
    write(days, a.out)
    print(f'{len(years)} years, {total} photos ({undated} with no date), {stats["bapa"]} of Bapa')
    print(f'day/year slots filled: {stats["exact"]} exact day, {stats["range"]} from a trip page, {stats["near"]} from a nearby day')
    per = collections.Counter(len(v) for v in days.values())
    print('years per day:', dict(sorted(per.items())))


if __name__ == '__main__':
    sys.exit(main())
