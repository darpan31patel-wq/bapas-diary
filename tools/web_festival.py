"""Festival days on the Today page (Darpan, 30 Oct 2026: "make special cards for the Diwali days, especially the Diwali
day and that New Year day, which is an Annakut day ... according to the Indian date"). Website only: nothing here
touches the daily 2pm picture.

On the day this year's BAPS calendar says is Diwali (or Annakut), Today shows every year's Diwali, each on its own
Indian date, not the same English date: 2014's card is 23 October 2014, 2025's is 20 October 2025. Each year's card is
what Today itself shows on that year's festival day (the day files after web_rules.py day, so every Today rule holds:
Bapa in person only, his whole head framed, channel darshans), with the photos that say the festival first: for Diwali
the Chopda Pujan, the diyas, lights, arti and fireworks; for Annakut the annakut itself, thal, sweets and food.

    python3 tools/web_festival.py --day day/data/day --db bapa.db --deep-tags deep-tags.json --out day/data/fest

Writes data/fest/diwali.json and data/fest/annakut.json in the day files' own shape, so the page draws them the same way:
  {"date": "fest", "fest": "diwali", "title": "Diwali", "years": [{"y": 2014, "d": "2014-10-23", "place": ..., "p": [...]}],
   "cal": {"2014": [indian date, festivals, notes]}, "stories": []}
Before 2010 (no BAPS calendar in the diary) the festival's day is the one tools/old_festivals.py worked out from the moon
and the sun, the table OLD_FEST in site/search-ask.js.
"""
import argparse, datetime, json, os, re, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST = 1950   # the channels' darshans of Bapa start here (web_rules.TG_FROM)

FESTS = {
    'diwali': dict(
        title='Diwali', old='Diwali', ti='Aso Vad Amas',
        cal=re.compile(r'^diwali$', re.I),
        words=re.compile(r'diwali|deepavali|chopda|sharda|lakshmi|\bdiya|\bdiva\b|\bdivas\b|\blamps?\b|fireworks|lit up|'
                         r'illuminat|lights?\b|rangoli', re.I),
        tags={'fireworks', 'diya', 'lights', 'lit up at night', 'mandir at night', 'arti', 'rangoli'}, strong={'fireworks', 'diya', 'rangoli'},
        keep_all=True),   # Chopda Pujan is Bapa's Diwali: every photo of the day stays, the festive ones first
    'annakut': dict(
        title='Annakut', old='Annakut and Bestu Varash (New Year)', ti='Kartak Sud Padvo',
        cal=re.compile(r'annakut', re.I),
        words=re.compile(r'annakut|thal\b|thaal|prasad|sweets|food|fruit|mithai|dishes|offer(s|ed|ing)? (the )?(annakut|thal)', re.I),
        tags={'annakut', 'food', 'sweets', 'thal', 'fruit', 'dry fruits', 'vegetables', 'serving food', 'eating'}, strong={'annakut', 'sweets', 'thal'},
        keep_all=False),  # "everything surrounding food": a year with food photos shows only those
    # the other festivals (Darpan, 30 Oct 2026: "I want to do that for all the festivals"): every photo of the day stays,
    # the ones that show or say the festival first
    'janmashtami': dict(title='Janmashtami', old='Janmashtami', ti='Shravan Vad Atham', cal=re.compile(r'janmashtami', re.I),
        words=re.compile(r'janmashtami|krishna|krushna|matki|dahi.?handi|cradle|paranu|midnight', re.I),
        tags={'murti', 'arti', 'night'}, strong={'peacock feathers'}),
    'holi': dict(title='Holi', old='Holi', ti='Fagan Sud Punam', cal=re.compile(r'^holi\b', re.I),
        words=re.compile(r'\bholi\b|holika|bonfire|fire', re.I), tags={'night', 'arti'}, strong=set()),
    'fuldol': dict(title='Fuldol', old='Pushpadolotsav (Dhuleti)', ti='Fagan Vad Padvo', cal=re.compile(r'pushpadol|fuldol|dhuleti', re.I),
        words=re.compile(r'fuldol|pushpadol|dhuleti|colou?rs?|rang|sprinkl|swing|hindol|petals', re.I),
        tags={'showering flowers', 'petals', 'flowers', 'flower decoration'}, strong={'showering flowers', 'petals'}),
    'gurupurnima': dict(title='Guru Purnima', old='Guru Purnima', ti='Ashadh Sud Punam', cal=re.compile(r'guru purnima', re.I),
        words=re.compile(r'guru ?purnima|guru ?pujan|pujan|garland|vandan|guru parampara', re.I),
        tags={'garland', 'puja', 'flowers'}, strong={'garland'}),
    'harinom': dict(title='Swaminarayan Jayanti', old='Swaminarayan Jayanti (Hari Navmi)', ti='Chaitra Sud Nom',
        cal=re.compile(r'hari-?nom|hari navmi|swaminarayan jayanti', re.I),
        words=re.compile(r'jayanti|hari ?n(o|av)m|ram ?navmi|cradle|paranu|birthday|janma', re.I),
        tags={'arti', 'flowers', 'garland'}, strong={'cake'}),
    'vasant': dict(title='Vasant Panchami', old='Vasant Panchmi', ti='Maha Sud Pancham', cal=re.compile(r'vasant panch', re.I),
        words=re.compile(r'vasant|panchmi|panchami|shikshapatri|brahmanand|nishkulanand|spring', re.I),
        tags={'yellow flowers', 'flowers', 'book'}, strong={'yellow flowers'}),
    'rathyatra': dict(title='Rathyatra', old='Rathyatra', ti='Ashadh Sud Bij', cal=re.compile(r'rath ?yatra', re.I),
        words=re.compile(r'rath|chariot|yatra|pull', re.I), tags={'procession', 'flags'}, strong={'chariot'}),
    'raksha': dict(title='Raksha Bandhan', old='Raksha Bandhan', ti='Shravan Sud Punam', cal=re.compile(r'raksha ?bandhan', re.I),
        words=re.compile(r'raksha|rakhi|nadachhadi|thread', re.I), tags=set(), strong=set()),
    'sharad': dict(title='Sharad Punam', old="Gunatitanand Swami's Birthday (Sharad Punam)", ti='Aso Sud Punam',
        cal=re.compile(r"sharad pun|gunatitanand swami'?s birthday", re.I),
        words=re.compile(r'sharad|punam|gunatitanand|dudh|pauva|moon', re.I), tags={'night', 'sweets'}, strong=set()),
    'psm': dict(title="Pramukh Swami Maharaj's Jayanti", old="Pramukh Swami Maharaj's Jayanti", ti='Magshar Sud Atham',
        cal=re.compile(r"pramukh swami maharaj('?s)? (janma )?jayanti(?! celebration)", re.I),
        words=re.compile(r'jayanti|birthday|janma|cake', re.I), tags={'garland', 'flowers', 'cake'}, strong={'cake'}),
    'msm': dict(title="Mahant Swami Maharaj's Jayanti", old="Mahant Swami Maharaj's Jayanti", ti='Bhadarvo Vad Nom',
        cal=re.compile(r"mahant swami maharaj('?s)? (janma )?jayanti(?! celebration)", re.I), since=2016,   # his own birthdays as Bapa
        words=re.compile(r'jayanti|birthday|janma|cake', re.I), tags={'garland', 'flowers', 'cake'}, strong={'cake'}),
}
for F in FESTS.values():
    F.setdefault('keep_all', True)
NEAR = 1   # a year whose photos come from a nearby day (web_rules NEAR_DAYS) counts only when it is the next or last day


def old_days(ask):
    """{festival: {year: 'YYYY-MM-DD'}} from site/search-ask.js's OLD_FEST (MMDD for each year from OLD_FEST_FROM)."""
    js = open(ask, encoding='utf-8').read()
    first = int(re.search(r'OLD_FEST_FROM = (\d+)', js).group(1))
    out = {}
    for name, days in re.findall(r'"([^"]+)": "([0-9-]+)"', js):
        out[name] = {first + i // 4: f'{first + i // 4}-{days[i:i + 2]}-{days[i + 2:i + 4]}'
                     for i in range(0, len(days), 4) if days[i] != '-'}
    return out


def festival_days(db, ask):
    """{key: {year: date}}: the BAPS calendar's day from 2010, the worked out day before."""
    old = old_days(ask)
    days = {k: dict((y, d) for y, d in old.get(F['old'], {}).items() if y >= FIRST) for k, F in FESTS.items()}
    seen = set()   # the year's first day the calendar names it (2010 also calls Aso Vad Amas Annakut, before Diwali)
    for date, fests in db.execute("SELECT date, festivals FROM calendar WHERE festivals != '' ORDER BY date"):
        for part in re.split(r'[;,/]| and ', fests or ''):
            for k, F in FESTS.items():
                y = int(date[:4])
                if F['cal'].search(part.strip()) and (k, y) not in seen:
                    seen.add((k, y))
                    days[k][y] = date
    return days


def festive(p, F, tags):
    """How much a photo is the festival, and whether its caption says it: the festival itself seen in it (its deep
    tags: the annakut, sweets, diyas, fireworks) 4, its caption saying it 3, something near it seen (food, lights) 1."""
    said = F['words'].search(p[2] or '') or F['words'].search(p[5] if len(p) > 5 and isinstance(p[5], str) else '')
    t = {x.strip() for x in tags.get(f'{p[0]}/{p[1]}', '').split(',')}
    return 3 * bool(said) + (4 if t & F['strong'] else 1 if t & F['tags'] else 0), bool(said)


def build(a):
    db = sqlite3.connect(a.db)
    tags = json.load(open(a.deep_tags, encoding='utf-8')) if a.deep_tags and os.path.exists(a.deep_tags) else {}
    os.makedirs(a.out, exist_ok=True)
    keys = set()
    for k, days in festival_days(db, a.ask).items():
        F = FESTS[k]
        out = {'date': 'fest', 'fest': k, 'title': F['title'], 'years': [], 'cal': {}, 'stories': []}
        files = {}
        for y, date in sorted(days.items()):
            if date[:4] >= str(datetime.date.today().year + 1) or y < F.get('since', 0):
                continue
            mmdd = date[5:]
            if mmdd not in files:
                path = os.path.join(a.day, mmdd + '.json')
                files[mmdd] = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
            D = files[mmdd]
            Y = next((Y for Y in D.get('years', []) if Y['y'] == y), None)
            if not Y:
                continue
            Y = json.loads(json.dumps(Y))
            if not Y['p'] and Y.get('trip'):   # photos from a nearby day: only the festival's own days
                d0, d1 = (datetime.date.fromisoformat(x) for x in Y['trip'])
                d = datetime.date.fromisoformat(date)
                if not (d0 - datetime.timedelta(NEAR) <= d <= d1 + datetime.timedelta(NEAR)):
                    continue
            for part in ('p', 't'):
                ps = Y.get(part) or []
                rated = [festive(p, F, tags) for p in ps]
                if part == 't':   # a trip's or a nearby day's photos: only those whose captions say this festival
                    ps, rated = [p for p, r in zip(ps, rated) if r[1]], [r for r in rated if r[1]]
                score = [r[0] for r in rated]
                order = sorted(range(len(ps)), key=lambda i: -score[i])   # stable: the best darshan first within each
                ps = [ps[i] for i in order]
                if not F['keep_all'] and sum(s > 0 for s in score) >= 2:
                    ps = ps[:sum(s > 0 for s in score)]
                Y[part] = ps
            if not Y['p'] and not Y.get('t'):
                continue
            if not Y.get('t'):
                Y.pop('t', None); Y.pop('trip', None)
            Y['d'] = date
            if re.fullmatch(r'\d{4}', (Y.get('place') or '').strip()):   # a few channel posts give the year where the town goes
                Y['place'] = ''
            Y.pop('day', None)   # the stories stay on their own date's page; the card says only what its photos show
            out['years'].append(Y)
            out['cal'][str(y)] = (D.get('cal') or {}).get(str(y)) or [F['ti'], F['title'], '']
            for part in ('p', 't'):
                keys.update(f'{p[0]}/{p[1]}' for p in Y.get(part) or [])
        with open(os.path.join(a.out, k + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
        n = sum(len(Y['p']) + len(Y.get('t') or []) for Y in out['years'])
        print(f"{k}: {len(out['years'])} years, {n} photos ({' '.join(str(Y['y']) for Y in out['years'])})")
    if a.keys:
        with open(a.keys, 'w') as fh:
            fh.write(''.join(k + '\n' for k in sorted(keys)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--day', required=True, help='the finished day files (after web_rules.py day)')
    ap.add_argument('--db', required=True, help='bapa.db, for the BAPS calendar')
    ap.add_argument('--deep-tags', help="what is in each photo (release deep-tags)")
    ap.add_argument('--ask', default=os.path.join(HERE, 'site', 'search-ask.js'), help='OLD_FEST, the days before 2010')
    ap.add_argument('--out', required=True)
    ap.add_argument('--keys', help='also list every photo shown (ALBUM/FILE), for a mockup')
    build(ap.parse_args())


if __name__ == '__main__':
    main()
