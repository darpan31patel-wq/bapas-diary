"""Deep photo tags for the website search (Darpan, 25 Oct 2026: "red flowers or blue sky or smiling or food or animals").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org (the photos come from
R2, photos.bapas-diary.com). Runs on GitHub with an open SigLIP 2 model (no Claude, no paid service).

The model turns each photo into a list of numbers once (embed). Any word can then be compared with every photo in
seconds (score), so adding a new search word never needs the photos again.

    python3 tools/deep_tags.py sample --db bapas.db --years years.txt --n 2000 --out photos
    python3 tools/deep_tags.py embed --photos photos --out emb.npz
    python3 tools/deep_tags.py sheets --emb emb.npz --photos photos --out sheets

Every photo (.github/workflows/website-deeptags.yml): plan cuts the years in R2 into shards, each shard is fetched
and embedded on its own machine and kept as emb-YEAR-I-N.npz in the release deep-tags, then tags turns all of them
into deep-tags.json ({"ALBUM/FILE": "smiling, garland"}) with the words checked by eye (KEEP in tools/deep_words.py).
"""
import argparse, json, os, random, sqlite3, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = ('ViT-SO400M-14-SigLIP2', 'webli')
PHOTOS = 'https://photos.bapas-diary.com/'


def sample(a):
    years = {int(l) for l in open(a.years) if l.strip().isdigit()}
    db = sqlite3.connect(a.db)
    rows = [r for r in db.execute('SELECT year, album, file FROM photos') if r[0] in years]
    random.Random(a.seed).shuffle(rows)
    rows = rows[:a.n]
    print(f'{len(rows)} photos from years {sorted(years)}')
    fetch(rows, a.out, a.tier)


def plan(a):
    """The shards still to do: every year in R2 cut into pieces of about --size photos, minus those already kept."""
    years = sorted(int(l) for l in open(a.years) if l.strip().isdigit())
    have = set(open(a.have).read().split()) if a.have and os.path.exists(a.have) else set()
    db = sqlite3.connect(a.db)
    todo = []
    for y in years:
        n = db.execute('SELECT count(*) FROM photos WHERE year = ?', (y,)).fetchone()[0]
        parts = max(1, -(-n // a.size))
        todo += [f'{y}-{i}-{parts}' for i in range(parts) if f'emb-{y}-{i}-{parts}.npz' not in have]
    print(json.dumps(todo[:a.max]))


def shard(a):
    """Download one shard's small photos from R2: YEAR-I-N is the I-th of N slices of that year."""
    y, i, n = map(int, a.shard.split('-'))
    db = sqlite3.connect(a.db)
    rows = db.execute('SELECT year, album, file FROM photos WHERE year = ? ORDER BY album, file', (y,)).fetchall()
    k = -(-len(rows) // n)
    fetch(rows[i * k:(i + 1) * k], a.out, a.tier)


def fetch(rows, out, tier):
    def get(r):
        key = f'{r[1]}/{r[2]}'
        path = os.path.join(out, key)
        if os.path.exists(path):
            return 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        err = None
        for wait in (2, 10, 30):
            try:
                req = urllib.request.Request(PHOTOS + tier + '/' + urllib.request.quote(key), headers={'User-Agent': 'bapas-diary-tags'})
                data = urllib.request.urlopen(req, timeout=30).read()
                open(path, 'wb').write(data)
                return 1
            except Exception as e:
                err = e
                time.sleep(wait)
        print(key, err)
        return 0
    with ThreadPoolExecutor(16) as ex:
        print(sum(ex.map(get, rows)), 'of', len(rows), 'downloaded')


def tags(a):
    """Every kept photo number against the checked words (KEEP) -> {ALBUM/FILE: 'smiling, garland'}."""
    import glob, numpy as np
    sys.path.insert(0, os.path.dirname(__file__))
    from deep_words import KEEP
    w = np.load(a.words)
    names = list(w['words'])
    out = {}
    for f in sorted(glob.glob(os.path.join(a.emb, 'emb-*.npz'))):
        z = np.load(f)
        L = z['emb'].astype('float32') @ w['emb'].T * float(w['scale']) + float(w['bias'])
        for k, row in zip(z['keys'], L):
            got = [t for t, ws in KEEP.items() if any(row[names.index(n)] > b for n, b in ws)]
            if got:
                out[str(k)] = ', '.join(got)
    json.dump(out, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
    print(len(out), 'photos tagged')


def load_model():
    import torch, open_clip
    torch.set_num_threads(os.cpu_count() or 4)
    model, _, prep = open_clip.create_model_and_transforms(*MODEL)
    model.eval()
    return model, prep, open_clip.get_tokenizer(MODEL[0])


def embed(a):
    import numpy as np, torch
    from PIL import Image
    model, prep, _ = load_model()
    files = sorted(os.path.relpath(os.path.join(r, f), a.photos) for r, _, fs in os.walk(a.photos) for f in fs)
    keys, vecs, t0 = [], [], time.time()
    for i in range(0, len(files), a.batch):
        part, ims = [], []
        for f in files[i:i + a.batch]:
            try:
                ims.append(prep(Image.open(os.path.join(a.photos, f)).convert('RGB')))
                part.append(f)
            except Exception as e:
                print(f, e)
        if not ims:
            continue
        with torch.no_grad():
            v = model.encode_image(torch.stack(ims))
            v = v / v.norm(dim=-1, keepdim=True)
        keys += part
        vecs.append(v.numpy().astype('float16'))
        n = i + len(part)
        print(f'{n} of {len(files)}, {n / (time.time() - t0):.1f} photos a second', flush=True)
    np.savez_compressed(a.out, keys=np.array(keys), emb=np.concatenate(vecs))


def words(a):
    """Only the words: their numbers, so photos can be scored anywhere without the model."""
    import numpy as np, torch
    sys.path.insert(0, os.path.dirname(__file__))
    from deep_words import WORDS
    model, _, tok = load_model()
    with torch.no_grad():
        t = model.encode_text(tok(list(WORDS.values())))
        t = t / t.norm(dim=-1, keepdim=True)
    np.savez_compressed(a.out, words=np.array(list(WORDS)), emb=t.numpy().astype('float32'),
                        scale=model.logit_scale.exp().item(), bias=model.logit_bias.item())


def probs(emb, words):
    """Each word against each photo: SigLIP gives a real yes chance (0 to 1), not just a ranking."""
    import numpy as np, torch
    model, _, tok = load_model()
    with torch.no_grad():
        t = model.encode_text(tok(list(words.values())))
        t = t / t.norm(dim=-1, keepdim=True)
        logits = torch.from_numpy(emb.astype('float32')) @ t.T * model.logit_scale.exp() + model.logit_bias
        return torch.sigmoid(logits).numpy()


def sheets(a):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, os.path.dirname(__file__))
    from deep_words import WORDS
    z = np.load(a.emb)
    keys, p = list(z['keys']), probs(z['emb'], WORDS)
    names = list(WORDS)
    os.makedirs(a.out, exist_ok=True)
    json.dump({'words': names, 'keys': keys, 'p': np.round(p, 4).tolist()}, open(os.path.join(a.out, 'probs.json'), 'w'))
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    T, N, ROWS = 140, 10, 8

    def thumb(k):
        im = Image.open(os.path.join(a.photos, k)).convert('RGB')
        im.thumbnail((T, T))
        return im
    # one row per word: its best ten photos, with the chance on each
    for page in range(0, len(names), ROWS):
        sheet = Image.new('RGB', (190 + N * (T + 4), ROWS * (T + 24)), 'white')
        d = ImageDraw.Draw(sheet)
        for r, j in enumerate(range(page, min(page + ROWS, len(names)))):
            y = r * (T + 24)
            col = p[:, j]
            d.text((6, y + 10), names[j], fill='black', font=font)
            for lim, dy in ((0.5, 34), (0.2, 52), (0.05, 70)):
                d.text((6, y + dy), f'over {lim}: {(col > lim).sum()}', fill='#555', font=small)
            for c, i in enumerate(np.argsort(-col)[:N]):
                x = 190 + c * (T + 4)
                sheet.paste(thumb(keys[i]), (x, y + 2))
                d.text((x + 2, y + T + 4), f'{col[i]:.2f}', fill='red' if col[i] < a.bar else 'green', font=small)
        sheet.save(os.path.join(a.out, f'words-{page // ROWS + 1:02d}.jpg'), quality=80)
    # one tile per photo: every word over the bar, best first, so it reads the way the search would show it
    rnd = random.Random(1).sample(range(len(keys)), min(48, len(keys)))
    W, H = 360, 230
    for s in range(0, len(rnd), 12):
        sheet = Image.new('RGB', (4 * (W + 8), 3 * (H + 8)), 'white')
        d = ImageDraw.Draw(sheet)
        for c, i in enumerate(rnd[s:s + 12]):
            x, y = (c % 4) * (W + 8), (c // 4) * (H + 8)
            im = Image.open(os.path.join(a.photos, keys[i])).convert('RGB')
            im.thumbnail((W // 2, H))
            sheet.paste(im, (x, y))
            got = [(p[i, j], names[j]) for j in range(len(names)) if p[i, j] > a.bar]
            ty = y
            for v, n in sorted(got, reverse=True)[:14]:
                d.text((x + W // 2 + 6, ty), f'{n} {v:.2f}', fill='black', font=small)
                ty += 16
        sheet.save(os.path.join(a.out, f'photos-{s // 12 + 1:02d}.jpg'), quality=80)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('sample')
    s.add_argument('--db', default='bapas.db')
    s.add_argument('--years', required=True)
    s.add_argument('--n', type=int, default=2000)
    s.add_argument('--seed', type=int, default=25)
    s.add_argument('--tier', default='s')
    s.add_argument('--out', default='photos')
    e = sub.add_parser('embed')
    e.add_argument('--photos', required=True)
    e.add_argument('--out', default='emb.npz')
    e.add_argument('--batch', type=int, default=32)
    h = sub.add_parser('sheets')
    h.add_argument('--emb', required=True)
    h.add_argument('--photos', required=True)
    h.add_argument('--out', default='sheets')
    h.add_argument('--bar', type=float, default=0.1)
    w = sub.add_parser('words')
    w.add_argument('--out', default='words.npz')
    p = sub.add_parser('plan')
    p.add_argument('--db', default='bapas.db')
    p.add_argument('--years', required=True)
    p.add_argument('--have', help='names of the files already kept, one a line')
    p.add_argument('--size', type=int, default=2500)
    p.add_argument('--max', type=int, default=250)
    d = sub.add_parser('shard')
    d.add_argument('--db', default='bapas.db')
    d.add_argument('--shard', required=True)
    d.add_argument('--tier', default='s')
    d.add_argument('--out', default='photos')
    t = sub.add_parser('tags')
    t.add_argument('--emb', required=True, help='folder of emb-*.npz')
    t.add_argument('--words', default='words.npz')
    t.add_argument('--out', default='deep-tags.json')
    a = ap.parse_args()
    {'sample': sample, 'embed': embed, 'sheets': sheets, 'words': words, 'plan': plan, 'shard': shard, 'tags': tags}[a.cmd](a)


if __name__ == '__main__':
    main()
