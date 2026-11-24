"""Every photo at the highest resolution there is, from the Drive archive into Cloudflare R2 (Darpan, 24 Oct 2026:
"I just want the highest res").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org. Runs on GitHub
(.github/workflows/website-hires.yml), which starts it by itself every few hours:

    python3 tools/hires_photos.py --db bapas.db --check check.txt --done done.txt --have have.txt

check.txt is the Drive archive's own count (release `database`). A year is copied once the archive has every photo of
it ("to fetch" 0). The Drive copy is the biggest baps.org gives: the photographer's original for 1999 and 2022 on (up
to 5472 px), the web size otherwise. For each photo, named by album and file like the pages expect:
  o/ALBUM/FILE   the original exactly as saved, for zooming in
  l/ALBUM/FILE   up to 2560 px, sharp full screen that still opens fast
  m/ALBUM/FILE   up to 1200 px, the big view
  s/ALBUM/FILE   480 px wide, search results and thumbnails
  t/ALBUM/FILE   short side 240 px, the Calendar's day squares
1999 is done first (it is on the site already, from the smaller baps.org copies), then the newest years.
When a year is finished it is added to years.txt in R2, which the website build reads.
"""
import argparse, io, os, re, shutil, subprocess, sys, time
from concurrent.futures import ProcessPoolExecutor
import sqlite3
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None   # originals are big on purpose
SIZES = (('l', 2560, 86), ('m', 1200, 82))   # longest side, JPEG quality
SMALL = 480


def quiet_now():
    # 04:30 to 07:30 UTC stays free for the daily picture's morning run (coordinator, 23 Oct 2026).
    t = time.gmtime()
    return 4 * 60 + 30 <= t.tm_hour * 60 + t.tm_min < 7 * 60 + 30


def ready_years(check):
    """Years the Drive archive has finished, from the table in check.txt."""
    out = []
    for line in open(check):
        m = re.match(r'(\d{4})\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+([\d,]+)\s*$', line)
        if m and m.group(2).replace(',', '') == '0':
            out.append(int(m.group(1)))
    return out


def jpeg(im, q):
    b = io.BytesIO()
    im.save(b, 'JPEG', quality=q, optimize=True, progressive=True)
    return b.getvalue()


def make(job):
    """One photo: the original plus the three smaller copies. Returns None when it worked."""
    src, out, key = job
    try:
        body = open(src, 'rb').read()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(body))).convert('RGB')
        files = {'o': body}
        for tier, side, q in SIZES:
            c = im.copy()
            if max(c.size) > side:
                c.thumbnail((side, side), Image.LANCZOS)
            files[tier] = jpeg(c, q)
        c = im.copy()
        if c.width > SMALL:
            c = c.resize((SMALL, round(c.height * SMALL / c.width)), Image.LANCZOS)
        files['s'] = jpeg(c, 78)
        # t/: the tiny copy for the Calendar's day squares, short side 240 px (website review, 28 Oct 2026). JPEG here,
        # because the send command marks everything image/jpeg; the first 264,608 were made as WebP by website-tiny.yml
        c = c.copy()
        k = 240 / min(c.size)
        if k < 1:
            c = c.resize((max(1, round(c.width * k)), max(1, round(c.height * k))), Image.LANCZOS)
        files['t'] = jpeg(c, 72)
        for tier, data in files.items():
            path = os.path.join(out, tier, key)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
    except Exception as e:
        return f'{key}: {e}'


def send(cmd, out):
    """Send OUT to R2. R2 sometimes says 'reduce your request rate' for a moment, so wait and try again (sync only
    sends what is not there yet)."""
    for wait in (10, 30, 90, 240, 0):
        env = {'AWS_RETRY_MODE': 'adaptive', 'AWS_MAX_ATTEMPTS': '8', **os.environ, 'OUT': out}
        if subprocess.run(cmd, shell=True, env=env).returncode == 0:
            return True
        if wait:
            print(f'  R2 did not take every file, trying again in {wait} s', flush=True)
            time.sleep(wait)
    return False


def redo(db, have, todo, done):
    """Photos whose full size copy reached R2 but whose smaller copies did not (Darpan, 19 Nov 2026: 901 News photos
    showed as empty tiles). tools/hires_redo.txt lists ALBUM/FILE, one per line. Any whose 480 px copy is still missing
    is made again from Drive: it is taken out of have, and its year goes back on the to do list. Returns the years that
    are on the list only for these photos, so they are not marked finished when they are not."""
    import urllib.parse, urllib.request
    from concurrent.futures import ThreadPoolExecutor
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hires_redo.txt')
    if not os.path.exists(path):
        return set()
    keys = [l.strip() for l in open(path, encoding='utf-8') if '/' in l.strip()]

    def missing(k):
        al, f = k.split('/', 1)
        url = f'https://photos.bapas-diary.com/s/{al}/{urllib.parse.quote(f)}'
        for _ in range(3):
            try:
                req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'bapas-diary-build'})
                with urllib.request.urlopen(req, timeout=20):
                    return False
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return True
            except Exception:
                pass
        return False   # could not tell: leave it for the next run

    with ThreadPoolExecutor(16) as ex:
        again = [k for k, m in zip(keys, ex.map(missing, keys)) if m]
    years = set()
    for k in again:
        have.discard(f'o/{k}')
        al, f = k.split('/', 1)
        r = db.execute('SELECT year FROM photos WHERE album = ? AND file = ?', (al, f)).fetchone()
        if r and r[0]:
            years.add(r[0])
    print(f'Smaller copies missing for {len(again)} of {len(keys)} listed photos; making them again ({sorted(years)})',
          flush=True)
    keep = {y for y in years if y not in todo and y not in done}   # not finished in Drive yet: never mark it done
    todo[:0] = [y for y in sorted(years) if y not in todo]
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--check', default='check.txt', help="the Drive archive's check.txt")
    ap.add_argument('--done', default='done.txt', help='years already finished, one per line (years.txt from R2)')
    ap.add_argument('--have', default='have.txt', help='o/ALBUM/FILE keys already in R2')
    ap.add_argument('--remote', default="gdrive:Bapa's Archive")
    ap.add_argument('--work', default='work')
    ap.add_argument('--send', required=True, help='command that sends WORK/out to R2 (tried again if it fails)')
    ap.add_argument('--year-done', required=True, help='command run with YEAR set when a year is finished')
    ap.add_argument('--chunk', type=int, default=400)
    ap.add_argument('--minutes', type=float, default=320)
    ap.add_argument('--shard', type=int, default=0, help='this machine, counted from 0 (Darpan, 25 Oct: 6 machines at once)')
    ap.add_argument('--shards', type=int, default=1, help='how many machines share the years')
    ap.add_argument('--years', default='', help='only these years, comma separated (website-hires-boost.yml)')
    ap.add_argument('--part', type=int, default=0, help='this machine when many share the same years photo by photo')
    ap.add_argument('--parts', type=int, default=1, help='how many machines share each year photo by photo')
    ap.add_argument('--reverse', action='store_true', help='last photos first, so a helper meets the main run halfway')
    a = ap.parse_args()
    end = time.time() + a.minutes * 60
    done = {int(l) for l in open(a.done).read().split() if l.isdigit()} if os.path.exists(a.done) else set()
    have = set(open(a.have).read().split('\n')) if os.path.exists(a.have) else set()
    ready = ready_years(a.check)
    todo = [y for y in sorted(ready, key=lambda y: (y != 1999, -y)) if y not in done]
    db = sqlite3.connect(a.db)
    if a.shards > 1:
        # every machine works out the same split from the database alone, so no year is done twice or missed:
        # the biggest years first, each to the machine with the fewest photos so far
        size = dict(db.execute('SELECT year, COUNT(*) FROM photos GROUP BY year'))
        load, mine = [0] * a.shards, []
        for y in sorted(ready, key=lambda y: (-size.get(y, 0), y)):
            k = load.index(min(load))
            load[k] += size.get(y, 0)
            if k == a.shard:
                mine.append(y)
        todo = [y for y in todo if y in mine]
    if a.years:
        todo = [y for y in todo if str(y) in a.years.split(',')]
    keep = set()
    if a.shard == 0 and a.part == 0 and not a.years:
        keep = redo(db, have, todo, done)
    print(f'Drive archive finished: {sorted(ready)}; already in R2 at full size: {sorted(done)}; to do now: {todo}', flush=True)
    inbox, out = os.path.join(a.work, 'in'), os.path.join(a.work, 'out')
    with ProcessPoolExecutor() as pool:
        for year in todo:
            rows = [(al, f, rel) for al, f, rel in db.execute(
                'SELECT album, file, local_path FROM photos WHERE year = ? ORDER BY album, file', (year,))
                if f'o/{al}/{f}' not in have][a.part::a.parts]
            if a.reverse:
                rows.reverse()
            print(f'{year}: {len(rows):,} photos to copy', flush=True)
            lost = 0
            for i in range(0, len(rows), a.chunk):
                if time.time() > end or quiet_now():
                    print('Stopping for now (out of time, or 04:30 to 07:30 UTC); the next run carries on.')
                    return
                part = rows[i:i + a.chunk]
                shutil.rmtree(a.work, ignore_errors=True)
                os.makedirs(inbox)
                with open(os.path.join(a.work, 'list.txt'), 'w') as f:
                    f.write('\n'.join(rel for _, _, rel in part) + '\n')
                subprocess.run(['rclone', 'copy', a.remote, inbox, '--files-from-raw', os.path.join(a.work, 'list.txt'),
                                '--transfers', '8', '--checkers', '8', '--ignore-errors'], check=False)
                jobs = [(os.path.join(inbox, rel), out, f'{al}/{f}') for al, f, rel in part if os.path.exists(os.path.join(inbox, rel))]
                for err in pool.map(make, jobs, chunksize=8):
                    if err:
                        print('  could not use', err)
                lost += len(part) - len(jobs)
                if jobs and not send(a.send, out):   # R2 still saying no after a few tries: count them as not done yet
                    lost += len(jobs)
                print(f'  {year}: {min(i + a.chunk, len(rows)):,} of {len(rows):,} ({len(part) - len(jobs)} not in Drive)', flush=True)
            if lost > max(20, len(rows) // 50):   # more than baps.org ever refused: Drive was not answering, try again next run
                print(f'{year}: {lost} photos did not come from Drive; the next run tries them again')
                continue
            if year in keep:   # only a few photos made again, the year itself is not finished yet
                print(f'{year}: photos made again', flush=True)
                continue
            subprocess.run(a.year_done, shell=True, check=True, env={**os.environ, 'YEAR': str(year)})
            print(f'{year} finished', flush=True)
    shutil.rmtree(a.work, ignore_errors=True)


if __name__ == '__main__':
    main()
