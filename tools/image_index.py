"""Search by photo for the website search (Darpan, 26 Oct 2026: "upload an image, or paste an image, or a part of the
image ... try and find the same image").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org (the small photos come
from R2, photos.bapas-diary.com). The open DINOv2 small model (Meta, Apache 2.0) turns each photo into numbers once, on
GitHub. The same model file runs in the visitor's browser for their picture, so nothing costs anything to run.

    python3 tools/image_index.py plan --db bapas.db --years years.txt --have have.txt
    python3 tools/image_index.py shard --db bapas.db --shard 2026-0-11 --out photos
    python3 tools/image_index.py embed --model dinov2-small-q8.onnx --photos photos --out pic-2026-0-11.npz
    python3 tools/image_index.py build --emb emb --out image
    python3 tools/image_index.py plan --db bapas.db --years years.txt --keys image/keys.json --stamp 2026102902   (daily: new photos only)

build writes what the search page reads (site/search-image.js), all in one folder:
  meta.json     sizes, the model file name, and the usual value of each number (mc, mm)
  keys.json     ["ALBUM/FILE", ...], one per photo, in the order of the rows
  vec-I.bin     96 bytes per photo (see build), cut into files under 20 MB (Cloudflare Pages takes 25 MB at most)
"""
import argparse, glob, json, os, sqlite3, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SIDE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
SIZE = 6000   # photos per shard


def missing(a):
    """Photos of the years in R2 that have no numbers yet (not in --keys, the keys.json of the last build), in order."""
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    have = set(json.load(open(a.keys)))
    db = sqlite3.connect(a.db)
    rows = db.execute(f'SELECT album, file FROM photos WHERE year IN ({",".join("?" * len(years))}) ORDER BY year, album, file', years).fetchall()
    return [r for r in rows if f'{r[0]}/{r[1]}' not in have]


def plan(a):
    """The shards still to do. With --keys (the daily timer): only photos added since the last build, as new-STAMP-I-N
    slices. Without: every year in R2 cut into slices of about SIZE photos, minus those already kept."""
    if a.keys and os.path.exists(a.keys):
        n = len(missing(a))
        parts = -(-n // SIZE)
        print(json.dumps([f'new-{a.stamp}-{i}-{parts}' for i in range(parts)]))
        return
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
    """Download one shard's small photos from R2: YEAR-I-N is the I-th of N slices of that year, new-STAMP-I-N the I-th
    of N slices of the photos with no numbers yet (same --keys and --years as plan)."""
    import urllib.request, time
    if a.shard.startswith('new-'):
        _, _, i, n = a.shard.split('-')
        i, n = int(i), int(n)
        rows = missing(a)
    else:
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
    import numpy as np, onnxruntime as ort
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    # one photo at a time, as in the browser: the model's 8 bit steps are scaled to everything run together, so a
    # photo run in a batch of 64 comes out slightly different (about 0.985 alike) from the same photo run alone
    opt = ort.SessionOptions()
    opt.intra_op_num_threads = 1
    sess = [ort.InferenceSession(a.model, opt, providers=['CPUExecutionProvider']) for _ in range(os.cpu_count() or 4)]
    files = sorted(glob.glob(os.path.join(a.photos, '*', '*')))

    def one(i):
        f = files[i]
        try:
            im = Image.open(f).convert('RGB').resize((SIDE, SIDE), Image.BILINEAR)
        except Exception as e:
            print(f, e)
            return None
        x = ((np.asarray(im, 'f4') / 255 - np.array(MEAN, 'f4')) / np.array(STD, 'f4')).transpose(2, 0, 1)[None]
        t = sess[i % len(sess)].run(None, {'x': x})[0][0]
        p = t[1:].reshape(16, 16, -1)
        win = np.stack([p[y:y + 8, x:x + 8].mean((0, 1)) for y in (0, 4, 8) for x in (0, 4, 8)])
        return os.path.relpath(f, a.photos), t[0], p.mean((0, 1)), win
    keys, out = [], {'cls': [], 'mean': [], 'win': []}
    with ThreadPoolExecutor(len(sess)) as ex:
        for i, r in enumerate(ex.map(one, range(len(files)))):
            if r:
                keys.append(r[0])
                for k, v in zip(out, r[1:]):
                    out[k].append(v.astype('f2'))
            if i % 1000 == 0:
                print(i, 'of', len(files), flush=True)
    out = {k: np.stack(v) for k, v in out.items()}
    np.savez(a.out, keys=np.array(keys), **out)


def build(a):
    """All shards -> the files the page reads. Each photo is kept as 768 yes/no answers (96 bytes): is each of the
    model's 384 whole picture numbers, and each of its 384 average-of-parts numbers, above the usual value? Tested on
    18,000 photos (26 Oct 2026): as good as the full numbers for whole photos, screenshots and big crops, at a 16th of
    the size, so the whole diary is about 25 MB."""
    import numpy as np
    keys, cls, mean, seen = [], [], [], set()
    for f in sorted(glob.glob(os.path.join(a.emb, 'pic-*.npz'))):
        z = np.load(f)
        keep = [i for i, k in enumerate(z['keys']) if str(k) not in seen]   # a photo kept twice counts once
        seen.update(str(z['keys'][i]) for i in keep)
        keys += [str(z['keys'][i]) for i in keep]
        cls.append(z['cls'][keep].astype('f4'))
        mean.append(z['mean'][keep].astype('f4'))
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
    s.add_argument('--keys', help='keys.json of the last build: plan only the photos added since'); s.add_argument('--stamp', default='0')
    s = sub.add_parser('shard'); s.add_argument('--db', default='bapas.db'); s.add_argument('--shard'); s.add_argument('--out', default='photos')
    s.add_argument('--years'); s.add_argument('--keys')
    s = sub.add_parser('embed'); s.add_argument('--model'); s.add_argument('--photos'); s.add_argument('--out')
    s = sub.add_parser('build'); s.add_argument('--emb'); s.add_argument('--out'); s.add_argument('--model', default='dinov2-small-q8.onnx')
    a = ap.parse_args()
    globals()[a.cmd](a)
