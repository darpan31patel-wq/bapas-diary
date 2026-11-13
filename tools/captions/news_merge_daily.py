"""Website only (Darpan, 9 Nov 2026: "WANT CAPTIONS AND ARTICLES", "MAKE IT HAPPEN RIGHT NOW"): adds the News articles
news_chrome.js read in his Chrome to crawl/news/articles.json on the `database` branch (same shape as the 6 Nov read, so
build_archive.py and the website's Stories read them with no change), and keeps every photo address of baps.org's new
News galleries in crawl/news/webnext.json.

    python3 news_merge_daily.py --known --crawl crawl          (what is saved already, to hand to NEWS.run)
    python3 news_merge_daily.py --text read.txt --crawl crawl  (NEWS.show()'s text, copied exactly from get_page_text)

Captions: the new News galleries carry no captions. A gallery photo that is also on one of Bapa's day pages (same file
name) gets that day page's caption: it is linked to the article as a gallery row, so the article lists it with its
caption. Every article's hash must match, so an article passed on wrongly is never saved.
"""
import argparse, glob, json, os, re, sys, urllib.parse

def js_hash(s):
    h = 5381
    b = s.encode('utf-16-le')
    for i in range(0, len(b), 2):
        h = (h * 33 + int.from_bytes(b[i:i + 2], 'little')) & 0xFFFFFFFF
    return format(h, 'x')


MONTHS = {m: i for i, m in enumerate('jan feb mar apr may jun jul aug sep oct nov dec'.split(), 1)}


def iso_(s):
    m = re.search(r'(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})', s or '')
    return f'{m[3]}-{MONTHS[m[2].lower()]:02d}-{int(m[1]):02d}' if m and m[2].lower() in MONTHS else None


def place_(title):
    parts = [p.strip() for p in (title or '').split(',') if p.strip()]
    if len(parts) < 2:
        return None
    keep = 3 if len(parts) > 3 and len(parts[-2]) <= 3 else 2
    return ', '.join(parts[1:][-keep:])


REGIONS = {'abudhabi': 'Abu Dhabi', 'newdelhi': 'New Delhi', 'washingtondc': 'Washington DC', 'newzealand': 'New Zealand',
           'mountgambier': 'Mount Gambier', 'newcastle-de': 'New Castle, DE', 'birmingham-al': 'Birmingham, AL',
           'apac': 'Asia Pacific', 'americas': 'North America'}


def region(path):
    """'/uganda/news/...' -> 'Uganda' (the new site files each article under its mandir or country)"""
    m = re.match(r'^/([a-z0-9-]+)/news/', path)
    return REGIONS.get(m[1], m[1].replace('-', ' ').title()) if m else None


def stem(f):
    """'Diwali_Celebration_with_MSM_20261108-014-Gondal_display-1794155696071.JPG' and
    'Diwali_Celebration_with_MSM_20261108_014_Gondal.JPG' -> 'diwali_celebration_with_msm_20261108_014_gondal'"""
    f = re.sub(r'\.(jpe?g|png|webp)$', '', f.split('/')[-1], flags=re.I)
    f = re.sub(r'_(display|thumb|original)-\d+$', '', f, flags=re.I)
    return re.sub(r'[-_ ]+', '_', f).lower()


def expand(run):
    """'X_20261108-[1-174/3]-Gondal' -> X_20261108-001-Gondal ... X_20261108-174-Gondal"""
    m = re.match(r'^(.*)\[(\d+)-(\d+)/(\d+)\](.*)$', run)
    if not m:
        return [run]
    return [f'{m[1]}{str(n).zfill(int(m[4]))}{m[5]}' for n in range(int(m[2]), int(m[3]) + 1)]


def parse(text):
    """NX.show()'s text: '@@@ path', 'L listed', 'H hash', 'N photos captions', 'P folder', 'S name runs', 'T words'."""
    arts, a = [], None
    for line in text.split('\n'):
        tag, _, val = line.partition(' ')
        if tag == '@@@':
            a = {'p': val.strip(), 'lines': [], 'runs': [], 'dir': '', 'n': 0}
            arts.append(a)
        elif a is None:
            continue
        elif tag == 'L': a['listed'] = val.strip()
        elif tag == 'H': a['hash'] = val.strip()
        elif tag == 'N': a['n'] = int((val.split() or ['0'])[0])
        elif tag == 'P': a['dir'] = val.strip()
        elif tag == 'S': a['runs'].append(val)
        elif tag == 'Q':
            k, _, rest = val.partition('|')
            a['runs'].append((a['runs'][-1] if a['runs'] else '')[:int(k)] + rest)
        elif tag == 'D': a.setdefault('dic', []).append(val)
        elif tag == 'T': a['lines'].append(val)
        elif tag == 'F': a['f'] = val.split()
        elif tag == 'R': a['refresh'] = True
    for a in arts:     # a gallery read again names its long repeated parts once ("D ..."), then writes ~1, ~2 ... for them
        if a.get('dic'):
            a['runs'] = [re.sub(r'~(\d)', lambda m: a['dic'][int(m[1]) - 1], r) for r in a['runs']]
    return arts


ap = argparse.ArgumentParser()
ap.add_argument('--crawl', default='crawl')
ap.add_argument('--known', action='store_true')
ap.add_argument('--text')
ap.add_argument('--refresh', action='store_true')
a = ap.parse_args()
apath = os.path.join(a.crawl, 'news', 'articles.json')
wpath = os.path.join(a.crawl, 'news', 'webnext.json')
A = json.load(open(apath, encoding='utf-8'))

def files(x, names):
    """the 'F' tokens back to full addresses on static.wn.baps-apps.org, one for each name"""
    out, n, ext = [], 0, None
    for name, t in zip(names, x.get('f') or []):
        if t.startswith('!'):
            out.append(('https://i.ytimg.com/' if t.startswith('!vi/') else 'https://static.wn.baps-apps.org/') + t[1:]); continue   # vi/: a video's thumbnail
        m = re.match(r'^(-?\d+)(\.\w+)?$', t)
        n += int(m[1]); ext = m[2] or ext
        out.append(f"https://static.wn.baps-apps.org/{urllib.parse.quote(x['dir'] + name)}_display-{n}{ext}")
    return out if len(out) == len(names) and x.get('f') else []


if a.refresh:      # new site articles saved without exact file names, for NEWS.refresh
    W = json.load(open(wpath, encoding='utf-8')) if os.path.exists(wpath) else {}
    print(json.dumps([p for p, v in W.items() if v.get('photos') and not v.get('files')], ensure_ascii=False))
    sys.exit()

if a.known:
    known = [p for p in A if not p.startswith('/News/')]
    known += sorted({m[1] for p in A for m in [re.search(r'/News/(?:2025|2026|2027)/.*-(\d+)\.aspx$', p)] if m})
    print(json.dumps(known, ensure_ascii=False))
    sys.exit()

W = json.load(open(wpath, encoding='utf-8')) if os.path.exists(wpath) else {}
day = {}
for f in sorted(glob.glob(os.path.join(a.crawl, 'button', '*.json'))):
    for r in json.load(open(f, encoding='utf-8')):
        m = re.search(r'GalleryImages/(\d+)/WebImages/([^/?#]+)$', r.get('i') or '')
        if m and r.get('c'):
            day.setdefault(stem(m[2]), [m[1], m[2], r['c']])

JUNK = re.compile(r'^(Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day \d{1,2} [A-Z][a-z]+ \d{4}$')
bad = 0
for x in parse(open(a.text, encoding='utf-8').read()):
    key = [x['lines'], x['runs'], x['dir']] + ([x['f']] if x.get('f') else [])
    if js_hash(json.dumps(key, ensure_ascii=False, separators=(',', ':'))) != x.get('hash'):
        print(f"{x['p']}: hash does not match, read it again"); bad += 1
        continue
    if x.get('refresh'):     # only the exact file names, for an article already saved
        names = [n for r in x['runs'] for n in expand(r)]
        f = files(x, names)
        if x['p'] in W and f:     # the gallery as baps.org shows it now (it may have gained photos since it was saved)
            changed = W[x['p']].get('names') != names
            W[x['p']].update(names=names, files=f, photos=len(f))
            print(f"{x['p']}: {len(f)} exact file names added" + (' (gallery changed, names updated)' if changed else ''))
        else:
            print(f"{x['p']}: not saved before, or no names, left as it is")
        continue
    lines = [l for l in x['lines'] if l != 'Local News' and not JUNK.match(l)]   # hub page labels, after the hash check
    if not lines and not x['n']:
        print(f"{x['p']}: the page had no words (not ready on baps.org yet?), left for the next night")
        continue
    if not lines:     # a gallery with no words: its name from the address
        lines = [x['p'].rstrip('/').rsplit('/', 1)[-1].replace('-', ' ').title()]
    title = lines[0]
    sub = lines[1] if len(lines) > 1 and ',' in lines[1] and len(lines[1]) < 120 else ''
    when = iso_(x.get('listed'))
    names = [n for r in x['runs'] for n in expand(r)]
    rows = [day[stem(n)] for n in names if stem(n) in day]
    gp = x['p'] + '/gallery'
    A[x['p']] = {'t': title, 'd': '', 'text': '\n'.join(lines[1:]), 'own': [],
                 'g': {gp: {'t': title, 'rows': rows}} if rows else {},
                 'date': when, 'listed': x.get('listed'), 'place': place_(sub) or place_(title) or region(x['p']),
                 'site': 'new', 'photos': x['n']}
    if x['n']:
        W[x['p']] = {'date': when, 'gallery': 'https://www.baps.org' + gp, 'folder': 'https://static.wn.baps-apps.org/' + x['dir'],
                     'photos': x['n'], 'names': names, 'files': files(x, names), 'captions_from_day_pages': len(rows)}
    print(f"{x['p']}: {when}, {len(lines)} lines, {x['n']} photos ({len(rows)} with captions from Bapa's day pages)")

json.dump(A, open(apath, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(W, open(wpath, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
sys.exit(1 if bad else 0)
