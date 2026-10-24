"""Which baps.org photos have a full size original, and under what name (Darpan, 23 Oct 2026: full size for all).

    python tools/fullsize_probe.py --db bapas.db --out fullsize-probe.json

Takes a dozen photos from every year, asks for each one in every folder and spelling baps.org might use, and notes
the picture size of whatever comes back, so we know the biggest copy that exists.
"""
import argparse, json, os, re, sqlite3, struct, urllib.error, urllib.parse, urllib.request

SITE = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/{size}/{file}'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
FOLDERS = ('FullSizeImages', 'WebImages', 'OriginalImages', 'Originals', 'LargeImages', 'ThumbnailImages')


def size_of(data):
    """(width, height) of a JPEG or PNG, or None."""
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', data[16:24])
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1; continue
        m = data[i + 1]
        if m in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack('>HH', data[i + 5:i + 9]); return w, h
        i += 2 + struct.unpack('>H', data[i + 2:i + 4])[0]
    return None


def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as r:
            data = r.read()
            return r.status, size_of(data), len(data)
    except urllib.error.HTTPError as e:
        return e.code, None, 0
    except Exception as e:
        return type(e).__name__, None, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--where', help="only these photos, e.g. \"file LIKE '%Robbinsville%'\" (24 Oct 2026: albums that won't come)")
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    rows = db.execute(f'SELECT year, album, file FROM photos WHERE {a.where} ORDER BY random() LIMIT 30').fetchall() if a.where else []
    for (y,) in [] if a.where else db.execute('SELECT DISTINCT year FROM photos ORDER BY year'):
        rows += db.execute('SELECT year, album, file FROM photos WHERE year = ? ORDER BY random() LIMIT 12', (y,)).fetchall()
    out = []
    for y, album, file in rows:
        stem, ext = os.path.splitext(file)
        names = list(dict.fromkeys([stem + '.jpg', file, stem + '.JPG', stem + '.jpeg', stem + '.png', file.replace('_', ' ')]))
        r = {'year': y, 'album': album, 'file': file, 'tries': {}}
        for folder in FOLDERS:
            for n in names if folder in ('FullSizeImages', 'WebImages') else names[:1]:
                code, dims, length = fetch(SITE.format(album=album, size=folder, file=urllib.parse.quote(n)))
                r['tries'][f'{folder}/{n}'] = [code, dims, length]
        out.append(r)
        best = {k: v for k, v in r['tries'].items() if v[0] == 200}
        print(y, album, file, {k.split('/')[0]: v[1] for k, v in best.items()}, flush=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    by_year = {}
    for r in out:
        full = any(k.startswith('FullSizeImages') and v[0] == 200 for k, v in r['tries'].items())
        c = by_year.setdefault(r['year'], [0, 0]); c[0] += 1; c[1] += full
    print('Full size original found, by year:', {y: f'{f} of {n}' for y, (n, f) in by_year.items()})


if __name__ == '__main__':
    main()
