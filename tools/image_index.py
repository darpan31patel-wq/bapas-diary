"""Search by photo for the website search (Darpan, 26 Oct 2026: "upload an image, or paste an image, or a part of the
image ... try and find the same image").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org (the small photos come
from R2, photos.bapas-diary.com). The open DINOv2 small model (Meta, Apache 2.0) turns each photo into numbers once, on
GitHub. The same model file runs in the visitor's browser for their picture, so nothing costs anything to run.

    python3 tools/image_index.py plan --db bapas.db --years years.txt --have have.txt
    python3 tools/image_index.py shard --db bapas.db --shard 2026-0-11 --out photos
    python3 tools/image_index.py embed --model dinov2-small-q8.onnx --photos photos --out pic-2026-0-11.npz
    python3 tools/image_index.py build --emb emb --out image

build writes what the search page reads (site/search-image.js), all in one folder:
  meta.json     sizes, the model file name, and the usual value of each number (mc, mm)
  keys.json     ["ALBUM/FILE", ...], one per photo, in the order of the rows
  vec-I.bin     96 bytes per photo (see build), cut into files under 20 MB (Cloudflare Pages takes 25 MB at most)
"""
import argparse, glob, json, os, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SIDE = 224
MEAN = np.array([0.485, 0.456, 0.406], 'f4')
STD = np.array([0.229, 0.224, 0.225], 'f4')
SIZE = 6000   # photos per shard


def plan(a):
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    have = set(open(a.have).read().split()) if a.have and os.path.exists(a.have) else set()
    db = sqlite3.connect(a.db)
    todo = []
    for y in years:
        n = db.execute('SELECT count(*) FROM photos WHERE year = ?', (y,)).fetchone()[0]
        parts = max(1, -(-n // SIZE))
        todo += [f'{y}-{i}-{parts}' for i in range(parts) if f'pic-{y}-{i}-{parts}.npz' not in have]
    print(json.dumps(todo))


def shard(a):
    """Download one shard's small photos from R2: YEAR-I-N is the I-th of N slices of that year."""
    import urllib.request, time
    y, i, n = map(int, a.shard.split('-'))
    rows = sqlite3.connect(a.db).execute('SELECT album, file FROM photos WHERE year = ? ORDER BY album, file', (y,)).fetchall()
    k = -(-len(rows) // n)
    rows = rows[i * k:(i + 1) * k]

    def get(r):
        key = f'{r[0]}/{r[1]}'
        path = os.path.join(a.out, key)
        if os.path.exists(path):
            return 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for wait in (2, 10, 30):
            try:
                req = urllib.request.Request('https://photos.bapas-diary.com/s/' + urllib.request.quote(key), headers={'User-Agent': 'bapas-diary-image-search'})
                open(path, 'wb').write(urllib.request.urlopen(req, timeout=30).read())
                return 1
            except Exception as e:
                err = e
                time.sleep(wait)
        print(key, err)
        return 0
    with ThreadPoolExecutor(16) as ex:
        print(sum(ex.map(get, rows)), 'of', len(rows), 'downloaded')


def embed(a):
    """Every photo -> the model's whole picture numbers (cls), the average of its parts (mean), and 9 half size windows."""
    import onnxruntime as ort
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    s = ort.InferenceSession(a.model, providers=['CPUExecutionProvider'])
    files = sorted(glob.glob(os.path.join(a.photos, '*', '*')))

    def prep(f):
        try:
            im = Image.open(f).convert('RGB').resize((SIDE, SIDE), Image.BILINEAR)
            return ((np.asarray(im, 'f4') / 255 - MEAN) / STD).transpose(2, 0, 1)
        except Exception as e:
            print(f, e)
    keys, out = [], {'cls': [], 'mean': [], 'win': []}
    with ThreadPoolExecutor(4) as ex:
        for i in range(0, len(files), 64):
            batch = [(f, x) for f, x in zip(files[i:i + 64], ex.map(prep, files[i:i + 64])) if x is not None]
            t = s.run(None, {'x': np.stack([x for _, x in batch])})[0]
            p = t[:, 1:].reshape(len(t), 16, 16, -1)
            out['cls'].append(t[:, 0].astype('f2'))
            out['mean'].append(p.mean((1, 2)).astype('f2'))
            out['win'].append(np.stack([p[:, y:y + 8, x:x + 8].mean((1, 2)) for y in (0, 4, 8) for x in (0, 4, 8)], 1).astype('f2'))
            keys += [os.path.relpath(f, a.photos) for f, _ in batch]
            if i % 1280 == 0:
                print(i, 'of', len(files), flush=True)
    np.savez(a.out, keys=np.array(keys), **{k: np.concatenate(v) for k, v in out.items()})


def build(a):
    """All shards -> the files the page reads. Each photo is kept as 768 yes/no answers (96 bytes): is each of the
    model's 384 whole picture numbers, and each of its 384 average-of-parts numbers, above the usual value? Tested on
    18,000 photos (26 Oct 2026): as good as the full numbers for whole photos, screenshots and big crops, at a 16th of
    the size, so the whole diary is about 25 MB."""
    keys, cls, mean = [], [], []
    for f in sorted(glob.glob(os.path.join(a.emb, 'pic-*.npz'))):
        z = np.load(f)
        keys += [str(k) for k in z['keys']]
        cls.append(z['cls'].astype('f4'))
        mean.append(z['mean'].astype('f4'))
    unit = lambda x: x / np.linalg.norm(x, axis=1, keepdims=True)
    cls, mean = unit(np.concatenate(cls)), unit(np.concatenate(mean))
    mc, mm = cls.mean(0), mean.mean(0)
    bits = np.packbits(np.concatenate([cls > mc, mean > mm], 1), axis=1)   # 96 bytes per photo, first bit = highest
    os.makedirs(a.out, exist_ok=True)
    per = (20 << 20) // bits.shape[1]
    vecs = []
    for i in range(0, len(bits), per):
        name = f'vec-{len(vecs)}.bin'
        bits[i:i + per].tofile(os.path.join(a.out, name))
        vecs.append(name)
    json.dump(keys, open(os.path.join(a.out, 'keys.json'), 'w'), separators=(',', ':'))
    model = os.path.basename(a.model)
    size = os.path.getsize(a.model) + sum(os.path.getsize(os.path.join(a.out, v)) for v in vecs) + os.path.getsize(os.path.join(a.out, 'keys.json')) // 5
    meta = {'n': len(keys), 'bytes': size, 'model': model, 'vecs': vecs, 'side': SIDE,
            'mc': [round(float(v), 6) for v in mc], 'mm': [round(float(v), 6) for v in mm]}
    json.dump(meta, open(os.path.join(a.out, 'meta.json'), 'w'), separators=(',', ':'))
    print(len(keys), 'photos ->', a.out, f'({size / 1e6:.1f} MB to fetch the first time)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('plan'); s.add_argument('--db', default='bapas.db'); s.add_argument('--years'); s.add_argument('--have')
    s = sub.add_parser('shard'); s.add_argument('--db', default='bapas.db'); s.add_argument('--shard'); s.add_argument('--out', default='photos')
    s = sub.add_parser('embed'); s.add_argument('--model'); s.add_argument('--photos'); s.add_argument('--out')
    s = sub.add_parser('build'); s.add_argument('--emb'); s.add_argument('--out'); s.add_argument('--model', default='dinov2-small-q8.onnx')
    a = ap.parse_args()
    globals()[a.cmd](a)
