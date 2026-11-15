"""Bapa's Jivan Charitra (the three study PDFs of the biography, 1921 to 1975) as website data, for the mockup."""
import json, re, datetime, sys
S = sys.argv[1]; OUT = sys.argv[2]
sh = json.load(open(S))
def rows(name):
    R = sh[name]; head = R['1']
    return [dict(zip(head, R[k])) for k in sorted(R, key=int) if k != '1']
def val(x):
    if isinstance(x, dict): return x.get('date') or x.get('number') or x.get('value')
    if isinstance(x, str) and x.startswith("'"): return x[1:]
    if isinstance(x, float) and x.is_integer(): return str(int(x))
    return x

# the videos the PDFs link, by the day or thing they sit beside (read from the link positions on each page)
V = {
 '1939-11-07': 'LIWsAMh_5dI', '1940-01-10': 'U-fDjoD61qU', '1950-05-21': 'aE0qCQQMM8w', '1960-02-22': 'tRb7HZS3_9E',
 '1971-01-23': '0dPzmR2xoQ8', '1971-11-26': '1sx_5WdxMt8', '1972-11-25': 'C6jbEnvnwhQ', '1972-11-30': 'C6jbEnvnwhQ',
 '1972-12-14': 'Mfu9zhcVop0', '1973-01-01': 'AR84Mmyzxvg', '1973-12-03': 'k6uSsg1jr8s', '1974-01-25': 'LTmAYSAcQh4',
 '1974-03-29': 'fRjHujCEH10', '1974-07-19': 'yS-XyDfQWJ4', '1974-07-28': 'bUK7KM7DbW4', '1974-08-03': '8I4u0bhimwM',
 '1974-09-16': 'elA9eV0UwK0', '1974-09-29': '-y6OlgIn60k', '1974-11-13': 'Ryr0POTEj4s', '1974-12-04': '-nxatp_umDg',
 '1974-12-22': '1dOED05LBDo', '1975-01-04': 'ZH5onjo3t74',
}
# videos beside a row that has no single day (by the row's date in the Timeline sheet)
VROW = {'1939-11-22': 'LIWsAMh_5dI', '1947-07-01': 'XvQTwaqnU5s', '1951-05-10': 'S9G9Mm_3lHc', '1951-05-11': 'UNmfnZMk9t8',
        '1953-07-01': 'SjSBsVuPvaU', '1956-12-01': 'SjSBsVuPvaU', '1960-01-15': 'tRb7HZS3_9E', '1970-02-01': '3WOxo9I6Sxk',
        '1970-06-06': '3WOxo9I6Sxk', '1974-05-28': 'bU8W_I5mmkM', '1974-09-10': 'KMyi4rT2aZU', '1974-09-20': 'qV_nCC6C2Y0',
        '1974-02-15': '03r_kvt48zY', '1974-03-30': 'fRjHujCEH10', '1974-05-06': 'x6pqab1fYFA', '1974-05-12': 'bU8W_I5mmkM',
        '1974-06-03': '_lEo6M1i29M', '1974-07-06': '-iiriHvgXp0', '1974-07-27': 'bUK7KM7DbW4', '1974-08-13': '_lEo6M1i29M',
        '1974-10-06': '1FV2HsrADvM', '1974-11-18': 'YpwzPLmuDcw', '1974-12-01': '-nxatp_umDg', '1974-12-08': 'fRjHujCEH10',
        '1972-11-25': 'C6jbEnvnwhQ', '1974-03-29': 'fRjHujCEH10', '1972-07-01': None}
# dates Claude worked out from a tithi, not written in the PDFs: kept back until Darpan checks them
HELD = {'1921-12-07', '1939-11-22', '1951-05-10'}

PAGE = re.compile(r'\s*\((?:page|pages|p\.)\s*[\d\u2013-]+\)', re.I)
def split(ev):
    ev = PAGE.sub('', ev)
    # the event line: first sentence is the heading, the rest its words
    parts = re.split(r'(?<=[.!?"])\s+(?=[A-Z"])', ev.strip())
    h = parts[0].rstrip('.'); w = [' '.join(parts[1:])] if len(parts) > 1 else []
    return h, w

guru = lambda d: 'Pramukh Swami Maharaj'
days, ranges, held, reads, videos = {}, [], [], [], {}
for r in rows('Timeline'):
    d = val(r['Sort date']); prec = r['Date precision'] or ''; ev = r['Event']
    end = val(r['End date']); place = r['Location'] or ''
    h, w = split(ev)
    vid = V.get(d) if prec.startswith('Day') else VROW.get(d)
    item = {'d': d, 'pl': place, 'h': h, 'w': w, 'v': vid, 'pg': val(r['Page']), 'vol': r['Biography volume'],
            'prec': prec, 'conf': r['Confidence'], 'note': r['Notes'], 'written': val(r['Date as written']), 'cat': r['Category'],
            'people': r['People'], 'region': r['Region / country'], 'end': end}
    if d in HELD:
        held.append(item); continue
    if prec in ('Day', 'Day (derived)'):
        days.setdefault(d[5:], {}).setdefault(d[:4], []).append(item)
        if vid: videos[d] = [vid, h]
    elif prec == 'Range' and end:
        ranges.append(item)
    # every row goes into Search, by its day, month or year as the biography gives it
    sd = d if prec.startswith('Day') or prec == 'Range' else d[:7] if prec.startswith('Month') or prec.startswith('Fortnight') else d[:4]
    reads.append([sd, place, 'Jivan Charitra', h, w if w else [h + '.'], [], '', d])
for r in rows('Undated incidents'):
    reads.append([None, r['Location'] or '', 'Jivan Charitra', r['Virtue'] + ': ' + r['Incident'].rstrip('.'), [r['Incident']], [], '', r['Approximate period (Claude\'s estimate)']])

months = {}
for r in rows('Monthly calendar'):
    months[val(r['Month start'])[:7]] = [p.strip() for p in r['Main places (as dated in the biography)'].split(',')]
months['1975-01'] = ['Nairobi', 'Mumbai']

# Travels: one stop a month at the places the biography dates in it, then every exact day as its own stop
COUNTRY = {'Kenya': 'Kenya', 'Tanzania': 'Tanzania', 'Zambia': 'Zambia', 'England': 'UK', 'USA': 'USA', 'Canada': 'Canada',
           'South Africa': 'South Africa', 'Rhodesia (Zimbabwe)': 'Zimbabwe', 'Mauritius': 'Mauritius'}
def eom(ym):
    y, m = map(int, ym.split('-')); n = datetime.date(y + m // 12, m % 12 + 1, 1) - datetime.timedelta(1); return n.isoformat()
stays = {}
D = datetime.date.fromisoformat
iso = lambda x: x.isoformat()
exact = sorted([it for md in days.values() for y in md.values() for it in y if it['d'] >= '1971-02-01'], key=lambda x: x['d'])
TOWN = {'Kudaya station': 'Kudaya station', 'England (coast)': None, 'South Africa': None, 'Mauritius': 'Mauritius'}
def town(it):
    p = it['pl'] or ''
    if p in TOWN: return TOWN[p]
    return p.split(';')[0].split(',')[0].strip() or None
# the plan: (from, to, place, caption) blocks; exact days cut into them
blocks = []
for ym, pls in sorted(months.items()):
    if '1971-02' <= ym <= '1974-03':
        blocks.append([ym + '-01', eom(ym), pls[0], 'This month: ' + ', '.join(pls)])
# the special train yatra: its dated halts, and the halts between them as the route diagram orders them
TRAIN = [('1972-11-25', 'Vadodara'), ('1972-11-26', 'Ujjain'), ('1972-11-27', 'Bhopal', 1), ('1972-11-28', 'Agra'),
         ('1972-11-29', 'Agra', 1), ('1972-11-30', 'Haridwar'),
         ('1972-12-01', 'Delhi', 'On the train yatra: Delhi, Mathura, Kanpur, Prayag, Ayodhya, Chhapaiya, Kashi'),
         ('1972-12-14', 'Kolkata'), ('1972-12-15', 'Kolkata', 1), ('1972-12-17', 'Jagannath Puri'),
         ('1972-12-18', 'Madurai', 'On the train yatra: Rajahmundry, Vijayawada, Kanchi, Pondicherry, Madurai, Rameshwar, Kanyakumari, Bangalore, Mysore, Tirupati'),
         ('1973-01-01', 'Kudaya station'), ('1973-01-02', 'Pandharpur', 'On the train yatra: Pandharpur, Solapur'), ('1973-01-03', 'Poona'),
         ('1973-01-04', 'Mumbai', 'The yatra ends via Mumbai. This month: Pandharpur, Poona, Uran, Daman, Pardi')]
blocks = [b for b in blocks if not ('1972-11-25' <= b[0] <= '1973-01-03' or '1972-11-25' <= b[1] <= '1973-01-03')] + blocks[:0]
nov72 = [b for b in [[ '1972-11-01', '1972-11-24', 'Ahmedabad', 'This month: ' + ', '.join(months['1972-11'])]]]
jan73 = [['1973-01-04', '1973-01-31', 'Pandharpur', 'This month: ' + ', '.join(months['1973-01'])]]
blocks += nov72
for i, t in enumerate(TRAIN):
    a = t[0]; b = iso(D(TRAIN[i + 1][0]) - datetime.timedelta(1)) if i + 1 < len(TRAIN) else '1973-01-31'
    cap = t[2] if len(t) > 2 and isinstance(t[2], str) else 'Special train yatra'
    blocks.append([a, b, t[1], cap])
# the 1974 world yatra by country, as the bar chart and the stays give it
WORLD = [('1974-03-29', '1974-05-05', 'Nairobi', 'Kenya: Nairobi, Mombasa, Nakuru, Kisumu, Nanyuki'),
         ('1974-05-06', '1974-05-11', 'Dar es Salaam', 'Tanzania: Dar es Salaam, Mwanza'),
         ('1974-05-12', '1974-06-02', 'Lusaka', 'Zambia: Ndola, Kitwe, Chingola, Mufulira, Kabwe, Lusaka, Livingstone'),
         ('1974-06-03', '1974-07-05', 'London', 'England: London and other towns'),
         ('1974-07-06', '1974-08-11', 'New York', 'USA: New York, Hoboken, Newark, Scranton, Philadelphia, Washington, Cincinnati, Chicago, Cleveland, Rochester, Poughkeepsie, Boston'),
         ('1974-08-12', '1974-10-05', 'London', 'England: London, Leicester, Wellingborough, Birmingham, Bolton, Liverpool, Preston, Coventry, Nuneaton, Peterborough, Luton'),
         ('1974-10-06', '1974-11-17', 'Durban', 'South Africa: Johannesburg (Lenasia), Durban (Isipingo), Pretoria'),
         ('1974-11-18', '1974-11-30', 'Bulawayo', 'Rhodesia: Bulawayo, Kwekwe, Gatooma, Norton'),
         ('1974-12-01', '1974-12-07', 'Mauritius', 'Mauritius'),
         ('1974-12-08', '1975-01-03', 'Nairobi', 'Kenya: Nairobi, Mombasa, Nakuru')]
blocks = [[b[0], min(b[1], '1974-03-28'), b[2], b[3]] for b in blocks if b[0] < '1974-03-29'] + [list(w) for w in WORLD]

blocks = [b for b in blocks if b[0] <= b[1]]
blocks.sort()
for a, b, p, cap in blocks:
    cur = a
    for it in [x for x in exact if a <= x['d'] <= b]:
        t = town(it)
        if not t: continue
        if it['d'] > cur: stays.setdefault(cur[:4], []).append({'p': p, 'a': cur, 'b': iso(D(it['d']) - datetime.timedelta(1)), 'cap': cap, 'n': 0})
        if stays.get(it['d'][:4]) and stays[it['d'][:4]][-1]['a'] == it['d']:
            stays[it['d'][:4]][-1]['cap'] += '. ' + it['h']; cur = iso(D(it['d']) + datetime.timedelta(1)); continue
        stays.setdefault(it['d'][:4], []).append({'p': t, 'a': it['d'], 'b': it['d'], 'cap': it['h'], 'n': 0, 'v': it['v']})
        cur = iso(D(it['d']) + datetime.timedelta(1))
    if cur <= b: stays.setdefault(cur[:4], []).append({'p': p, 'a': cur, 'b': b, 'cap': cap, 'n': 0})
stays.setdefault('1975', []).append({'p': 'Mumbai', 'a': '1975-01-04', 'b': '1975-01-04', 'cap': 'Return to India after the 281 day dharma yatra', 'n': 0, 'v': V['1975-01-04']})
names = sorted({s['p'] for y in stays.values() for s in y})
json.dump({'days': days, 'ranges': ranges, 'months': months, 'held': held, 'reads': reads, 'videos': videos,
           'stays': stays, 'names': names}, open(OUT, 'w'), ensure_ascii=False, indent=1)
n = sum(len(v) for md in days.values() for v in md.values())
print(f'{n} exact days on {len(days)} dates; {len(ranges)} ranges; {len(months)} months; {len(held)} held; {len(reads)} search rows; {len(videos)} day videos; stays', {y: len(v) for y, v in stays.items()}, len(names), 'places')
print(names)
