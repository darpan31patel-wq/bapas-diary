"""The wide word list for Search (Darpan, 26 Oct 2026: grass, blue flowers, plane, football found nothing).

Website only, like tools/deep_tags.py: nothing touches the daily 2pm picture, nothing comes from baps.org.

    python3 tools/deep_big.py words --out words-big.npz      # the numbers of every word in BIG (needs the model)
    python3 tools/deep_big.py ladder --emb emb --words words-big.npz --out ladder   # sheets to set each word's bar by eye
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from deep_tags import load_model, fetch


def words(a):
    import numpy as np, torch
    from deep_words_big import BIG
    model, _, tok = load_model()
    vecs = []
    with torch.no_grad():
        ps = list(BIG.values())
        for i in range(0, len(ps), 64):
            t = model.encode_text(tok(ps[i:i + 64]))
            vecs.append((t / t.norm(dim=-1, keepdim=True)).numpy())
    np.savez_compressed(a.out, words=np.array(list(BIG)), prompts=np.array(ps), emb=np.concatenate(vecs).astype('float32'),
                        scale=model.logit_scale.exp().item(), bias=model.logit_bias.item())
    print(len(BIG), 'words')


RANKS = [1, 2, 3, 4, 6, 8, 11, 15, 20, 27, 36, 48, 64, 85, 110, 150, 200, 280, 400, 560, 800, 1100, 1600, 2300, 3200,
         4500, 6400]


def ladder(a):
    """One row a word: the photos at rank 1, 2, 3 ... 6400 among all kept photos, with the score under each, so the
    place where the photos stop being right can be read off by eye and becomes that word's bar."""
    import glob, numpy as np
    from PIL import Image, ImageDraw, ImageFont
    w = np.load(a.words)
    names = list(w['words'])
    keys, E = [], []
    for f in sorted(glob.glob(os.path.join(a.emb, 'emb-*.npz'))):
        z = np.load(f)
        keys += [str(k) for k in z['keys']]
        E.append(z['emb'].astype('float32'))
    L = np.concatenate(E) @ w['emb'].T * float(w['scale']) + float(w['bias'])
    rows = {}
    for j in range(len(names)):
        o = np.argsort(-L[:, j])
        rows[j] = [(r, keys[o[r - 1]], L[o[r - 1], j]) for r in RANKS if r <= len(o)]
    need = sorted({k for r in rows.values() for _, k, _ in r})
    fetch([(0, *k.rsplit('/', 1)) for k in need], a.photos, a.tier)
    T, PER = 110, 9
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    os.makedirs(a.out, exist_ok=True)
    for p in range(0, len(names), PER):
        sh = Image.new('RGB', (130 + len(RANKS) * (T + 3), PER * (T + 18)), 'white')
        d = ImageDraw.Draw(sh)
        for r, j in enumerate(range(p, min(p + PER, len(names)))):
            y = r * (T + 18)
            d.text((4, y + 8), names[j], fill='black', font=font)
            for c, (rk, k, v) in enumerate(rows[j]):
                x = 130 + c * (T + 3)
                try:
                    im = Image.open(os.path.join(a.photos, k)).convert('RGB')
                    im.thumbnail((T, T))
                    sh.paste(im, (x, y))
                except Exception:
                    pass
                d.text((x + 1, y + T + 2), f'#{rk} {v:.1f}', fill='#333', font=small)
        sh.save(os.path.join(a.out, f'ladder-{p // PER + 1:03d}.jpg'), quality=75)
    print(len(names), 'words,', len(keys), 'photos')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('words')
    w.add_argument('--out', default='words-big.npz')
    f = sub.add_parser('ladder')
    f.add_argument('--emb', required=True, help='folder of emb-*.npz')
    f.add_argument('--words', default='words-big.npz')
    f.add_argument('--photos', default='photos')
    f.add_argument('--tier', default='s')
    f.add_argument('--out', default='ladder')
    a = ap.parse_args()
    {'words': words, 'ladder': ladder}[a.cmd](a)


if __name__ == '__main__':
    main()
