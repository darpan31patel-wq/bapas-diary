"""A day with Bapa, a section on Today under the polaroids (Darpan, 31 Oct 2026: "A day with Bapa: one real day in
order, morning puja to evening arti. do mockups. a version do like a timeline and all the possible scenarios that Bapa
could be doing at that time, based off all the captions and all the different events").

Two versions, both from bapa.db (only photos where Bapa is recognised by face, tools/web_faces.py), so only Bapa in
person; Pramukh Swami Maharaj and Mahant Swami Maharaj always side by side:
  A  one real day on this date: the fullest day with Pramukh Swami Maharaj and the fullest with Mahant Swami Maharaj,
     each from morning puja to evening arti, a few moments in the order the photos were taken
     -> out/data/dayflow/MM-DD.json
  B  Bapa's day: the parts of the day, and everything the captions show him doing in each, with how many days of
     photos there are of it and photos from many years (the page picks a different few each day)
     -> out/data/dayflow/day.json

The photos carry no clock time. The order of the day is the order the photos were taken (their file numbers): every
activity's middle place in its days (morning arti at 5% of the day's photos, morning puja 18%, evening arti 92% ...)
puts it in a part of the day. Website only: nothing here touches the daily 2pm picture chain and nothing is fetched
from baps.org.

    python3 tools/web_dayflow.py --db bapa.db --faces faces --out out/data/dayflow
"""
import argparse, collections, json, os, re, sqlite3, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import web_bapa_rules as R
import web_year as Y

PSM_UNTIL = R.PSM_UNTIL
# what Bapa is doing, by the words of the caption; first match wins, in this order
DOING = [
    ('arti', 'Morning arti', r'morning arti|mangla arti|shangar arti'),
    ('puja', 'Morning puja', r'\bpuja\b(?! darshan of thakorji)|meditates|turns the mala|applies (?:a )?(?:tilak|chandlo|chandan)'),
    ('darshan', 'Darshan of Thakorji', r'engrossed in darshan|darshan of (?:shri )?(?:thakorji|harikrishna)|pradakshina|bows to thakorji'),
    ('thal', 'Offers thal', r'\bthal\b|lunch|meal|takes (?:his )?(?:prasad|food)|mango ras'),
    ('reads', 'Reads and discourses', r'reads the shikshapatri|satsang diksha|swamini vato|vachanamrut|discourses|katha'),
    ('greets', 'Greets devotees', r'greets|jai swaminarayan|folded hands|waves'),
    ('children', 'Blesses the children', r'\b(?:child|children|balaks?|baliks?|kishores?)\b'),
    ('visits', 'Visits and blesses', r'padhramani|visits|inaugurates|observes|views'),
    ('sadhus', 'With the sadhus', r'(?:in conversation|discussion|meeting|interacts) with (?:the )?sadhus|video conference|video call'),
    ('walk', 'His walk', r'\bwalk'),
    ('assembly', 'The assembly', r'assembly|sabha|blesses (?:all|the devotees|devotees)'),
    ('letters', 'Letters', r'letter|writes'),
    ('evening', 'Evening arti', r'evening arti|sandhya arti'),
]
DOING = [(k, t, re.compile(p, re.I)) for k, t, p in DOING]
PARTS = [('Early morning', ('arti', 'puja')), ('Morning', ('darshan', 'thal', 'reads')), ('Midday', ('greets', 'children')),
         ('Afternoon', ('visits', 'sadhus', 'walk')), ('Evening', ('assembly', 'letters', 'evening'))]
PART_OF = {k: i for i, (_, ks) in enumerate(PARTS) for k in ks}
EDGES = [.12, .38, .55, .72]   # a photo nothing names takes its part of the day from where it falls in the day


def doing(cap):
    for k, _, rx in DOING:
        if rx.search(cap or ''):
            return k
    return None


def part(k, at):
    return PART_OF[k] if k in PART_OF else sum(at > e for e in EDGES)


def days_of(db, faces):
    """{date: [photo, ...]} in the order they were taken, every year."""
    out = collections.defaultdict(list)
    for year in sorted(y for (y,) in db.execute('SELECT DISTINCT year FROM photos WHERE year IS NOT NULL')):
        yr = Y.Year(db, faces, year)
        rows = sorted((r for r in yr.rows if r['day'][:4] == str(year)), key=lambda r: r['key'])
        for r in rows:
            r['yr'] = yr
            out[r['day']].append(r)
    for d, rows in out.items():
        n = max(1, len(rows) - 1)
        for i, r in enumerate(rows):
            r['at'] = i / n
            r['do'] = doing(r['raw'])
    return out


def fullness(rows):
    ks = {r['do'] for r in rows if r['do']}
    return (('puja' in ks or 'arti' in ks) + ('evening' in ks) + len({part(r['do'], r['at']) for r in rows})) * 10 + len(ks) + min(len(rows), 60) / 60


def pack(r):
    return dict(k=r['key'], c=r['cap'], fx=round(max(0, min(1, r['fx'])), 3), fy=round(max(0, min(1, r['fy'])), 3))


SAID = [(re.compile(r'\bmorning (?:assembly|session|walk)|in the morning', re.I), 1), (re.compile(r'\bafternoon', re.I), 3),
        (re.compile(r'\bevening\b|\bnight\b', re.I), 4)]


def said(cap, p):
    """The part of the day the caption itself names ("the afternoon assembly") wins over the usual one."""
    for rx, q in SAID:
        if rx.search(cap or ''):
            return q
    return p


def one_day(d, rows, n=8):
    """A few moments through one day, morning puja to evening arti: one for each thing Bapa did that day (the clearest
    photo of it), put in the part of the day where that is done (the photos carry no clock time, and on days of more
    than one album their file order is not always the order of the day)."""
    yr = rows[0]['yr']
    groups = collections.OrderedDict()   # each thing Bapa did, in the usual order of his day
    for r in rows:
        if r['do']:
            groups.setdefault(r['do'], []).append(r)
    order = [k for k, _, _ in DOING]
    ks = sorted(groups, key=order.index)
    if len(ks) > n:   # keep the start and end of the day, and the things with most photos between
        keep = {ks[0], ks[-1]} | set(sorted(ks[1:-1], key=lambda k: -len(groups[k]))[:n - 2])
        ks = [k for k in ks if k in keep]
    out, caps = [], set()
    for k in ks:
        for r in sorted(groups[k], key=lambda r: -yr.score(r, close=False)):
            if r['cap'] and r['cap'] not in caps:
                caps.add(r['cap'])
                out.append(dict(pack(r), p=said(r['raw'], PART_OF[k]), d=k))
                break
    place = collections.Counter(R.tidy(r['place']).split(',')[0].strip() for r in rows).most_common(1)[0][0]
    out.sort(key=lambda m: m['p'])   # stable: the usual order within each part of the day
    return dict(date=d, place=place, n=len(rows), m=out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapa.db')
    ap.add_argument('--faces', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--dates', help='only these MM-DD (comma separated), for a mockup')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    years = {y for (y,) in db.execute('SELECT DISTINCT year FROM photos WHERE year IS NOT NULL')}
    faces = Y.load_faces(a.faces, years)
    days = days_of(db, faces)
    os.makedirs(a.out, exist_ok=True)
    full = {d: fullness(rows) for d, rows in days.items() if len(rows) >= 12}

    # A: every date of the year, the fullest day with each guru (the nearest date within two weeks when that date has no whole day)
    want = a.dates.split(',') if a.dates else sorted({d[5:] for d in days} | {f'{m:02d}-{x:02d}' for m in range(1, 13) for x in range(1, 32)})
    by_mmdd = collections.defaultdict(list)
    for d in full:
        by_mmdd[d[5:]].append(d)
    wrote = 0
    seen = {}
    moments = lambda d: seen[d] if d in seen else seen.setdefault(d, one_day(d, days[d]))
    for mmdd in want:
        try:
            import datetime
            base = datetime.date(2000, int(mmdd[:2]), int(mmdd[3:]))
        except ValueError:
            continue
        both = []
        for psm in (True, False):
            pick = None
            # a whole day (five moments or more) as near this date as can be, within two weeks; else the day with the
            # most moments within a month, the nearest of those
            for gap in range(0, 15):
                near = {(base + datetime.timedelta(days=s * gap)).strftime('%m-%d') for s in (1, -1)}
                ds = [d for m in near for d in by_mmdd.get(m, []) if (d < PSM_UNTIL) == psm and len(moments(d)['m']) >= 5]
                if ds:
                    pick = max(ds, key=lambda d: (min(len(moments(d)['m']), 8), full[d]))
                    break
            if not pick:
                ds = [(gap, d) for gap in range(0, 31) for m in {(base + datetime.timedelta(days=s * gap)).strftime('%m-%d') for s in (1, -1)}
                      for d in by_mmdd.get(m, []) if (d < PSM_UNTIL) == psm and len(moments(d)['m']) >= 3]
                if ds:
                    pick = max(ds, key=lambda x: (min(len(moments(x[1])['m']), 8), -x[0]))[1]
            if pick:
                both.append(dict(moments(pick), g='psm' if psm else 'msm'))
        if len(both) == 2:   # never one guru without the other
            json.dump(dict(days=both), open(os.path.join(a.out, mmdd + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
            wrote += 1

    # B: the parts of the day and what Bapa does in each, from every day with enough photos
    at, cnt, dd, pool = collections.defaultdict(list), collections.Counter(), collections.defaultdict(set), collections.defaultdict(list)
    for d, rows in days.items():
        if len(rows) < 12:
            continue
        for r in rows:
            if r['do']:
                at[r['do']].append(r['at'])
                cnt[r['do']] += 1
                dd[r['do']].add(d)
                pool[r['do']].append(r)
    acts = []
    for k, title, _ in DOING:
        if not cnt[k]:
            continue
        rows = pool[k]
        picks = {}
        for psm in (True, False):   # up to 24 photos with each guru, one a year at most, clearest first
            side = [r for r in rows if (r['day'] < PSM_UNTIL) == psm]
            by_year = collections.defaultdict(list)
            for r in side:
                by_year[r['day'][:4]].append(r)
            got = []
            for yv, rs in sorted(by_year.items()):
                yr = rs[0]['yr']
                best = sorted(rs, key=lambda r: -yr.score(r, close=False))[:3]
                for r in best:
                    if yr.score(r, close=False) >= 0:
                        got.append(dict(pack(r), d=r['day'], pl=R.tidy(r['place']).split(',')[0].strip()))
            picks['psm' if psm else 'msm'] = got[:24]
        acts.append(dict(k=k, t=title, part=PART_OF[k], days=len(dd[k]), photos=cnt[k], mid=round(statistics.median(at[k]), 2),
                         y0=min(dd[k])[:4], y1=max(dd[k])[:4], psm=picks['psm'], msm=picks['msm']))
    acts.sort(key=lambda x: (x['part'], x['mid']))
    out = dict(parts=[p for p, _ in PARTS], acts=acts, days=len(full))
    json.dump(out, open(os.path.join(a.out, 'day.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'dayflow: {wrote} dates, {len(acts)} things Bapa does across {len(full)} full days')


if __name__ == '__main__':
    main()
