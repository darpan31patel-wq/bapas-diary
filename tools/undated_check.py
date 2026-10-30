"""Checks on the undated photos before they go into Search (Darpan, 30 Oct 2026). Website only, run on GitHub
(.github/workflows/undated-build.yml), where the R2 copies of the dated photos can be reached.

    python3 tools/undated_check.py match --photos out/s/undated --index image --out match.json
    python3 tools/undated_check.py same --photos out/s/undated --match match.json --out same.json
    python3 tools/undated_check.py kinds --emb emb-undated.npz --out kinds.json
    python3 tools/undated_check.py sheets --photos out/s/undated --undated out/undated.json --match match.json --kinds kinds.json --out sheets

match: each photo against every dated photo in the diary with the Search by photo numbers (the DINOv2 model and the
  96 byte answers of release image-search, tools/image_index.py on branch hi1iz6): the three nearest, with how many of
  the 768 answers differ (0 is the same photo). A photo already in the diary with its date needs no undated copy.
kinds: what sort of picture each is, with the open SigLIP model of the deep tags (tools/deep_tags.py): Bapa in person,
  or a statue, murti, poster, collage, framed photo, painting, cartoon, building, sign or pasted on background. Darpan's
  rule for Bapa's pages (25 Oct 2026): only photos with Bapa in them in person.
sheets: contact sheets to check both by eye before any bar is set.
"""
import argparse, io, json, os, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PHOTOS = 'https://photos.bapas-diary.com/'
M = 'an elderly Hindu monk in saffron robes'
KINDS = {
    'in person': f'a real photograph of {M}',
    'statue': 'a golden or marble statue of a seated monk',
    'murti': 'richly dressed Hindu murtis in a mandir shrine',
    'poster': 'a poster or graphic design with large printed text',
    'collage': 'a collage grid of many small photos',
    'framed': 'a framed photograph of a monk on a wall, garlanded',
    'painting': 'a painting or drawing of a monk',
    'cartoon': 'a cartoon illustration',
    'building': 'a building or temple with no people',
    'sign': 'a street sign',
    'pasted': 'a photo of a monk pasted onto a famous landmark',
}


def match(a):
    import numpy as np, onnxruntime as ort
    from PIL import Image
    meta = json.load(open(os.path.join(a.index, 'meta.json')))
    keys = json.load(open(os.path.join(a.index, 'keys.json')))
    bits = np.concatenate([np.fromfile(os.path.join(a.index, v), np.uint8) for v in meta['vecs']]).reshape(-1, 96)
    B = np.unpackbits(bits, axis=1).astype(np.float32) * 2 - 1
    mc, mm = np.array(meta['mc'], 'f4'), np.array(meta['mm'], 'f4')
    sess = ort.InferenceSession(os.path.join(a.index, meta['model']), providers=['CPUExecutionProvider'])
    mean, std = np.array((0.485, 0.456, 0.406), 'f4'), np.array((0.229, 0.224, 0.225), 'f4')
    out = {}
    for n, f in enumerate(sorted(os.listdir(a.photos))):
        im = Image.open(os.path.join(a.photos, f)).convert('RGB').resize((meta['side'], meta['side']), Image.BILINEAR)
        x = ((np.asarray(im, 'f4') / 255 - mean) / std).transpose(2, 0, 1)[None]
        t = sess.run(None, {'x': x})[0][0]
        cls, avg = t[0], t[1:].mean(0)
        q = np.concatenate([cls / np.linalg.norm(cls) > mc, avg / np.linalg.norm(avg) > mm]).astype(np.float32) * 2 - 1
        s = B @ q
        top = np.argsort(-s)[:3]
        out[f] = [[keys[j], int((768 - s[j]) // 2)] for j in top]
        if n % 200 == 0:
            print(n, 'photos matched', flush=True)
    json.dump(out, open(a.out, 'w'), separators=(',', ':'))


def same(a):
    """The nearest dated photos (match) checked point by point: ORB corners in both, matched, and the share that agree
    on one shift and scale (RANSAC). The same photo, even cropped or touched up, keeps many agreeing points; a photo
    of the same moment from a step to the side keeps few. Writes {photo: [ALBUM/FILE, points that agree, distance]}."""
    import cv2, numpy as np
    from PIL import Image
    m = json.load(open(a.match))
    orb = cv2.ORB_create(1500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    def feats(im):
        g = cv2.cvtColor(np.array(im.convert('RGB')), cv2.COLOR_RGB2GRAY)
        return orb.detectAndCompute(g, None)

    def agree(f1, f2):
        (k1, d1), (k2, d2) = f1, f2
        if d1 is None or d2 is None or len(k1) < 8 or len(k2) < 8:
            return 0
        ms = bf.match(d1, d2)
        if len(ms) < 8:
            return 0
        p1 = np.float32([k1[x.queryIdx].pt for x in ms]); p2 = np.float32([k2[x.trainIdx].pt for x in ms])
        _, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=4)
        return int(inl.sum()) if inl is not None else 0

    def remote(k):
        for wait in (2, 10, 0):
            try:
                req = urllib.request.Request(PHOTOS + 's/' + urllib.parse.quote(k), headers={'User-Agent': 'bapas-diary-undated'})
                return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read()))
            except Exception:
                import time; time.sleep(wait)
        return None
    out = {}
    from concurrent.futures import ThreadPoolExecutor
    todo = [(f, k, d) for f, v in m.items() for k, d in v if d < a.max]
    with ThreadPoolExecutor(16) as ex:
        ims = dict(zip([(f, k) for f, k, _ in todo], ex.map(lambda t: remote(t[1]), todo)))
    for f, k, d in todo:
        im = ims[(f, k)]
        if im is None:
            continue
        n = agree(feats(Image.open(os.path.join(a.photos, f))), feats(im))
        if f not in out or n > out[f][1]:
            out[f] = [k, n, d]
    json.dump(out, open(a.out, 'w'), separators=(',', ':'))
    print(len(out), 'checked,', sum(1 for v in out.values() if v[1] >= 30), 'with 30 or more points that agree')


def kinds(a):
    import numpy as np
    from deep_tags import probs
    z = np.load(a.emb)
    p = probs(z['emb'], KINDS)
    json.dump({os.path.basename(str(k)): {w: round(float(v), 4) for w, v in zip(KINDS, row)} for k, row in zip(z['keys'], p)},
              open(a.out, 'w'), separators=(',', ':'))


def sheets(a):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
    T, N = 150, 12
    os.makedirs(a.out, exist_ok=True)

    def remote(k):
        try:
            req = urllib.request.Request(PHOTOS + 's/' + urllib.parse.quote(k), headers={'User-Agent': 'bapas-diary-undated'})
            return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert('RGB')
        except Exception:
            return Image.new('RGB', (T, T), 'grey')

    def sheet(cells, name):
        rows = -(-len(cells) // N)
        s = Image.new('RGB', (N * T, max(1, rows) * (T + 16)), 'white')
        d = ImageDraw.Draw(s)
        for i, (im, label) in enumerate(cells):
            im = im.copy(); im.thumbnail((T, T))
            x, y = (i % N) * T, (i // N) * (T + 16)
            s.paste(im, (x, y)); d.text((x + 2, y + T + 1), label, fill='black', font=font)
        s.save(os.path.join(a.out, name), quality=80)

    local = lambda f: Image.open(os.path.join(a.photos, f)).convert('RGB')
    m = json.load(open(a.match))
    # the same photo in the dated diary: side by side, nearest first, in bands of difference
    for lo, hi in ((0, 40), (40, 70), (70, 100), (100, 130), (130, 160)):
        pairs = [(f, v[0]) for f, v in sorted(m.items(), key=lambda kv: kv[1][0][1]) if lo <= v[0][1] < hi][:30]
        cells = []
        for f, (k, dist) in pairs:
            cells += [(local(f), f), (remote(k), f'{dist} {k}'[:24])]
        sheet(cells, f'match-{lo:03d}.jpg')
    if a.same and os.path.exists(a.same):
        sm = json.load(open(a.same))
        for lo, hi in ((0, 10), (10, 20), (20, 30), (30, 50), (50, 1000)):
            pairs = sorted(((f, v) for f, v in sm.items() if lo <= v[1] < hi), key=lambda x: -x[1][1])[:30]
            cells = []
            for f, (k, n, d) in pairs:
                cells += [(local(f), f), (remote(k), f'{n}pt {k}'[:24])]
            sheet(cells, f'same-{lo:03d}.jpg')
        return
    k = json.load(open(a.kinds))
    for w in KINDS:
        top = sorted(k, key=lambda f: -k[f][w])[:96]
        sheet([(local(f), f"{f[:5]} {k[f][w]:.3f}") for f in top], f'kind-{w.replace(" ", "-")}.jpg')
    # the photos most unlike Bapa in person, to see what would be left out
    low = sorted(k, key=lambda f: k[f]['in person'])[:192]
    sheet([(local(f), f"{f[:5]} {k[f]['in person']:.3f}") for f in low[:96]], 'least-in-person-1.jpg')
    sheet([(local(f), f"{f[:5]} {k[f]['in person']:.3f}") for f in low[96:]], 'least-in-person-2.jpg')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('match'); s.add_argument('--photos'); s.add_argument('--index'); s.add_argument('--out')
    s = sub.add_parser('same'); s.add_argument('--photos'); s.add_argument('--match'); s.add_argument('--out')
    s.add_argument('--max', type=int, default=200)
    s = sub.add_parser('kinds'); s.add_argument('--emb'); s.add_argument('--out')
    s = sub.add_parser('sheets'); s.add_argument('--photos'); s.add_argument('--undated'); s.add_argument('--match')
    s.add_argument('--kinds'); s.add_argument('--same'); s.add_argument('--out')
    a = ap.parse_args()
    globals()[a.cmd](a)
