"""The Indian calendar for every day before 2010, worked out from the moon and the sun (Darpan, 13 Nov 2026: "can we start
tagging all the festivals and the Indian dates and the Indian events on our calendar, as we haven't uploaded any Indian
calendars before 2010?").

baps.org has calendars only from January 2010 (calendar/baps-calendar.json, table `calendar` in bapas.db). For the
years before, each day is worked out the way the Gujarati calendar is made, and every rule is learnt from, and checked
on, the BAPS calendar of 2010 to 2027:

  Indian date   the tithi at sunrise in Ahmedabad; the month starts at each new moon (amant) and is named by the
                sun's sidereal sign (Lahiri), with adhik months; the Vikram Samvat turns on Kartak Sud Padvo. The
                Ekadashi is kept as BAPS keeps it: a day whose sunrise is Baras but whose arunodaya (96 minutes before
                sunrise) is still Ekadashi is Ekadashi, and so is the day after an Ekadashi touched by Dasham at
                arunodaya.
  festivals     tools/old_festivals.py: each festival's month, tithi and the time of day the tithi must hold (sunrise
                for most, evening for Holi and Diwali, night for Sharad Punam). On a festival day the Indian date says
                the festival's tithi, as the BAPS calendar does.
  notes         the Ekadashi names, Shri Hari Navmi, Akshar Purnima, the Shraddh days, Hindola and the other yearly
                days, from the BAPS calendar of 2026 (and 2027 for an adhik month), on the day with the same Indian
                date; a fixed English date (Gandhi Jayanti, Natal) stays on its date. Days that need the weekday or
                an eclipse are left out, and so is any smrutiparva or jayanti before the year it began.

How sure: run `make` and it prints the check, the worked out days of 2010 to 2027 against the BAPS calendar.

    python3 tools/old_calendar.py make --db bapas.db     needs `pip install ephem`; writes calendar/worked-out-calendar.json
    python3 tools/old_calendar.py add --db bapas.db      the website build: adds those days to this build's copy of the
                                                         calendar table (never over a BAPS calendar day)

The 2pm picture (make.py) reads only calendar/baps-calendar.json, so it never sees these days.
"""
import argparse, collections, datetime as dt, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'calendar', 'worked-out-calendar.json')
FIRST, LAST = 1970, 2009
SOURCE = 'Worked out from the moon and the sun (baps.org has calendars from 2010)'
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# kept off the older years: they need the weekday, an eclipse or a fast marker, or only repeat the Indian date
NOTE_OUT = ('Vruddhi Tithi', 'Grahan', 'Ekadashi (Smart)', 'Somvati', 'Sud Terash', 'Nij_', 'Samvatsari', 'Gurunanak',
            'Pramukhvarni', 'Bhai Bij')   # the last two: the festival list has them already
# the year each one began: nothing before it
SINCE = {'Pramukh Swami': 2017, 'Pramukh Varni': 1950, 'Yogiji Maharaj': 1971, 'Shastriji Maharaj': 1951,
         'Mahant Swami Maharaj': 2099, 'Gujarat Sthapana': 1960, 'Independence Day': 1947, 'Republic Day': 1950,
         'Saradar Patel': 1950}


def since_ok(name, year):
    return all(year >= y for k, y in SINCE.items() if k.lower() in name.lower())


# ---------------------------------------------------------------- the sums (make only)

def engine():
    import ephem, math, functools
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import old_festivals as of

    @functools.lru_cache(None)
    def sunrise(day):
        return of.sun_times(day)[0]

    def tithi_at(x):
        sun, moon = of.longitudes(ephem.Date(x))
        return int(((moon - sun) % 360) // 12)

    def tname(i):
        return 'Punam' if i == 14 else 'Amas' if i == 29 else of.TITHI[i % 15]

    def plain(d):
        r = sunrise(d)
        t = tithi_at(r)
        month = of.month_from(round(float(ephem.previous_new_moon(ephem.Date(r))), 4))
        return t, month

    def day(d):
        t, month = plain(d)
        r = sunrise(d)
        if t % 15 == 11 and tithi_at(r - 96 / 1440) % 15 == 10:
            t -= 1
        else:
            rp = sunrise(d - dt.timedelta(days=1))
            if t % 15 == 11 and tithi_at(rp) % 15 == 10 and tithi_at(rp - 96 / 1440) % 15 == 9:
                t -= 1
        return t, month

    return of, day, tname


def work_out(first, last, rules, template, about, of, day, tname):
    """Every day from first to last (years), as rows like calendar/baps-calendar.json's days."""
    rows, by_key = {}, collections.defaultdict(list)
    d = dt.date(first, 1, 1) - dt.timedelta(days=40)
    while d <= dt.date(last, 12, 31) + dt.timedelta(days=40):
        t, month = day(d)
        rows[d] = dict(t=t, month=month)
        d += dt.timedelta(days=1)
    # festivals, on the day the sums find; that day says the festival's tithi
    fest = collections.defaultdict(list)
    for name, rule in rules.items():
        for y in range(first, last + 1):
            if not since_ok(name, y):
                continue
            if 'fixed' in rule:
                fest[dt.date.fromisoformat(f"{y}-{rule['fixed']}")].append(name)
                continue
            f = of.find(y, rule['month'], rule['tithi'], rule['when'], rule['usual'])
            if f and f in rows:
                fest[f].append(name)
                rows[f]['t'], rows[f]['month'] = rule.get('label', rule['tithi']), rule['month']
    # New Year (Annakut, Bestu Varas) by the rule the known years keep: the day after Diwali, unless Amas still holds
    # for more than 4 hours after that day's sunrise, then the day after that. Right in 25 of 26 years: the BAPS
    # calendar 2010 to 2027 (2023 the only miss) and the New Year assemblies with Bapa in Gondal, Delhi 1999 to 2009.
    ny = next((n for n in rules if 'Bestu' in n or 'New Year' in n), None)
    dw = 'Diwali' if 'Diwali' in rules else None
    if ny and dw:
        import ephem
        for d in sorted(fest):
            if dw in fest[d] and first <= d.year <= last:
                d1 = d + dt.timedelta(days=1)
                rise = of.sun_times(d1)[0]
                lo, hi = rise - 0.2, rise + 1.0   # Padvo begins when the moon is 0 degrees past the sun again
                el = lambda x: (lambda s_m: (s_m[1] - s_m[0] + 180) % 360 - 180)(of.longitudes(ephem.Date(x)))
                if el(lo) < 0 <= el(hi):
                    for _ in range(40):
                        mid = (lo + hi) / 2
                        lo, hi = (lo, mid) if el(mid) >= 0 else (mid, hi)
                    late = (hi - rise) * 24 > 4
                else:
                    late = False
                new = d1 + dt.timedelta(days=1 if late else 0)
                for x in [x for x in list(fest) if x.year == d.year and abs((x - d).days) < 5 and ny in fest[x]]:
                    fest[x].remove(ny)
                fest[new].append(ny)
                if new in rows:
                    rows[new]['t'], rows[new]['month'] = 0, 'Kartak'
                if late and d1 in rows:   # the day between keeps Amas, as BAPS writes it (2022, 2024 to 2026)
                    rows[d1]['t'], rows[d1]['month'] = 29, 'Aso'
                bb = next((n for n in rules if n.startswith('Bhai B')), None)   # Bhai Beej the day after New Year
                if bb:
                    for x in [x for x in list(fest) if x.year == d.year and abs((x - d).days) < 6 and bb in fest[x]]:
                        fest[x].remove(bb)
                    fest[new + dt.timedelta(days=1)].append(bb)
                    if new + dt.timedelta(days=1) in rows:
                        rows[new + dt.timedelta(days=1)]['t'], rows[new + dt.timedelta(days=1)]['month'] = 1, 'Kartak'
    # the Vikram Samvat: turns on the first Kartak Sud day after Aso
    vs, prev = None, None
    for d in sorted(rows):
        r = rows[d]
        if vs is None:
            vs = d.year + 56 + (d.month >= 11)
        if prev and prev['month'] == 'Aso' and r['month'] == 'Kartak':
            vs = d.year + 57
        r['vs'], prev = vs, r
    for d in rows:
        r = rows[d]
        r['key'] = (r['month'], 'Sud' if r['t'] < 15 else 'Vad', tname(r['t']))
        by_key[(d.year, r['key'])].append(d)
    # the yearly notes, on the day with the same Indian date (an Ekadashi's on its last day, the fast)
    notes = collections.defaultdict(list)
    for (key, fixed), phrases in template.items():
        for y in range(first, last + 1):
            if key is None:
                ds = [dt.date.fromisoformat(f'{y}-{fixed}')]
            else:
                # the days of this year with that Indian date, the run nearest the usual English date
                usual = dt.date.fromisoformat(f'{y}-{fixed[5:]}')
                ds = sorted(x for x in by_key.get((y, key), []) + by_key.get((y + 1, key), []) + by_key.get((y - 1, key), [])
                            if abs((x - usual).days) < 45 and x.year == y)
                if not ds:
                    continue
                ds = [ds[-1] if key[2] == 'Ekadashi' else ds[0]]
            for p in phrases:
                if since_ok(p, y) and p not in notes[ds[0]]:
                    notes[ds[0]].append(p)
    out = []
    for d in sorted(rows):
        if not first <= d.year <= last:
            continue
        r = rows[d]
        m, p, t = r['key']
        fs = [f for f in fest.get(d, [])]
        same = lambda x: x.lower().replace(' ', '').replace('aa', 'a')[:7]
        ns = [n for n in notes.get(d, []) if same(n) not in {same(f) for f in fs}]
        nxt = rows.get(d + dt.timedelta(days=1))
        ek = t == 'Ekadashi' and not (nxt and nxt['key'] == r['key'])
        out.append(dict(date=str(d), weekday=WEEKDAYS[d.weekday()], vikram_samvat=r['vs'], lunar_months=m,
                        month=m, paksha=p, tithi=t, indian_date=f'{m} {p} {t}',
                        festivals=[dict(name=f, about=about.get(f, '')) for f in fs], notes=ns,
                        ekadashi=ek, punam=t == 'Punam', amas=t == 'Amas', worked_out=True, source=SOURCE))
    return out


# Darpan, 13 Nov 2026: "match our guesstimations with the articles and pictures ... and just see if the festivals line
# up". The dated News stories and photo captions before 2010 that name a festival, held in India (abroad a festival is
# often kept on the weekend or by the local calendar), choose between rules that fit the BAPS calendar equally well.
RECORD_WORDS = {'Diwali': r'\bdiwali\b', 'Annakut': r'new year.{0,3}(celebration|day|blessing)|bestu|nutan varsh', 'Janmashtami': r'janmashtami',
                'Guru Purnima': r'guru ?pu?o?rnima', 'Rathyatra': r'rath ?yatra', 'Raksha Bandhan': r'raksha ?bandhan',
                'Vasant Panch': r'vasant panch', 'Pushpadolotsav': r'fuldol|pushpadol|dhuleti', 'Holi': r'\bholi\b',
                'Hari Navmi': r'swaminarayan jayanti|hari ?nav', 'Sharad Punam': r'sharad pu', 'Shivratri': r'shivratri',
                'Dev Diwali': r'dev diwali', 'Jal Jhilani': r'jal ?jhilani', 'Yogi Jayanti': r'yogi ?jayanti',
                'Ramnavmi': r'ram ?nav', 'Prabodhini': r'prabodhini', 'Bhai Beej': r'bhai b'}
ABROAD = r'\b(usa|uk|london|canada|chicago|new jersey|houston|atlanta|africa|nairobi|australia|auckland|europe|america|' \
         r'leicester|toronto|edison|robbinsville|los angeles|dubai|singapore|asia pacific|middle east|, il|, nj|, tx|, ga|, ca)\b'


def records(db):
    """[(date, text)] before 2010 from the News stories and the photo captions, in India only."""
    import re
    out = set()
    for d, t, pl in db.execute("SELECT date, title, place FROM articles WHERE date < '2010' AND date != ''"):
        out.add((d, f'{t} {pl or ""}'))
    for d, c, pl in db.execute("SELECT date, caption, place FROM photos WHERE date < '2010' AND date_from IS NULL AND caption != ''"):
        out.add((d, f'{c} {pl or ""}'))
    return [(d, t.lower()) for d, t in out if re.match(r'\d{4}-\d\d-\d\d$', d or '') and not re.search(ABROAD, t.lower())]


def better_rules(db, of, rules):
    """For each festival, the tithi next to the one BAPS writes, or another time of day, when it fits the BAPS calendar
    as well (within 2 years) and the records before 2010 better. Shivratri: Chaudas at night (18 of 18), not the Teras
    the calendar writes; Sharad Punam: the Punam at sunrise, as Gondal kept it on 4 October 2009; New Year on the first sunrise of Kartak Sud Padvo, as Gondal kept it in 2001 and 2009."""
    import re
    recs = records(db)
    for name, r in rules.items():
        if 'fixed' in r:
            continue
        words = next((w for k, w in RECORD_WORDS.items() if k.lower() in name.lower()), None)
        ds = [d for d, f in db.execute("SELECT date, festivals FROM calendar WHERE festivals != ''") if name in of.festivals(f)]
        said = [d for d, t in recs if words and re.search(words, t) and not (name == 'Diwali' and 'dev diwali' in t)]
        cands = []
        for T in (r['tithi'] - 1, r['tithi'], r['tithi'] + 1):
            if not 0 <= T < 30:
                continue
            for w in of.WHENS + ['midday']:
                baps = sum(str(of.find(int(d[:4]), r['month'], T, w, r['usual'])) == d for d in ds)
                got = {str(of.find(y, r['month'], T, w, r['usual'])) for y in {int(d[:4]) for d in said}}
                cands.append((baps, sum(d in got for d in said), T == r['tithi'] and w == r['when'], T, w))
        best = max(c[0] for c in cands)
        ok = [c for c in cands if c[0] >= best - 2 and c[0] >= 0.7 * len(ds)]
        rec, baps, same, T, w = max((c[1], c[0], c[2], c[3], c[4]) for c in ok)
        if (T, w) != (r['tithi'], r['when']):
            print(f'{name}: {w} tithi {T} instead of {r["when"]} tithi {r["tithi"]} (BAPS {baps} of {len(ds)}, records {rec} of {len(said)})', file=sys.stderr)
            r.update(label=r['tithi'], tithi=T, when=w, right=baps, moved=True)
    # festivals on the same Indian date stay together (Ramnavmi with Swaminarayan Jayanti)
    for name, r in rules.items():
        if r.get('moved'):
            for other, o in rules.items():
                if not o.get('moved') and 'fixed' not in o and (o['month'], o['tithi']) == (r['month'], r['label']):
                    o.update(label=o['tithi'], tithi=r['tithi'], when=r['when'], moved=True)
                    print(f'{other}: with {name}', file=sys.stderr)
    return rules


def make(a):
    of, day, tname = engine()
    db = sqlite3.connect(a.db)
    rules = {k: v for k, v in of.learn(db).items() if v['right'] >= 0.75 * v['of'] and 'Mahant Swami' not in k}
    rules = better_rules(db, of, rules)
    about = {}
    for name, ab in db.execute("SELECT festivals, festival_about FROM calendar WHERE festivals != '' ORDER BY date"):
        for n in of.festivals(name):
            if ab:
                about[n] = ab.split('; ')[0]
    # the yearly notes: each phrase the BAPS calendar writes in 8 or more years, on its usual Indian date (or its
    # fixed English date), kept only where the sums put it on the BAPS calendar's own day 85 times in 100
    seen = collections.defaultdict(list)
    for d, m, pk, t, n in db.execute("SELECT date, month, paksha, tithi, notes FROM calendar WHERE notes != ''"):
        for part in n.split('; '):
            for p in part.split(', '):
                p = p.strip()
                if p and p not in ('Prarambh', 'Punam', 'Ekadashi(Fast)') and not any(x in p for x in NOTE_OUT) and not p.startswith(m.replace('Adhik ', '')) and m:
                    seen[p].append((d, (m, pk, t.split('/')[0])))
    template = {}
    for p, xs in seen.items():
        if len(xs) < 8:
            continue
        mmdd = collections.Counter(d[5:] for d, k in xs).most_common(1)[0]
        if mmdd[1] >= 0.8 * len(xs):
            template[(None, mmdd[0])] = [p]
            continue
        key = collections.Counter(k for d, k in xs).most_common(1)[0][0]
        usual = sorted(d[5:] for d, k in xs)[len(xs) // 2].replace('02-29', '02-28')
        template[(key, 'near ' + usual)] = template.get((key, 'near ' + usual), []) + [p]
    test = work_out(2010, 2027, rules, template, about, of, day, tname)
    put = {(r['date'], n) for r in test for n in r['notes']}
    good = {p for p, xs in seen.items() if len(xs) >= 8 and sum((d, p) in put for d, k in xs) >= 0.85 * len(xs)}
    template = {k: [p for p in ps if p in good] for k, ps in template.items()}
    # one spelling for each note: the one written most often
    keep = set()
    for p in sorted(good, key=lambda p: -len(seen[p])):
        if not any(p.lower().replace(' ', '')[:7] == q.lower().replace(' ', '')[:7] for q in keep):
            keep.add(p)
    template = {k: [p for p in ps if p in keep] for k, ps in template.items()}
    template = {k: ps for k, ps in template.items() if ps}
    print(f'notes kept: {sorted(p for ps in template.values() for p in ps)}', file=sys.stderr)
    # the check: the same sums on the years the BAPS calendar has
    test = work_out(2010, 2027, rules, template, about, of, day, tname)
    baps = {d: (ind, f) for d, ind, f in db.execute('SELECT date, indian_date, festivals FROM calendar')}
    n = same = near = 0
    for r in test:
        b = baps.get(r['date'])
        if not b or not b[0]:
            continue
        n += 1
        bt = b[0].split('/')[0]
        same += r['indian_date'] == bt
    fr = fn = 0
    for name in rules:
        bd = [d for d, (ind, f) in baps.items() if name in of.festivals(f)]
        wd = {r['date'] for r in test if any(x['name'] == name for x in r['festivals'])}
        fn += len(bd)
        fr += sum(d in wd for d in bd)
    print(f'check on 2010 to 2027: Indian date the same as the BAPS calendar on {same} of {n} days ({100 * same / n:.1f}%); '
          f'festivals on the same day {fr} of {fn} ({100 * fr / fn:.1f}%)', file=sys.stderr)
    days = work_out(a.first, a.last, rules, template, about, of, day, tname)
    head = {'source': SOURCE, 'first': days[0]['date'], 'last': days[-1]['date'],
            'check': {'days': n, 'same_indian_date': same, 'festival_days': fn, 'same_festival_day': fr},
            'about': {x['name']: x['about'] for d in days for x in d['festivals'] if x['about']},
            'columns': ['date', 'vikram_samvat', 'month', 'paksha', 'tithi', 'festivals', 'notes', 'ekadashi']}
    rows = [json.dumps([d['date'], d['vikram_samvat'], d['month'], d['paksha'], d['tithi'], [x['name'] for x in d['festivals']],
                        d['notes'], int(d['ekadashi'])], ensure_ascii=False, separators=(',', ':')) for d in days]
    with open(OUT, 'w', encoding='utf-8') as f:   # one day a line
        f.write(json.dumps(head, ensure_ascii=False, indent=1)[:-2] + ',\n "days": [\n' + ',\n'.join(rows) + '\n]}\n')
    print(f'{OUT}: {len(days)} days, {sum(bool(d["festivals"]) for d in days)} with a festival', file=sys.stderr)


def add(a):
    """This build's copy of the calendar table gets the worked out days; a BAPS calendar day is never replaced."""
    if not os.path.exists(OUT):
        print('old calendar: no worked out days, nothing added')
        return
    saved = json.load(open(OUT, encoding='utf-8'))
    about = saved['about']
    days = []
    for date, vs, m, p, t, fs, ns, ek in saved['days']:
        d = dt.date.fromisoformat(date)
        days.append(dict(date=date, weekday=WEEKDAYS[d.weekday()], vikram_samvat=vs, lunar_months=m, month=m, paksha=p,
                         tithi=t, indian_date=f'{m} {p} {t}', festivals=[dict(name=f, about=about.get(f, '')) for f in fs],
                         notes=ns, ekadashi=ek, punam=t == 'Punam', amas=t == 'Amas', source=SOURCE))
    db = sqlite3.connect(a.db)
    before = db.execute('SELECT count(*) FROM calendar').fetchone()[0]
    db.executemany('INSERT OR IGNORE INTO calendar VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', [
        (c['date'], c['weekday'], c['vikram_samvat'], c['lunar_months'], c['month'], c['paksha'], c['tithi'],
         c['indian_date'], '; '.join(f['name'] for f in c['festivals']),
         '; '.join(f['about'] for f in c['festivals'] if f.get('about')), '; '.join(c['notes']),
         int(c['ekadashi']), int(c['punam']), int(c['amas']), c['source']) for c in days])
    db.commit()
    print(f'old calendar: {db.execute("SELECT count(*) FROM calendar").fetchone()[0] - before} worked out days added before 2010')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=['make', 'add'])
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--first', type=int, default=FIRST)
    ap.add_argument('--last', type=int, default=LAST)
    a = ap.parse_args()
    make(a) if a.what == 'make' else add(a)
