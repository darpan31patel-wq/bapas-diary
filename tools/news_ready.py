"""Which baps.org News galleries already have their photos in the website's photo store (R2), so Search shows a story's
photos only once they have arrived and never a wall of "Photo coming soon" (Darpan, 9 Nov 2026: "why is the number on
the top of the search page still the same").

    python3 tools/news_ready.py --db bapas.db --out news-ready.txt

Asks the photo store for one photo of each News album (the first one, small size) and writes the albums that have it, one
per line. build_search.py --news-ready news-ready.txt then leaves out the News photos of every other album.
"""
import argparse, concurrent.futures, sqlite3, urllib.parse, urllib.request


def has(url):
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'bapas-diary-build'})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--photos', default='https://photos.bapas-diary.com/')
    ap.add_argument('--out', default='news-ready.txt')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    first = db.execute("SELECT album, min(file) FROM photos WHERE source = 'news' GROUP BY album").fetchall()
    with concurrent.futures.ThreadPoolExecutor(32) as ex:
        ok = list(ex.map(lambda r: has(f'{a.photos}s/{r[0]}/{urllib.parse.quote(r[1])}'), first))
    ready = sorted(al for (al, _), y in zip(first, ok) if y)
    open(a.out, 'w').write(''.join(al + '\n' for al in ready))
    print(f'News albums in the photo store: {len(ready):,} of {len(first):,}')


if __name__ == '__main__':
    main()
