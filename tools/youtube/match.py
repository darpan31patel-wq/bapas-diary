"""Pair each BAPS Guruhari Darshan video with the diary day(s) it shows (website only, never the daily 2pm picture).

Reads data/youtube/flat.tsv (the Guruhari Darshan playlist, newest first) and, when present,
data/youtube/channel/*.tsv (every other video on the BAPS channel), and writes data/youtube/days.json (date -> videos,
the shortest, most exact video first) and data/youtube/undated.json.

Days come from each title. Every way the channel writes them is read (Darpan, 31 Oct 2026, after 31 October 2016,
2017 and 2018 showed no Video Darshan though the videos are there):
  "23-24 Oct 2026", "29 to 31 Oct 2013", "31 October to 2 November 2018", "30 Sep - 2 Oct 2018",
  "29 Dec 2025 - 1 Jan 2026", "August 31 - September 01, 2023", "January 9 and 11-13, 2014", "1 & 2 Nov. 2013",
  "2nd August 2014", "30-31Oct 2020", "30 May & 5-6 June 2023".
A festival video with no date in its title ("New Year Celebration with HH Mahant Swami Maharaj, Gondal, India") gets
that festival's day from the BAPS calendar (calendar/baps-calendar.json), in the year the title names or between the
dated videos either side of it in the playlist (within 10 days: festival videos were often uploaded a few days late).
No guessing beyond that.
"""
import csv, datetime as dt, glob, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YT = os.path.join(HERE, 'data', 'youtube')
MONTHS = {m: i + 1 for i, m in enumerate('jan feb mar apr may jun jul aug sep oct nov dec'.split())}
MONTHS['sept'] = 9
RANGE, LIST = {'-', '–', '—', 'to', 'till', 'until'}, {'&', 'and', ','}
TOKEN = re.compile(r"(\d{4})(?!\d)|(\d{1,2})(?:st|nd|rd|th)?(?![\d])|([A-Za-z]+)\.?|([-–—&,])")


def month(word):
    w = word.lower()
    if w in MONTHS or w == 'sept':
        return MONTHS[w]
    full = 'january february march april may june july august september october november december'.split()
    return full.index(w) + 1 if w in full else None


def dates(title):
    """Every day the title names, as a set of dates."""
    t = re.sub(r'(\d)([A-Za-z]{3,9})\b', lambda m: m.group(1) + ' ' + m.group(2) if month(m.group(2)) else m.group(0), title)
    atoms = []      # [day, month, year, joined to the one before by a range?]
    pending = []    # atoms still waiting for their month (or year)
    want_month = None
    joint = None
    for y, d, w, p in TOKEN.findall(t):
        if d:
            a = [int(d), want_month, None, joint in RANGE and bool(atoms)]
            atoms.append(a)
            pending.append(a)
            joint = None
        elif y:
            for a in atoms:
                if a[1] and a[2] is None:
                    a[2] = int(y)
            pending, want_month = [], None
        elif w and month(w):
            m = month(w)
            waiting = [a for a in pending if a[1] is None]
            for a in waiting:
                a[1] = m
            want_month = None if waiting else m
            pending = [a for a in pending if a[1] == m]
        elif w and w.lower() in RANGE | LIST or p:
            joint = (w or p).lower()
        else:   # any other word ends the date: "85th Birthday", "10th Anniversary" are not days
            pending, want_month, joint = [], None, None
    days = set()
    prev = None
    for d, m, y, ranged in atoms:
        if not (m and y):
            prev = None
            continue
        try:
            day = dt.date(y, m, d)
        except ValueError:
            prev = None
            continue
        if ranged and prev and 0 < (day - prev).days <= 15:
            days.update(prev + dt.timedelta(n) for n in range((day - prev).days))
        days.add(day)
        prev = day
    return days


# festival videos with no date: title words -> the BAPS calendar's festival name
FESTS = [
    (r'new year|nutan varsh|bestu|annakut', r'annakut|bestu|new year'),
    (r'diwali|chopda|sharda pujan', r'^diwali$'),
    (r'pushpadol|fuldol|dhuleti', r'pushpadol|fuldol|dhuleti'),
    (r'sharad purnima|sharad punam', r'sharad|gunatitanand swami(.s birthday| janma jayanti)'),
    (r'janmashtami', r'janmashtami'),
    (r'guru ?purnima', r'guru purnima'),
    (r'rath ?yatra', r'rathyatra'),
    (r'vasant panch', r'vasant panch'),
    (r'jal ?jhilani', r'jal jhilani'),
    (r'prabodhini', r'prabodhini'),
    (r'dev diwali', r'dev diwali'),
    (r'hari ?nom|ram ?navmi|swaminarayan jayanti', r'hari-?nom|ramnavmi'),
    (r"pramukh swami maharaj's.*(janma jayanti|birth)|birthday celebration of .*pramukh", r"pramukh swami maharaj's jayanti"),
    (r"mahant swami maharaj's.*(janma jayanti|birth)|birthday celebration of .*mahant", r'mahant swami maharaj.*jayanti'),
]
cal = {}
try:
    for day in json.load(open(os.path.join(HERE, 'calendar', 'baps-calendar.json')))['days']:
        for f in day['festivals']:
            cal.setdefault(f['name'].lower(), []).append(dt.date.fromisoformat(day['date']))
except (OSError, KeyError, ValueError):
    pass


def festival_day(title, lo, hi):
    """The festival's day from the BAPS calendar, inside lo..hi (and the year in the title, if it names one)."""
    year = re.search(r'\b(20\d\d)\b', title)
    for words, name in FESTS:
        if not re.search(words, title, re.I):
            continue
        hits = sorted({d for n, ds in cal.items() if re.search(name, n) for d in ds
                       if (not year or d.year == int(year.group(1))) and (lo is None or lo <= d <= hi)})
        return hits[0] if len(hits) == 1 else None
    return None


def read(path):
    rows = []
    for l in open(path, encoding='utf-8'):
        parts = l.rstrip('\n').split('\t')
        if len(parts) >= 2 and parts[1] not in ('NA', '[Private video]', '[Deleted video]'):
            rows.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ''))
    return rows


def place(rows):
    """Dated days per video, and festival days for undated ones from their dated neighbours (rows are newest first)."""
    got = [(v, t, s, dates(t)) for v, t, s in rows]
    out = []
    for i, (v, t, s, ds) in enumerate(got):
        if not ds:
            newer = next((min(x[3]) for x in reversed(got[:i]) if x[3]), None)
            older = next((max(x[3]) for x in got[i + 1:] if x[3]), None)
            lo = older - dt.timedelta(10) if older else None
            hi = newer + dt.timedelta(10) if newer else None
            if lo and hi and lo <= hi and (hi - lo).days <= 60:
                f = festival_day(t, lo, hi)
            elif re.search(r'\b20\d\d\b', t):
                f = festival_day(t, None, None)
            else:
                f = None
            ds = {f} if f else set()
        out.append((v, t, s, ds))
    return out


lists = [place(read(os.path.join(YT, 'flat.tsv')))]
ch = os.path.join(YT, 'channel')
for f in ('videos.tsv', 'streams.tsv'):   # the channel's own pages, newest first
    if os.path.exists(os.path.join(ch, f)):
        lists.append(place(read(os.path.join(ch, f))))
if os.path.exists(os.path.join(ch, 'in-playlists.tsv')):   # every channel playlist, each in its own order
    per = {}
    for l in open(os.path.join(ch, 'in-playlists.tsv'), encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 3:
            per.setdefault(p[0], []).append(p[1:])
    for p, rows in per.items():
        lists.append(place([(r[0], r[1], r[2] if len(r) > 2 else '') for r in rows if r[1] not in ('NA', '[Private video]', '[Deleted video]')]))

# Only Guruhari Darshan style videos of Bapa from the wider channel: dated in the title or a festival with Bapa
BAPA = re.compile(r'guruhari darshan|mahant swami|pramukh swami|swamishri|bapa\b', re.I)
vids, seen, undated = {}, {}, []
for n, rows in enumerate(lists):
    for v, t, s, ds in rows:
        if n and not BAPA.search(t):
            continue
        if ds:
            seen.setdefault(v, (t, s, set()))[2].update(ds)
        elif v not in seen:
            undated.append(t)
for v, (t, s, ds) in seen.items():
    for d in ds:
        vids.setdefault(d, []).append((len(ds), v, t, s))
undated = sorted({t for t in undated if not any(t == x[0] for x in seen.values())})
out = {d.isoformat(): [{'id': v, 'title': t, 'secs': int(s) if s.isdigit() else None}
                       for _, v, t, s in sorted(x, key=lambda r: r[0])] for d, x in sorted(vids.items())}
json.dump(out, open(os.path.join(YT, 'days.json'), 'w'), ensure_ascii=False, indent=0)
json.dump(undated, open(os.path.join(YT, 'undated.json'), 'w'), ensure_ascii=False, indent=1)
print(len(out), 'days,', len(seen), 'videos,', len(undated), 'undated')
