"""The Diwali days on Today (Darpan, 31 Oct 2026: "Festival sparkle ... Bapa's New Year ashirwad ... Diwali through the
years ... Annakut gallery"). Website only: nothing here touches the daily 2pm picture.

From Dhanteras to Bhai Bij Today shows three more things under the board, all from this one file:

  Bapa's Diwali, every year   one row a year from 1999: where he was, the Chopda Pujan (or that Diwali's best darshan)
                              and the Diwali video, playing inside the page. From data/fest/diwali.json, so every Today
                              rule holds (Bapa in person only, his whole head framed).
  New Year ashirwad           his New Year blessings video from each year, with that year's Annakut darshan of him
                              (data/fest/annakut.json). The BAPS channel's own blessing video first, then the New Year
                              or Annakut celebration of that day.
  Annakut gallery             the annakut spreads of every mandir and year, grouped by place, with Bapa's own darshan
                              of the annakut beside them. The spreads are the offering itself, so they need not show
                              Bapa ("the annakut spreads from every mandir"); a spread whose caption names a guru is
                              left out, so no murti or portrait of one guru stands alone. Bapa's photos are only ones
                              of him in person doing darshan or arti of the annakut.

  Chopda Pujan with Bapa      (Darpan, 5 Nov 2026: "Yes to all 1-4") every Chopda Pujan BAPS put on YouTube, a tile a
                              year: Pramukh Swami Maharaj's (2009, 2010, 2013) and Mahant Swami Maharaj's (2016 on),
                              each with that Diwali's own darshan of him and its gold Video Darshan, playing in the page.
  Annakut of the years        one darshan a year of Bapa at the annakut, oldest first, at the top of the Annakut
                              gallery: his own darshan or arti of the annakut where the diary has one, else that
                              Annakut's photo of him whose caption says annakut. Bapa in person only.

    python3 tools/web_diwali.py --db bapas.db --bapa bapa.db --deep-tags deep-tags.json --fest out/data/fest

Writes out/data/fest/season.json. Run after tools/web_festival.py and tools/web_videos.py (it reads their files).
"""
import argparse, collections, csv, datetime, json, os, re, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = 1999          # "every year 1999 to 2025"
MSM = '2016-08-13'    # Swamishri before this day is Pramukh Swami Maharaj, from it Mahant Swami Maharaj

CHOPDA = re.compile(r'chopda|sharda|lakshmi ?pujan|account books?', re.I)
DIWALI_V = re.compile(r'chopda', re.I)
NEW_YEAR = re.compile(r'new year|nava varsh|navu varsh|nutan varsh|bestu', re.I)
BLESS = re.compile(r'bless|ashirwad|ashirvad|prayers', re.I)
BAPAS = re.compile(r'bless|ashirwad|ashirvad|swami maharaj|swamishri|guruhari', re.I)   # his own video, not a mandir's
NOT_HIS = re.compile(r'forthcoming|greeting card|mahapuja|prime minister|celebrations? \d{4} (houston|la|chicago|edison|atlanta|toronto|london)|'
                     r'\b(uk|france) [–-]|vallabh vidyanagar|mandir, london|london, uk$', re.I)
ANNAKUT = re.compile(r'annakut|annkut|anakut|haatdi|hatadi', re.I)
PEOPLE = re.compile(r'devotees|children|swamis|sadhus|youths|ceremony|assembly|mahapuja|participat', re.I)
GURU = re.compile(r'pramukh swami|mahant swami|swamishri|yogiji|shastriji|bhagatji|gunatitanand|guru', re.I)
DARSHAN = re.compile(r'^(swamishri|param pujya|pramukh swami|mahant swami|hh )[^.]{0,80}(darshan|arti|aarti|observes|amid|offers|sings)', re.I)
MONTHS = 'jan feb mar apr may jun jul aug sep oct nov dec'.split()


def town(place):
    """'Gondal, India' -> 'Gondal'; '2004, New York' -> 'New York'; first real place of an album that went to two."""
    for part in (place or '').split(','):
        part = part.strip()
        if part and not re.fullmatch(r'\d{4}', part) and part.lower() not in ('india', 'uk', 'usa'):
            return part
    return ''


def title_day(t):
    """A date written in a video's title, '27 Oct 2011', '28 October 2019', 'October 15, 2023' -> '2011-10-27'."""
    m = re.search(r'\b(\d{1,2})(?:-\d{1,2})? ([A-Z][a-z]{2,8})\.? (\d{4})', t) or None
    if m:
        d, mon, y = m.groups()
    else:
        m = re.search(r'\b([A-Z][a-z]{2,8}) (\d{1,2}), (\d{4})', t)
        if not m:
            return ''
        mon, d, y = m.groups()
    if mon[:3].lower() not in MONTHS:
        return ''
    return f'{y}-{MONTHS.index(mon[:3].lower()) + 1:02d}-{int(d):02d}'


def title_place(t):
    """'New Year's Blessings, Guruhari Ashirwad, 22 Oct 2025, Gondal, India' -> 'Gondal'."""
    parts = [x.strip() for x in t.split('|')[0].split(',')]
    for i in range(len(parts) - 1, 0, -1):
        if parts[i] in ('India', 'UK', 'USA', 'France', 'Kenya', 'Australia'):
            return parts[i - 1]
    return ''


def face(p):
    """Sorts a Today photo by how well it shows his face: close ups first, then the biggest face."""
    f = p[4] if len(p) > 4 and isinstance(p[4], list) and len(p[4]) > 7 else [0] * 8
    return (-f[7], -f[4] * f[5])


def near(a, b, days=2):
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days) <= days


def load(path):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {'years': []}


def diwali_rows(fest):
    """Every Diwali from 1999, the Chopda Pujan first, with its own video (web_videos put the festival's video first)."""
    out = []
    for Y in load(os.path.join(fest, 'diwali.json'))['years']:
        if Y['y'] < FIRST:
            continue
        ps = list(Y.get('p') or []) or list(Y.get('t') or [])
        ps.sort(key=lambda p: not CHOPDA.search(p[2] or ''))   # stable: the Chopda Pujan first, then as Today has them
        vs = sorted(Y.get('v') or [], key=lambda v: not DIWALI_V.search(v[1]))
        row = {'y': Y['y'], 'd': Y['d'], 'place': Y.get('place') or '', 'p': ps[:3],
               'chopda': bool(ps and CHOPDA.search(ps[0][2] or ''))}
        if Y.get('ti'):
            row['ti'] = Y['ti']
        if vs:
            row['v'] = vs[0][:2]
        out.append(row)
    return out


def ashirwad_rows(fest, channel, days_json):
    """One New Year blessing a year: the channel's blessing video first, else that day's New Year or Annakut video."""
    ann = {Y['y']: Y for Y in load(os.path.join(fest, 'annakut.json'))['years']}
    dw = {Y['y']: Y for Y in load(os.path.join(fest, 'diwali.json'))['years']}
    by_id = {}
    for d, vs in json.load(open(days_json, encoding='utf-8')).items():
        for v in vs:
            by_id.setdefault(v['id'], (v['title'], v.get('secs') or 0, d))
    for path in channel:
        if os.path.exists(path):
            for row in csv.reader(open(path, encoding='utf-8'), delimiter='\t'):
                if len(row) >= 2 and row[0] not in by_id:
                    vid, t = row[-3], row[-2]
                    secs = int(row[-1]) if row[-1].isdigit() else 0
                    by_id.setdefault(vid, (t, secs, title_day(t)))
    best = {}
    for vid, (t, secs, d) in by_id.items():
        if not (NEW_YEAR.search(t) or ANNAKUT.search(t)) or NOT_HIS.search(t) or not BAPAS.search(t) and not d:
            continue
        y = int(d[:4]) if d else int((re.search(r'\b(19|20)\d\d\b', t) or [0])[0] or 0)
        if not y or y < FIRST:
            continue
        nd = ann.get(y, {}).get('d')
        if d and nd and not near(d, nd):   # a New Year video of the New Year itself, not an annakut months away
            continue
        if not d and not NEW_YEAR.search(t):
            continue
        rank = (0 if BLESS.search(t) else 1 if NEW_YEAR.search(t) else 2, -bool(re.search(r'-1\b|part 1', t, re.I)), -secs)
        if y not in best or rank < best[y][0]:
            best[y] = (rank, [vid, t.strip(), secs], d or nd or '')
    out = []
    for y in sorted(best):
        _, v, d = best[y]
        Y = ann.get(y) or dw.get(y) or {}
        ps = [p for Z in (ann.get(y), dw.get(y)) if Z for p in (Z.get('p') or Z.get('t') or [])]
        ps.sort(key=face)   # the tile is a darshan of him, so the clearest close up of his face first, not the food
        place = Y.get('place') or title_place(v[1])
        d = d or Y.get('d') or ''
        out.append({'y': y, 'd': d, 'place': place, 'v': v, 'p': ps[:2],
                    'guru': 'Mahant Swami Maharaj' if d and d >= MSM or y > 2016 else 'Pramukh Swami Maharaj'})
    return out


HIS_ANNAKUT = {}   # year: [(date, place, photo)], Bapa's own darshan or arti of the annakut, best first


def annakut_rows(db, bapa, tags):
    """Every mandir's annakuts, year by year: the spreads, and Bapa's own darshan of them."""
    him = {}
    for a, f, rank, fx, fy, close, why in bapa.execute('SELECT album, file, rank, fx, fy, close, why FROM bapa_pick'):
        him[(a, f)] = (rank, fx, fy, close, why)
    groups = collections.defaultdict(lambda: {'s': [], 'b': [], 'd': ''})
    for d, place, a, f, cap, is_bapa in db.execute(
            'SELECT coalesce(date, date_from), place, album, file, caption, is_bapa FROM photos ORDER BY album, file'):
        cap = (cap or '').strip()
        t = tags.get(f'{a}/{f}', '')
        if not d or d[:4] < str(FIRST) or not ANNAKUT.search(cap):   # the caption itself says annakut
            continue
        p = town(place)
        if not p:
            continue
        g = groups[(p, d[:4])]
        h = him.get((a, f))
        if h and h[4] == 'recognised' and DARSHAN.search(cap) and ANNAKUT.search(cap):
            g['b'].append((h[0], [a, f, cap, 1, [round(h[1] or .5, 3), round(h[2] or .3, 3)]], d))   # where his face is, as Today's photos have it
        elif not h and not is_bapa and not GURU.search(cap) and not PEOPLE.search(cap) and not re.search(r'\b(smiling|laughing|folded hands)\b', t):
            g['s'].append((('annakut' not in t) + ('food' not in t), [a, f, cap], d))
    places = collections.defaultdict(list)
    for (p, y), g in groups.items():
        if not g['s']:
            continue
        s = sorted(g['s'], key=lambda x: x[0])[:4]
        b = sorted(g['b'], key=lambda x: x[0])[:2]
        for x in sorted(g['b'], key=lambda x: x[0]):   # each darshan of him with its own day, for Annakut of the years
            HIS_ANNAKUT.setdefault(int(y), []).append((x[2], p, x[1]))
        places[p].append({'y': int(y), 'd': min(x[2] for x in s + b), 's': [x[1] for x in s], 'b': [x[1] for x in b]})
    out = [{'place': p, 'years': sorted(ys, key=lambda r: r['y'])} for p, ys in places.items()]
    out.sort(key=lambda r: (-len(r['years']), -sum(len(y['b']) for y in r['years']), r['place']))
    return out


CHOPDA_VIDEO = re.compile(r'chopda|sharda ?pujan', re.I)


def place_on(db, date):
    """The town most of that day's photos were taken in."""
    rows = db.execute('SELECT place, count(*) FROM photos WHERE coalesce(date, date_from) = ? GROUP BY place ORDER BY 2 DESC', (date,)).fetchall()
    return next((town(p) for p, _ in rows if town(p)), '')


def chopda_rows(fest, videos, db, bapa):
    """Every Chopda Pujan video of Bapa, a row a year: the Chopda Pujan darshan first, then its blessings."""
    dw = {Y['y']: Y for Y in load(os.path.join(fest, 'diwali.json'))['years']}
    found = {}
    for d, vs in json.load(open(os.path.join(videos, 'days.json'), encoding='utf-8')).items():
        for v in vs:
            if CHOPDA_VIDEO.search(v['title']):
                found.setdefault(v['id'], (v['title'].strip(), v.get('secs') or 0, d))
    for name in ('videos.tsv', 'streams.tsv'):
        path = os.path.join(videos, 'channel', name)
        if os.path.exists(path):
            for row in csv.reader(open(path, encoding='utf-8'), delimiter='\t'):
                if len(row) >= 3 and CHOPDA_VIDEO.search(row[-2]) and row[-3] not in found:
                    found[row[-3]] = (row[-2].strip(), int(row[-1]) if row[-1].isdigit() else 0, title_day(row[-2]))
    years = collections.defaultdict(list)
    for vid, (t, secs, d) in found.items():
        y = int(d[:4]) if d else int((re.search(r'\b(19|20)\d\d\b', t) or [0])[0] or 0)
        if y < FIRST or re.search(r'forthcoming|greeting card|prime minister', t, re.I):   # no year: not put on a Diwali
            continue
        years[y].append((bool(BLESS.search(t)), -secs, vid, t, secs, d))
    him = {}
    for a, f, rank, fx, fy, close, why in bapa.execute('SELECT album, file, rank, fx, fy, close, why FROM bapa_pick'):
        if why == 'recognised':
            him[(a, f)] = (rank, fx, fy)
    out = []
    for y in sorted(years):
        vs = sorted(years[y])[:2]   # the Chopda Pujan itself, then his blessings that evening
        Y = dw.get(y) or {}
        d = Y.get('d') or next((x[5] for x in vs if x[5]), '')
        ps = list(Y.get('p') or Y.get('t') or [])
        ps.sort(key=lambda p: (not CHOPDA.search(p[2] or ''), face(p)))
        days = [d] + [(datetime.date.fromisoformat(d) + datetime.timedelta(k)).isoformat() for k in (-1, 1)] if d else []
        for day in days if not ps else []:   # a Diwali Today has no card for: his own recognised darshan of that day
            got = []                          # (or the day before or after), the Chopda Pujan first
            for a, f, cap in bapa.execute('SELECT album, file, caption FROM photos WHERE coalesce(date, date_from) = ?', (day,)):   # bapa.db: captions say what Bapa does
                h = him.get((a, f))
                if h and not GURU.search(re.sub(r'^(swamishri|pramukh swami maharaj|mahant swami maharaj)\b', '', (cap or '').strip(), flags=re.I)):
                    got.append(((not CHOPDA.search(cap or ''), h[0]), [a, f, (cap or '').strip(), 1, [round(h[1] or .5, 3), round(h[2] or .3, 3)]]))
            ps = [p for _, p in sorted(got)]
            if ps:
                break
        place = Y.get('place') or next((title_place(x[3]) for x in vs if title_place(x[3])), '') or (place_on(db, d) if d else '')
        for k in (-1, 1):   # a Diwali with no photos of its own day: the town of the day before or after
            if not place and d:
                place = place_on(db, (datetime.date.fromisoformat(d) + datetime.timedelta(k)).isoformat())
        out.append({'y': y, 'd': d, 'place': place, 'v': [[x[2], x[3], x[4]] for x in vs], 'p': ps[:1],
                    'guru': 'Mahant Swami Maharaj' if d and d >= MSM or y > 2016 else 'Pramukh Swami Maharaj'})
    return out


def annakut_years(fest):
    """One darshan a year of Bapa at the annakut, oldest first: his own darshan or arti of the annakut (the gallery's
    gold frames), else that year's Annakut photo of him on Today whose caption says annakut."""
    best, ann = {}, load(os.path.join(fest, 'annakut.json'))['years']
    day = {Y['y']: Y['d'] for Y in ann}   # the New Year's Annakut itself, not a mango annakut or a Haatdi months away
    for y, got in HIS_ANNAKUT.items():
        for d, place, p in got:
            if y in day and near(d, day[y], 1):
                best[y] = {'y': y, 'd': d, 'place': place, 'p': p}
                break
    for Y in ann:
        ps = [p for p in (Y.get('p') or []) + (Y.get('t') or []) if ANNAKUT.search(p[2] or '')
              and not (len(p) > 4 and isinstance(p[4], list) and len(p[4]) > 7 and p[4][4] < .08)]   # never a tiny far off face
        if Y['y'] not in best and ps:
            best[Y['y']] = {'y': Y['y'], 'd': Y['d'], 'place': Y.get('place') or '', 'p': ps[0]}
    for r in best.values():   # 'Swamishri performs annakut arti' -> 'Performs annakut arti': his name is on the tile by its date
        cap = re.sub(r'^(swamishri|param pujya mahant swami|param pujya pramukh swami maharaj|pramukh swami maharaj|mahant swami maharaj)\s+', '', r['p'][2] or '', flags=re.I)
        r['p'] = [r['p'][0], r['p'][1], cap[:1].upper() + cap[1:]] + list(r['p'][3:])
    return [best[y] for y in sorted(best)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='bapas.db: every photo, for the annakut spreads')
    ap.add_argument('--bapa', required=True, help="bapa.db: the photos of Bapa, with bapa_pick")
    ap.add_argument('--deep-tags', help='what is in each photo (release deep-tags)')
    ap.add_argument('--fest', required=True, help='the festival files (tools/web_festival.py, tools/web_videos.py); season.json goes here too')
    ap.add_argument('--videos', default=os.path.join(HERE, 'data', 'youtube'))
    a = ap.parse_args()
    tags = json.load(open(a.deep_tags, encoding='utf-8')) if a.deep_tags and os.path.exists(a.deep_tags) else {}
    out = {
        'diwali': diwali_rows(a.fest),
        'ashirwad': ashirwad_rows(a.fest, [os.path.join(a.videos, 'channel', 'videos.tsv')], os.path.join(a.videos, 'days.json')),
        'annakut': annakut_rows(sqlite3.connect(a.db), sqlite3.connect(a.bapa), tags),
        'chopda': chopda_rows(a.fest, a.videos, sqlite3.connect(a.db), sqlite3.connect(a.bapa)),
    }
    out['annyears'] = annakut_years(a.fest)   # after annakut_rows, which finds his annakut darshans
    this = datetime.date.today().year
    for k in ('diwali', 'ashirwad', 'chopda', 'annyears'):
        out[k] = [r for r in out[k] if r['y'] < this or r.get('d', '9') < datetime.date.today().isoformat()]
    with open(os.path.join(a.fest, 'season.json'), 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print(f"season: {len(out['diwali'])} Diwalis, {len(out['ashirwad'])} New Year blessings "
          f"({' '.join(str(r['y']) for r in out['ashirwad'])}), annakuts at {len(out['annakut'])} places, "
          f"{sum(len(y['s']) + len(y['b']) for r in out['annakut'] for y in r['years'])} photos; "
          f"Chopda Pujan videos {' '.join(str(r['y']) for r in out['chopda'])}; Annakut of the years {len(out['annyears'])} "
          f"({out['annyears'][0]['y'] if out['annyears'] else '-'} to {out['annyears'][-1]['y'] if out['annyears'] else '-'})")


if __name__ == '__main__':
    main()
