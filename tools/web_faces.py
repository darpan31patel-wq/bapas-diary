"""Bapa's photos for the website's Bapa pages, chosen by Darpan's face rules (Darpan, 25 Oct 2026: the rules the On this
day picture uses, so Today, Calendar and share a day show only photos where Bapa is recognised, best darshan first).

Website only: nothing here touches the daily 2pm picture chain and nothing is fetched from baps.org. The photos come
from R2 (photos.bapas-diary.com, the high res copy), one year at a time as each year lands there. Runs on GitHub
(.github/workflows/website-faces.yml), never 04:30 to 07:30 UTC.

    python3 tools/web_faces.py plan --db bapas.db --years years.txt --have have.txt     shards still to look at
    python3 tools/web_faces.py scan --db bapas.db --shard 2026-0-12 --out face2-2026-0-12.json.gz
    python3 tools/web_faces.py pick --db bapas.db --faces faces --out bapa.db --top bapa-top.db
    python3 tools/web_faces.py order --db bapa.db --day out/data/day                  best darshan first on Today
    python3 tools/web_faces.py mockup --old bapas.db --db bapa.db --days 10-25 --out mockup

scan keeps, for every photo, Bapa's best face: {"ALBUM/FILE": [similarity, x, y, w, h, front, sharp, bright, W, H, faces, other]}
(other: that face's score against the other guru, which must be lower)
(x, y, w, h as parts of the photo's width and height, W and H the size of the m/ copy that was looked at).

pick writes bapa.db: the database with only the photos of Bapa the rules keep, and table bapa_pick (album, file, rank,
fx, fy, close) giving each photo's place in its year on its day (0 is the darshan shown first) and where his face is.
bapa-top.db keeps just the first photo of each year on each day, for the pages that show one photo (Calendar, share a
day). Years not yet in R2 keep the caption based choice (is_bapa = 1) until their faces have been looked at.
"""
import argparse, datetime, gzip, io, json, os, re, sqlite3, shutil, sys, time, urllib.parse, urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
import web_bapa_rules as R

PHOTOS = 'https://photos.bapas-diary.com/'
ASPECT = .69     # the frame make.py judges an action shot against (its tall cards)
PREFIX = 'face2-'   # the shard files in release website-faces (face2: also checked against the other guru)
THIN_DAY = 5     # fewer years than this with a recognised photo: the other years keep their caption based photos


def quiet_now():
    # 04:30 to 07:30 UTC stays free for the daily picture's morning run (coordinator, 23 Oct 2026).
    t = time.gmtime()
    return 4 * 60 + 30 <= t.tm_hour * 60 + t.tm_min < 7 * 60 + 30


def wait_quiet():
    while quiet_now():
        print('04:30 to 07:30 UTC: waiting for the daily picture to finish', flush=True)
        time.sleep(300)


def plan(a):
    """The shards still to do: every year in R2 cut into pieces of about --size photos, minus those already kept."""
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    have = set(open(a.have).read().split()) if a.have and os.path.exists(a.have) else set()
    db = sqlite3.connect(a.db)
    todo = []
    for y in years:
        n = db.execute('SELECT count(*) FROM photos WHERE year = ?', (y,)).fetchone()[0]
        parts = max(1, -(-n // a.size))
        todo += [f'{y}-{i}-{parts}' for i in range(parts) if f'{PREFIX}{y}-{i}-{parts}.json.gz' not in have]
    print(json.dumps(todo[:a.max]))


def look(job):
    """One photo: Bapa's best face in it, by make.py's face check."""
    key, when, body = job
    try:
        from PIL import Image
        cv2.setNumThreads(1)   # one photo per process already uses every core
        im = Image.open(io.BytesIO(body)).convert('RGB')
        face, sim, front, n, other = R.bapa_face(im, when)
        if not face:
            return key, [0, 0, 0, 0, 0, 0, 0, 0, im.width, im.height, n, 0]
        sharp, bright = R.face_quality(im, face)
        x, y, w, h = face
        W, H = im.size
        return key, [round(sim, 3), round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4), round(front, 2),
                     round(sharp), round(bright), W, H, n, round(other, 3)]
    except Exception as e:
        print(key, e, flush=True)
        return key, None


def scan(a):
    """Look at every photo of one shard (YEAR-I-N, the I-th of N slices of that year) from R2's m/ copies."""
    y, i, n = map(int, a.shard.split('-'))
    db = sqlite3.connect(a.db)
    rows = db.execute("SELECT album, file, coalesce(date, date_from, year || '-07-01') FROM photos WHERE year = ? "
                      'ORDER BY album, file', (y,)).fetchall()
    k = -(-len(rows) // n)
    rows = rows[i * k:(i + 1) * k]
    print(f'{a.shard}: {len(rows)} photos', flush=True)

    def get(r):
        key = f'{r[0]}/{r[1]}'
        for wait in (2, 10, 30, 0):
            try:
                req = urllib.request.Request(PHOTOS + a.tier + '/' + urllib.parse.quote(key), headers={'User-Agent': 'bapas-diary-faces'})
                return key, r[2], urllib.request.urlopen(req, timeout=30).read()
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
            except Exception:
                pass
            time.sleep(wait)
        return key, r[2], None

    out, missing, t0 = {}, 0, time.time()
    with ThreadPoolExecutor(16) as net, ProcessPoolExecutor(os.cpu_count()) as cpu:
        for s in range(0, len(rows), 400):
            wait_quiet()
            got = list(net.map(get, rows[s:s + 400]))
            missing += sum(1 for g in got if g[2] is None)
            for key, rec in cpu.map(look, [g for g in got if g[2]], chunksize=8):
                if rec:
                    out[key] = rec
            print(f'  {s + len(got)} of {len(rows)}, {sum(1 for v in out.values() if v[0] >= R.SAME_PERSON)} with Bapa, '
                  f'{missing} not in R2, {time.time() - t0:.0f}s', flush=True)
    with gzip.open(a.out, 'wt') as f:
        json.dump(out, f, separators=(',', ':'))


def load_faces(folder):
    faces = {}
    for f in sorted(os.listdir(folder)):
        if f.startswith(PREFIX) and f.endswith('.json.gz'):
            faces.update(json.load(gzip.open(os.path.join(folder, f), 'rt')))
    return faces


def judge(c, rec):
    """make.py's two scores for one recognised photo: (close darshan score, action shot score, nice, special, close_ok)."""
    sim, x, y, w, h, front, sharp, bright, W, H = rec[:10]
    r = h
    keep = R.frame_keep(W, H, ASPECT)
    cap = R.caption({'c': c})
    special = R.is_special(c)
    subject = R.bapa_is_subject(c)
    doing = bool(R.DOING.search(c)) and not R.JUST_A_FACE.search(c)
    close_ok = h * H >= R.CLOSE_MIN_FACE and front >= .35 and sharp >= R.SHARP_MIN and bright >= R.BRIGHT_MIN
    s_close = 1 + min(r, .35) + sim + (.2 if R.JUST_A_FACE.search(c) else 0) + .9 * (front - .6)
    s_close -= (.6 if not subject else 0) + (1.5 if not close_ok else 0) + (.4 if cap == R.DARSHAN else 0)
    s_doing = (1 + sim + .6 * max(0, 1 - abs(r - .18) / .15) + (.4 if doing else 0) + (.3 if special else 0)
               - (.5 if r < .1 else 0) - (.6 if not subject else 0)
               - (0 if keep >= R.ACTION_KEEP else (.3 if special else 1.5)))
    soft = .5 * max(0, 1 - sharp / (2 * R.SHARP_MIN)) + .5 * max(0, 1 - bright / (1.5 * R.BRIGHT_MIN))
    s_close -= soft
    s_doing -= soft + R.SIDE_LOSS * max(0, R.SIDE_FRONT - front) / R.SIDE_FRONT
    if R.GUEST.search(cap) and not R.western(c):   # meeting or honouring guests loses, unless a western guest
        s_close -= 2.5; s_doing -= 2.5
    nice = front >= R.SIDE_FRONT and doing and subject and r >= .13 and (keep >= R.ACTION_KEEP or special) and s_doing >= 2.0
    return s_close, s_doing, nice, special, close_ok


ERA_NAMES = {True: (r'Pramukh Swami|Swamishri|\bBapa\b|\bHDH\b', r'Mahant Swami'),    # (this Bapa, the other guru)
             False: (r'Mahant Swami|Swamishri|\bBapa\b|\bHDH\b', r'Pramukh Swami')}


def other_guru(db):
    """Photos of the other guru, by caption, which the face check can't always tell apart: in 1999 Mahant Swami Maharaj,
    then on his own travels (Africa, Israel), scores up to .8 against Pramukh Swami Maharaj's fingerprint and only .3
    against his own, which is made from photos of him today. A photo is the other guru's when its caption names him and
    not that day's Bapa, or when it is in an album whose captions name the other guru more often than Bapa (so the
    album's 'Performs the arti' photos go too), unless its own caption names Bapa."""
    albums, rows = {}, []
    for al, fi, cap, d in db.execute('SELECT album, file, caption, coalesce(date, date_from) FROM photos'):
        this, that = ERA_NAMES[(d or '') < R.PSM_UNTIL]
        c = cap or ''
        mine, theirs = bool(re.search(this, c)), bool(re.search(that, c)) and not re.search(that + r"(?: Maharaj)?(?:'s|’s)? (?:murti|portrait|photo|image)", c)
        n = albums.setdefault(al, [0, 0])
        n[0] += mine; n[1] += theirs
        rows.append((al, fi, mine, theirs))
    return {(al, fi) for al, fi, mine, theirs in rows
            if not mine and (theirs or albums[al][1] > albums[al][0])}


def pick(a):
    faces = load_faces(a.faces)
    scanned = {int(f[len(PREFIX):].split('-')[0]) for f in os.listdir(a.faces) if f.startswith(PREFIX)}
    src = sqlite3.connect(a.db)
    pins = json.load(open(os.path.join(R.HERE, 'archive', 'picks.json'))) if os.path.exists(os.path.join(R.HERE, 'archive', 'picks.json')) else {}
    diary = {}
    for date, url in src.execute('SELECT date, photo_url FROM diary WHERE photo_url IS NOT NULL'):
        diary[(url.split('/GalleryImages/')[-1].split('/')[0], url.rsplit('/', 1)[-1])] = date
    groups = {}   # (date or 'trip|from|to', year) -> [(album, file, caption, is_bapa, date_from)]
    for y, date, d0, d1, album, file, cap, bapa in src.execute(
            'SELECT year, date, date_from, date_to, album, file, caption, is_bapa FROM photos'):
        g = date or f'trip|{d0}|{d1}'
        groups.setdefault((g, y), []).append((album, file, cap or '', bapa or 0, d0))
    other = other_guru(src)

    def seen(al, fi):   # Bapa recognised by face, in a photo that isn't of the other guru
        return faces.get(f'{al}/{fi}', [0])[0] >= R.SAME_PERSON and (al, fi) not in other

    keep, why = {}, {'recognised': 0, 'pin': 0, 'caption only (year not in R2 yet)': 0, 'caption only (thin day)': 0}
    by_day = {}
    for (g, y), rows in groups.items():
        if g[:4] != 'trip':
            by_day.setdefault(g[5:], set())
            if y in scanned and any(seen(r[0], r[1]) for r in rows):
                by_day[g[5:]].add(y)
    for (g, y), rows in groups.items():
        mmdd = g[5:] if g[:4] != 'trip' else None
        want = pins.get(mmdd, {}).get(str(y)) if mmdd else None
        ranked = []
        for al, fi, c, bapa, d0 in rows:
            rec = faces.get(f'{al}/{fi}')
            pinned = (al, fi) in diary or (isinstance(want, str) and want.lower() in c.lower())
            if R.JUNK.search(c) and not pinned:   # website link text, not a photo of the day
                continue
            if (al, fi) in other and not pinned:
                continue
            if seen(al, fi):
                sc, sd, nice, special, close_ok = judge(c, rec)
                ranked.append(dict(k=(al, fi), c=c, sc=sc, sd=sd, nice=nice, special=special, close=close_ok, rec=rec, pin=pinned, why='recognised'))
            elif pinned:
                ranked.append(dict(k=(al, fi), c=c, sc=-5, sd=-5, nice=False, special=False, close=False, rec=rec, pin=True, why='pin'))
            elif bapa == 1 and (y not in scanned or rec is None):
                ranked.append(dict(k=(al, fi), c=c, sc=-9, sd=-9, nice=False, special=False, close=False, rec=None, pin=False, why='caption only (year not in R2 yet)'))
            elif bapa == 1 and mmdd and len(by_day.get(mmdd, ())) < THIN_DAY:
                ranked.append(dict(k=(al, fi), c=c, sc=-9, sd=-9, nice=False, special=False, close=False, rec=None, pin=False, why='caption only (thin day)'))
        if any(v['why'] == 'recognised' for v in ranked):   # recognised photos come first: then nothing unrecognised but pins
            ranked = [v for v in ranked if v['why'] in ('recognised', 'pin')]
        if not ranked:
            continue
        action = any(v['nice'] and v['special'] for v in ranked)   # a close darshan, unless a special action shot
        ranked.sort(key=lambda v: (not v['pin'], not (action and v['nice'] and v['special']), -(v['sd'] if action and v['nice'] and v['special'] else v['sc'])))
        for n, v in enumerate(ranked):
            v['rank'] = n
            keep[v['k']] = (g, y, v)
            why[v['why']] += 1

    # one photo per year per day for Calendar and share a day: the first, but no two years on a day with the same caption
    top = set()
    days = {}
    for k, (g, y, v) in keep.items():
        days.setdefault(g[5:] if g[:4] != 'trip' else g, {}).setdefault((g, y), []).append(v)
    for d, ys in days.items():
        used = []
        for gy in sorted(ys):
            vs = sorted(ys[gy], key=lambda v: v['rank'])
            choice = next((v for v in vs if v['pin']), None) or next(
                (v for v in vs if not any(R.same_caption(R.caption_key(R.caption({'c': v['c']})), u) for u in used)), vs[0])
            used.append(R.caption_key(R.caption({'c': choice['c']})))
            top.add(choice['k'])

    for out, only in ((a.out, None), (a.top, top)):
        if not out:
            continue
        if os.path.exists(out):
            os.remove(out)
        src.execute('VACUUM INTO ?', (out,))
        db = sqlite3.connect(out)
        db.execute('CREATE TEMP TABLE k (album TEXT, file TEXT, PRIMARY KEY (album, file))')
        db.executemany('INSERT INTO k VALUES (?, ?)', [k for k in keep if only is None or k in only])
        db.execute('DELETE FROM photos WHERE NOT EXISTS (SELECT 1 FROM k WHERE k.album = photos.album AND k.file = photos.file)')
        db.execute('UPDATE photos SET is_bapa = 1')
        db.execute('CREATE TABLE bapa_pick (album TEXT, file TEXT, rank INTEGER, fx REAL, fy REAL, close INTEGER, sim REAL, why TEXT, '
                   'PRIMARY KEY (album, file))')
        db.executemany('INSERT INTO bapa_pick VALUES (?, ?, ?, ?, ?, ?, ?, ?)', [
            (k[0], k[1], v['rank'], round(v['rec'][1] + v['rec'][3] / 2, 3) if v['rec'] and v['rec'][0] else None,
             round(v['rec'][2] + v['rec'][4] / 2, 3) if v['rec'] and v['rec'][0] else None, int(v['close']),
             v['rec'][0] if v['rec'] else None, v['why']) for k, (g, y, v) in keep.items() if only is None or k in only])
        db.commit()
        db.execute('VACUUM')
        n = db.execute('SELECT count(*) FROM photos').fetchone()[0]
        print(f'{out}: {n} photos')
    print('years with faces looked at:', ' '.join(map(str, sorted(scanned))) or 'none yet')
    print('kept:', json.dumps(why))


def order(a):
    """Today's cards open on the best darshan: each year's photos in pick order, with where his face is (p[4])."""
    db = sqlite3.connect(a.db)
    rank = {(al, fi): (r, fx, fy) for al, fi, r, fx, fy in db.execute('SELECT album, file, rank, fx, fy FROM bapa_pick')}
    n = 0
    for f in sorted(os.listdir(a.day)):
        if not f.endswith('.json'):
            continue
        path = os.path.join(a.day, f)
        data = json.load(open(path, encoding='utf-8'))
        for Y in data.get('years', []):
            for part in ('p', 't'):
                ps = Y.get(part)
                if not ps:
                    continue
                ps.sort(key=lambda p: rank.get((p[0], p[1]), (9999,))[0])
                for p in ps:
                    r = rank.get((p[0], p[1]))
                    if r and r[1] is not None and len(p) == 4:
                        p.append([r[1], r[2]])
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
        n += 1
    print(f'{n} days put in pick order')


def mockup(a):
    """Before and after, for a few days: for each year in R2 (--years), the first photos its Today card shows now
    (the caption says Bapa, album order, the 2pm picture's photo first) and with the face rules, from R2's small copies."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    years = {int(l) for l in open(a.years) if l.strip().isdigit()}
    old, new = sqlite3.connect(a.old), sqlite3.connect(a.db)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    mid = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 21)
    os.makedirs(a.out, exist_ok=True)
    N, CW, CH, GAP = 6, 200, 250, 12

    def photo(key, focus=None):
        try:
            req = urllib.request.Request(PHOTOS + 's/' + urllib.parse.quote(key), headers={'User-Agent': 'bapas-diary-faces'})
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read()))).convert('RGB')
        except Exception:
            return Image.new('RGB', (CW, CH), (60, 40, 40))
        return ImageOps.fit(im, (CW, CH), Image.LANCZOS, centering=focus or (.5, .28))

    summary = {}
    for mmdd in a.days:
        strips = []
        for y in sorted(years):
            d = old.execute('SELECT photo_url FROM diary WHERE date = ?', (f'{y}-{mmdd}',)).fetchone()
            first = (d[0].split('/GalleryImages/')[-1].split('/')[0], d[0].rsplit('/', 1)[-1]) if d and d[0] else None
            b = [(al, fi, c or '', None) for al, fi, c in old.execute(
                'SELECT album, file, caption FROM photos WHERE date = ? AND is_bapa = 1 ORDER BY album, file', (f'{y}-{mmdd}',))]
            b.sort(key=lambda p: (p[0], p[1]) != first)
            n_all = old.execute('SELECT count(*) FROM photos WHERE date = ?', (f'{y}-{mmdd}',)).fetchone()[0]
            f = [(al, fi, c or '', (fx, min(1, fy * 1.15)) if fx is not None else None) for al, fi, c, fx, fy in new.execute(
                'SELECT p.album, p.file, p.caption, b.fx, b.fy FROM photos p JOIN bapa_pick b USING (album, file) '
                'WHERE p.date = ? ORDER BY b.rank', (f'{y}-{mmdd}',))]
            if not b and not f:
                continue
            strips.append((y, n_all, b, f))
            summary.setdefault(mmdd, {})[str(y)] = {'photos that day': n_all, 'now': len(b), 'face rules': len(f)}
        if not strips:
            continue
        W = 230 + N * (CW + GAP) + 30
        rowh = CH + 60
        sheet = Image.new('RGB', (W, 110 + len(strips) * (2 * rowh + 50)), (250, 244, 232))
        dr = ImageDraw.Draw(sheet)
        title = datetime.date(2000, int(mmdd[:2]), int(mmdd[3:])).strftime('%-d %B')
        dr.text((30, 30), f'{title} on Today: the photos each year shows first', font=bold, fill=(90, 20, 30))
        top = 100
        for y, n_all, b, f in strips:
            dr.text((30, top + 10), str(y), font=bold, fill=(90, 20, 30))
            dr.text((30, top + 52), f'{n_all} photos\nthat day', font=font, fill=(120, 90, 80))
            for k, (lst, label) in enumerate(((b, f'Now: {len(b)} photos (caption says Bapa)'),
                                              (f, f'With the face rules: {len(f)} photos (Bapa\'s face recognised)'))):
                y0 = top + k * rowh
                dr.text((230, y0), label, font=mid, fill=(150, 40, 40) if k == 0 else (40, 110, 60))
                for i, (al, fi, c, focus) in enumerate(lst[:N]):
                    x0 = 230 + i * (CW + GAP)
                    sheet.paste(photo(f'{al}/{fi}', focus), (x0, y0 + 30))
                    cap = R.caption({'c': c}) or ''
                    dr.text((x0, y0 + 32 + CH), cap[:21] + ('...' if len(cap) > 21 else ''), font=font, fill=(60, 40, 40))
                if not lst:
                    dr.text((240, y0 + 120), 'year left out: Bapa not recognised in any photo', font=font, fill=(120, 90, 80))
            top += 2 * rowh + 50
        sheet.save(os.path.join(a.out, f'{mmdd}.jpg'), quality=84)
        print(mmdd, json.dumps(summary[mmdd]))
    json.dump(summary, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan'); p.add_argument('--db', required=True); p.add_argument('--years', required=True)
    p.add_argument('--have'); p.add_argument('--size', type=int, default=2500); p.add_argument('--max', type=int, default=200)
    p = sub.add_parser('scan'); p.add_argument('--db', required=True); p.add_argument('--shard', required=True)
    p.add_argument('--out', required=True); p.add_argument('--tier', default='m')
    p = sub.add_parser('pick'); p.add_argument('--db', required=True); p.add_argument('--faces', required=True)
    p.add_argument('--out', required=True); p.add_argument('--top')
    p = sub.add_parser('order'); p.add_argument('--db', required=True); p.add_argument('--day', required=True)
    p = sub.add_parser('mockup'); p.add_argument('--old', required=True); p.add_argument('--db', required=True)
    p.add_argument('--years', required=True); p.add_argument('--days', nargs='+', required=True); p.add_argument('--out', required=True)
    a = ap.parse_args()
    {'plan': plan, 'scan': scan, 'pick': pick, 'order': order, 'mockup': mockup}[a.cmd](a)


if __name__ == '__main__':
    main()
