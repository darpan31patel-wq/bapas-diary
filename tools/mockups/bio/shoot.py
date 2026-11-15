"""Mockup only: Bapa's Jivan Charitra (Bhavesh Patel's three study PDFs of the biography, 1921 to 1975) shown on the
REAL live pages of bapas-diary.com. Nothing is published: the live pages are opened in a browser here and this run's
copy of their data is added to as the page loads (Darpan, 15 Nov 2026: "mockup, taken from this documents, make sure
nothing is missed"). Writes shots/*.jpg and a log of every patch that was or was not applied.

    python3 shoot.py bio.json cities500.txt shots
"""
import json, re, sys, unicodedata
from datetime import date
from playwright.sync_api import sync_playwright

BIO = json.load(open(sys.argv[1])); GEO = sys.argv[2]; OUT = sys.argv[3]
SITE = 'https://bapas-diary.com'
log = []
def note(*a): log.append(' '.join(map(str, a))); print(*a, flush=True)

# --- towns on the map: Travels' own towns first, then GeoNames (towns of 500 people or more) -----------------------
ALIAS = {'Poona': 'Pune', 'Selvas': 'Silvassa', 'Jagannath Puri': 'Puri', 'Mauritius': 'Port Louis', 'Kolkata': 'Kolkata',
         'Atladra': 'Vadodara', 'Kudaya station': None, 'Vidyanagar': 'Vallabh Vidyanagar', 'Bhadra': 'Bhadra'}
CC = {'Nairobi': 'KE', 'Nakuru': 'KE', 'Dar es Salaam': 'TZ', 'Lusaka': 'ZM', 'London': 'GB', 'New York': 'US',
      'Cincinnati': 'US', 'Toronto': 'CA', 'Durban': 'ZA', 'Bulawayo': 'ZW', 'Mauritius': 'MU', 'Hoboken': 'US', 'Leicester': 'GB'}
COUNTRY = {'IN': 'India', 'KE': 'Kenya', 'TZ': 'Tanzania', 'ZM': 'Zambia', 'GB': 'UK', 'US': 'USA', 'CA': 'Canada',
           'ZA': 'South Africa', 'ZW': 'Zimbabwe', 'MU': 'Mauritius'}
fold = lambda s: unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()
geo = {}
for line in open(GEO, encoding='utf-8'):
    f = line.rstrip('\n').split('\t')
    if len(f) < 15: continue
    cc, adm, pop = f[8], f[10], int(f[14] or 0)
    for nm in {f[1], f[2]}:
        k = (fold(nm), cc)
        score = pop + (10**9 if cc == 'IN' and adm == '09' else 0)   # Gujarat first among towns of one name
        if k not in geo or score > geo[k][0]: geo[k] = (score, [round(float(f[5]), 4), round(float(f[4]), 4)])

HAND = {'Dharmaj': [72.80, 22.42], 'Matar': [72.67, 22.71], 'Bhadran': [72.90, 22.36], 'Chuda': [71.68, 22.48],
        'Mojidad': [71.63, 22.58], 'Mahijda': [72.74, 22.79]}   # villages GeoNames does not list, placed by hand (approximate)
def place(name, have):
    if name in have: return have[name]
    if name in HAND: return {'name': name, 'country': 'India', 'll': HAND[name]}
    for k, v in have.items():
        if fold(k).split(' (')[0] == fold(name): return v
    want = ALIAS.get(name, name)
    if want is None: return None
    cc = CC.get(name, 'IN')
    hit = geo.get((fold(want), cc))
    if not hit: return None
    return {'name': name, 'country': COUNTRY.get(cc, cc), 'll': hit[1]}

# --- what each page gets ------------------------------------------------------------------------------------------
MONTHS = 'January February March April May June July August September October November December'.split()
def month_line(ym):
    pl = BIO['months'].get(ym)
    if not pl: return None
    y, m = ym.split('-')
    return {'k': 'm', 't': f'In {MONTHS[int(m) - 1]} {y} Pramukh Swami Maharaj was in ' + (', '.join(pl[:-1]) + ' and ' + pl[-1] if len(pl) > 1 else pl[0]), 'w': []}

def day_stories(md):   # Today: the biography's day as an On this day story of its year (no photo, so no card on the rope)
    out = []
    for y, items in (BIO['days'].get(md) or {}).items():
        for it in items:
            v = [[it['v'], it['h']]] if it['v'] else ''
            out.append([int(y), it['pl'], it['h'], {'h': it['h'], 'w': it['w'], 'k': 'Jivan Charitra', 'v': v}])
    return out

def reports(md):   # the day box: the day's story, the stretch of days it is in, and where he was that month
    out = {}
    for y in range(1921, 1976):
        d = f'{y}-{md}'; lst = []
        for it in (BIO['days'].get(md) or {}).get(str(y), []):
            lst.append({'k': 'jc', 't': it['h'], 'pl': [it['pl']] if it['pl'] else [], 'w': it['w']})
        for r in BIO['ranges']:
            if r['d'] <= d <= r['end'] and r['d'] != d and r['cat'] != 'Life phase' and 'months' not in (r['conf'] or '') and (date.fromisoformat(r['end']) - date.fromisoformat(r['d'])).days <= 300:
                lst.append({'k': 'jc', 't': r['h'], 'pl': [r['pl']] if r['pl'] and len(r['pl']) < 40 else [], 'w': r['w']})
        if lst or BIO['months'].get(d[:7]):
            m = month_line(d[:7])
            if m: lst.append(m)
        if lst: out[str(y)] = lst
    return out

PATCH = {
  'today': [
    (".map(s => [s[2], s[3].h || '', s[3].w || [], s[3].l || 0])", ".map(s => [s[2], s[3].h || '', s[3].w || [], s[3].l || 0, s[3].k || ''])"),
    ("function storyHTML(line, h, w, l) {", "function storyHTML(line, h, w, l, k) {"),
    ('<div class="day-story"><p class="story-line"><b>On this day</b>${esc(top)}</p>`', '<div class="day-story"><p class="story-line"><b>${k ? esc(k) : \'On this day\'}</b>${esc(top)}</p>`'),
    ("${Y && Y.v ? watchVideo(Y.v, 'go vgo') : ''}</div>`", "${Y && Y.v ? watchVideo(Y.v, 'go vgo') : (stories.find(s => s[3] && s[3].v) ? watchVideo(stories.find(s => s[3] && s[3].v)[3].v, 'go vgo') : '')}</div>`"),
  ],
  'photos': [
    ("const top = r.k === 'p' ?", "const top = r.k === 'jc' ? `<b>Jivan Charitra</b>${esc(r.t || '')}${where ? `, <i>${esc(where)}</i>` : ''}` : r.k === 'm' ? `<b>This month</b>${esc(r.t || '')}` : r.k === 'p' ?"),
  ],
  'search': [
    ("${READ_KIND[p.k] || 'Prasang'}", "${READ_KIND[p.k] || (p.k === 'Jivan Charitra' ? 'Jivan Charitra' : 'Prasang')}"),
  ],
}
def patch(kind, html):
    for old, new in PATCH[kind]:
        n = html.count(old)
        note(f'{kind}: {"applied " + str(n) if n else "NOT FOUND"}: {old[:70]}')
        html = html.replace(old, new)
    return html

def travels(html):
    m = re.search(r'(<script[^>]*id="trips"[^>]*>)(.*?)(</script>)', html, re.S)
    data = json.loads(m.group(2)); have = data['places']; miss = []
    for y, stays in BIO['stays'].items():
        keep = []
        for s in stays:
            p = place(s['p'], have)
            if not p: miss.append(s['p']); continue
            have.setdefault(s['p'], p)
            keep.append({'p': s['p'], 'a': s['a'], 'b': s['b'], 'n': 0, 'cap': s['cap']})
        data['years'][y] = keep + [x for x in data['years'].get(y, []) if x['a'] > (keep[-1]['b'] if keep else '')]
    data['years'] = dict(sorted(data['years'].items()))
    note('travels: years now', list(data['years'])[:8], '... towns not on the map:', sorted(set(miss)))
    return html[:m.start(2)] + json.dumps(data, ensure_ascii=False) + html[m.end(2):]

def handler(route, request):
    u = request.url; path = u.split('bapas-diary.com', 1)[-1].split('#')[0].split('?')[0]
    try:
        if request.resource_type == 'document' and path in ('', '/'):
            r = route.fetch(); return route.fulfill(response=r, body=patch('today', r.text()))
        if request.resource_type == 'document' and path.startswith('/photos/'):
            r = route.fetch(); return route.fulfill(response=r, body=patch('photos', r.text()))
        if request.resource_type == 'document' and path.startswith('/search/'):
            r = route.fetch(); return route.fulfill(response=r, body=patch('search', r.text()))
        if request.resource_type == 'document' and path.startswith('/travels/') and path.count('/') == 2:
            r = route.fetch(); return route.fulfill(response=r, body=travels(r.text()))
        m = re.match(r'/data/day/(\d\d-\d\d)\.json$', path)
        if m:
            r = route.fetch(); d = r.json() if r.ok else {}
            d.setdefault('stories', []).extend(day_stories(m.group(1)))
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(d, ensure_ascii=False))
        m = re.match(r'/data/reports/(\d\d-\d\d)\.json$', path)
        if m:
            r = route.fetch(); d = r.json() if r.ok else {}
            d.update(reports(m.group(1)))
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(d, ensure_ascii=False))
        m = re.match(r'/data/videos/(19[2-7]\d)\.json$', path)
        if m:
            d = {k: [v[0], v[1]] for k, v in BIO['videos'].items() if k.startswith(m.group(1))}
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(d))
        if path == '/search/data/reads.json':
            r = route.fetch(); d = r.json() if r.ok else []
            d += [x for x in BIO['reads'] if x[0] and len(x[0]) == 10]
            d.sort(key=lambda x: x[0])
            return route.fulfill(status=200, content_type='application/json', body=json.dumps(d, ensure_ascii=False))
    except Exception as e:
        note('route error', path, e)
    return route.continue_()

SHOTS = [   # name, address, width, height, what to do before the shot
  ('today-19-july', '/#07-19', 1600, 1000, '#y1974'),
  ('today-7-november', '/#11-07', 1600, 1000, '#y1939'),
  ('today-3-august-phone', '/#08-03', 390, 844, '#y1974'),
  ('today-23-january-phone', '/#01-23', 390, 844, '#y1971'),
  ('daybox-19-july-1974', '/photos/#date=1974-07-19', 1600, 1000, None),
  ('daybox-5-december-1972-phone', '/photos/#date=1972-12-05', 390, 844, None),
  ('travels-19-july-1974', '/travels/#1974-07-19', 1600, 1000, None),
  ('travels-30-november-1972-phone', '/travels/#1972-11-30', 390, 844, None),
  ('travels-26-november-1971', '/travels/#1971-11-26', 1600, 1000, None),
  ('search-cincinnati', '/search/#q=Cincinnati', 1600, 1000, None),
]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, addr, w, h, sel in SHOTS:
        ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=2 if w < 500 else 1,
                            is_mobile=w < 500, has_touch=w < 500)
        ctx.route('**/*', handler)
        pg = ctx.new_page()
        pg.on('console', lambda m: m.type == 'error' and note('console', m.text[:200]))
        try:
            if addr.startswith('/#'):   # Today opens on today's date, then moves to the date in the address
                pg.goto(SITE + '/', wait_until='load', timeout=90000); pg.wait_for_timeout(5000)
                pg.evaluate(f"location.hash = '{addr[1:]}'")
            else:
                pg.goto(SITE + addr, wait_until='load', timeout=90000)
        except Exception as e:
            note(name, 'load', e)
        pg.wait_for_timeout(6000)
        if name.startswith('search'):
            c = pg.query_selector('#cards')
            if c: c.scroll_into_view_if_needed(); pg.evaluate('window.scrollBy(0, -260)'); pg.wait_for_timeout(2000)
        if sel:
            el = pg.query_selector(sel)
            note(name, 'found' if el else 'NO', sel)
            if el:
                el.scroll_into_view_if_needed(); pg.evaluate('window.scrollBy(0, -120)'); pg.wait_for_timeout(1500)
        pg.screenshot(path=f'{OUT}/{name}.jpg', type='jpeg', quality=82)
        if sel and pg.query_selector(sel):   # and the year's own section by itself
            pg.query_selector(sel).screenshot(path=f'{OUT}/{name}-section.jpg', type='jpeg', quality=85)
        if name.startswith('today') and w > 500:
            pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(1500)
            pg.screenshot(path=f'{OUT}/{name}-top.jpg', type='jpeg', quality=82)
        ctx.close()
    b.close()
open(f'{OUT}/log.txt', 'w').write('\n'.join(log) + '\n')
