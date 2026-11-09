"""Turn the per-year crawl files (bapas-diary-YYYY.json from tools/crawl.js) into archive/vicharan/MM-DD.txt,
one file per day of the year, listing every captioned photo of Bapa on that day in each year.

    python tools/build_db.py /path/to/folder/with/bapas-diary-YYYY.json [--out archive/vicharan]

A photo's date comes from its file name when it carries one (2014_10_16_..., y091016-..., 20111016-...),
otherwise from its page title or address (16 October 2014, 15 to 23 January 1999, ...).
Every dated photo is kept (make.py picks). If a year has nothing on the exact day, the nearest day of the same trip stands in
(a trip page covering the day, else the closest dated photo), never more than NEAR days away (Darpan, 3 Nov 2026: only
3 days before or after the actual day). A trip page's photos carry no day of their own, so it counts only when its whole
trip lies within NEAR days of the day.
"""
import argparse, collections, datetime, glob, json, os, re, sys

NEAR = 3          # a nearby day of the same trip stands in for a missing one, at most 3 days before or after (was up to a week)
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


def continued(rows, when):
    """A caption starting '...' carries on from the photo before it ('... and performs arti of Thakorji'):
    when that one is of Bapa, this one is too, and reads 'Swamishri performs arti of Thakorji'. HTML in a caption is dropped."""
    out, prev = [], ''
    for album, file, cap in rows:
        cap = re.sub(r'<[^>]+>', '', cap or '').replace('\ufffd', "'").strip()
        m = re.match(r'^(?:\.\.\.|…|\.\.)\s*(?:(?:and|then|And|Then)\s+)*(.*)$', cap)
        if m:
            rest = m.group(1).strip()
            if (rest[:1].islower() or about_bapa(prev, when)) and rest[:1].isalpha() and not re.match(r'(Shri|Bhagwan|Thakorji|Pujya|Param)\b', rest) and not NOT_BAPA.search(rest):
                cap = 'Swamishri ' + rest[0].lower() + rest[1:]
            else:
                cap = rest
        out.append((album, file, cap))
        prev = cap
    return out


def short(c):
    """'Swamishri blesses devotees' -> 'blesses devotees' (a lower case caption means 'Swamishri ...' to make.py)."""
    c = re.sub(r'\s+', ' ', c).strip().replace('|', '/')
    m = NAME_START.match(c)
    if m and len(c) > m.end():
        rest = c[m.end():]
        if rest[:1].isalpha() and rest.split(' ', 1)[0].lower() not in ('and', 'with', 'at', 'in'):
            return rest[0].lower() + rest[1:]
    return c


MON_SHORT = {m[:3]: i + 1 for i, m in enumerate(MONTHS)}


def text_dates(found, year):
    """Dates in the body text of a page ('6 Sep 1999', '10 Sept.', 'Sept 12, 2004'), as (first, last) in that year."""
    out = []
    for t in found:
        t = t.strip().rstrip('.,')
        m = re.match(rf'(\d{{1,2}})\w*(?:\s*(?:to|-|–|&|and)\s*(\d{{1,2}})\w*)?\s+([A-Za-z]+)\.?,?\s*(\d{{4}})?$', t)
        if m:
            days, mon, yr = [m.group(1)] + ([m.group(2)] if m.group(2) else []), m.group(3), m.group(4)
        else:
            m = re.match(rf'([A-Za-z]+)\.?\s+(\d{{1,2}})\w*(?:\s*(?:to|-|–|&|and)\s*(\d{{1,2}}))?,\s*(\d{{4}})$', t)   # 'July 11, 2004' only with a comma and year
            if not m:
                m = re.match(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$', t)
                if m and int(m.group(3)) == year and d(year, int(m.group(2)), int(m.group(1))):
                    out.append(d(year, int(m.group(2)), int(m.group(1))))
                continue
            days, mon, yr = [m.group(2)] + ([m.group(3)] if m.group(3) else []), m.group(1), m.group(4)
        if yr and int(yr) != year:
            continue
        mo = MON_SHORT.get(mon[:3].lower())
        if not mo:
            continue
        for day in days:
            x = d(year, mo, int(day))
            if x:
                out.append(x)
    if not out or (max(out) - min(out)).days > 45:    # a page about many events: no single trip to pin it to
        return None
    return min(out), max(out)


def load(folder, fixes=None):
    """{year: [(date or None, (first, last) or None, album, file, caption, place)]}, one entry per photo.
    fixes: bapas-diary-fixes.json from a second look in Chrome: body text dates of undated pages, rows of pages that failed."""
    out = {}
    fx = json.load(open(fixes, encoding='utf-8')) if fixes and os.path.exists(fixes) else {'dates': {}, 'rows': {}}
    for f in sorted(glob.glob(os.path.join(folder, 'bapas-diary-[12][0-9][0-9][0-9].json'))):
        data = json.load(open(f, encoding='utf-8'))
        y = data['year']
        seen = {}
        for p in data['pages']:
            if p.get('failed') and fx['rows'].get(p['p']):
                p = dict(p, t=fx['rows'][p['p']]['t'], rows=fx['rows'][p['p']]['rows'], failed=False)
            span = page_dates(p['p'], p.get('t', ''), y)
            if not span and fx['dates'].get(p['p']):
                span = text_dates(fx['dates'][p['p']]['f'], y)
            rows = continued(p['rows'], span[0] if span else datetime.date(y, 7, 1))
            # 'Swamishri' is left as it is. baps.org files 36 pages of 1999 under "HH Mahant Swami Maharaj's Vicharan" though they
            # are Pramukh Swami Maharaj's tours, and before 13 Aug 2016 Swamishri is always Pramukh Swami Maharaj. Turning it into
            # 'Mahant Swami Maharaj' there (24 Oct 2026) put the wrong guru's name on 335 photos (Darpan, 31 Oct 2026).
            place = place_of(p.get('t', ''))
            for album, file, cap in rows:
                key = (album, file)
                day = file_date(file, y) or (span[0] if span and span[0] == span[1] else None)
                old = seen.get(key)
                # a photo can show up on a report page and its gallery page: keep the most exact date and a caption
                if old is None or (day and not old[0]) or (span and not old[1] and not old[0]) or (cap and not old[4] and (day or not old[0])):
                    seen[key] = (day, span if span and span[0] != span[1] else None, album, file, cap or (old[4] if old else ''), place or (old[5] if old else ''))
        out[y] = list(seen.values())
    return out


# ---------------------------------------------------------------- the baps.org News galleries
# Darpan, 9 Nov 2026 ('use all articles and photos'): the News articles and their photo galleries (crawl/news/articles.json,
# read in his Chrome 4 to 6 Nov 2026) join the day lists. A News article can be about anything anywhere (a kids' sports
# day in New Jersey), so its photos only join a day when Bapa was there: the article or its captions speak of Swamishri
# and its town is where the vicharan pages put him on that day (when the vicharan pages say nothing for that day, the
# article's own words decide).
# Only the exact English date counts: a photo's own dated file name, else the article's date when the article is of one day.
# News photos are only ever added: they never take the place of a vicharan photo, and make.py's face check still decides.
TOWN_ALIAS = {'amdavad': 'ahmedabad', 'delhi': 'new delhi', 'bombay': 'mumbai', 'baroda': 'vadodara', 'atladara': 'vadodara', 'atladra': 'vadodara',
              'neasden': 'london', 'calcutta': 'kolkata', 'gadhada': 'gadhada', 'gadhda': 'gadhada', 'sarangpur': 'sarangpur', 'salangpur': 'sarangpur',
              'navsari': 'navsari', 'tithal': 'tithal', 'gandhinagar': 'gandhinagar'}
NOT_TOWN = {'india', 'uk', 'usa', 'canada', 'kenya', 'uganda', 'tanzania', 'south africa', 'australia', 'new zealand', 'uae', 'europe', 'uk & europe',
            'north america', 'africa', 'asia pacific', 'gujarat', 'england', 'worldwide', 'uk and europe', 'east africa', 'middle east'}
PRESENT = re.compile(r"\bSwamishri\b|\b(?:presence|blessings in person) of (?:HH |H\.H\. |His Holiness |Param Pujya |Pujya |P\.P\. )?(?:Pramukh|Mahant) Swami", re.I)


def towns(place):
    """'London, New Delhi' or 'Atladara (Vadodara), India' -> {'london', 'new delhi'}, {'vadodara'} (countries are not towns)."""
    out = set()
    for part in re.split(r'[,/()&]| and | to ', place or ''):
        t = re.sub(r'\s+', ' ', part).strip().lower()
        if t and t not in NOT_TOWN and not re.fullmatch(r'[a-z]{2}', t):
            out.add(TOWN_ALIAS.get(t, t))
    return out


def bapa_towns(years):
    """{date: towns} where the vicharan pages put Bapa: a dated photo's page, and every day of a trip page."""
    out = collections.defaultdict(set)
    for photos in years.values():
        for day, span, album, file, cap, place in photos:
            if day:
                out[day] |= towns(place)
            elif span and (span[1] - span[0]).days <= 31:
                for i in range((span[1] - span[0]).days + 1):
                    out[span[0] + datetime.timedelta(i)] |= towns(place)
    return out


def news_place(place):
    """'London, UK & Europe' -> 'London, UK'; a News place that is not a town and country ('My Best Friend | Shishu Din,
    UK & Europe', 'BAPS Shri Swaminarayan Mandir, North America') is left empty: make.py then uses the year's own place."""
    parts = [x.strip() for x in (place or '').replace(' & Europe', '').split(',') if x.strip()]
    if not parts or '|' in place or not towns(parts[0]) or re.search(r'Mandir|Din\b|Celebration', parts[0]):
        return ''
    return ', '.join(parts)


def news_caption(cap, section, title):
    """(caption, has its own words): a gallery photo's own caption; when it has none, or it only repeats the article's
    title ("Parents' Day, London, UK 2006"), the event's name is the caption ("Parents' Day") and it counts as a title."""
    strip = lambda t: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t or '').replace('\u2019', "'").replace('\ufffd', "'")).strip()
    cap, title, section = re.sub(r'\s*-\s*$', '', strip(cap)), strip(title), strip(section)
    parts = [x.strip() for x in title.split(',') if x.strip()]
    name = parts[0] if parts else ''                                   # 'Akshardham Shilnyas Vidhi, New Delhi, India' -> the event
    low = cap.lower()
    own = bool(cap) and not (name and low.startswith(name.lower()) and len(cap) <= len(title) + 6) and low != section.lower()
    if own:
        return cap, True
    return name or cap, False


def many_days(path, a, year, when=None):
    """True when a News article is not of its one listed day: it covers a festival week or a tour, or its own words and
    gallery headings give other days ('4 Nov. Diksha', '6 Nov. Murti-Pratishtha' under an article listed on 11 Nov).
    Its photos then belong to no single date unless their own file names carry one."""
    span = page_dates(path, a.get('t') or '', year)
    if span and span[0] != span[1]:
        return True
    days = {file_date(r[1], year) for g in (a.get('g') or {}).values() for r in g.get('rows') or []} - {None}
    head = ((a.get('text') or '')[:600] + ' ' + ' '.join(a.get('g') or {})).lower().replace('-', ' ')
    if len(days) > 1 or re.search(r'\b\d{1,2}(?:st|nd|rd|th)?\s*(?:to|\u2013)\s*\d{1,2}(?:st|nd|rd|th)?\s+' + MON, head):
        return True
    said = set()
    for m in re.finditer(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?(?:,?\s+(\d{4}))?', head):
        if not m[3] or int(m[3]) == year:
            said.add((MON_SHORT[m[2]], int(m[1])))
    for m in re.finditer(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?,\s+(\d{4})', head):
        if int(m[3]) == year:
            said.add((MON_SHORT[m[1]], int(m[2])))
    return bool(when and said and said != {(when.month, when.day)})


def load_news(path, years):
    """({year: [photos]}, counts): the News gallery photos that belong in the day lists, in the same shape as load()
    gives ((date, None, album, file, caption, place)), and how many were left out and why."""
    stats, out = collections.Counter(), {}
    if not path or not os.path.exists(path):
        return out, stats
    where = bapa_towns(years)
    have = {(x[2], x[3].lower()) for v in years.values() for x in v}
    for apath, a in sorted(json.load(open(path, encoding='utf-8')).items()):
        when = a.get('date')
        if not when:
            stats['no date'] += 1
            continue
        day0 = datetime.date.fromisoformat(when)
        if day0.year not in years:
            stats['before 1999'] += 1
            continue
        town = towns(a.get('place'))
        says = bool(PRESENT.search((a.get('t') or '') + ' ' + (a.get('text') or '')))
        gals = list((a.get('g') or {}).items()) + [('', {'t': '', 'rows': a.get('own') or []})]   # a gallery's own captions first
        words = (a.get('t') or '') + ' ' + (a.get('text') or '')
        spread = many_days(apath, a, day0.year, day0)
        any_named = any(about_bapa(r[2], day0) for gp, g in gals for r in g.get('rows') or [] if len(r) > 2 and r[2] and r[2] != a.get('t'))
        seen = set()
        for gp, g in gals:
            section = re.sub(r'-\d+$', '', gp.rsplit('/', 1)[-1].replace('.aspx', '')).replace('-', ' ') if gp else ''
            caps = [news_caption(r[2] if len(r) > 2 else '', section, a.get('t')) for r in g.get('rows') or []]
            rows = continued([(r[0], r[1], c[0]) for r, c in zip(g.get('rows') or [], caps)], day0)
            for (album, file, cap), (_, own) in zip(rows, caps):
                key = (album, file.lower())
                if key in seen or key in have:
                    continue
                seen.add(key)
                day = file_date(file, day0.year)
                if day and abs((day - day0).days) > 31:
                    day = None
                if not day and spread:                        # a festival week or a tour: no single day to give it
                    stats['from an article of many days'] += 1
                    continue
                day = day or day0
                known = set().union(*(where.get(day + datetime.timedelta(k), set()) for k in (-1, 0, 1)))
                named = about_bapa(cap, day)
                if known and town:
                    ok = bool(town & known) and (says or named or any_named)
                    why = 'Bapa was in another town' if not town & known else 'the article does not speak of Bapa'
                elif known:                                   # 'UK & Europe', 'North America': only when the words name his town
                    ok = (says or named) and any(re.search(rf'\b{re.escape(t)}\b', words, re.I) for t in known)
                    why = 'Bapa was in another town'
                else:
                    ok = says or named
                    why = 'the article does not speak of Bapa'
                if not ok:
                    stats[why] += 1
                    continue
                have.add(key)
                out.setdefault(day.year, []).append((day, None, album, file, cap, news_place(a.get('place')) + ('|news' if own else '|newstitle')))
                stats['added'] += 1
                stats['added, captioned as Bapa'] += named
    return out, stats


def build(years):
    """{'MM-DD': {year: (actual date, [photos])}} with the exact day, else the trip's range page, else the nearest day."""
    days = collections.defaultdict(dict)
    stats = collections.Counter()
    for y, photos in years.items():
        bapa = [x for x in photos if x[0] or x[1]]     # every dated photo stays in (Darpan: don't cut anything out); make.py picks
        stats['bapa'] += sum(1 for day, span, album, file, cap, place in bapa if about_bapa(cap, day or span[0]))
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
            far = lambda x: max(abs((x[1][0] - day).days), abs((x[1][1] - day).days))   # the furthest day a trip page's photo could be from
            cover = [x for x in ranged if x[1][0] <= day <= x[1][1] and far(x) <= NEAR]
            if cover:
                days[mmdd][y] = (day, cover); stats['range'] += 1
                continue
            gap = lambda x: min(abs((x[1][0] - day).days), abs((x[1][1] - day).days))
            near = [t for t in dated if abs((t - day).days) <= NEAR]
            near_r = [x for x in ranged if far(x) <= NEAR]
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


def write(days, out, news=None):
    os.makedirs(out, exist_ok=True)
    for mmdd in sorted(set(days) | set(news or {})):
        per_year = days.get(mmdd, {})
        when = datetime.date(2024, int(mmdd[:2]), int(mmdd[3:]))
        lines = [f"# Every captioned photo of Bapa on baps.org's {when.day} {when:%B} vicharan pages, from the full crawl of every year (tools/build_db.py).",
                 '# "#year album prefix|place|date" starts a group (date only when the photo is from a nearby day of the same trip). Each line: photo ids|caption.',
                 '# A caption starting lower case means "Swamishri ...". Every photo is listed, murtis and devotees too; make.py picks.']
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
        # the News galleries come after every vicharan group, so a year's place and first photos stay the vicharan pages' own.
        # Only a News photo of the exact English date (Darpan, 9 Nov 2026): never a nearby day, never a festival week.
        # '#year album|place||news' marks them; 'newstitle' when the photo has no words of its own, only the article's title.
        for y in sorted((news or {}).get(mmdd, {})):
            actual, photos = news[mmdd][y]
            if actual.strftime('%m-%d') != mmdd:
                continue
            groups = collections.OrderedDict()
            for day, span, album, file, cap, place in photos:
                groups.setdefault((album, place), collections.OrderedDict()).setdefault(short(cap), []).append(file[:-4] if file.lower().endswith('.jpg') else file)
            for (album, place), caps in groups.items():
                place, tag = place.rsplit('|', 1)
                lines.append(f'#{y} {album}|{place}||{tag}')
                for cap, ids in caps.items():
                    for k in range(0, len(ids), 2):          # make.py reads two photos a line: every News photo gets its turn
                        lines.append(','.join(ids[k:k + 2]) + '|' + cap)
        open(os.path.join(out, mmdd + '.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'archive', 'vicharan'))
    ap.add_argument('--fixes', help='bapas-diary-fixes.json (dates for undated pages, rows for failed ones)')
    ap.add_argument('--news', help='crawl/news/articles.json: the baps.org News articles and their galleries (default: news/articles.json in the folder)')
    a = ap.parse_args()
    years = load(a.folder, a.fixes or os.path.join(a.folder, 'bapas-diary-fixes.json'))
    total = sum(len(v) for v in years.values())
    undated = sum(1 for v in years.values() for x in v if not x[0] and not x[1])
    days, stats = build(years)
    news, why = load_news(a.news or os.path.join(a.folder, 'news', 'articles.json'), years)
    news_days, _ = build(news)
    write(days, a.out, news_days)
    if why:
        print('News galleries:', ', '.join(f'{v} {k}' for k, v in why.most_common()))
        exact = [(m, y) for m, v in news_days.items() for y, (act, _) in v.items() if act.strftime('%m-%d') == m]
        print('  day/year slots that gain News photos (exact date only):', len(exact),
              '; years that had no photo at all:', sum(1 for m, y in exact if y not in days[m]))
    print(f'{len(years)} years, {total} photos ({undated} with no date), {stats["bapa"]} captioned as Bapa')
    print(f'day/year slots filled: {stats["exact"]} exact day, {stats["range"]} from a trip page, {stats["near"]} from a nearby day')
    per = collections.Counter(len(v) for v in days.values())
    print('years per day:', dict(sorted(per.items())))


if __name__ == '__main__':
    sys.exit(main())
