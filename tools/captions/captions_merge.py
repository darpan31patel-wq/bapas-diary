"""Website only (Darpan, 25 Oct 2026): adds one day page read by captions_chrome.js to crawl/button/YYYY-MM.json on the
`database` branch, the same file the screensaver button filled, so the next database build has each new photo WITH its
caption (build_archive.py reads crawl/button as source 'button'). A page read again replaces its earlier rows.

    python3 captions_merge.py --known --crawl crawl            (pages already saved, to hand to CAP.run)
    python3 captions_merge.py --part part.json --crawl crawl
part.json is CAP.part(i), CAP.compact(i) or CAP.short(i) exactly (CAP.short's caption pieces joined); its hash must match, so a page passed on wrongly is never saved.
"""
import argparse, datetime, json, os, re, sys


def js_hash(s):
    h = 5381
    b = s.encode('utf-16-le')
    for i in range(0, len(b), 2):
        h = (h * 33 + int.from_bytes(b[i:i + 2], 'little')) & 0xFFFFFFFF
    return format(h, 'x')


ap = argparse.ArgumentParser()
ap.add_argument('--part')
ap.add_argument('--crawl', default='crawl')
ap.add_argument('--known', action='store_true', help='print the pages already saved, for CAP.run')
a = ap.parse_args()
if a.known:
    import glob
    print(json.dumps(sorted({h['page'] for p in glob.glob(os.path.join(a.crawl, 'button', '*.json'))
                             for h in json.load(open(p, encoding='utf-8')) if h.get('page')})))
    sys.exit()
x = json.load(open(a.part, encoding='utf-8'))
if 'caps' in x:   # [n, caption] is one caption n times in a row (CAP.short)
    x['caps'] = [c for e in x['caps'] for c in ([e[1]] * e[0] if isinstance(e, list) else [e])]
if 'caps' in x:   # CAP.compact(i): runs of numbered files written once, e.g. "37046 2026_10_21_[1-45/3]_Morbi.jpg"
    files = []
    for f in x['files']:
        al, f = f.split(' ', 1)
        m = re.match(r'^(.*)\[(\d+)-(\d+)/(\d+)\](.*)$', f)
        files += [(al, f'{m[1]}{n:0{m[4]}d}{m[5]}') for n in range(int(m[2]), int(m[3]) + 1)] if m else [(al, f)]
    if len(files) != len(x['caps']):
        sys.exit(f"{x['page']}: {len(files)} photos but {len(x['caps'])} captions, read this page again")
    x['rows'] = [[al, f, c] for (al, f), c in zip(files, x['caps'])]
rows = x['rows']
if js_hash(json.dumps(rows, ensure_ascii=False, separators=(',', ':'))) != x['hash']:
    sys.exit(f"{x['page']}: hash does not match, read this page again with CAP.part")
m = re.search(r'/(\d{1,2})-([A-Za-z]+)-(\d{4})-\d+\.aspx$', x.get('day') or x['page'])   # an album linked from a day page takes that day
day = datetime.datetime.strptime(f'{m[1]} {m[2]} {m[3]}', '%d %B %Y').date()
place = x['title'].split("Vicharan,", 1)[1].strip() if "Vicharan," in x['title'] else ''
path = os.path.join(a.crawl, 'button', f'{day:%Y-%m}.json')
have = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
have = [h for h in have if h.get('page') != x['page']]
urls = {h['i'] for h in have}
add = [{'d': day.isoformat(), 'p': place, 'i': f'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{al}/WebImages/{f}',
        'c': c, 'page': x['page']} for al, f, c in rows]
add = [r for r in add if r['i'] not in urls]
have += add
have.sort(key=lambda h: (h['d'], h['page'], h['i']))
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(have, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"{x['page']}: {len(add)} photos with captions ({day}, {place})")
