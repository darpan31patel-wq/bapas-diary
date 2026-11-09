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
    ap.add_argument('--prune', action='store_true', help='also take the News photos of the other albums out of --db, so every '
                    'page (Today, Calendar, Through the years, Search) shows News photos only once their files have arrived')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    if 'source' not in [r[1] for r in db.execute('PRAGMA table_info(photos)')]:
        open(a.out, 'w').write('')
        print('No News photos in this database')
        return
    first = db.execute("SELECT album, min(file) FROM photos WHERE source = 'news' GROUP BY album").fetchall()
    with concurrent.futures.ThreadPoolExecutor(32) as ex:
        ok = list(ex.map(lambda r: has(f'{a.photos}s/{r[0]}/{urllib.parse.quote(r[1])}'), first))
    ready = sorted(al for (al, _), y in zip(first, ok) if y)
    open(a.out, 'w').write(''.join(al + '\n' for al in ready))
    print(f'News albums in the photo store: {len(ready):,} of {len(first):,}')
    if a.prune:
        db.execute("CREATE TEMP TABLE ready(album TEXT PRIMARY KEY)")
        db.executemany("INSERT INTO ready VALUES (?)", [(al,) for al in ready])
        gone = db.execute("SELECT count(*) FROM photos WHERE source = 'news' AND album NOT IN (SELECT album FROM ready)").fetchone()[0]
        db.execute("DELETE FROM photos WHERE source = 'news' AND album NOT IN (SELECT album FROM ready)")
        db.commit()
        print(f'News photos waiting for their files, left out of this build: {gone:,}')


if __name__ == '__main__':
    main()
