"""Build bapas.db, one SQLite file holding everything Bapa's Diary knows (Darpan, 22 Oct 2026: the offline database).

    python tools/build_archive.py --crawl /path/to/bapas-diary-crawl --out bapas.db

Tables (every photo, nothing cut out):
  photos     every baps.org vicharan photo: year, date (or the page's date range), place, album, file, caption,
             is_bapa (the photo_urls view gives its full size and 800 px web addresses)
  tg_posts   every post of both Telegram channels (history = Today in BAPS History, satpurush = Satpurush in UK & Europe)
  tg_events  the dated stories read out of those posts
  tg_cards   the older guru cards made from the channel
  diary      every daily Bapa's Diary picture so far: which photo and caption each year showed
  about      when and from what it was built

The photo and video files themselves are fetched by tools/archive_download.py, which saves them next to this file.
"""
import argparse, datetime, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import build_db   # noqa: E402  (the crawl reader and its date rules)

CHANNELS = {'history': ('TodayinBAPShistory', 'telegram'), 'satpurush': ('SatpurushInUKEurope', 'telegram/satpurush')}

SCHEMA = """
CREATE TABLE about (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE photos (
  year INTEGER, date TEXT, date_from TEXT, date_to TEXT, place TEXT, album TEXT, file TEXT, caption TEXT,
  is_bapa INTEGER, local_path TEXT, PRIMARY KEY (album, file));
CREATE VIEW photo_urls AS SELECT album, file,
  'https://www.baps.org/Data/Sites/1/Media/GalleryImages/' || album || '/FullSizeImages/' || file AS full_url,
  'https://www.baps.org/Data/Sites/1/Media/GalleryImages/' || album || '/WebImages/' || file AS web_url FROM photos;
CREATE INDEX photos_date ON photos (date);
CREATE INDEX photos_day ON photos (substr(date, 6, 5));
CREATE TABLE tg_posts (
  channel TEXT, id INTEGER, posted TEXT, date TEXT, place TEXT, text TEXT, photos INTEGER, videos INTEGER,
  files INTEGER, forwarded_from TEXT, links TEXT, url TEXT, local_folder TEXT, PRIMARY KEY (channel, id));
CREATE INDEX tg_posts_date ON tg_posts (date);
CREATE TABLE tg_events (channel TEXT, date TEXT, place TEXT, line TEXT, story TEXT, special INTEGER, headline TEXT,
  guru INTEGER, posts TEXT, data TEXT);
CREATE INDEX tg_events_date ON tg_events (date);
CREATE TABLE tg_cards (date TEXT, card TEXT, guru INTEGER, data TEXT);
CREATE TABLE diary (date TEXT, year INTEGER, photo_url TEXT, caption TEXT, PRIMARY KEY (date, year));
"""


def load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--crawl', required=True, help='folder with bapas-diary-YYYY.json and bapas-diary-fixes.json')
    ap.add_argument('--out', default='bapas.db')
    a = ap.parse_args()

    if os.path.exists(a.out):
        os.remove(a.out)
    db = sqlite3.connect(a.out)
    db.executescript(SCHEMA)

    years = build_db.load(a.crawl, os.path.join(a.crawl, 'bapas-diary-fixes.json'))
    rows = []
    for y, photos in years.items():
        for day, span, album, file, cap, place in photos:
            when = day or (span[0] if span and span[0] == span[1] else None)
            near = when or (span and span[0]) or datetime.date(y, 7, 1)
            rows.append((y, when and str(when), span and str(span[0]), span and str(span[1]), place, album, file, cap,
                         int(build_db.about_bapa(cap, near)), f'photos/baps/{y}/{album}/{file}'))
    db.executemany('INSERT OR IGNORE INTO photos VALUES (?,?,?,?,?,?,?,?,?,?)', rows)

    for ch, (name, folder) in CHANNELS.items():
        posts = load_json(os.path.join(HERE, folder, 'posts.json'), [])
        db.executemany('INSERT OR IGNORE INTO tg_posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', [
            (ch, p['id'], p.get('posted'), p.get('date'), p.get('place'), p.get('text'), p.get('photos', 0),
             p.get('videos', 0), p.get('files', 0), p.get('forwarded_from'), json.dumps(p.get('links') or []),
             f'https://t.me/{name}/{p["id"]}', f'telegram/{ch}/{p["id"]}') for p in posts])
        events = load_json(os.path.join(HERE, folder, 'events.json'), [])
        db.executemany('INSERT INTO tg_events VALUES (?,?,?,?,?,?,?,?,?,?)', [
            (ch, e.get('date'), e.get('place'), e.get('line'), e.get('story') or e.get('whatsapp'), int(bool(e.get('special'))),
             e.get('headline'), int(bool(e.get('guru'))), json.dumps(e.get('posts') or []), json.dumps(e, ensure_ascii=False))
            for e in events])
    cards = load_json(os.path.join(HERE, 'telegram', 'cards.json'), [])
    db.executemany('INSERT INTO tg_cards VALUES (?,?,?,?)', [
        (d, c.get('card'), int(bool(c.get('guru'))), json.dumps(c, ensure_ascii=False)) for d, c in cards.items() if isinstance(c, dict)])

    shown = load_json(os.path.join(HERE, 'archive', 'shown.json'), {})
    db.executemany('INSERT OR IGNORE INTO diary VALUES (?,?,?,?)', [
        (d, int(y), v.get('i') if isinstance(v, dict) else v, v.get('c') if isinstance(v, dict) else None)
        for d, ys in shown.items() if isinstance(ys, dict) for y, v in ys.items() if y.isdigit()])

    counts = {t: db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('photos', 'tg_posts', 'tg_events', 'tg_cards', 'diary')}
    db.executemany('INSERT INTO about VALUES (?,?)', [
        ('built', datetime.date.today().isoformat()),
        ('from', 'baps.org vicharan crawl 1999 to 2026 (18 Oct 2026), Today in BAPS History and Satpurush in UK & Europe '
                 'Telegram channels, Bapa\'s Diary shown record'),
        ('full_url', 'FullSizeImages is the original upload; WebImages (about 800 px) is used when there is no original'),
        ('counts', json.dumps(counts))])
    db.commit()
    db.execute('VACUUM')
    db.close()
    print(a.out, counts, f'{os.path.getsize(a.out) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
