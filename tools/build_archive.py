"""Build bapas.db, one SQLite file holding everything Bapa's Diary knows (Darpan, 22 Oct 2026: the offline database).

    python tools/build_archive.py --crawl /path/to/bapas-diary-crawl --scan scan.json --out bapas.db

Tables (every photo, nothing cut out):
  photos     every baps.org vicharan photo: year, date (or the page's date range), place, album, file, caption,
             is_bapa, source (the photo_urls view gives its full size and 800 px web addresses). Three ways in:
               page    the day pages, crawled in Darpan's Chrome on 18 Oct 2026 (crawl/bapas-diary-YYYY.json)
               button  the newer day pages his screensaver's button has read since (crawl/button/YYYY-MM.json)
               scan    photos in an album that no page lists, found by tools/album_scan.py (scan.json, no caption)
  tg_posts   every post of both Telegram channels (history = Today in BAPS History, satpurush = Satpurush in UK & Europe)
  tg_events  the dated stories read out of those posts
  tg_cards   the older guru cards made from the channel
  diary      every daily Bapa's Diary picture so far: which photo and caption each year showed
  about      when and from what it was built

The photo and video files themselves are fetched by tools/archive_download.py, which saves them next to this file.
"""
import argparse, datetime, glob, json, os, re, sqlite3, sys, urllib.parse

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
import build_db   # noqa: E402  (the crawl reader and its date rules)
import satpurush  # noqa: E402  (which day each Satpurush photo post belongs to)

CHANNELS = {'history': ('TodayinBAPShistory', 'telegram', 'Today in BAPS History'),
            'satpurush': ('SatpurushInUKEurope', 'telegram/satpurush', 'Satpurush in UK & Europe')}
BAD = re.compile(r'[\\/:*?"<>|\n\r\t]+')


def clean(text, most):
    """Text that is safe in a file or folder name on a Mac, Windows or Google Drive, cut at a word near `most` letters."""
    text = re.sub(r'\s+', ' ', BAD.sub(' ', text or '')).strip(' .,;-')
    if len(text) > most:
        text = text[:most].rsplit(' ', 1)[0]
    return text.strip(' .,;-')


def photo_path(y, when, d0, d1, place, file, cap):
    """photos/baps.org/2019/2019-01-05 Mumbai/Swamishri performs the arti (2019_01_05_001_Mumbai).jpg"""
    day = str(when) if when else f'{d0} to {d1}'
    town = clean(re.sub(r',\s*India$', '', place or ''), 40)
    stem, ext = os.path.splitext(file)
    name = f'{clean(cap, 80)} ({stem}){ext}' if clean(cap, 80) else file
    return f'photos/baps.org/{y}/{clean(day + " " + town, 70)}/{name}'


def post_folder(title, p):
    """telegram/Today in BAPS History/2016-05-13 Sarangpur Mandir Shatabdi Mahotsav (post 20)"""
    first = next((l for l in (p.get('text') or '').split('\n') if l.strip() and not satpurush.DATE.match(l)), '')
    words = p.get('place') or first
    day = p.get('date') or ('posted ' + (p.get('posted') or '')[:10])
    return f'telegram/{title}/{clean(day + " " + clean(words, 60), 80)} (post {p["id"]})'


def date_posts(ch, folder, posts):
    """Gives the untitled photo and video posts the day and place of the dated post before them, so every folder has a date."""
    if ch == 'satpurush':
        for st in satpurush.stories(sorted(posts, key=lambda p: p['id'])):
            place = satpurush.parts(st['text'])[0]
            for p in [q for q in posts if q['id'] == st['id']] + st['media']:
                p.update(date=st['date'], place=place)
        return posts
    last = None
    for p in sorted(posts, key=lambda p: p['id']):
        if p.get('date'):
            last = p
        elif last and (p.get('photos') or p.get('videos')) and not (p.get('text') or '').strip() and p['id'] - last['id'] <= 30:
            p.update(date=last['date'], place=last.get('place'))
        else:
            last = None
    return posts

SCHEMA = """
CREATE TABLE about (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE photos (
  year INTEGER, date TEXT, date_from TEXT, date_to TEXT, place TEXT, album TEXT, file TEXT, caption TEXT,
  is_bapa INTEGER, source TEXT, local_path TEXT, PRIMARY KEY (album, file));
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


def newer(rows, crawl, scan):
    """Photos the 18 Oct crawl doesn't have: the screensaver button's day pages, then the album scan's finds."""
    have = {(r[5], r[6].lower()) for r in rows}
    album_day = {r[5]: r for r in rows}   # a found photo goes in its album's folder, with its date and place
    out = []
    for path in sorted(glob.glob(os.path.join(crawl, 'button', '*.json'))):
        for x in load_json(path, []):
            m = re.search(r'GalleryImages/(\d+)/\w+/(.+)$', x['i'])
            album, file = m[1], urllib.parse.unquote(m[2])
            if (album, file.lower()) in have:
                continue
            have.add((album, file.lower()))
            when = datetime.date.fromisoformat(x['d'])
            out.append((when.year, x['d'], None, None, x.get('p'), album, file, x.get('c'), int(build_db.about_bapa(x.get('c'), when)),
                        'button', photo_path(when.year, x['d'], None, None, x.get('p'), file, x.get('c'))))
            album_day.setdefault(album, out[-1])
    for x in load_json(scan or '', {}).get('extra', []):
        album, file = x['album'], x['file']
        if (album, file.lower()) in have:
            continue
        have.add((album, file.lower()))
        sib = album_day.get(album)
        if sib:
            y, when, d0, d1, place = sib[:5]
        else:   # a new album no page has shown yet: its date and place are in the file name
            m = re.match(r'(\d{4})_(\d{2})_(\d{2})_\d+_([A-Za-z_]+?)_*(?:f|Edit)?\.jpg$', file)
            y, when, d0, d1, place = int(m[1]), f'{m[1]}-{m[2]}-{m[3]}', None, None, m[4].replace('_', ' ')
        out.append((y, when, d0, d1, place, album, file, None, None, 'scan', photo_path(y, when, d0, d1, place, file, '')))
    return out


def load_json(path, default):
    try:
        return json.load(open(path, encoding='utf-8'))
    except (OSError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--crawl', required=True, help='folder with bapas-diary-YYYY.json and bapas-diary-fixes.json')
    ap.add_argument('--scan', help="album_scan.py's scan.json: photos no page lists")
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
                         int(build_db.about_bapa(cap, near)), 'page', photo_path(y, when, span and span[0], span and span[1], place, file, cap)))
    rows += newer(rows, a.crawl, a.scan)
    seen = {}
    for r in rows:
        seen[r[-1].lower()] = seen.get(r[-1].lower(), 0) + 1
    rows = [r[:-1] + (re.sub(r' \((.*)\)(\.\w+)$', lambda m: f' ({r[5]} {m[1]}){m[2]}', r[-1]) if seen[r[-1].lower()] > 1 else r[-1],)
            for r in rows]
    db.executemany('INSERT OR IGNORE INTO photos VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows)

    for ch, (name, folder, title) in CHANNELS.items():
        posts = date_posts(ch, folder, load_json(os.path.join(HERE, folder, 'posts.json'), []))
        db.executemany('INSERT OR IGNORE INTO tg_posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', [
            (ch, p['id'], p.get('posted'), p.get('date'), p.get('place'), p.get('text'), p.get('photos', 0),
             p.get('videos', 0), p.get('files', 0), p.get('forwarded_from'), json.dumps(p.get('links') or []),
             f'https://t.me/{name}/{p["id"]}', post_folder(title, p)) for p in posts])
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
    counts['photos_by_source'] = dict(db.execute('SELECT source, count(*) FROM photos GROUP BY source').fetchall())
    db.executemany('INSERT INTO about VALUES (?,?)', [
        ('built', datetime.date.today().isoformat()),
        ('from', 'baps.org vicharan crawl 1999 to 2026 (18 Oct 2026), Today in BAPS History and Satpurush in UK & Europe '
                 'Telegram channels, Bapa\'s Diary shown record'),
        ('full_url', 'FullSizeImages is the original upload; WebImages (about 800 px) is used when there is no original'),
        ('scan', json.dumps({k: v for k, v in load_json(a.scan or '', {}).items() if k not in ('extra', 'done')}
                            | {'albums_checked': len(load_json(a.scan or '', {}).get('done', {}))})),
        ('counts', json.dumps(counts))])
    db.commit()
    db.execute('VACUUM')
    db.close()
    print(a.out, counts, f'{os.path.getsize(a.out) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
