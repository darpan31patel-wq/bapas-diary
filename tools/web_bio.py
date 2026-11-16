"""Pramukh Swami Maharaj's Jivan Charitra, 1921 to 1975, on the website: the English of Bhavesh Patel's three study
PDFs of the biography (Darpan, 15 Nov 2026: "mockup, taken from this documents, make sure nothing is missed";
16 Nov 2026: "yes jivan charitra"). Website only: nothing here touches the daily 2pm picture.

The data is data/bio/bio.json (made once from the PDFs and Darpan's timeline sheet). Three dates Claude worked out
from a tithi are not in it until Darpan checks them. English dates only, no source line, no page numbers.

    python3 tools/web_bio.py --bio data/bio/bio.json --out out              # Today, the day box, videos, Travels
    python3 tools/web_bio.py --bio data/bio/bio.json --reads reads.json      # Search rows, before build_search.py

--out     out/data/day/MM-DD.json   the day's story under its year on Today, labelled Jivan Charitra
          out/data/reports/MM-DD.json  a clicked day: the day's story, the journey it is part of, where he was that month
          out/data/videos/YYYY.json the gold Video Darshan for the days the biography's videos cover
          out/travels/index.html    1971 to 1975 on the Journey, the 1974 world journey included; days the photos or
                                    the old site's reports already give are never moved or changed
--reads   adds the biography's exact days to Search's written things (kind "Jivan Charitra")
"""
import argparse, datetime, json, os, re

MONTHS = 'January February March April May June July August September October November December'.split()
D = datetime.date.fromisoformat


def load(p, empty):
    try:
        return json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        return empty


def save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':'))


def month_line(bio, ym):
    pl = bio['months'].get(ym)
    if not pl:
        return None
    y, m = ym.split('-')
    where = ', '.join(pl[:-1]) + ' and ' + pl[-1] if len(pl) > 1 else pl[0]
    return {'k': 'm', 't': f'In {MONTHS[int(m) - 1]} {y} Pramukh Swami Maharaj was in {where}', 'w': []}


def today(bio, out):
    n = 0
    for md, years in bio['days'].items():
        p = os.path.join(out, 'data', 'day', md + '.json')
        d = load(p, {})
        if not d and not os.path.exists(p):
            continue   # Today makes a file for every day; never invent one
        st = d.setdefault('stories', [])
        have = {(s[0], s[2]) for s in st if isinstance(s, list) and len(s) > 2}
        for y, items in years.items():
            for it in items:
                if (int(y), it['h']) in have:
                    continue
                v = [[it['v'], it['h']]] if it['v'] else ''
                st.append([int(y), it['pl'], it['h'], {'h': it['h'], 'w': it['w'], 'k': 'Jivan Charitra', 'v': v}])
                n += 1
        save(p, d)
    print(f'Today: {n} Jivan Charitra stories')


def reports(bio, out):
    n = 0
    for mo in range(1, 13):
        for da in range(1, 32):
            md = f'{mo:02d}-{da:02d}'
            add = {}
            for y in range(1921, 1976):
                d = f'{y}-{md}'
                try:
                    D(d)
                except ValueError:
                    continue
                lst = [{'k': 'jc', 't': it['h'], 'pl': [it['pl']] if it['pl'] else [], 'w': it['w']}
                       for it in (bio['days'].get(md) or {}).get(str(y), [])]
                for r in bio['ranges']:   # the journey this day is part of (not the life phases, not month guesses)
                    if (r['d'] < d <= r['end'] and r['cat'] != 'Life phase' and 'months' not in (r['conf'] or '')
                            and (D(r['end']) - D(r['d'])).days <= 300):
                        lst.append({'k': 'jc', 't': r['h'], 'pl': [r['pl']] if r['pl'] and len(r['pl']) < 40 else [], 'w': r['w']})
                m = month_line(bio, d[:7])
                if m:
                    lst.append(m)
                if lst:
                    add[str(y)] = lst
            if add:
                p = os.path.join(out, 'data', 'reports', md + '.json')
                d = load(p, {})
                for y, lst in add.items():
                    d.setdefault(y, [])
                    d[y] = [x for x in d[y] if x.get('k') not in ('jc', 'm')] + lst
                save(p, d)
                n += len(add)
    print(f'Day box: Jivan Charitra lines on {n} days')


def videos(bio, out):
    by = {}
    for d, v in bio['videos'].items():
        by.setdefault(d[:4], {})[d] = v
    for y, days in by.items():
        p = os.path.join(out, 'data', 'videos', y + '.json')
        d = load(p, {})
        for k, v in days.items():
            d.setdefault(k, v)
        save(p, d)
    print(f'Video Darshan: {len(bio["videos"])} days, {len(by)} years')


def travels(bio, out):
    p = os.path.join(out, 'travels', 'index.html')
    if not os.path.exists(p):
        print('Travels: no page'); return
    html = open(p, encoding='utf-8').read()
    m = re.search(r'(<script id="trips" type="application/json">)(.*?)(</script>)', html, re.S)
    data = json.loads(m.group(2))
    covered = set()
    for stops in data['years'].values():
        for s in stops:
            a, b = D(s['a']), D(s['b'])
            while a <= b:
                covered.add(a.isoformat()); a += datetime.timedelta(1)
    fold = lambda s: re.sub(r'\s+', ' ', re.sub(r'[^a-z ]+', ' ', s.lower())).strip()
    by_name = {fold(v['name']): k for k, v in data['places'].items()}
    n, off = 0, set()
    for y, stays in bio['stays'].items():
        for s in stays:
            g = bio['places'].get(s['p'])
            if not g:
                off.add(s['p']); continue
            pid = s['p'] if s['p'] in data['places'] else by_name.get(fold(g['name']))
            if not pid:
                pid = s['p']
                data['places'][pid] = {'name': g['name'], 'country': g['country'], 'll': g['ll']}
                by_name[fold(g['name'])] = pid
            # only the days nothing else on the Journey gives
            a, b, cur = D(s['a']), D(s['b']), None
            runs = []
            while a <= b:
                if a.isoformat() not in covered:
                    if cur and (a - cur[1]).days == 1:
                        cur[1] = a
                    else:
                        cur = [a, a]; runs.append(cur)
                a += datetime.timedelta(1)
            for a, b in runs:
                stay = {'p': pid, 'a': a.isoformat(), 'b': b.isoformat(), 'n': 0, 'cap': s['cap'], 'r': 1}
                data['years'].setdefault(stay['a'][:4], []).append(stay)
                n += 1
    for y in data['years']:   # date order, moving the photo squares (keyed by position) with their stops
        old = data['years'][y]
        order = sorted(range(len(old)), key=lambda i: (old[i]['a'], old[i].get('r', 0)))
        if order != list(range(len(old))):
            pics = data.get('pics', {}); moved = {}
            for new_i, old_i in enumerate(order):
                if f'{y}-{old_i}' in pics:
                    moved[f'{y}-{new_i}'] = pics.pop(f'{y}-{old_i}')
            pics.update(moved)
            data['years'][y] = [old[i] for i in order]
    data['years'] = dict(sorted(data['years'].items()))
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    html = html[:m.start(2)] + blob + html[m.end(2):]
    first = next(iter(data['years']))
    html = re.sub(r'<span class="yrs">\d{4} to 13 August 2016</span>', f'<span class="yrs">{first} to 13 August 2016</span>', html)
    open(p, 'w', encoding='utf-8').write(html)
    print(f'Travels: {n} Jivan Charitra stays, journey now starts {first}; not on the map: {sorted(off)}')


def reads(bio, path):
    rows = load(path, [])
    have = {(r[0], r[3]) for r in rows}
    new = [[r[0], r[1], 'Jivan Charitra', r[3], r[4], [], '', r[0]] for r in bio['reads']
           if r[0] and len(r[0]) == 10 and (r[0], r[3]) not in have]
    rows += new
    rows.sort(key=lambda r: r[0] or '')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Search: {len(new)} Jivan Charitra stories')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bio', default='data/bio/bio.json')
    ap.add_argument('--out')
    ap.add_argument('--reads')
    a = ap.parse_args()
    bio = json.load(open(a.bio, encoding='utf-8'))
    if a.out:
        today(bio, a.out); reports(bio, a.out); videos(bio, a.out); travels(bio, a.out)
    if a.reads:
        reads(bio, a.reads)


if __name__ == '__main__':
    main()
