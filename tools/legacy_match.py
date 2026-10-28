#!/usr/bin/env python3
"""Legacy pairs found by what is IN the photos, not only by the caption (Darpan, 28 Oct 2026: "the matching should
consider the actual scene, surroundings, activities and visual similarities ... if Bapa is eating, find other pictures
of him eating, even if they were taken at completely different locations").

Website only. Reads bapas.db, the face scan (release website-faces face2-*.json.gz: Bapa there in person, sharp, how
big) and the SigLIP 2 photo fingerprints the deep tagging already made for every photo (release deep-tags emb-*.npz and
words.npz). No photo is downloaded here.

    python3 tools/legacy_match.py --db bapas.db --emb emb/ --faces face/ --out site/legacy-cands.json

For every scene or activity in SCENES it takes the photos of Pramukh Swami Maharaj and of Mahant Swami Maharaj that the
fingerprint says show it most clearly, then pairs them so the two photos LOOK alike (fingerprint closeness), with a
bonus for the same place. It writes the best few pairs of each scene for Claude to check by eye (tools/legacy_sheets.py
draws them), and the same closeness for the pairs already on the page (site/then-now-picks.json) so weak ones show up.
"""
import argparse, glob, gzip, json, os, re, sqlite3

import numpy as np

PSM_UNTIL = '2016-08-13'
# label on the page -> words.npz words that describe it (the photo's best one must be among them)
SCENES = {
    'Taking a meal': ['eating', 'thal', 'food'],
    'Outside the mandir': ['shikhar', 'mandir', 'carvings', 'dome'],
    'Walking': ['walking'],
    'Reading': ['reading', 'book'],
    'Writing a letter': ['writing', 'letter', 'signing'],
    'Morning puja': ['puja'],
    'Arti': ['arti', 'lamps'],
    'Abhishek': ['abhishek'],
    'Pushpanjali': ['pushpanjali', 'throwing flowers', 'petals'],
    'Giving prasad': ['giving prasad', 'sweets', 'fruit'],
    'With the children': ['children', 'baby', 'patting head'],
    'On a swing': ['on a swing'],
    'In the garden': ['garden', 'trees', 'grass'],
    'By the water': ['sea', 'river', 'lake', 'on a boat'],
    'Travelling': ['in a car', 'on a plane', 'airport', 'plane'],
    'Planting a tree': ['planting tree'],
    'Lighting the lamp': ['lighting lamp'],
    'Cutting the ribbon': ['cutting ribbon', 'unveiling'],
    'Annakut': ['annakut'],
    'Yagna': ['yagna', 'fire'],
    'Nagar yatra': ['procession', 'nagar yatra', 'on a chariot'],
    'Speaking to the assembly': ['speaking', 'microphone'],
}
OTHER = {True: (r'Pramukh Swami|Swamishri|\bBapa\b|\bHDH\b', r'Mahant Swami'),
         False: (r'Mahant Swami|Swamishri|\bBapa\b|\bHDH\b', r'Pramukh Swami')}
# a photo OF Bapa (murti, portrait, banner, screen) never counts: he must be there in person
LIKENESS = re.compile(r"(?:'s|’s) (?:murti|portrait|photo|image)|\bportrait\b|murti of (?:Brahmaswarup|Pramukh|Mahant|Param)"
                      r"|banner|poster|hoarding|cut-?out|on (?:the )?screen|video|painting|framed", re.I)


def load(a, extra=()):
    db = sqlite3.connect(a.db)
    rows, albums = {}, {}
    for al, fi, d, place, cap, bapa in db.execute(
            'select album, file, coalesce(date, date_from), place, caption, is_bapa from photos'):
        if not d:
            continue
        psm = d < PSM_UNTIL
        this, that = OTHER[psm]
        c = cap or ''
        mine, theirs = bool(re.search(this, c)), bool(re.search(that, c))
        n = albums.setdefault(al, [0, 0]); n[0] += mine; n[1] += theirs
        rows[f'{al}/{fi}'] = dict(album=al, file=fi, date=d, place=place or '', cap=c, psm=psm, mine=mine, theirs=theirs)
    faces = {}
    for f in glob.glob(os.path.join(a.faces, 'face2-*.json.gz')):
        faces.update(json.load(gzip.open(f, 'rt')))
    keep = {}
    for k, r in rows.items():
        rec = faces.get(k)
        if not rec or not rec[0]:
            continue
        sim, x, y, w, h, front, sharp, bright, W, H, n, other = rec[:12]
        if sim < .5 or other >= sim or sharp < 40 or bright < 40 or not (.03 <= h <= .4):
            continue
        if not r['mine'] and (r['theirs'] or albums[r['album']][1] > albums[r['album']][0]):
            continue
        if LIKENESS.search(r['cap']):
            continue
        r.update(sim=sim, h=h, front=front, sharp=sharp, W=W, H=H)
        keep[k] = r
    keys, embs = [], []
    for f in sorted(glob.glob(os.path.join(a.emb, 'emb-*.npz'))):
        z = np.load(f)
        m = np.array([k in keep or k in extra for k in z['keys']])
        if m.any():
            keys += list(z['keys'][m]); embs.append(z['emb'][m].astype(np.float32))
    E = np.vstack(embs)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    w = np.load(os.path.join(a.emb, 'words.npz'), allow_pickle=True)
    return keep, keys, E, w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--emb', required=True)
    ap.add_argument('--faces', required=True)
    ap.add_argument('--picks', default='site/then-now-picks.json')
    ap.add_argument('--out', default='site/legacy-cands.json')
    ap.add_argument('--top', type=int, default=60, help='photos of each guru kept per scene')
    ap.add_argument('--pairs', type=int, default=8, help='pairs per scene for the contact sheet')
    a = ap.parse_args()
    old = json.load(open(a.picks))
    extra = {f"{p[g]['album']}/{p[g]['file']}" for p in old for g in ('psm', 'msm')}
    keep, keys, E, w = load(a, extra)
    inkeep = np.array([k in keep for k in keys])
    words = list(w['words'])
    T = w['emb'].astype(np.float32); T /= np.linalg.norm(T, axis=1, keepdims=True)
    L = float(w['scale']) * (E @ T.T) + float(w['bias'])     # SigLIP logits, photo x word
    # each word's logits sit at very different levels (garden ~-25, eating ~-8), so compare how far above its own usual
    # level a photo is for that word (z score over every photo with Bapa)
    L = (L - L[inkeep].mean(0)) / L[inkeep].std(0)
    psm = np.array([k in keep and keep[k]['psm'] for k in keys])
    msm = np.array([k in keep and not keep[k]['psm'] for k in keys])
    idx = {k: i for i, k in enumerate(keys)}
    print(inkeep.sum(), 'photos with Bapa there in person,', psm.sum(), 'PSM', msm.sum(), 'MSM', flush=True)
    allw = [words.index(x) for v in SCENES.values() for x in v]
    top = L[:, allw].max(1)                                   # each photo's clearest scene word
    out = {'scenes': {}, 'old': []}
    used = set()
    for label, ws in SCENES.items():
        wi = [words.index(x) for x in ws]
        s = L[:, wi].max(1)
        ok = (s >= top - .5) & (s > 3)
        sides = []
        for g in (psm, msm):
            c = np.where(ok & g)[0]
            c = c[np.argsort(-s[c])][:a.top]
            sides.append(c)
        P, M = sides
        if not len(P) or not len(M):
            print(label, 'no photos', len(P), len(M)); continue
        S = E[P] @ E[M].T                                     # how alike each pair looks
        pl = np.array([[keep[keys[p]]['place'] == keep[keys[m]]['place'] for m in M] for p in P])
        sc = S + .05 * pl + .02 * (s[P][:, None] + s[M][None, :])
        pairs, up, um = [], set(), set()
        for flat in np.argsort(-sc, axis=None):
            i, j = divmod(int(flat), len(M))
            p, m = keys[P[i]], keys[M[j]]
            if i in up or j in um or (p, m) in used:
                continue
            up.add(i); um.add(j); used.add((p, m))
            pairs.append(dict(psm=p, msm=m, look=round(float(S[i, j]), 3), same_place=bool(pl[i, j]),
                              ps=round(float(s[P[i]]), 1), ms=round(float(s[M[j]]), 1)))
            if len(pairs) >= a.pairs:
                break
        out['scenes'][label] = pairs
        print(f'{label}: {len(P)} PSM, {len(M)} MSM, best look {pairs[0]["look"]}', flush=True)
    for p in old:
        kp, km = f"{p['psm']['album']}/{p['psm']['file']}", f"{p['msm']['album']}/{p['msm']['file']}"
        look = round(float(E[idx[kp]] @ E[idx[km]]), 3) if kp in idx and km in idx else None
        out['old'].append(dict(place=p['place'], moment=p['moment'], psm=kp, msm=km, look=look,
                               psm_ok=kp in keep, msm_ok=km in keep))
    out['info'] = {k: dict(date=keep[k]['date'], place=keep[k]['place'], cap=keep[k]['cap'], w=keep[k]['W'], h=keep[k]['H'])
                   for v in out['scenes'].values() for p in v for k in (p['psm'], p['msm'])}
    json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
