"""The wide word list for Search (Darpan, 26 Oct 2026: grass, blue flowers, plane, football found nothing).

Website only, like tools/deep_tags.py: nothing touches the daily 2pm picture, nothing comes from baps.org.

    python3 tools/deep_big.py words --out words-big.npz      # the numbers of every word in BIG (needs the model)
    python3 tools/deep_big.py fetch --keys keys.txt --out photos   # only these photos from R2, to check by eye
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


def keys(a):
    rows = []
    for l in open(a.keys):
        if '/' in l.strip():
            album, file = l.strip().rsplit('/', 1)
            rows.append((0, album, file))
    fetch(rows, a.out, a.tier)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    w = sub.add_parser('words')
    w.add_argument('--out', default='words-big.npz')
    f = sub.add_parser('fetch')
    f.add_argument('--keys', required=True)
    f.add_argument('--tier', default='s')
    f.add_argument('--out', default='photos')
    a = ap.parse_args()
    {'words': words, 'fetch': keys}[a.cmd](a)


if __name__ == '__main__':
    main()
