"""The murti darshan archive's photos and list (Darpan, 29 Oct 2026: "yes" to the Darshan tab). Website only: nothing here
touches the daily 2pm picture, and it never asks the mandir's site for anything; it only reads the copies already in the
website's own photo store (R2 darshan/YYYYMMDD/code_DD.jpg, saved by darshan_copy.sh).

For every day there that has no small copies yet, it makes two smaller copies of each photo:
    darshan/s/YYYYMMDD/code.jpg   480 px wide, for the day squares
    darshan/m/YYYYMMDD/code.jpg   1600 px wide, for the big photo
reads the day's main colours from the central shrine photo, and writes darshan/archive.js, the list the Darshan page reads:
    window.DARSHAN_DAYS = [{"d": "2026-10-29", "k": ["ddm", "gm", ...], "c": ["Pink", "Red"]}, ...]   (oldest first)
A script file, not JSON, so the page can load it from photos.bapas-diary.com like any picture.

    python3 tools/screensaver/darshan_archive.py [--minutes 8]
Needs aws (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY for R2), R2 (endpoint) and BUCKET, as darshan_copy.sh does.
"""
import argparse, colorsys, json, os, re, subprocess, sys, tempfile, time
from collections import Counter
from PIL import Image

# every photo the mandir posts each morning, in the order the page shows them
CODES = ['ddm', 'ddm_c', 'gm', 'gm_c', 'hkm_c', 'varni', 'bm', 'sm', 'ym', 'psm']
SIZES = {'s': 480, 'm': 1600}
KEY = re.compile(r'^darshan/(\d{8})/([a-z_]+)_(\d\d)\.jpg$')


def aws(*a, capture=False):
    cmd = ['aws', 's3', *a, '--endpoint-url', os.environ['R2']]
    if capture:
        return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    subprocess.run(cmd + ['--only-show-errors'], check=True)


def put(path, key, ctype, cache):
    aws('cp', path, f"s3://{os.environ['BUCKET']}/{key}", '--content-type', ctype, '--cache-control', cache)


# The day's colours: the three murtis' clothes in the central shrine photo, below the garlands. Gold work, skin and the
# dark wood are left out (a strong bright yellow still counts as yellow cloth); the colour that covers most of what is
# left names the day, and the next one too when it covers at least a third as much. Checked by eye against 61 days
# (30 Aug to 29 Oct 2026): the first colour matched 6 days in 10, one of the two 8 in 10.
def colour_name(h, s, v):
    h *= 360
    if s < .16:
        return 'White' if v > .75 else None
    if v < .42 or s < .35:
        return None
    if 30 <= h < 56:
        return 'Yellow' if s > .8 and v > .75 and h >= 44 else None
    if h >= 350 or h < 10:
        return 'Red'
    if h >= 318:
        return 'Pink'
    if h < 30:
        return 'Orange' if s > .6 else None
    if h < 68:
        return 'Yellow'
    if h < 170:
        return 'Green'
    if h < 255:
        return 'Blue'
    if h < 292:
        return 'Purple'
    return 'Pink'


def colours(im):
    w, h = im.size
    c = Counter()
    for p in im.crop((int(w * .12), int(h * .45), int(w * .88), int(h * .82))).resize((90, 90)).getdata():
        k = colour_name(*colorsys.rgb_to_hsv(*(x / 255 for x in p)))
        if k:
            c[k] += .6 if k == 'White' else 1
    top = c.most_common(2)
    if not top:
        return ['White']
    return [top[0][0]] + ([top[1][0]] if len(top) > 1 and top[1][1] >= .35 * top[0][1] else [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--minutes', type=float, default=8, help='stop making copies after this long (the rest wait for the next run)')
    args = ap.parse_args()
    t0 = time.time()
    bucket = os.environ['BUCKET']
    have = set()
    for line in aws('ls', f's3://{bucket}/darshan/', '--recursive', capture=True).splitlines():
        parts = line.split()
        if parts:
            have.add(parts[-1])
    days = {}
    for k in have:
        m = KEY.match(k)
        if m and m[2] in CODES and m[1][6:] == m[3]:
            days.setdefault(m[1], set()).add(m[2])
    work = tempfile.mkdtemp()
    old = {}
    if 'darshan/archive.js' in have:
        aws('cp', f's3://{bucket}/darshan/archive.js', f'{work}/old.js')
        txt = open(f'{work}/old.js', encoding='utf-8').read()
        old = {x['d'].replace('-', ''): x for x in json.loads(txt[txt.index('['):txt.rindex(']') + 1])}
    made = 0
    out = []
    for ymd in sorted(days):
        codes = [c for c in CODES if c in days[ymd]]
        missing = [c for c in codes if f'darshan/s/{ymd}/{c}.jpg' not in have or f'darshan/m/{ymd}/{c}.jpg' not in have]
        col = (old.get(ymd) or {}).get('c')
        if (missing or not col) and time.time() - t0 < args.minutes * 60:
            for c in codes:
                if c not in missing and (col or c != 'ddm'):
                    continue
                src = f'{work}/{c}.jpg'
                aws('cp', f's3://{bucket}/darshan/{ymd}/{c}_{ymd[6:]}.jpg', src)
                im = Image.open(src).convert('RGB')
                if c == 'ddm':
                    col = colours(im)
                if c in missing:
                    for size, px in SIZES.items():
                        t = im.copy()
                        t.thumbnail((px, px * 2), Image.LANCZOS)
                        t.save(f'{work}/{size}.jpg', quality=82 if size == 's' else 86, optimize=True, progressive=True)
                        put(f'{work}/{size}.jpg', f'darshan/{size}/{ymd}/{c}.jpg', 'image/jpeg', 'public, max-age=31536000, immutable')
                    made += 1
                os.remove(src)
            missing = []
        if missing or not col:
            continue   # not ready yet: shown once its small copies are made
        out.append({'d': f'{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}', 'k': codes, 'c': col})
    with open(f'{work}/archive.js', 'w', encoding='utf-8') as f:
        f.write('window.DARSHAN_DAYS=' + json.dumps(out, separators=(',', ':')) + ';\n')
    put(f'{work}/archive.js', 'darshan/archive.js', 'application/javascript', 'public, max-age=600')
    waiting = sum(1 for d in days if d not in {x['d'].replace('-', '') for x in out})
    print(f'::notice::darshan archive: {len(out)} days listed, {made} photos given small copies, {waiting} days still waiting')


if __name__ == '__main__':
    sys.exit(main())
