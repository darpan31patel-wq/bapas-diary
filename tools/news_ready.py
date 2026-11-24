"""Which baps.org News galleries already have their photos in the website's photo store (R2), so Search shows a story's
photos only once they have arrived and never a wall of "Photo coming soon" (Darpan, 9 Nov 2026: "why is the number on
the top of the search page still the same").

    python3 tools/news_ready.py --db bapas.db --out news-ready.txt

Asks the photo store for one photo of each News album (the first one, small size) and writes the albums that have it, one
per line. build_search.py --news-ready news-ready.txt then leaves out the News photos of every other album.
"""
import argparse, concurrent.futures, datetime, sqlite3, urllib.parse, urllib.request


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
    one_gallery(db)


def one_gallery(db):
    """One gallery for each day (Darpan, 12 Nov 2026, from Tyagpurush Swami's note on 2 February 2026: "can we just add all
    the galleries from that day into that day's", "one master gallery on our website so you can see all the pictures at
    once"). The News stories' photos already sit on their own day; this takes out what would show twice:

    1. The link pictures at the end of a baps.org day page. They are the cover photo of a News story, captioned with the
       story's name ("Mahant Swami Maharaj's 92nd Birthday Celebration"), and the crawl kept them as day photos. The
       story's whole gallery now shows on the day instead, so the link picture goes. Known by: its caption is the name of
       a News story dated within 3 days, and that story has the same file.
    2. A News photo that is the very same file as one of the day's own photos (the stories often reuse them).
    Only this build's copy of the database changes; bapas.db itself and the daily picture are untouched."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name = 'article_photos'").fetchone():
        return
    stories = {}
    for path, title, place, date in db.execute("SELECT path, title, place, date FROM articles WHERE date IS NOT NULL"):
        name = title or ''
        if place and name.endswith(', ' + place):
            name = name[:-len(place) - 2]
        stories.setdefault(name.strip().lower(), []).append((path, date))
    files = {}
    for path, file in db.execute("SELECT path, lower(file) FROM article_photos"):
        files.setdefault(path, set()).add(file)
    near = lambda a, b: abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days) <= 3
    links = [(album, file, date) for album, file, cap, date in db.execute(
                 "SELECT album, file, caption, date FROM photos WHERE source != 'news' AND date IS NOT NULL")
             if any(near(date, d) and file.lower() in files.get(path, ()) for path, d in stories.get((cap or '').strip().lower(), ()))]
    per_day = {}
    for album, file, date in links:
        per_day[album, date] = per_day.get((album, date), 0) + 1
    # a day page links each story with one picture, so many of them on one day are the day's own photos (a 2004 album
    # captions all 31 of its photos "National Sponsored Walk"): those stay
    links = [(album, file) for album, file, date in links if per_day[album, date] <= 3]
    db.executemany("DELETE FROM photos WHERE album = ? AND file = ?", links)
    twice = db.execute("SELECT count(*) FROM photos n WHERE n.source = 'news' AND EXISTS (SELECT 1 FROM photos p WHERE "
                       "p.source != 'news' AND p.date = n.date AND lower(p.file) = lower(n.file))").fetchone()[0]
    db.execute("DELETE FROM photos WHERE source = 'news' AND rowid IN (SELECT n.rowid FROM photos n JOIN photos p ON "
               "p.source != 'news' AND p.date = n.date AND lower(p.file) = lower(n.file) WHERE n.source = 'news')")
    db.commit()
    print(f'One gallery a day: {len(links):,} News link pictures taken out of the day photos, '
          f'{twice:,} News photos that are the same as a day photo shown once')


if __name__ == '__main__':
    main()
