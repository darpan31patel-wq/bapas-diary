"""Faces for Who was with Bapa (Darpan, 28 Oct 2026: "enter a person's name and find relevant pictures containing that
person... improve the accuracy of identifying people across different years, locations and photographs").

Every face in every photo in R2 gets a face number (128 numbers) from two small open models of the OpenCV model zoo,
YuNet (finds faces, MIT) and SFace (face numbers, Apache 2.0). Run on GitHub machines, nothing at all on the website.
Then each person's look is learnt from the photos whose captions name them, and the same face is found in photos whose
captions do not.

    python3 tools/people_faces.py plan --db bapas.db --years years.txt --have have.txt        # shards still to do
    python3 tools/people_faces.py index --db bapas.db --shard 2002-0-3 --out faces-2002-0-3.npz

A shard file holds keys (ALBUM/FILE of each photo with a face), rows (photo, x, y, w, h, score: one row a face,
in the photo's own pixels at web size) and emb (int8, 128 numbers a face, times 300).
"""
import argparse, json, os, re, sqlite3, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

PHOTOS = 'https://photos.bapas-diary.com/'
ZOO = 'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/'
MODELS = {'yunet.onnx': 'face_detection_yunet/face_detection_yunet_2023mar.onnx',
          'sface.onnx': 'face_recognition_sface/face_recognition_sface_2021dec.onnx'}
SIZE = 2500          # photos a shard
MIN_FACE = 28        # pixels: smaller faces are too blurred to tell people apart
LONG = 960           # photos are looked at with their long side at most this


def plan(a):
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    have = set(open(a.have).read().split()) if a.have and os.path.exists(a.have) else set()
    db = sqlite3.connect(a.db)
    todo = []
    for y in years:
        n = db.execute('SELECT count(*) FROM photos WHERE year = ?', (y,)).fetchone()[0]
        parts = max(1, -(-n // SIZE))
        todo += [f'{y}-{i}-{parts}' for i in range(parts) if f'faces-{y}-{i}-{parts}.npz' not in have]
    print(json.dumps(todo[:a.max]))


def models(folder):
    os.makedirs(folder, exist_ok=True)
    for name, path in MODELS.items():
        if not os.path.exists(os.path.join(folder, name)):
            urllib.request.urlretrieve(ZOO + path, os.path.join(folder, name))
    return os.path.join(folder, 'yunet.onnx'), os.path.join(folder, 'sface.onnx')


def get(key, tier='m'):
    for wait in (2, 10, 30):
        try:
            req = urllib.request.Request(PHOTOS + tier + '/' + urllib.request.quote(key), headers={'User-Agent': 'bapas-diary-faces'})
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception:
            time.sleep(wait)
    return None


def index(a):
    import cv2
    import numpy as np
    y, i, n = map(int, a.shard.split('-'))
    db = sqlite3.connect(a.db)
    rows = db.execute('SELECT album, file FROM photos WHERE year = ? ORDER BY album, file', (y,)).fetchall()
    k = -(-len(rows) // n)
    keys = [f'{al}/{f}' for al, f in rows[i * k:(i + 1) * k]]
    yunet, sface = models(a.models)
    det = cv2.FaceDetectorYN.create(yunet, '', (320, 320), 0.7)
    rec = cv2.FaceRecognizerSF.create(sface, '')
    out_keys, out_rows, out_emb, missing = [], [], [], 0
    with ThreadPoolExecutor(12) as ex:
        for key, data in zip(keys, ex.map(get, keys)):
            if not data:
                missing += 1
                continue
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            h, w = img.shape[:2]
            s = min(1.0, LONG / max(h, w))
            if s < 1:
                img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
                h, w = img.shape[:2]
            det.setInputSize((w, h))
            _, found = det.detect(img)
            got = False
            for f in found if found is not None else []:
                if min(f[2], f[3]) < MIN_FACE:
                    continue
                e = rec.feature(rec.alignCrop(img, f)).flatten()
                e /= np.linalg.norm(e) or 1
                if not got:
                    out_keys.append(key)
                    got = True
                out_rows.append([len(out_keys) - 1, *(f[:4] / s), f[14]])
                out_emb.append(np.clip(np.round(e * 300), -127, 127).astype(np.int8))   # values stay under 0.42: x300 keeps detail
    np.savez_compressed(a.out, keys=np.array(out_keys), rows=np.array(out_rows, np.float32).reshape(-1, 6),
                        emb=np.array(out_emb, np.int8).reshape(-1, 128))
    print(f'{a.shard}: {len(keys)} photos, {missing} missing, {len(out_rows)} faces in {len(out_keys)} photos')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan'); p.add_argument('--db', default='bapas.db'); p.add_argument('--years'); p.add_argument('--have'); p.add_argument('--max', type=int, default=256)
    p = sub.add_parser('index'); p.add_argument('--db', default='bapas.db'); p.add_argument('--shard'); p.add_argument('--out'); p.add_argument('--models', default='face-models')
    p = sub.add_parser('match'); p.add_argument('--db', default='bapas.db'); p.add_argument('--faces', default='faces'); p.add_argument('--out', default='people-faces.json')
    p.add_argument('--thresh', type=float, default=.6); p.add_argument('--margin', type=float, default=.06); p.add_argument('--protos', type=int, default=60); p.add_argument('--bapa', type=float, default=.5); p.add_argument('--min-photos', type=int, default=4)
    p = sub.add_parser('sheets'); p.add_argument('--sheets'); p.add_argument('--out', default='sheets'); p.add_argument('--max', type=int, default=80)
    a = ap.parse_args()
    {'plan': plan, 'index': index, 'match': match, 'sheets': sheets}[a.cmd](a)



# ---------- learning each person's face (run where the shard files are; nothing here needs the photos) ----------
PASSED = '2016-08-13'   # Pramukh Swami Maharaj until this day, Mahant Swami Maharaj from it


def load(folder):
    import numpy as np
    keys, rows, emb = [], [], []
    for f in sorted(os.listdir(folder)):
        if not f.startswith('faces-') or not f.endswith('.npz'):
            continue
        d = np.load(os.path.join(folder, f))
        r = d['rows'].copy()
        r[:, 0] += len(keys)
        keys += d['keys'].tolist()
        rows.append(r)
        emb.append(d['emb'])
    rows = np.concatenate(rows)
    e = np.concatenate(emb).astype(np.float32)
    e /= np.linalg.norm(e, axis=1, keepdims=True) + 1e-9
    return keys, rows, e.astype(np.float16)


def match(a):
    """Each person's face, learnt from photos whose captions name them, then looked for in every other photo.
    Writes {name: [[ALBUM/FILE, score], ...]} of photos found by face only, and contact sheets to check by eye."""
    import re, sys
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import search_people
    keys, rows, E = load(a.faces)
    print(len(keys), 'photos with faces,', len(rows), 'faces')
    db = sqlite3.connect(a.db)
    info = {f'{al}/{f}': (c or '', b == 1, d or '') for al, f, c, b, d in
            db.execute('SELECT album, file, caption, is_bapa, coalesce(date, date_from) FROM photos')}
    photo = rows[:, 0].astype(int)
    size = np.minimum(rows[:, 3], rows[:, 4])
    good = (rows[:, 5] >= .8) & (size >= 36)
    faces_in = {}
    for i, p in enumerate(photo):
        faces_in.setdefault(p, []).append(i)

    def sims(c, idx=None):   # one face number against many, in pieces so memory stays small
        idx = np.arange(len(E)) if idx is None else np.asarray(idx)
        out = np.empty(len(idx), np.float32)
        for s in range(0, len(idx), 200000):
            out[s:s + 200000] = E[idx[s:s + 200000]].astype(np.float32) @ c
        return out

    # Bapa: the one face in close photos whose caption is about Swamishri, for each guru
    bapa = np.zeros(len(E), bool)
    for era in 'PM':
        one = [faces_in[p][0] for p, k in enumerate(keys) if p in faces_in and len(faces_in[p]) == 1 and good[faces_in[p][0]]
               and info.get(k, ('', 0, ''))[1] and re.match(r'swamishri\b', info[k][0].lower())
               and ((info[k][2] < PASSED) == (era == 'P'))]
        ex = E[one[:6000]].astype(np.float32)
        c = ex.mean(0); c /= np.linalg.norm(c)
        for _ in range(3):   # the faces most like the middle are him; the rest are other people in "Swamishri ..." photos
            s = ex @ c
            keep = ex[s > np.percentile(s, 40)]
            c = keep.mean(0); c /= np.linalg.norm(c)
        ref = keep[:3000]
        for s in range(0, len(E), 100000):
            m = (E[s:s + 100000].astype(np.float32) @ ref.T)
            bapa[s:s + 100000] |= np.sort(m, axis=1)[:, -8:].mean(1) > a.bapa
        print(era, 'Bapa faces so far', int(bapa.sum()))

    people = search_people.people(db)
    # 1. each person's face, from the photos whose captions name them. Strong photos are the ones with only one face
    #    besides Bapa's ("Swamishri blesses Shri Narendra Modi", "Pujya Viveksagar Swami addresses the assembly"):
    #    the face there must be them. It must agree across several strong photos, so a face that is only often near
    #    them (an attendant, a crowd) is never learnt as theirs.
    learnt = []
    for name, kind, spell, n, days, first, last in people:
        if n < a.min_photos:
            continue
        rx = re.compile('(?:^|[^a-z])(?:' + '|'.join(re.escape(s) for s in spell) + ')')
        mine = {p for p, k in enumerate(keys) if rx.search(info.get(k, ('',))[0].lower())}
        strong = []
        for p in mine:
            fs = faces_in.get(p, [])
            other = [i for i in fs if good[i] and not bapa[i]]
            if len(other) == 1 and len(fs) <= 3:
                strong.append(other[0])
        if len(strong) < 2:
            continue
        C = E[strong].astype(np.float32)
        agree = (C @ C.T > .42).sum(1) - 1   # faces change over 50 years (Narendra Modi 2002 and 2024), so a quarter is enough
        need = max(1 if len(strong) < 4 else 2, .25 * (len(strong) - 1))
        if agree.max() < need:
            continue
        c = C[agree >= need].mean(0)
        c /= np.linalg.norm(c)
        cand = np.array([i for p in mine for i in faces_in.get(p, []) if good[i] and not bapa[i]])
        cs = E[cand].astype(np.float32) @ c
        members = cand[cs > .5][np.argsort(-cs[cs > .5])][:a.protos]
        if len(members) < 2:
            continue
        learnt.append((name, kind, members, mine))
    print(len(learnt), 'people with a face learnt')
    # 2. every face in a photo with Bapa against every learnt face: a face is a person's when it is close to their
    #    faces (the mean of its three closest) and clearly closer than to anyone else's
    P = np.concatenate([m for _, _, m, _ in learnt])
    owner = np.concatenate([[j] * len(m) for j, (_, _, m, _) in enumerate(learnt)])
    PE = E[P].astype(np.float32).T
    with_bapa = np.array([info.get(k, ('', False))[1] for k in keys])
    look = np.where(good & ~bapa & with_bapa[photo])[0]
    best = np.zeros(len(look), np.int32); top = np.zeros(len(look), np.float32); second = np.zeros(len(look), np.float32)
    bounds = np.r_[0, np.cumsum([len(m) for _, _, m, _ in learnt])]
    for s in range(0, len(look), 20000):
        M = E[look[s:s + 20000]].astype(np.float32) @ PE
        score = np.stack([np.sort(M[:, bounds[j]:bounds[j + 1]], axis=1)[:, -3:].mean(1) for j in range(len(learnt))], 1)
        o = np.argsort(-score, axis=1)
        r = np.arange(len(score))
        best[s:s + 20000], top[s:s + 20000], second[s:s + 20000] = o[:, 0], score[r, o[:, 0]], score[r, o[:, 1]]
    found, sheets = {}, {}
    for j, (name, kind, members, mine) in enumerate(learnt):
        hit = np.where((best == j) & (top >= a.thresh) & (top - second >= a.margin))[0]
        hit = [h for h in hit[np.argsort(-top[hit])] if photo[look[h]] not in mine]
        more, seen = [], set()
        for h in hit:
            k = keys[photo[look[h]]]
            if k not in seen:
                seen.add(k)
                more.append([k, round(float(top[h]), 3)])
        print(f'{name}: {len(mine)} captioned photos, face learnt from {len(members)}, found in {len(more)} more')
        found[name] = {'captioned': len(mine), 'learnt': len(members), 'more': more}
        show = [hit[i] for i in sorted(set(np.linspace(0, len(hit) - 1, 24).astype(int)))] if hit else []   # best to weakest
        sheets[name] = ([keys[photo[i]] for i in members[:12]], [rows[i][1:5].tolist() for i in members[:12]],
                        [keys[photo[look[h]]] for h in show], [rows[look[h]][1:5].tolist() for h in show])
    json.dump(found, open(a.out, 'w'), ensure_ascii=False)
    json.dump(sheets, open(a.out.replace('.json', '-sheets.json'), 'w'), ensure_ascii=False)


def sheets(a):
    """Contact sheets to check by eye: for each person, top row the faces learnt from their captioned photos, then
    the faces found in photos whose captions do not name them, best first, each with its score."""
    import cv2
    import numpy as np
    data = json.load(open(a.sheets))
    os.makedirs(a.out, exist_ok=True)
    cache = {}

    def crop(key, box):
        if key not in cache:
            raw = get(key)
            cache[key] = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR) if raw else None
        img = cache[key]
        if img is None:
            return np.zeros((112, 112, 3), np.uint8)
        x, y, w, h = map(int, box)
        m = int(w * .35)
        c = img[max(0, y - m):y + h + m, max(0, x - m):x + w + m]
        return cv2.resize(c, (112, 112)) if c.size else np.zeros((112, 112, 3), np.uint8)

    for name, (seed_keys, seed_boxes, more_keys, more_boxes) in list(data.items())[:a.max]:
        tiles = [crop(k, b) for k, b in zip(seed_keys, seed_boxes)]
        row1 = np.hstack(tiles + [np.zeros((112, 112, 3), np.uint8)] * (12 - len(tiles)))
        found = [crop(k, b) for k, b in zip(more_keys, more_boxes)]
        found += [np.zeros((112, 112, 3), np.uint8)] * (24 - len(found))
        sheet = np.vstack([np.full((30, 112 * 12, 3), 255, np.uint8), row1, np.full((8, 112 * 12, 3), 255, np.uint8),
                           np.hstack(found[:12]), np.hstack(found[12:24])])
        cv2.putText(sheet, name, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 0), 2)
        cv2.imwrite(os.path.join(a.out, re.sub(r'[^A-Za-z0-9]+', '-', name) + '.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 80])


if __name__ == '__main__':
    main()
