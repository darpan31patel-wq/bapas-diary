"""Travels and "Where is Bapa" filled in for the early years from the old BAPS website's day by day reports (Darpan,
13 Nov 2026: "Travels filled in for the early years. The same reports say where Bapa was each day").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from swaminarayan.org.

    python3 tools/sorg_travels.py geo --days sorg-days.json --travels live/travels/index.html --geonames cities500.txt --out sorg-geo.json
    python3 tools/sorg_travels.py add --days sorg-days.json --geo sorg-geo.json --travels out/travels/index.html

geo   finds each town the reports name on the map: first the towns Travels already has, then GeoNames (towns of 500
      people or more, read from the file, nothing fetched here). A name that two towns share (Mandvi in Kachchh and
      Mandvi near Surat) goes to the one nearest the towns he was in the days before and after. Writes
      {"Bhuj": {"name": "Bhuj", "country": "India", "ll": [69.67, 23.25], "from": "travels" | "geonames <id>"}};
      a name it cannot find is left out and listed, never guessed.
add   puts a stay on the Journey for every run of days the reports tell and the Journey does not have yet (no photo of
      those days): each day goes to the town he ended the day in, and the days in one town in a row are one stay. The
      stays the photos already give are never moved or changed.
calendar  the Calendar's days with no photo get the town the report names (out/data/calendar.json)
"""
import argparse, collections, datetime, json, math, re, sys

ALIASES = {'amdavad': 'ahmedabad', 'ahmadabad': 'ahmedabad', 'vadodara': 'vadodara', 'baroda': 'vadodara',
           'bombay': 'mumbai', 'calcutta': 'kolkata', 'madras': 'chennai', 'bharuch': 'bharuch', 'broach': 'bharuch',
           'surat': 'surat', 'kachchh': 'bhuj', 'akshardham': 'gandhinagar', 'shahibaug': 'ahmedabad',
           'vidyanagar': 'vallabh vidyanagar', 'neasden': 'london', 'nairobi': 'nairobi', 'bahrain': 'manama',
           'kuwait': 'kuwait city', 'muscat': 'muscat', 'dar-es-salaam': 'dar es salaam', 'new york': 'new york city'}
COUNTRY = {'IN': 'India', 'GB': 'UK', 'US': 'USA', 'KE': 'Kenya', 'TZ': 'Tanzania', 'UG': 'Uganda', 'CA': 'Canada',
           'AE': 'UAE', 'BH': 'Bahrain', 'KW': 'Kuwait', 'OM': 'Oman', 'AU': 'Australia', 'NZ': 'New Zealand',
           'ZA': 'South Africa', 'ZM': 'Zambia', 'MW': 'Malawi', 'SG': 'Singapore', 'MY': 'Malaysia', 'HK': 'Hong Kong',
           'BE': 'Belgium', 'FR': 'France', 'DE': 'Germany', 'PT': 'Portugal', 'NL': 'Netherlands', 'NP': 'Nepal',
           'LK': 'Sri Lanka', 'BD': 'Bangladesh', 'TH': 'Thailand', 'JP': 'Japan', 'MU': 'Mauritius', 'BW': 'Botswana'}


def trips(html):
    m = re.search(r'(<script id="trips" type="application/json">)(.*?)(</script>)', html, re.S)
    return m, json.loads(m.group(2))


def key(name):
    k = re.sub(r'[^a-z ]+', ' ', name.lower()).strip()
    k = re.sub(r'\s+', ' ', k)
    return ALIASES.get(k, k)


def km(a, b):
    (x1, y1), (x2, y2) = a, b
    p = math.pi / 180
    h = math.sin((y2 - y1) * p / 2) ** 2 + math.cos(y1 * p) * math.cos(y2 * p) * math.sin((x2 - x1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(min(1, h)))


def geo(a):
    days = json.load(open(a.days, encoding='utf-8'))
    _, data = trips(open(a.travels, encoding='utf-8').read())
    have = {key(v['name']): dict(v, **{'from': 'travels'}) for v in data['places'].values()}
    have.update({key(k): dict(v, **{'from': 'travels'}) for k, v in data['places'].items()})
    names = sorted({p for d in days.values() for p in d['pl']})
    want = {key(n) for n in names} - set(have)
    cand = collections.defaultdict(list)
    if a.geonames:
        for line in open(a.geonames, encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            if len(f) < 15 or f[6] != 'P':
                continue
            for n in {f[1], f[2]} | set(f[3].split(',') if len(f[3]) < 400 else []):
                k = key(n)
                if k in want:
                    cand[k].append(dict(name=f[1], country=COUNTRY.get(f[8], f[8]), ll=[round(float(f[5]), 2), round(float(f[4]), 2)],
                                        pop=int(f[14] or 0), id=f[0], cc=f[8], adm=f[10]))
    # each day's towns in order, to choose between two towns of the same name by the towns around them
    order = [key(p) for d in sorted(days) for p in days[d]['pl']]
    found = dict(have)
    for _ in range(3):   # names with one town first, then the rest by their neighbours
        for i, k in enumerate(order):
            if k in found or k not in cand:
                continue
            cs = cand[k]
            near = [found[order[j]]['ll'] for j in range(max(0, i - 6), min(len(order), i + 7)) if j != i and order[j] in found]
            if len(cs) == 1 and not near:
                c = cs[0]
            elif near:
                c = min(cs, key=lambda c: min(km(c['ll'], n) for n in near) - min(c['pop'], 2e6) / 2e5)
                if min(km(c['ll'], n) for n in near) > 2500 and len(cs) > 1:   # nothing nearby: the biggest town of that name
                    c = max(cs, key=lambda c: c['pop'])
            elif _ == 2:
                c = max(cs, key=lambda c: c['pop'])
            else:
                continue
            found[k] = dict(name=c['name'], country=c['country'], ll=c['ll'], **{'from': f"geonames {c['id']}"})
    out, lost = {}, []
    for n in names:
        v = found.get(key(n))
        if v:
            out[n] = v
        else:
            lost.append(n)
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'towns on the map: {len(out)} of {len(names)}; not found ({len(lost)}): {", ".join(lost)}')


def add(a):
    days = json.load(open(a.days, encoding='utf-8'))
    places = json.load(open(a.geo, encoding='utf-8'))
    html = open(a.travels, encoding='utf-8').read()
    m, data = trips(html)
    covered = set()
    for y, stops in data['years'].items():
        for s in stops:
            d0, d1 = datetime.date.fromisoformat(s['a']), datetime.date.fromisoformat(s['b'])
            while d0 <= d1:
                covered.add(d0.isoformat())
                d0 += datetime.timedelta(days=1)
    by_name = {key(v['name']): k for k, v in data['places'].items()}
    added = collections.Counter()
    runs = []   # (town, first day, last day)
    for d in sorted(days):
        if d in covered:
            continue
        town = next((p for p in reversed(days[d]['pl']) if p in places), None)   # where he ended the day
        if not town:
            continue
        nxt = (datetime.date.fromisoformat(runs[-1][2]) + datetime.timedelta(days=1)).isoformat() if runs else None
        if runs and runs[-1][0] == town and nxt == d:
            runs[-1][2] = d
        else:
            runs.append([town, d, d])
    for town, d0, d1 in runs:
        g = places[town]
        pid = by_name.get(key(g['name']))
        if not pid:
            pid = g['name']
            while pid in data['places']:
                pid += ' '
            data['places'][pid] = {'name': g['name'], 'country': g['country'], 'll': g['ll']}
            by_name[key(g['name'])] = pid
        data['years'].setdefault(d0[:4], []).append({'p': pid, 'a': d0, 'b': d1, 'n': 0, 'cap': '', 'r': 1})
        added[d0[:4]] += 1
    for y in data['years']:
        # keep each year's stops in date order; the photo sheet squares (pics) are keyed by position, so move them too
        old = data['years'][y]
        order = sorted(range(len(old)), key=lambda i: (old[i]['a'], old[i].get('r', 0)))
        if order != list(range(len(old))):
            pics = data.get('pics', {})
            moved = {}
            for new_i, old_i in enumerate(order):
                k = f'{y}-{old_i}'
                if k in pics:
                    moved[f'{y}-{new_i}'] = pics.pop(k)
            pics.update(moved)
            data['years'][y] = [old[i] for i in order]
    data['years'] = dict(sorted(data['years'].items()))
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:m.start(2)] + blob + html[m.end(2):]
    open(a.travels, 'w', encoding='utf-8').write(html)
    print(f'Travels: {sum(added.values())} stays added from the reports ({", ".join(f"{y}: {n}" for y, n in sorted(added.items()))})')


def calendar(a):
    """the Calendar's days with no photo get the town the report names, so its journey along the top reaches back too"""
    days = json.load(open(a.days, encoding='utf-8'))
    cal = json.load(open(a.cal, encoding='utf-8'))
    n = 0
    for d, v in days.items():
        rows = cal.get('m', {}).get(d[:7])
        i = int(d[8:]) - 1
        if rows and i < len(rows) and isinstance(rows[i], list) and len(rows[i]) > 3 and not rows[i][3] and v['pl']:
            rows[i][3] = v['pl'][-1]
            n += 1
    json.dump(cal, open(a.cal, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'Calendar: {n} days given their town from the reports')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('geo')
    g.add_argument('--days', required=True); g.add_argument('--travels', required=True)
    g.add_argument('--geonames'); g.add_argument('--out', required=True)
    d = sub.add_parser('add')
    d.add_argument('--days', required=True); d.add_argument('--geo', required=True); d.add_argument('--travels', required=True)
    c = sub.add_parser('calendar')
    c.add_argument('--days', required=True); c.add_argument('--cal', required=True)
    a = ap.parse_args()
    {'geo': geo, 'add': add, 'calendar': calendar}[a.cmd](a)


if __name__ == '__main__':
    main()
