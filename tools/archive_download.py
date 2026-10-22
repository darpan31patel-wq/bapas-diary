"""Download every photo and video of the Bapa's Diary database into Google Drive (Darpan, 22 Oct 2026).

Run on the Mac, overnight, with Google Drive for desktop set to "Stream files":

    python3 archive_download.py                 # until everything is saved (stop any time with Ctrl+C)
    python3 archive_download.py --until 07:00   # stop at 7am
    python3 archive_download.py --only telegram # just the two Telegram channels

Everything goes into "My Drive/Bapa's Archive": bapas.db (the database), photos/baps/YEAR/ALBUM/FILE.jpg and
telegram/CHANNEL/POST/1.jpg, 2.jpg, video-1.mp4 ... Files already there are skipped, so a stopped run carries on
where it left off. It is gentle on purpose: one file at a time with a pause between them, and if baps.org ever
shows its "Just a moment" check it stops for the night instead of trying to get round it.
Uses only what comes with Python 3, nothing to install.
"""
import argparse, datetime, glob, gzip, html, os, re, shutil, sqlite3, sys, time, urllib.error, urllib.request

DB_URL = 'https://github.com/darpan31patel-wq/bapas-diary/releases/download/database/bapas.db.gz'
SITE = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/{size}/{file}'
CHANNELS = {'history': 'TodayinBAPShistory', 'satpurush': 'SatpurushInUKEurope'}
UA = 'Mozilla/5.0 (Macintosh) bapas-diary-archive (personal offline copy)'


class SlowDown(Exception):
    """baps.org or Telegram asked us to wait: stop for tonight."""


def drive_folder():
    """'My Drive' from Google Drive for desktop (any language), or None."""
    for d in sorted(glob.glob(os.path.expanduser('~/Library/CloudStorage/GoogleDrive-*/*'))):
        if os.path.isdir(d) and not os.path.basename(d).startswith('.') and 'Shared' not in os.path.basename(d):
            return d
    return None


def get(url, timeout=60, may_be_missing=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body, kind = r.read(), r.headers.get('Content-Type', '')
    except urllib.error.HTTPError as e:
        if may_be_missing and e.code in (403, 404):   # e.g. no original upload kept for this photo
            return None, ''
        if e.code in (403, 429, 503):
            raise SlowDown(f'{e.code} from {url.split("/")[2]}')
        if e.code == 404:
            return None, ''
        raise
    if b'Just a moment' in body[:3000] or b'cf-chl' in body[:3000]:
        raise SlowDown('the "Just a moment" check on ' + url.split('/')[2])
    return body, kind


def save(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'wb') as f:
        f.write(body)
    os.replace(tmp, path)


class Progress:
    def __init__(self, name, total):
        self.name, self.total, self.done, self.saved, self.bytes, self.start = name, total, 0, 0, 0, time.time()

    def tick(self, saved_bytes=0):
        self.done += 1
        if saved_bytes:
            self.saved += 1
            self.bytes += saved_bytes
        if self.done % 100 == 0 or self.done == self.total:
            rate = self.saved / max(1, time.time() - self.start) * 3600
            left = (self.total - self.done) / rate if rate else 0
            print(f'  {self.name}: {self.done:,} of {self.total:,} checked, {self.saved:,} saved this run '
                  f'({self.bytes / 1e9:.2f} GB), about {rate:,.0f} an hour'
                  + (f', roughly {left:,.0f} hours left' if rate and self.saved > 50 else ''), flush=True)


def write_captions(db, root):
    """Beside the photos, in plain text: captions.csv in each baps.org album folder, post.txt in each Telegram post folder
    (date, place, the post's words and its link). No internet needed, and only written when missing."""
    import csv
    albums = {}
    for y, album, file, date, d0, d1, place, cap in db.execute(
            'SELECT year, album, file, date, date_from, date_to, place, caption FROM photos'):
        albums.setdefault((y, album), []).append((file, date or f'{d0} to {d1}', place, cap))
    for (y, album), rows in albums.items():
        path = os.path.join(root, 'photos', 'baps', str(y), album, 'captions.csv')
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['file', 'date', 'place', 'caption'])
            w.writerows(sorted(rows))
    for ch, pid, posted, date, place, text, url, rel in db.execute(
            'SELECT channel, id, posted, date, place, text, url, local_folder FROM tg_posts'):
        path = os.path.join(root, rel, 'post.txt')
        if os.path.exists(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'{url}\nPosted {posted}\n' + (f'About {date}' + (f', {place}' if place else '') + '\n' if date else '') + f'\n{text or ""}\n')


def baps_photos(db, root, gap, stop_at):
    rows = db.execute('SELECT album, file, local_path FROM photos ORDER BY year DESC, coalesce(date, date_from) DESC').fetchall()
    p = Progress('baps.org photos', len(rows))
    full_ok = [True, 0, 0]   # still trying originals, originals found, originals missing
    print(f'baps.org: {len(rows):,} photos, newest years first')
    for album, file, rel in rows:
        if stop_at and datetime.datetime.now() >= stop_at:
            print('  time to stop for tonight'); return False
        path = os.path.join(root, rel)
        if os.path.exists(path):
            p.tick(); continue
        body = None
        for size in ('FullSizeImages', 'WebImages') if full_ok[0] else ('WebImages',):   # the original upload, else the 800 px copy
            body, kind = get(SITE.format(album=album, size=size, file=file), may_be_missing=size == 'FullSizeImages')
            if body and kind.startswith('image'):
                if size == 'FullSizeImages':
                    full_ok[1] += 1
                break
            body = None
            if size == 'FullSizeImages':
                full_ok[2] += 1
                if full_ok[2] >= 50 and not full_ok[1]:   # baps.org doesn't give originals: stop asking for them
                    full_ok[0] = False
                    print('  baps.org has no full size originals for these, saving the 800 px web size')
        if body:
            save(path, body)
        else:
            with open(os.path.join(root, 'photos', 'missing.txt'), 'a') as f:
                f.write(f'{album}/{file}\n')
        p.tick(len(body or b''))
        time.sleep(gap)
    return True


def media_in(page):
    """Photo and video addresses in a post's embed page."""
    photos = re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", page)
    videos = re.findall(r'<video[^>]+src="([^"]+)"', page)
    too_big = len(re.findall(r'message_media_not_supported|Media is too big', page))
    return [html.unescape(u) for u in photos], [html.unescape(u) for u in videos], too_big


def telegram(db, root, gap, stop_at):
    rows = db.execute('SELECT channel, id, local_folder FROM tg_posts WHERE photos > 0 OR videos > 0 ORDER BY channel, id').fetchall()
    p = Progress('Telegram posts', len(rows))
    print(f'Telegram: {len(rows):,} posts with photos or videos')
    for ch, pid, rel in rows:
        if stop_at and datetime.datetime.now() >= stop_at:
            print('  time to stop for tonight'); return False
        folder = os.path.join(root, rel)
        if os.path.exists(os.path.join(folder, '.done')):
            p.tick(); continue
        body, _ = get(f'https://t.me/{CHANNELS[ch]}/{pid}?embed=1&mode=tme')
        page = (body or b'').decode('utf-8', 'replace')
        photos, videos, too_big = media_in(page)
        got = 0
        for kind, urls in (('', photos), ('video-', videos)):
            for n, url in enumerate(urls, 1):
                name = os.path.join(folder, f'{kind}{n}.{"mp4" if kind else "jpg"}')
                if not os.path.exists(name):
                    data, _ = get(url, timeout=300)
                    if data:
                        save(name, data); got += len(data)
                    time.sleep(gap / 2)
        if too_big:
            with open(os.path.join(root, 'telegram', 'too-big-for-the-web.txt'), 'a') as f:
                f.write(f'https://t.me/{CHANNELS[ch]}/{pid}\n')
        os.makedirs(folder, exist_ok=True)
        open(os.path.join(folder, '.done'), 'w').close()
        p.tick(got)
        time.sleep(gap)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--to', help="where to save (default: Google Drive, My Drive/Bapa's Archive)")
    ap.add_argument('--until', help='stop at this time, e.g. 07:00')
    ap.add_argument('--only', choices=('baps', 'telegram'))
    ap.add_argument('--gap', type=float, default=2.0, help='seconds between files (default 2)')
    a = ap.parse_args()

    root = a.to
    if not root:
        drive = drive_folder()
        if not drive:
            sys.exit('Google Drive for desktop was not found. Install it, sign in, set it to "Stream files", then run this again '
                     '(or pass --to with any folder).')
        root = os.path.join(drive, "Bapa's Archive")
    os.makedirs(root, exist_ok=True)
    print('Saving into', root)

    db_path = os.path.join(root, 'bapas.db')
    if not os.path.exists(db_path):
        print('Fetching the database (about 10 MB)...')
        body, _ = get(DB_URL, timeout=300)
        save(db_path, gzip.decompress(body))
    local = os.path.join(os.path.expanduser('~'), '.bapas-archive.db')   # read a local copy, not the one Drive is syncing
    shutil.copyfile(db_path, local)
    db = sqlite3.connect(local)

    stop_at = None
    if a.until:
        h, m = map(int, a.until.split(':'))
        stop_at = datetime.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
        if stop_at <= datetime.datetime.now():
            stop_at += datetime.timedelta(days=1)
        print('Stopping at', stop_at.strftime('%H:%M on %d %b'))

    try:
        print('Writing the captions beside the photos (captions.csv, post.txt)...')
        write_captions(db, root)
        if a.only != 'baps':
            telegram(db, root, a.gap, stop_at)
        if a.only != 'telegram':
            baps_photos(db, root, a.gap, stop_at)
        print('All done for now. Run it again any time: it only fetches what is new or missing.')
    except SlowDown as e:
        print(f'\nStopped: {e}. That means "please slow down", so it is finished for tonight. Run it again tomorrow night.')
    except KeyboardInterrupt:
        print('\nStopped. Run it again any time and it carries on where it left off.')


if __name__ == '__main__':
    main()
