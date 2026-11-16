"""The Indian calendar on Travels and Legacy, for every year now that the days before 2010 are worked out too (Darpan,
14 Nov 2026: "this means that we can also update the travel section. We can also add more pictures to legacy. We can add
all this information into search as well once it's tagged"; 16 Nov: "legacy is the tab that is called legacy").

Runs in the website build after the festival cards (tools/web_festival.py), on the finished pages in --out:

  Travels   out/travels/fests.json {date: "Diwali · Annakut · New Year"}: the main festivals (the 12 Today tags, without
            Ekadashi) of every day the BAPS calendar or the worked out calendar has. Each stay's card says which of them
            fell during the stay, in a gold line under its dates.
  Legacy    out/then-and-now/cal.json {date: "Aso Vad Amas · Diwali"}: each photo's date also says its Indian date and
            festival. And out/then-and-now/fest-pairs.json: Pramukh Swami Maharaj and Mahant Swami Maharaj at the same
            festival, years apart, from the festival cards' own photos (Bapa in person, whole head framed), only photos
            whose caption or contents show the festival; they join the shuffle like the weekly pairs.

    python3 tools/web_old_calendar.py --db bapa.db --fest out/data/fest --deep-tags deep-tags.json --out out
"""
import argparse, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Today's festival tags (site/day.html KEEP), without Ekadashi: a stay's line names only the big days
MAIN = [('Diwali', r'^diwali\b'), ('Annakut', r'annakut'), ('New Year', r'bestu|nutan varsh|^new year$'),
        ('Janmashtami', r'janmashtami'), ('Guru Purnima', r'guru purnima'),
        ('Swaminarayan Jayanti', r"hari-?nom|swaminarayan jayanti|swaminarayan's birthday"), ('Vasant Panchami', r'vasant panch'),
        ('Holi', r'^holi\b'), ('Rathyatra', r'rath ?yatra'), ('Raksha Bandhan', r'raksha ?bandhan'), ('Pushpadolotsav', r'pushpadol|fuldol')]
HANDOVER = '2016-08-13'   # before this day Swamishri is Pramukh Swami Maharaj
PAIRS_EACH = 2            # festival pairs for each festival
NOT_PAIRED = {'psm', 'msm'}   # their own Jayantis: one guru's day, not the same festival for both
# the festival named in the photo's own caption, nothing near it ('Performs his morning puja' is not Dhanteras)
NAMED = {'diwali': r'diwali|deepavali|chopda|sharda pujan', 'annakut': r'annakut|new year', 'dhanteras': r'dhan ?teras|lakshmi pujan',
         'kalichaudas': r'kali ?ch', 'bhaibij': r'bhai ?b(ee|i)j', 'janmashtami': r'janmashtami|janmotsav|krishna janm',
         'holi': r'\bholi\b', 'fuldol': r'fuldol|pushpadol|dhuleti|colou?red water', 'gurupurnima': r'guru ?purnima|guru ?pujan',
         'harinom': r'swaminarayan jayanti|hari ?jayanti|hari ?n(o|av)mi', 'vasant': r'vasant', 'rathyatra': r'rath ?yatra|chariot',
         'raksha': r'raksha|rakhi|nadachhadi', 'sharad': r'sharad'}


def main_fests(fests, notes=''):
    parts = [x.strip() for x in re.split(r'[;,/]', f'{fests or ""};{notes or ""}') if x.strip()]
    return [n for n, rx in MAIN if any(re.search(rx, x, re.I) for x in parts)]


def calendar(db):
    return {d: (ind or '', main_fests(f, n)) for d, ind, f, n in db.execute('SELECT date, indian_date, festivals, notes FROM calendar')}


def inject(path, pairs, what):
    """Put each (before, add) into the page right after `before`; a page that has moved on is left as it is."""
    page = open(path, encoding='utf-8').read()
    for before, add in pairs:
        if add in page:
            continue
        if before not in page:
            print(f'{what}: page changed, nothing added ({before[:40]!r} not found)')
            return False
        page = page.replace(before, before + add, 1)
    open(path, 'w', encoding='utf-8').write(page)
    return True


TRAVELS_CSS = ('\n/* the festivals during a stay, under its dates (Darpan, 14 Nov 2026) */\n'
               '.story .stayfest { margin-top: 6px; color: var(--gold, #d9a94e); font-style: italic; font-size: 15px; letter-spacing: .01em; }\n'
               '.story .stayfest:empty { display: none; }\n')
TRAVELS_JS = ('\n// the festivals during each stay (tools/web_old_calendar.py, Darpan, 14 Nov 2026)\n'
              'let FESTS = {}, STAYNOW = null; fetch(\'fests.json\').then(r => r.ok ? r.json() : {}).then(f => { FESTS = f;\n'
              '  if (STAYNOW) document.getElementById(\'stayfest\').textContent = stayFests(STAYNOW); }).catch(() => {});\n'
              'function stayFests(s) {\n'
              '  const out = [];\n'
              '  for (let d = new Date(s.a + \'T12:00:00Z\'), end = new Date(s.b + \'T12:00:00Z\'); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {\n'
              '    const f = FESTS[d.toISOString().slice(0, 10)]; if (f) f.split(\' · \').forEach(x => { if (!out.includes(x)) out.push(x); });\n'
              '  }\n'
              '  return out.join(\' · \');\n'
              '}\n')


def travels(a, cal):
    page = os.path.join(a.out, 'travels', 'index.html')
    days = {d: ' · '.join(f) for d, (ind, f) in cal.items() if f}
    with open(os.path.join(a.out, 'travels', 'fests.json'), 'w', encoding='utf-8') as fh:
        json.dump(days, fh, ensure_ascii=False, separators=(',', ':'))
    ok = inject(page, [
        ('<style>', TRAVELS_CSS),   # at the top of the first style block
        ('Video Darshan</a></span></div>', '\n  <div class="stayfest" id="stayfest"></div>'),
        ("$('dates').textContent = fmtRange(tgt.a, tgt.b);", " STAYNOW = tgt; $('stayfest').textContent = stayFests(tgt);"),
        ('<script>', TRAVELS_JS),
    ], 'travels')
    print(f'travels: {len(days)} festival days{"" if ok else " (page not changed)"}')


LEGACY_JS = ('\n// each photo\'s Indian date and festival, and the festival pairs (tools/web_old_calendar.py, Darpan, 14 Nov 2026)\n'
             'let CALW = {};\n'
             'const calw = d => CALW[d] ? \' · \' + CALW[d] : \'\';\n')
LEGACY_LATE = ('\n// the festival pairs join the shuffle like the weekly ones; the dates get their Indian date once it has loaded\n'
               'fetch(\'cal.json\').then(r => r.ok ? r.json() : {}).then(c => { CALW = c; const p = PAIRS[i];\n'
               '  if (p) for (const [k, s] of [[\'p\', p.psm], [\'m\', p.msm]]) $(k + \'date\').textContent = fmt(s.date) + calw(s.date); }).catch(() => {});\n'
               'fetch(\'fest-pairs.json\').then(r => r.ok ? r.json() : []).then(more => {\n'
               '  const have = new Set(PAIRS.map(p => p.psm.file + p.msm.file));\n'
               '  more.filter(p => p.psm && p.msm && !have.has(p.psm.file + p.msm.file)).forEach(p => {\n'
               '    srcs(p); PAIRS.splice(i + 1 + Math.floor(Math.random() * (PAIRS.length - i)), 0, p);\n'
               '  });\n'
               '}).catch(() => {});\n')


def tidy(c):
    """A caption fit to show: no markup, never a file name ('Diwali Celebration with MSM 20261108-127-Gondal')."""
    c = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c or '')).strip()
    return '' if re.search(r'\d{6,}|_|\bMSM\b|\bPSM\b|\b20\d\d \d+$', c) else c


def fest_pairs(a, db):
    """Both gurus at the same festival, from the festival cards (out/data/fest/KEY.json): only photos whose own caption
    names the festival, with Bapa in them and his face found (Darpan, 29 Oct 2026: both photos must truly show what the
    heading says); each photo's own town from the database."""
    import web_festival as W
    tags = json.load(open(a.deep_tags, encoding='utf-8')) if a.deep_tags and os.path.exists(a.deep_tags) else {}
    town = lambda al, f: (db.execute('SELECT place FROM photos WHERE album = ? AND file = ?', (al, f)).fetchone() or [''])[0] or ''
    out = []
    for key, F in W.FESTS.items():
        path = os.path.join(a.fest, key + '.json')
        if key in NOT_PAIRED or not os.path.exists(path):
            continue
        best = {'P': [], 'M': []}
        for Y in json.load(open(path, encoding='utf-8')).get('years', []):
            for p in Y.get('p') or []:
                score, said = W.festive(p, F, tags)
                named = re.compile(NAMED.get(key, r'^$'), re.I)
                caps = [tidy(p[5]) if len(p) > 5 and isinstance(p[5], str) else '', tidy(p[2])]
                cap = next((c for c in caps if c and named.search(c) and len(c) <= 90), '')
                if cap and p[3] and len(p) > 4 and p[4]:
                    place = town(p[0], p[1]) or Y.get('place') or ''
                    best['P' if Y['d'] < HANDOVER else 'M'].append((score, Y['y'], Y['d'], place, cap, p))
                    break        # the year's most festive photo
        # Pramukh Swami Maharaj's years before 2010 first (the newly tagged ones), then the most festive; Mahant Swami
        # Maharaj's most festive, the latest first
        ps = sorted(best['P'], key=lambda x: (x[1] >= 2010, -x[0], x[1]))
        ms = sorted(best['M'], key=lambda x: (-x[0], -x[1]))
        for (s1, y1, d1, pl1, c1, p1), (s2, y2, d2, pl2, c2, p2) in list(zip(ps, ms))[:PAIRS_EACH]:
            out.append({'moment': F['title'], 'fest': key,
                        'psm': {'date': d1, 'place': pl1, 'cap': c1, 'album': p1[0], 'file': p1[1], 't': size(p1[0])},
                        'msm': {'date': d2, 'place': pl2, 'cap': c2, 'album': p2[0], 'file': p2[1], 't': size(p2[0])}})
    return out


def size(album):
    """The photo store keeps baps.org albums large (l/); the early darshan photos only medium (m/early/)."""
    return 'l' if album.isdigit() or album.startswith('webnext') else 'm'


def legacy(a, cal, db):
    page = os.path.join(a.out, 'then-and-now', 'index.html')
    html = open(page, encoding='utf-8').read()
    pairs = fest_pairs(a, db) if a.fest else []
    more = os.path.join(a.out, 'then-and-now', 'more.json')
    dates = set(re.findall(r'"date": ?"(\d{4}-\d\d-\d\d)"', html))
    if os.path.exists(more):
        dates |= set(re.findall(r'"date": ?"(\d{4}-\d\d-\d\d)"', open(more, encoding='utf-8').read()))
    dates |= {p[g]['date'] for p in pairs for g in ('psm', 'msm')}
    words = {d: ' · '.join([cal[d][0]] + cal[d][1]) for d in sorted(dates) if d in cal and cal[d][0]}
    with open(os.path.join(a.out, 'then-and-now', 'cal.json'), 'w', encoding='utf-8') as fh:
        json.dump(words, fh, ensure_ascii=False, separators=(',', ':'))
    with open(os.path.join(a.out, 'then-and-now', 'fest-pairs.json'), 'w', encoding='utf-8') as fh:
        json.dump(pairs, fh, ensure_ascii=False, separators=(',', ':'))
    ok = inject(page, [
        ("const $ = id => document.getElementById(id);", LEGACY_JS),
        ("$(k + 'date').textContent = fmt(s.date);", " $(k + 'date').textContent += calw(s.date);"),
        ("const want = PAIRS.findIndex(", ''),
    ], 'legacy')
    if ok:   # the late part goes just before the page opens its first pair
        html = open(page, encoding='utf-8').read()
        if LEGACY_LATE not in html:
            k = html.index('const want = PAIRS.findIndex(')
            open(page, 'w', encoding='utf-8').write(html[:k] + LEGACY_LATE.lstrip('\n') + html[k:])
    print(f'legacy: Indian dates for {len(words)} photo days, {len(pairs)} festival pairs '
          f'({", ".join(sorted({p["moment"] for p in pairs}))}){"" if ok else " (page not changed)"}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='bapa.db: its calendar table, before 2010 too (tools/old_calendar.py)')
    ap.add_argument('--fest', help='the festival cards, out/data/fest (tools/web_festival.py)')
    ap.add_argument('--deep-tags', help='what is in each photo (release deep-tags)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    cal = calendar(db)
    travels(a, cal)
    legacy(a, cal, db)
