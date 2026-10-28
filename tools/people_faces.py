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
import argparse, json, os, sqlite3, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

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
    a = ap.parse_args()
    {'plan': plan, 'index': index}[a.cmd](a)


if __name__ == '__main__':
    main()
