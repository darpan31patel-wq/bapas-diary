"""Web sized photos for the website bapas-diary.com, into Cloudflare R2 (Darpan, 23 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs on GitHub (.github/workflows/website-photos.yml):

    python3 tools/web_photos.py --db bapas.db --years 1999 2012 --out web --have have.txt

For every baps.org photo of those years it saves two files, named by album and file so the pages can find them:
  web/s/ALBUM/FILE   small, 480 px wide, for search results and thumbnails
  web/m/ALBUM/FILE   medium, the baps.org web size as it is (up to 1200 px), for the big view
The workflow sends web/ to R2 every --every files and empties it. Photos already in R2 (--have) are skipped, so a
stopped run carries on. Gentle like archive_download.py: one file at a time with a pause, and it stops for the
night if baps.org shows its "Just a moment" check (never tries to get round it).
"""
import argparse, io, os, sqlite3, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive_download import SITE, SlowDown, get   # same polite fetch as the Drive archive
from PIL import Image

SMALL = 480


def small(body):
    im = Image.open(io.BytesIO(body))
    im = im.convert('RGB')
    if im.width > SMALL:
        im = im.resize((SMALL, round(im.height * SMALL / im.width)), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, 'JPEG', quality=78, optimize=True, progressive=True)
    return out.getvalue()


def save(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(body)


def quiet_now():
    # The daily 2pm picture fetches from baps.org at 05:15 and 06:15 UTC; never compete with it.
    t = time.gmtime()
    return 4 * 60 + 30 <= t.tm_hour * 60 + t.tm_min < 7 * 60 + 30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--years', nargs='+', type=int, required=True)
    ap.add_argument('--out', default='web')
    ap.add_argument('--have', help='keys already in R2, one per line (s/ALBUM/FILE)')
    ap.add_argument('--send', help='command that sends --out to R2 and empties it')
    ap.add_argument('--every', type=int, default=500)
    ap.add_argument('--gap', type=float, default=2.0, help='seconds between files')
    ap.add_argument('--minutes', type=float, default=330, help='stop after this long')
    a = ap.parse_args()
    have = set(open(a.have).read().split()) if a.have and os.path.exists(a.have) else set()
    end = time.time() + a.minutes * 60
    db = sqlite3.connect(a.db)
    q = 'SELECT DISTINCT album, file FROM photos WHERE year IN (%s) ORDER BY year, album, file' % ','.join('?' * len(a.years))
    todo = [(al, f) for al, f in db.execute(q, a.years) if f's/{al}/{f}' not in have]
    print(f'{len(todo)} photos to do for {a.years} ({len(have)} already in R2)', flush=True)
    made = missing = 0

    def send():
        if a.send:
            subprocess.run(a.send, shell=True, check=True)

    try:
        for i, (album, file) in enumerate(todo):
            if time.time() > end:
                print('Out of time for this run; the next run carries on.')
                break
            if quiet_now():
                print('Stopping: 04:30 to 07:30 UTC is kept free for the daily picture\'s baps.org fetches.')
                break
            body, _ = get(SITE.format(album=album, size='WebImages', file=file))
            if body:
                try:
                    s = small(body)
                except Exception as e:   # not a picture after all
                    print(f'  not a picture: {album}/{file}: {e}')
                    missing += 1
                    continue
                save(os.path.join(a.out, 'm', album, file), body)
                save(os.path.join(a.out, 's', album, file), s)
                made += 1
                if made % a.every == 0:
                    send()
                    print(f'  {i + 1} of {len(todo)}: {made} sent, {missing} missing', flush=True)
            else:
                missing += 1
            time.sleep(a.gap)
    except SlowDown as e:
        print(f'Stopping for now: {e}')
    finally:
        send()
    print(f'Done: {made} photos sent to R2, {missing} missing on baps.org')


if __name__ == '__main__':
    main()
