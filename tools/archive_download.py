"""Download every photo and video of the Bapa's Diary database into Google Drive (Darpan, 22 Oct 2026).

Runs on GitHub (.github/workflows/drive.yml, straight into Drive) or on the Mac, overnight, with Google Drive for desktop set to "Stream files":

    python3 archive_download.py                 # until everything is saved (stop any time with Ctrl+C)
    python3 archive_download.py --until 07:00   # stop at 7am
    python3 archive_download.py --only telegram # just the two Telegram channels
    python3 archive_download.py --check         # no downloading: count what is saved against the database

Everything goes into "My Drive/Bapa's Archive": bapas.db (the database), then
  photos/baps.org/2019/2019-01-05 Mumbai/Swamishri performs the arti (2019_01_05_001_Mumbai).jpg  (+ captions.csv)
  telegram/Today in BAPS History/2016-05-13 Sarangpur Mandir Shatabdi Mahotsav (post 20)/photo 1.jpg, video 1.mp4, post.txt
check.txt says, year by year, how many photos the database knows, how many are saved and which baps.org refused.
Files already there are skipped, so a stopped run carries on
where it left off. It is gentle on purpose: one file at a time with a pause between them, and if baps.org ever
shows its "Just a moment" check it stops for the night instead of trying to get round it.
Uses only what comes with Python 3, nothing to install.
"""
import argparse, datetime, glob, gzip, html, os, re, shutil, sqlite3, sys, time, urllib.error, urllib.parse, urllib.request

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


failures = [0]   # files in a row that wouldn't come, whatever the reason


def get(url, timeout=60, may_be_missing=False):
    """(body, content type), or (None, '') when the file isn't there or won't come after three tries. A server
    hiccup (500, a timeout, a dropped line) skips that one file, it never stops the night (Darpan, 23 Oct 2026)."""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body, kind = r.read(), r.headers.get('Content-Type', '')
            break
        except urllib.error.HTTPError as e:
            if e.code in (403, 404) and may_be_missing:   # e.g. no original upload kept for this photo
                return None, ''
            if e.code == 404:
                return None, ''
            if e.code in (403, 429):
                raise SlowDown(f'{e.code} from {url.split("/")[2]}')
        except Exception:   # timeout, connection reset, half a file
            pass
        time.sleep(5 * (attempt + 1))
    else:
        failures[0] += 1
        print(f'  skipped (would not download): {url[:120]}', flush=True)
        if failures[0] >= 30:
            raise SlowDown(f'30 files in a row would not download from {url.split("/")[2]}')
        return None, ''
    failures[0] = 0
    if b'Just a moment' in body[:3000] or b'cf-chl' in body[:3000]:
        raise SlowDown('the "Just a moment" check on ' + url.split('/')[2])
    return body, kind


ROOT, HAVE = [''], set()   # the folder saved into, and files already safe elsewhere (--have, for GitHub: already in Drive)
HOOK = {'cmd': None, 'every': 1500, 'files': 0, 'bytes': 0}


def there(path):
    """Is this file saved, here or (on GitHub) already in Drive?"""
    return os.path.exists(path) or os.path.relpath(path, ROOT[0]) in HAVE


def save(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'wb') as f:
        f.write(body)
    os.replace(tmp, path)
    HOOK['files'] += 1; HOOK['bytes'] += len(body)
    if HOOK['cmd'] and (HOOK['files'] >= HOOK['every'] or HOOK['bytes'] > 3e9):
        hand_over()


def hand_over():
    """On GitHub: send what has been saved so far to Drive (rclone move), so the runner's small disk never fills."""
    import subprocess, threading
    lock = HOOK.setdefault('lock', threading.Lock())
    if not HOOK['cmd'] or not lock.acquire(blocking=False):
        return
    try:
        HOOK['files'], HOOK['bytes'] = 0, 0
        subprocess.run(HOOK['cmd'], shell=True, check=False)
    finally:
        lock.release()


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


def write_captions(db, root, years=None, photos=True, posts=True):
    """Beside the photos, in plain text: captions.csv in each baps.org day folder (every photo's file name, date, place,
    full caption and baps.org address), post.txt in each Telegram post folder (its link, date, place and words).
    No internet needed, and only written when missing."""
    import csv
    folders, newer = {}, set()
    how = {'page': 'day page', 'button': 'day page (screensaver button)', 'scan': 'album scan, not on any page'}
    for rel, album, file, date, d0, d1, place, cap, src, y in db.execute(
            'SELECT local_path, album, file, date, date_from, date_to, place, caption, source, year FROM photos'):
        if not photos or (years and y not in years):
            continue
        folders.setdefault(os.path.dirname(rel), []).append(
            (os.path.basename(rel), date or f'{d0} to {d1}', place, cap, SITE.format(album=album, size='WebImages', file=file),
             how.get(src, src)))
        if src != 'page':
            newer.add(os.path.dirname(rel))
    for folder, rows in folders.items():
        path = os.path.join(root, folder, 'captions.csv')
        if there(path) and folder not in newer:   # a folder the scan or button added to is written again
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['file', 'date', 'place', 'caption', 'baps.org', 'found on'])
            w.writerows(sorted(rows))
    for ch, pid, posted, date, place, text, url, rel in db.execute(
            'SELECT channel, id, posted, date, place, text, url, local_folder FROM tg_posts' + ('' if posts else ' WHERE 0')):
        path = os.path.join(root, rel, 'post.txt')
        if there(path):
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f'{url}\nPosted {posted}\n' + (f'About {date}' + (f', {place}' if place else '') + '\n' if date else '') + f'\n{text or ""}\n')


def baps_photos(db, root, gap, stop_at, years=None, notes=None):
    rows = db.execute('SELECT album, file, local_path, year FROM photos ORDER BY year DESC, coalesce(date, date_from) DESC').fetchall()
    if years:
        rows = [r for r in rows if r[3] in years]
    notes = notes or os.path.join(root, 'photos', 'missing.txt')
    p = Progress('baps.org photos', len(rows))
    full_ok = [True, 0, 0]   # still trying originals, originals found, originals missing
    misses = 0
    print(f'baps.org: {len(rows):,} photos, newest years first')
    for album, file, rel, year in rows:
        if stop_at and datetime.datetime.now() >= stop_at:
            print('  time to stop for tonight'); return False
        path = os.path.join(root, rel)
        if there(path):
            p.tick(); continue
        body = None
        # FullSizeImages is the photographer's upload when baps.org kept it (only kept for 1999 and from 2022, up to 5472 px); WebImages is
        # the biggest copy otherwise (1200 px from 2014, 400 to 800 px before). A dozen photos a year were tested, 23 Oct 2026.
        originals = full_ok[0] and (year == 1999 or year >= 2022)
        for size in ('FullSizeImages', 'WebImages') if originals else ('WebImages',):
            # baps.org serves '.jpg' but refuses '.JPG', and some names have spaces (screensaver project, 22 Oct 2026)
            name = urllib.parse.quote(re.sub(r'\.JPE?G$', '.jpg', file, flags=re.I))
            body, kind = get(SITE.format(album=album, size=size, file=name), may_be_missing=True)
            if body and kind.startswith('image'):
                if size == 'FullSizeImages':
                    full_ok[1] += 1
                break
            body = None
            if size == 'FullSizeImages':
                full_ok[2] += 1
                if full_ok[2] >= 50 and not full_ok[1]:   # baps.org doesn't give originals: stop asking for them
                    full_ok[0] = False
                    print('  baps.org has no full size originals for these, saving the web size')
        if body:
            save(path, body)
            misses = 0
        else:
            os.makedirs(os.path.dirname(notes), exist_ok=True)
            with open(notes, 'a') as f:
                f.write(f'{album}/{file}\n')
            misses += 1
            if misses >= 30:   # thirty in a row is not missing photos, it is baps.org saying no for now
                raise SlowDown('30 photos in a row refused by baps.org')
        p.tick(len(body or b''))
        time.sleep(gap)
    return True


def check(db, root):
    """check.txt: every photo and Telegram post the database knows, against what is saved in the folder."""
    missing = set()
    for path in glob.glob(os.path.join(root, 'photos', 'missing*.txt')):
        missing |= set(open(path).read().split('\n'))
    years, gone = {}, []
    for y, album, file, rel, src in db.execute('SELECT year, album, file, local_path, source FROM photos ORDER BY year'):
        c = years.setdefault(y, [0, 0, 0, 0])   # known, saved, refused by baps.org, still to fetch
        c[0] += 1
        if there(os.path.join(root, rel)):
            c[1] += 1
        elif f'{album}/{file}' in missing:
            c[2] += 1; gone.append(f'{album}/{file}')
        else:
            c[3] += 1
    by_src = dict(db.execute('SELECT source, count(*) FROM photos GROUP BY source').fetchall())
    tg = db.execute('SELECT channel, local_folder FROM tg_posts WHERE photos > 0 OR videos > 0').fetchall()
    tg_done = sum(there(os.path.join(root, rel, '.done')) for _, rel in tg)
    total = [sum(c[k] for c in years.values()) for k in range(4)]
    lines = [f'Bapa\'s Archive check, {datetime.datetime.now():%d %B %Y %H:%M}', '',
             f'baps.org photos: {total[0]:,} known ({by_src.get("page", 0):,} from the day pages, {by_src.get("button", 0):,} from '
             f'the screensaver button, {by_src.get("scan", 0):,} found by the album scan), {total[1]:,} saved, '
             f'{total[2]:,} refused by baps.org, {total[3]:,} still to fetch', '',
             'Year    known    saved  refused  to fetch'] + [
             f'{y}  {c[0]:>7,}  {c[1]:>7,}  {c[2]:>7,}  {c[3]:>8,}' for y, c in sorted(years.items())] + [
             '', f'Telegram: {len(tg):,} posts with photos or videos, {tg_done:,} saved']
    scan = db.execute("SELECT value FROM about WHERE key = 'scan'").fetchone()
    if scan:
        lines.append(f'Album scan: {scan[0]}')
    if gone:
        lines += ['', 'Refused by baps.org (tried every run):'] + gone
    with open(os.path.join(root, 'check.txt'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:3]))
    print(f'Telegram: {tg_done:,} of {len(tg):,} posts saved. Every year is in check.txt.')


def media_in(page):
    """Photo and video addresses in a post's embed page."""
    photos = re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", page)
    videos = re.findall(r'<video[^>]+src="([^"]+)"', page)
    too_big = len(re.findall(r'message_media_not_supported|Media is too big', page))
    return [html.unescape(u) for u in photos], [html.unescape(u) for u in videos], too_big


def telegram(db, root, gap, stop_at):
    """Four posts at a time: Telegram's file servers are quick, the wait is mostly the download itself."""
    import concurrent.futures
    rows = db.execute('SELECT channel, id, local_folder FROM tg_posts WHERE photos > 0 OR videos > 0 ORDER BY channel, id').fetchall()
    p = Progress('Telegram posts', len(rows))
    print(f'Telegram: {len(rows):,} posts with photos or videos')

    def one(row):
        ch, pid, rel = row
        folder = os.path.join(root, rel)
        if there(os.path.join(folder, '.done')):
            return 0
        body, _ = get(f'https://t.me/{CHANNELS[ch]}/{pid}?embed=1&mode=tme')
        if body is None:
            return 0   # the post's page wouldn't come: tried again next run
        photos, videos, too_big = media_in(body.decode('utf-8', 'replace'))
        got, whole = 0, True
        for kind, urls in (('', photos), ('video-', videos)):
            for n, url in enumerate(urls, 1):
                name = os.path.join(folder, f'{"video" if kind else "photo"} {n}.{"mp4" if kind else "jpg"}')
                if not there(name):
                    data, _ = get(url, timeout=300)
                    if data:
                        save(name, data); got += len(data)
                    else:
                        whole = False
        if too_big:
            with open(os.path.join(root, 'telegram', 'too-big-for-the-web.txt'), 'a') as f:
                f.write(f'https://t.me/{CHANNELS[ch]}/{pid}\n')
        if whole:   # a post with a file that wouldn't come is tried again next run
            os.makedirs(folder, exist_ok=True)
            open(os.path.join(folder, '.done'), 'w').close()
        time.sleep(gap / 2)
        return got

    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        for k in range(0, len(rows), 40):
            if stop_at and datetime.datetime.now() >= stop_at:
                print('  time to stop for tonight'); return False
            for got in pool.map(one, rows[k:k + 40]):
                p.tick(got)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--to', help="where to save (default: Google Drive, My Drive/Bapa's Archive)")
    ap.add_argument('--until', help='stop at this time, e.g. 07:00')
    ap.add_argument('--only', choices=('baps', 'telegram'))
    ap.add_argument('--gap', type=float, default=2.0, help='seconds between files (default 2)')
    ap.add_argument('--check', action='store_true', help='only count what is saved (check.txt), download nothing')
    ap.add_argument('--years', help='baps.org photos of these years only, e.g. 2025,2026 (GitHub runs several at once)')
    ap.add_argument('--have', help='list of files already saved elsewhere (rclone lsf -R), skipped')
    ap.add_argument('--hook', help='command run every 1,500 files, e.g. an rclone move into Drive')
    ap.add_argument('--notes', help='where to list the photos baps.org refused (default photos/missing.txt)')
    ap.add_argument('--hours', type=float, help='stop after this many hours')
    a = ap.parse_args()
    if a.have:
        HAVE.update(l.rstrip('\n') for l in open(a.have, encoding='utf-8') if l.strip())
        print(f'{len(HAVE):,} files already saved')
    HOOK['cmd'] = a.hook

    root = a.to
    if not root:
        drive = drive_folder()
        if not drive:
            sys.exit('Google Drive for desktop was not found. Install it, sign in, set it to "Stream files", then run this again '
                     '(or pass --to with any folder).')
        root = os.path.join(drive, "Bapa's Archive")
    os.makedirs(root, exist_ok=True)
    ROOT[0] = root
    print('Saving into', root)

    db_path = os.path.join(root, 'bapas.db')
    try:   # the newest database every run (it is rebuilt every Sunday with the new days)
        print('Fetching the newest database (about 10 MB)...')
        body, _ = get(DB_URL, timeout=300)
        save(db_path, gzip.decompress(body))
    except Exception as e:
        if not os.path.exists(db_path):
            sys.exit(f'Could not fetch the database: {e}')
        print('  could not fetch it, using the copy from last time')
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
    if a.hours:
        stop_at = datetime.datetime.now() + datetime.timedelta(hours=a.hours)

    if a.check:
        return check(db, root)
    finished = True
    try:
        print('Writing the captions beside the photos (captions.csv, post.txt)...')
        years = a.years and {int(y) for y in a.years.split(',')}
        write_captions(db, root, years, a.only != 'telegram', a.only != 'baps')
        if a.only != 'baps':
            finished = telegram(db, root, a.gap, stop_at) and finished
        if a.only != 'telegram':
            finished = baps_photos(db, root, a.gap, stop_at, years, a.notes) and finished
        print('All done for now. Run it again any time: it only fetches what is new or missing.' if finished else
              'Stopped for now. Run it again and it carries on where it left off.')
    except SlowDown as e:
        finished = False
        print(f'\nStopped: {e}. That means "please slow down", so it is finished for tonight. Run it again tomorrow night.')
    except KeyboardInterrupt:
        finished = False
        print('\nStopped. Run it again any time and it carries on where it left off.')
    hand_over()
    if a.hook:   # on GitHub the count is made once every run has handed its files to Drive
        sys.exit(0 if finished else 3)
    print('Counting what is saved...')
    check(db, root)


if __name__ == '__main__':
    main()
