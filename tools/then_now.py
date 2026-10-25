#!/usr/bin/env python3
"""Same place, then and now: Pramukh Swami Maharaj and Mahant Swami Maharaj at the same mandir doing the same thing,
years apart, side by side (Darpan, 25 Oct 2026: 'Same place, then and now: both Bapas at the same mandir side by
side, years apart. like it!').

Website only (bapas-diary.com). Nothing here touches the daily 2pm picture: it only reads bapas.db and the face models.

    python3 tools/then_now.py --db bapas.db --keys keys.txt --out then-now

--keys is the list of photos in R2 (one m/ALBUM/FILE per line); photos come from R2 only, never baps.org. For every
place in site/then-now.txt and every moment (morning puja, darshan, arti, ...) it takes photos of each guru whose
caption names that moment, finds Bapa in each with YuNet and SFace (tools/faces_years.py), keeps the best few of
each guru and the pair that matches best (the face about as big and in about the same spot in both photos).
It writes then-now/PLACE/MOMENT/psm-N.jpg and msm-N.jpg (at most PHOTO px), then-now/pairs.json and a contact
sheet per place (then-now/sheets/PLACE.jpg) so Claude can choose the pairs for the mockup by eye.
"""
import argparse, concurrent.futures, json, os, random, re, sqlite3, sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces_years as fy   # noqa: E402  (bapa(), score(), PSM_UNTIL; copied in from the faces branch by the workflow)

PHOTO = 1200      # the kept photo's longest side
TRY = 14          # photos of each guru tried for each place and moment
KEEP = 4          # kept for the contact sheet
MOMENTS = {       # what the caption says -> the moment's name on the page
    'puja': ('Morning puja', r'\bpuja\b'),
    'darshan': ('Darshan of Thakorji', r'darshan of (thakorji|the murtis|bhagwan|shri)|thakorji'),
    'arti': ('Arti', r'\barti\b'),
    'abhishek': ('Abhishek', r'abhishek'),
    'blesses': ('Blessing the assembly', r'bless|assembly'),
}


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def candidates(db, place, rx, guru, keys):
    cond = "< ?" if guru == 'psm' else ">= ?"
    rows = db.execute(f"""select coalesce(date, date_from), year, album, file, caption from photos
        where is_bapa = 1 and place = ? and coalesce(date, date_from) {cond}""", (place, fy.PSM_UNTIL)).fetchall()
    rows = [r for r in rows if re.search(rx, (r[4] or '').lower()) and f'm/{r[2]}/{r[3]}' in keys]
    # spread over the years: a few from each year rather than all from one visit
    by_year = {}
    for r in rows:
        by_year.setdefault(r[1], []).append(r)
    rnd = random.Random(f'{place}{rx}{guru}')
    for v in by_year.values():
        rnd.shuffle(v)
    out = []
    while len(out) < TRY and any(by_year.values()):
        for y in sorted(by_year):
            if by_year[y] and len(out) < TRY:
                out.append(by_year[y].pop())
    return out


def look(path, guru):
    bgr = cv2.imread(path)
    if bgr is None:
        return None
    f, sim = fy.bapa(bgr, guru)
    if f is None:
        return None
    s, info = fy.score(bgr, f, sim)
    h, w = bgr.shape[:2]
    info.update(cx=round(float(f[0] + f[2] / 2) / w, 3), cy=round(float(f[1] + f[3] / 2) / h, 3), w=w, h=h)
    return s, info, bgr


def match(a, b):
    """How alike two photos are framed: the face about as big and in the same part of the photo."""
    return -abs(a['close'] - b['close']) * 4 - abs(a['cx'] - b['cx']) - abs(a['cy'] - b['cy']) - abs(a['w'] / a['h'] - b['w'] / b['h'])


def sheet(place, found, out):
    T = 220
    rows = []
    for m, sides in found.items():
        tiles = []
        for g in ('psm', 'msm'):
            for i in range(KEEP):
                t = np.full((T, T, 3), 40, np.uint8)
                if i < len(sides[g]):
                    im = cv2.imread(os.path.join(out, sides[g][i]['path']))
                    k = T / max(im.shape[:2])
                    im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
                    y, x = (T - im.shape[0]) // 2, (T - im.shape[1]) // 2
                    t[y:y + im.shape[0], x:x + im.shape[1]] = im
                    cv2.putText(t, f"{g}-{i} {sides[g][i]['date'][:4]}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 255), 1)
                tiles.append(t)
            tiles.append(np.full((T, 8, 3), 255, np.uint8))
        row = np.hstack(tiles[:-1])
        label = np.full((24, row.shape[1], 3), 0, np.uint8)
        cv2.putText(label, m, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 1)
        rows += [label, row]
    if rows:
        os.makedirs(os.path.join(out, 'sheets'), exist_ok=True)
        cv2.imwrite(os.path.join(out, 'sheets', slug(place) + '.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--keys', required=True)
    ap.add_argument('--photos', default='photos', help='where the R2 photos are saved, laid out ALBUM/FILE')
    ap.add_argument('--places', default=os.path.join(fy.HERE, 'site', 'then-now.txt'))
    ap.add_argument('--out', default='then-now')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    db = sqlite3.connect(a.db)
    keys = set(l.strip() for l in open(a.keys) if l.strip())
    places = [l.strip() for l in open(a.places) if l.strip() and not l.startswith('#')]
    from r2 import get   # tools/r2.py: saves m/ALBUM/FILE from R2
    pairs = {}
    for place in places:
        found = {}
        for mk, (mname, rx) in MOMENTS.items():
            sides = {}
            for g in ('psm', 'msm'):
                rows = candidates(db, place, rx, g, keys)
                paths = [os.path.join(a.photos, r[2], r[3]) for r in rows]
                with concurrent.futures.ThreadPoolExecutor(8) as ex:
                    list(ex.map(lambda r: get(f'm/{r[2]}/{r[3]}', os.path.join(a.photos, r[2], r[3])), rows))
                good = []
                for r, p in zip(rows, paths):
                    got = look(p, g) if os.path.exists(p) else None
                    if got:
                        good.append((got[0], r, got[1], got[2]))
                good.sort(key=lambda x: -x[0])
                kept = []
                for i, (s, r, info, bgr) in enumerate(good[:KEEP]):
                    k = min(1, PHOTO / max(bgr.shape[:2]))
                    im = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k < 1 else bgr
                    rel = os.path.join(slug(place), mk, f'{g}-{i}.jpg')
                    os.makedirs(os.path.join(a.out, os.path.dirname(rel)), exist_ok=True)
                    cv2.imwrite(os.path.join(a.out, rel), im, [cv2.IMWRITE_JPEG_QUALITY, 88])
                    kept.append(dict(path=rel, date=r[0], album=r[2], file=r[3], caption=r[4], score=round(s, 2), **info))
                sides[g] = kept
                print(place, mname, g, f'{len(rows)} tried, {len(good)} with Bapa', flush=True)
            if sides['psm'] and sides['msm']:
                best = max(((p, m) for p in sides['psm'] for m in sides['msm']),
                           key=lambda pm: pm[0]['score'] + pm[1]['score'] + 2 * match(*pm))
                found[mname] = dict(psm=sides['psm'], msm=sides['msm'], best=[best[0]['path'], best[1]['path']])
        pairs[place] = found
        sheet(place, found, a.out)
    json.dump(pairs, open(os.path.join(a.out, 'pairs.json'), 'w'), indent=1)
    print(sum(len(v) for v in pairs.values()), 'place and moment pairs', flush=True)


if __name__ == '__main__':
    main()
