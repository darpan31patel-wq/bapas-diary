"""Mandirs Bapa opened: every murti pratishtha in the diary on a globe and a timeline, a third view inside Travels
(/travels/mandirs/, beside Journey and Places). Darpan, 31 Oct 2026: "Mandirs Bapa opened: map and timeline of murti
pratishthas ... yes".

Website only: nothing here touches the daily 2pm picture chain and nothing is fetched from baps.org. A murti pratishtha
is a day when a caption of a photo with Bapa in it (bapa.db, Bapa recognised by face, tools/web_faces.py) tells of the
pratishtha rituals, a newly consecrated mandir or the opening of a mandir; anniversaries (patotsav) are left out. The
town is where Bapa was that day on the Travels page, so the globe and the Journey agree. Days of one pratishtha festival
in the same town (no more than three days apart) are one pratishtha. Mandirs named in the captions ("murtis for the hari
mandirs of Varkheda and Dhulia") are listed with it. Pramukh Swami Maharaj before 13 Aug 2016, Mahant Swami Maharaj from
then, side by side at the top. The only link out is a gold "See more" into Search for that day.

    python3 tools/web_mandirs.py --db bapa.db --faces faces --travels out/travels/index.html --out out

Writes out/travels/mandirs/index.html from site/mandirs/mandirs.html and adds Mandirs to the Journey | Places switch
on out/travels/index.html and out/travels/places/index.html.
"""
import argparse, datetime, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import web_bapa_rules as R
import web_year as Y

PSM_UNTIL = R.PSM_UNTIL
PRATISHTHA = re.compile(r'prati?sh?th?a|consecration ceremony|newly consecrated|murtis? to be consecrated|consecrat\w* (?:the )?murti'
                        r'|opening ceremony of the (?:new )?mandir|inaugurat\w* (?:the |a )?(?:new )?(?:baps )?(?:shri )?'
                        r'(?:swaminarayan )?(?:hari )?mandir', re.I)
NOT = re.compile(r'patotsav|anniversar|varshik|jayanti|pratishtha day celebration|prana[- ]?pratishtha of the image|'
                 r'details of the |sanskar bhavan|school|chhatralay|hostel|memorial|shrine|footprints|charanarvind|'
                 r'akshar deri|sukh shaiya|samadhi|invitation', re.I)
# "murtis for the hari mandirs of Varkheda and Dhulia", "BAPS Shri Swaminarayan Mandir, Vankaner", "mandir in Bhatpura village"
FOR = [re.compile(r'mandirs?\s*(?:\([^)]*\)\s*)?(?:in|of|at|for)\s+(?:the\s+)?(?:villages?\s+(?:of\s+)?)?'
                  r'((?:[A-Z][\w\'-]*(?:\s+(?:[A-Z][\w\'-]*|\([^)]*\)))*)(?:(?:,\s*|\s+and\s+)[A-Z][\w\'-]*(?:\s+[A-Z][\w\'-]*)*)*)'),
       re.compile(r'(?:Swaminarayan|Hari) Mandirs?,\s+((?:[A-Z][\w\'-]*)(?:\s+[A-Z][\w\'-]*)*)'),
       re.compile(r'for\s+((?:[A-Z][\w\'-]*)(?:\s+[A-Z][\w\'-]*)*)\s+(?:(?i:hari)\s+)?(?i:mandir)')]
SKIP_NAME = re.compile(r'^(?:BAPS|Shri|Shree|Swaminarayan|Akshar|Purushottam|Maharaj|Bhagwan|Thakorji|India|USA|UK|The|Lord|Gujarat|'
                       r'Harikrishna|Ghanshyam|Gunatitanand|Swamishri|Murti|Hindu|Mandir|Mandirs|Hari|Rang|Ranga|Guru)$')


def days_between(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def names(cap):
    """The mandirs a caption names: towns and villages, never the deities or BAPS words."""
    out = []
    for rx in FOR:
        for m in rx.finditer(cap):
            for n in re.split(r',\s*|\s+and\s+', m.group(1)):
                n = re.sub(r'\s*\((?:[^)]*)\)$', '', n).strip(" .'-")
                n = re.sub(r'\s+(?:village|villages|town|city|district)$', '', n)
                n = re.sub(r'^(?:new|the)\s+', '', n)
                if not n[:1].isupper():
                    continue
                if n and not SKIP_NAME.match(n) and not any(SKIP_NAME.match(w) for w in n.split()[:1]) and len(n) > 2 and n not in out:
                    out.append(n)
    return out


def pratishthas(db, faces, trips):
    where = {}   # day -> the town Bapa was in, from the Travels page
    for y, stays in trips['years'].items():
        for s in stays:
            t = datetime.date.fromisoformat(s['a'])
            while t.isoformat() <= s['b']:
                where.setdefault(t.isoformat(), s['p'])
                t += datetime.timedelta(days=1)
    years = sorted({y for (y,) in db.execute('SELECT DISTINCT year FROM photos WHERE year IS NOT NULL')})
    events = []
    for year in years:
        yr = Y.Year(db, faces, year)
        hits = {}
        for r in yr.rows:
            if PRATISHTHA.search(r['raw']) and not NOT.search(r['raw']) and r['day'][:4] == str(year):
                hits.setdefault(r['day'], []).append(r)
        for d in sorted(hits):
            town = where.get(d) or R.tidy(hits[d][0]['place']).split(',')[0].strip()
            if town not in trips['places']:
                town = next((k for k in trips['places'] if k.lower() == town.lower()), None)
            if not town:
                continue
            last = events[-1] if events else None
            if last and last['p'] == town and days_between(last['b'], d) <= 3:
                last['b'] = d
                last['rows'] += hits[d]
            else:
                events.append(dict(p=town, a=d, b=d, rows=list(hits[d]), year=yr))
    out = []
    for e in events:
        y = e['year']
        pick = y.best(e['rows'], 1, close=False) or y.best(e['rows'], 1) or y.best(y.on(e['a'], e['b']), 1, close=False) or y.best(y.on(e['a'], e['b']), 1)
        if not pick:
            continue
        r = pick[0]
        mandirs = []
        for x in e['rows']:
            for n in names(x['raw']):
                if n not in mandirs and n.lower() != e['p'].lower():
                    mandirs.append(n)
        caps = [x['cap'] for x in e['rows'] if x['cap']]
        cap = max(caps, key=lambda c: (len(names(c)) > 0, 'murti' in c.lower(), -abs(len(c) - 90))) if caps else r['cap']
        out.append(dict(p=e['p'], a=e['a'], b=e['b'], n=len(y.on(e['a'], e['b'])), cap=R.undate(cap, e['a']), m=mandirs[:12],
                        k=r['key'], fx=round(max(0, min(1, r['fx'])), 3), fy=round(max(0, min(1, r['fy'])), 3)))
    return out


def page(template, trips, land, events):
    used = {e['p'] for e in events}
    places = {k: v for k, v in trips['places'].items() if k in used}
    data = json.dumps(dict(places=places, events=events), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    t = open(template, encoding='utf-8').read()
    t = t.replace('<!--LAND-->', '<script id="land" type="application/json">' + json.dumps(land, separators=(',', ':')) + '</script>')
    t = t.replace('<!--MANDIRS-->', '<script id="mandirs" type="application/json">' + data + '</script>')
    # as build_places.py does for the Places view on the website (site_menu.py and web_secure.py finish it later)
    t = t.replace('<!--MENULINK-->', '<link rel="stylesheet" href="/menu.css">').replace('/*MENUCSS*/', '').replace('<!--MOCK-->', '')
    t = t.replace('<!--LIBS-->', '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>\n'
                  '<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>')
    return t.replace('/*PSM*/', '/about/img/psm.jpg').replace('/*MSM*/', '/about/img/msm.jpg')


SWITCH = re.compile(r'(<nav class="views"[^>]*>)(.*?)(</nav>)', re.S)


def add_switch(path, on=False):
    """Journey | Places | Mandirs on the other Travels views (Mandirs lit on its own page)."""
    if not os.path.exists(path):
        return
    s = open(path, encoding='utf-8').read()
    m = SWITCH.search(s)
    if not m or '/travels/mandirs/' in m.group(2):
        return
    inner = m.group(2) + ('<a class="on" href="/travels/mandirs/" aria-current="page">Mandirs</a>' if on else '<a href="/travels/mandirs/">Mandirs</a>')
    open(path, 'w', encoding='utf-8').write(s[:m.start()] + m.group(1) + inner + m.group(3) + s[m.end():])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapa.db')
    ap.add_argument('--faces', required=True)
    ap.add_argument('--travels', required=True, help="the Travels page (its stops, towns and land)")
    ap.add_argument('--out', required=True, help='the built site')
    ap.add_argument('--template', default=os.path.join(HERE, '..', 'site', 'mandirs', 'mandirs.html'))
    ap.add_argument('--json', help='also write the pratishthas here (for checking)')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    trips, land = Y.travels(a.travels)
    years = {y for (y,) in db.execute('SELECT DISTINCT year FROM photos WHERE year IS NOT NULL')}
    faces = Y.load_faces(a.faces, years)
    events = pratishthas(db, faces, trips)
    if a.json:
        json.dump(events, open(a.json, 'w'), ensure_ascii=False, indent=0)
    html = page(a.template, trips, land, events)
    dst = os.path.join(a.out, 'travels', 'mandirs', 'index.html')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(html)
    add_switch(os.path.join(a.out, 'travels', 'index.html'))
    add_switch(os.path.join(a.out, 'travels', 'places', 'index.html'))
    add_switch(dst, on=True)
    towns = {e['p'] for e in events}
    print(f'mandirs: {len(events)} murti pratishthas in {len(towns)} towns, {sum(len(e["m"]) for e in events)} mandirs named, '
          f'{sum(e["a"] < PSM_UNTIL for e in events)} with Pramukh Swami Maharaj, {sum(e["a"] >= PSM_UNTIL for e in events)} with Mahant Swami Maharaj')


if __name__ == '__main__':
    main()
