#!/usr/bin/env python3
"""Bapa through the years: one close up of Bapa for every day, eyes lined up (Darpan, 23 Oct 2026: 'a close-up
picture of Bapa for every day that's possible ... I want the eyes to be in the exact same spot').

Website only (bapas-diary.com). Nothing here touches the daily 2pm picture: it only reads the face models.

    python3 tools/faces_years.py --db bapas.db --photos m --from 1999-01-01 --to 1999-12-31 --out faces

--photos is a folder of photos laid out ALBUM/FILE (the R2 web sizes) or, with --fetch, where to save them from
baps.org first. For every day (an album with only a date range counts as one day, its first, and only when no
photo of a day inside that range has its own date) it finds Bapa in each photo with YuNet and SFace (the same check
as models/README.md) and picks the closest good face (biggest, looking at the camera, sharp, light).

The page shows that photo whole, never cut (Darpan, 23 Oct 2026: 'I want the picture to be center frame, don't want
to cut the picture at all'), turned and sized in the browser so his eyes land on the same spot every day. So this
writes faces/p/DAY.jpg (the photo itself, at most PHOTO px), faces/f/DAY.jpg (a small lined up close up for the
timeline strip) and faces/faces.json (day, place, caption, album, file, his two eyes and the face size in p/DAY.jpg).
"""
import argparse, collections, json, math, os, sqlite3, sys, time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(HERE, 'models')
PSM_UNTIL = '2016-08-13'   # Pramukh Swami Maharaj before this date, Mahant Swami Maharaj after
SAME_PERSON = .5           # as make.py: strangers and murtis score below about .35
W, H = 240, 300            # a timeline thumbnail, 4:5
PHOTO = 1200               # the shown photo's longest side
EYE_Y = .42                # the eyes' height in the frame
EYE_GAP = .17              # the distance between the eyes, as a share of the frame's width
MIN_GAP = 9                # pixels between the eyes (span) in the photo: anything smaller is too far away to blow up

DETECT = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .6, .3, 5000)
RECOGNISE = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'face_recognition_sface_2021dec.onnx'), '')
BAPA = {k: np.array(v) for k, v in json.load(open(os.path.join(MODELS, 'bapa-faces.json'))).items()}


def front_view(f):
    """0 to 1: 1 looking at the camera, 0 a profile (as make.front_view)."""
    x, y, w, h, rx, ry, lx, ly, nx, ny = [float(v) for v in f[:10]]
    eyes = abs(lx - rx) / max(w, 1)
    centred = 1 - min(1, abs(nx - (lx + rx) / 2) / max(abs(lx - rx) / 2, 1))
    return max(0, min(1, (eyes - .18) / .25)) * (.5 + .5 * centred)


def bapa(bgr, guru):
    """Bapa's face in the photo (the detector's 15 numbers, similarity), or (None, best similarity)."""
    k = 1.0
    if max(bgr.shape[:2]) < 900:   # small web photos: look at them twice the size so far faces are found too
        k = 2.0
        bgr = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    DETECT.setInputSize((bgr.shape[1], bgr.shape[0]))
    faces = DETECT.detect(bgr)[1]
    best, best_sim = None, 0
    for f in faces if faces is not None else []:
        e = RECOGNISE.feature(RECOGNISE.alignCrop(bgr, f))[0]
        sim = float(BAPA[guru] @ (e / np.linalg.norm(e)))
        if sim > best_sim:
            best, best_sim = f.copy(), sim
    if best is not None:
        best[:14] /= k
    return (best, best_sim) if best_sim >= SAME_PERSON else (None, best_sim)


def quality(bgr, f):
    """(sharpness, brightness) of the face at a fixed 160 px, as make.face_quality."""
    x, y, w, h = [int(v) for v in f[:4]]
    crop = bgr[max(0, y):max(0, y + h), max(0, x):max(0, x + w)]
    if crop.shape[0] < 8 or crop.shape[1] < 8:
        return 0, 0
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g = cv2.resize(g, (160, max(1, round(160 * g.shape[0] / g.shape[1]))), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(g, cv2.CV_32F).var()), float(g.mean())


def span(f):
    """How big the face is in pixels: the gap between the eyes, or the eyes to the mouth when that's longer (the two
    are about equal on a face looking at the camera, but the eyes close up on a face turned to one side)."""
    rx, ry, lx, ly, _, _, mrx, mry, mlx, mly = [float(v) for v in f[4:14]]
    return max(math.hypot(lx - rx, ly - ry), math.hypot((mrx + mlx - rx - lx) / 2, (mry + mly - ry - ly) / 2))


def score(bgr, f, sim):
    """How good a close up the photo makes: mostly how big his face is in it, and never a blurry, dark or side face
    when there's a better one. Wider photos still count when the day has nothing closer (Darpan: 'it doesn't matter
    if it's wider, but the most close-up picture you have')."""
    gap = span(f)
    close = f[3] / min(bgr.shape[:2])                    # face height against the photo's short side
    front = front_view(f)
    sharp, bright = quality(bgr, f)
    s = min(close, .6) * 3 + min(gap, 120) / 120 + sim
    s -= 3 * max(0, .6 - front)                          # a side profile can't line its eyes up with the others
    s -= .8 * max(0, 1 - sharp / 40) + .8 * max(0, 1 - bright / 70)
    s -= 1.5 if gap < MIN_GAP * 2 else 0
    return float(s), dict(close=round(float(close), 3), gap=round(gap, 1), front=round(front, 2), sharp=round(sharp), bright=round(bright))


def align(bgr, f):
    """The photo turned, scaled and moved so his right eye and left eye sit on the same two points in every frame."""
    rx, ry, lx, ly = [float(v) for v in f[4:8]]
    if rx > lx:   # the detector's right eye is on the left of the photo; keep it so for a mirrored landmark set
        rx, ry, lx, ly = lx, ly, rx, ry
    ang = math.atan2(ly - ry, lx - rx)
    k = EYE_GAP * W / span(f)
    c, s = k * math.cos(-ang), k * math.sin(-ang)
    cx, cy = (rx + lx) / 2, (ry + ly) / 2
    M = np.array([[c, -s, W / 2 - (c * cx - s * cy)], [s, c, EYE_Y * H - (s * cx + c * cy)]], np.float32)
    sharp = cv2.warpAffine(bgr, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
    mask = cv2.warpAffine(np.full(bgr.shape[:2], 255, np.uint8), M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
    if mask.min() == 255:
        return sharp
    # the edges the photo doesn't reach: the same photo much bigger and blurred, so the frame never shows black
    soft = cv2.warpAffine(bgr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    soft = cv2.GaussianBlur(cv2.resize(soft, (W // 8, H // 8), interpolation=cv2.INTER_AREA), (0, 0), 3)
    soft = (cv2.resize(soft, (W, H), interpolation=cv2.INTER_LINEAR) * .55).astype(np.uint8)
    a = cv2.GaussianBlur(cv2.erode(mask, np.ones((5, 5), np.uint8)), (0, 0), 4).astype(np.float32)[..., None] / 255
    return (sharp * a + soft * (1 - a)).astype(np.uint8)


def fetch(album, file, dest):
    sys.path.insert(0, os.path.join(HERE, 'tools'))
    from archive_download import SITE, get   # the Drive archive's polite fetch: one at a time, stops at a check page
    body, _ = get(SITE.format(album=album, size='WebImages', file=file), may_be_missing=True)
    if body:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'wb').write(body)
    time.sleep(.6)
    return bool(body)


def day_groups(db, start, end):
    """{day: [(day, to, place, album, file, caption)]}, a range album counting as its first day, and only when no photo
    of a day inside its range has its own date."""
    rows = db.execute('SELECT coalesce(date, date_from) AS day, date_to, place, album, file, caption FROM photos '
                      'WHERE coalesce(date, date_from) BETWEEN ? AND ? ORDER BY day, album, file', (start, end)).fetchall()
    days = collections.defaultdict(list)
    dated = sorted({r[0] for r in rows if not r[1] or r[1] == r[0]})
    for r in rows:
        if r[1] and r[1] != r[0] and any(r[0] <= d <= r[1] for d in dated):
            continue   # a range album, and the range has days with their own dated photos: those come first
        days[r[0]].append(r)
    return days


def hint(rec):
    """How good a close up a photo looks from website-faces' scan (tools/web_faces.py on the face picker branch: [sim,
    x, y, w, h, front, sharp, bright, W, H, faces, other], box as parts of the photo), by score()'s rules, so only the
    best few of each day need looking at again for his eyes."""
    sim, x, y, w, h, front, sharp, bright, W_, H_ = rec[:10]
    close = h * H_ / max(1, min(W_, H_))
    return (min(close, .6) * 3 + min(w * W_ * .4, 120) / 120 + sim - 3 * max(0, .6 - front)
            - .8 * max(0, 1 - sharp / 40) - .8 * max(0, 1 - bright / 70))


def auto(a):
    """Every year in R2 (years.txt), straight from its m/ copies at --url: no photos are kept, the page shows the m/ copy
    itself with the eyes measured on it. Days already done with the same number of photos are skipped, so each run
    only does new years and the current year's new days. website-faces' scan (--hints) narrows each day to its best
    --keep photos of Bapa; a photo it hasn't looked at yet is always looked at; a year it hasn't scanned waits."""
    import gzip, urllib.parse, urllib.request
    from concurrent.futures import ThreadPoolExecutor
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    hints, scanned = {}, set()
    for f in sorted(os.listdir(a.hints)) if a.hints and os.path.isdir(a.hints) else []:
        if f.startswith('face2-') and f.endswith('.json.gz'):
            hints.update(json.load(gzip.open(os.path.join(a.hints, f), 'rt')))
            scanned.add(int(f[6:10]))
    db = sqlite3.connect(a.db)
    jp, sp = os.path.join(a.out, 'faces.json'), os.path.join(a.out, 'seen.json')
    os.makedirs(a.out, exist_ok=True)
    out = {x['day']: x for x in json.load(open(jp))} if os.path.exists(jp) else {}
    seen = json.load(open(sp)) if os.path.exists(sp) else {}

    def get(key):
        for wait in (2, 10, 30, 0):
            try:
                req = urllib.request.Request(a.url + urllib.parse.quote(key), headers={'User-Agent': 'bapas-diary-years'})
                return cv2.imdecode(np.frombuffer(urllib.request.urlopen(req, timeout=30).read(), np.uint8), cv2.IMREAD_COLOR)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
            except Exception:
                pass
            time.sleep(wait)
        return None

    todo = []
    for y in years:
        if y not in scanned:
            print(f'{y}: waiting for its face scan', flush=True)
            continue
        days = day_groups(db, f'{y}-01-01', f'{y}-12-31')
        new = [(d, xs) for d, xs in sorted(days.items()) if seen.get(d) != len(xs)]
        print(f'{y}: {len(days)} days, {len(new)} to do', flush=True)
        todo += new
    t0 = time.time()
    with ThreadPoolExecutor(16) as net:
        for n, (day, xs) in enumerate(todo):
            guru = 'psm' if day < PSM_UNTIL else 'msm'
            cands = []
            for r in xs:
                rec = hints.get(f'{r[3]}/{r[4]}')
                if rec is None:
                    cands.append((9, r))   # not scanned yet: a new photo
                elif rec[0] >= SAME_PERSON and rec[0] > rec[11]:
                    cands.append((hint(rec), r))
            cands = [r for _, r in sorted(cands, key=lambda c: -c[0])[:a.keep]]
            best = None
            for r, bgr in zip(cands, net.map(lambda r: get(f'{r[3]}/{r[4]}'), cands)):
                if bgr is None:
                    continue
                f, sim = bapa(bgr, guru)
                if f is None:
                    continue
                s, facts = score(bgr, f, sim)
                if facts['gap'] >= MIN_GAP and (best is None or s > best[0]):
                    best = (s, bgr, f, r, sim, facts)
            out.pop(day, None)
            if best:
                s, bgr, f, (_, to, place, album, file, cap), sim, facts = best
                rx, ry, lx, ly = [float(v) for v in f[4:8]]
                if rx > lx:
                    rx, ry, lx, ly = lx, ly, rx, ry
                out[day] = dict(day=day, to=to if to and to != day else None, place=place or '', caption=cap or '',
                                album=album, file=file, guru=guru, sim=round(sim, 2), score=round(s, 2), **facts,
                                photos=len(xs), w=bgr.shape[1], h=bgr.shape[0], src='m',
                                eyes=[round(v, 1) for v in (rx, ry, lx, ly)], span=round(span(f), 1))
            seen[day] = len(xs)
            if n % 50 == 0 or n == len(todo) - 1:
                print(f'  {n + 1}/{len(todo)} {day}: {len(cands)} looked at, {"close " + str(best[5]["close"]) if best else "no face"}, '
                      f'{time.time() - t0:.0f}s', flush=True)
                json.dump(sorted(out.values(), key=lambda x: x['day']), open(jp, 'w'), indent=0, ensure_ascii=False)
                json.dump(seen, open(sp, 'w'), sort_keys=True)
    json.dump(sorted(out.values(), key=lambda x: x['day']), open(jp, 'w'), indent=0, ensure_ascii=False)
    json.dump(seen, open(sp, 'w'), sort_keys=True)
    print(f'{len(out)} days with a close up, {len(todo)} looked at this time')


def main():
    if '--years' in sys.argv:
        ap = argparse.ArgumentParser()
        ap.add_argument('--db', default='bapas.db')
        ap.add_argument('--years', required=True, help='the years in R2, one a line (photos.bapas-diary.com/years.txt)')
        ap.add_argument('--hints', help="folder of website-faces' face2-*.json.gz")
        ap.add_argument('--url', default='https://photos.bapas-diary.com/m/')
        ap.add_argument('--keep', type=int, default=5)
        ap.add_argument('--out', default='faces')
        return auto(ap.parse_args())
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--photos', required=True)
    ap.add_argument('--from', dest='start', required=True)
    ap.add_argument('--to', dest='end', required=True)
    ap.add_argument('--out', default='faces')
    ap.add_argument('--fetch', action='store_true', help='download missing photos from baps.org first')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    days = day_groups(db, a.start, a.end)
    print(f'{sum(map(len, days.values()))} photos over {len(days)} days', flush=True)
    os.makedirs(os.path.join(a.out, 'f'), exist_ok=True)
    os.makedirs(os.path.join(a.out, 'p'), exist_ok=True)
    jp = os.path.join(a.out, 'faces.json')
    out = {x['day']: x for x in json.load(open(jp))} if os.path.exists(jp) else {}
    try:
        for n, (day, xs) in enumerate(sorted(days.items())):
            guru = 'psm' if day < PSM_UNTIL else 'msm'
            best = None
            for _, to, place, album, file, cap in xs:
                path = os.path.join(a.photos, album, file)
                if not os.path.exists(path) and not (a.fetch and fetch(album, file, path)):
                    continue
                bgr = cv2.imread(path)
                if bgr is None:
                    continue
                f, sim = bapa(bgr, guru)
                if f is None:
                    continue
                s, facts = score(bgr, f, sim)
                if facts['gap'] < MIN_GAP:
                    continue
                if best is None or s > best[0]:
                    best = (s, bgr, f, dict(day=day, to=to if to and to != day else None, place=place or '', caption=cap or '',
                                            album=album, file=file, guru=guru, sim=round(sim, 2), score=round(s, 2), **facts))
            if best:
                bgr, f = best[1], best[2]
                cv2.imwrite(os.path.join(a.out, 'f', day + '.jpg'), align(bgr, f), [cv2.IMWRITE_JPEG_QUALITY, 78])
                k = min(1, PHOTO / max(bgr.shape[:2]))
                if k < 1:
                    bgr = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
                cv2.imwrite(os.path.join(a.out, 'p', day + '.jpg'), bgr, [cv2.IMWRITE_JPEG_QUALITY, 84])
                rx, ry, lx, ly = [float(v) * k for v in f[4:8]]
                if rx > lx:
                    rx, ry, lx, ly = lx, ly, rx, ry
                out[day] = dict(best[3], photos=len(xs), w=bgr.shape[1], h=bgr.shape[0],
                                eyes=[round(v, 1) for v in (rx, ry, lx, ly)], span=round(span(f) * k, 1))
            print(f'  {n + 1}/{len(days)} {day}: {len(xs)} photos, ' + (f'close {best[3]["close"]}' if best else 'no face'), flush=True)
    except Exception as e:   # baps.org asked us to wait: keep what is done
        print(f'Stopping early: {e}')
    finally:
        json.dump(sorted(out.values(), key=lambda x: x['day']), open(jp, 'w'), indent=0, ensure_ascii=False)
    print(f'{len(out)} days with a close up')


if __name__ == '__main__':
    main()
