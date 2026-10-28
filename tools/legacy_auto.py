#!/usr/bin/env python3
"""Weekly Legacy pairs with no one checking them (Darpan, 28 Oct 2026: "update every week, dont need to show me, just
go live"). Website only, no AI at run time: the same photo fingerprints and face scan as tools/legacy_match.py, with
far stricter bars so only pairs as clear as the ones picked by eye get through.

    python3 tools/legacy_auto.py --db bapas.db --emb emb/ --faces face/ --picks site/then-now-picks.json \
        --more more.json --large large-keys.txt --out more.json [--sheet cands.json]

more.json is the list of pairs added so far by this tool (same shape as site/then-now-picks.json); every run keeps
them and adds at most WEEK new ones. The live page reads it (/then-and-now/more.json) next to its own pairs.

A pair only gets in when: both photos show Bapa there in person (face sim >= .52, sharp, not a close up, no murti,
portrait, banner or the other guru), both clearly show the same scene (z >= 3 for one of its words, and it is the
photo's clearest scene or nearly), they look alike (look >= .87, or >= .91 at two different places), neither photo is already
on the page nor nearly the same as one that is (look > .93), and at most two new pairs per scene and two per place.
"""
import argparse, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legacy_match as lm   # noqa: E402

WEEK = 6
PER_SCENE = 2
# scenes that came out clean by eye on 28 Oct; Walking, Yagna, By the water and Lighting the lamp mostly found other things
AUTO = {'Taking a meal': 'Taking prasad', 'Outside the mandir': 'Darshan in the mandir', 'Reading': 'Reading',
        'Writing a letter': 'Writing letters', 'Morning puja': 'Morning puja', 'Arti': 'Arti',
        'Abhishek': 'Abhishek', 'Pushpanjali': 'Showers of petals', 'Giving prasad': 'Giving prasad',
        'With the children': 'With the children', 'On a swing': 'In the hindolo', 'In the garden': 'In the garden',
        'Planting a tree': 'Caring for a plant', 'Annakut': 'Annakut darshan', 'Nagar yatra': 'Darshan for the devotees',
        'Speaking to the assembly': 'Blessing the assembly', 'Cutting the ribbon': 'Opening ceremony',
        'Travelling': 'Travelling'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--emb', required=True)
    ap.add_argument('--faces', required=True)
    ap.add_argument('--picks', required=True)
    ap.add_argument('--more', default='', help='last run\'s more.json (kept)')
    ap.add_argument('--large', default='', help="R2's l/ key list, so new photos show in high res")
    ap.add_argument('--out', required=True)
    ap.add_argument('--sheet', default='', help='also write the new pairs for tools/legacy_sheets.py')
    ap.add_argument('--week', type=int, default=WEEK)
    a = ap.parse_args()
    picks = json.load(open(a.picks))
    more = json.load(open(a.more)) if a.more and os.path.exists(a.more) else []
    on = picks + more
    used = {f"{p[g]['album']}/{p[g]['file']}" for p in on for g in ('psm', 'msm')}
    keep, keys, E, w = lm.load(a, used)
    # stricter than the eye checked matcher: a clear face, not a close up
    strict = np.array([k in keep and keep[k]['sim'] >= .52 and keep[k]['sharp'] >= 50 and .05 <= keep[k]['h'] <= .3
                       and keep[k]['front'] >= .45 and k not in used for k in keys])
    inkeep = np.array([k in keep for k in keys])
    words = list(w['words'])
    T = w['emb'].astype(np.float32); T /= np.linalg.norm(T, axis=1, keepdims=True)
    L = float(w['scale']) * (E @ T.T) + float(w['bias'])
    L = (L - L[inkeep].mean(0)) / L[inkeep].std(0)
    psm = np.array([k in keep and keep[k]['psm'] for k in keys])
    U = E[[i for i, k in enumerate(keys) if k in used]]        # photos already on the page
    near = (E @ U.T).max(1) if len(U) else np.zeros(len(keys))
    allw = [words.index(x) for v in lm.SCENES.values() for x in v]
    top = L[:, allw].max(1)
    found = []
    for label, nice in AUTO.items():
        wi = [words.index(x) for x in lm.SCENES[label]]
        s = L[:, wi].max(1)
        ok = strict & (s >= top - .3) & (s >= 3) & (near <= .93)
        P, M = np.where(ok & psm)[0], np.where(ok & ~psm)[0]
        if not len(P) or not len(M):
            continue
        S = E[P] @ E[M].T
        same = np.array([[keep[keys[p]]['place'] == keep[keys[m]]['place'] for m in M] for p in P])
        good = (S >= .91) | (same & (S >= .87))
        if not good.any():
            continue
        sc = np.where(good, S + .05 * same + .02 * (s[P][:, None] + s[M][None, :]), -9)
        for _ in range(PER_SCENE):   # the best pairs of this scene, each photo once
            i, j = divmod(int(sc.argmax()), len(M))
            if sc[i, j] < 0:
                break
            found.append((float(sc[i, j]), label, nice, keys[P[i]], keys[M[j]], float(S[i, j])))
            sc[i, :] = -9; sc[:, j] = -9
    found.sort(reverse=True)
    large = set(l.strip() for l in open(a.large)) if a.large and os.path.exists(a.large) else set()
    new, per_place = [], {}
    for score, label, nice, kp, km, look in found:
        rp, rm = keep[kp], keep[km]
        pl = rp['place'] if rp['place'] == rm['place'] else ''
        if pl and per_place.get(pl, 0) >= 2:
            continue
        per_place[pl] = per_place.get(pl, 0) + 1

        def side(k, r):
            al, fi = k.split('/', 1)
            return dict(date=r['date'], cap=r['cap'], album=al, file=fi, r=round(r['W'] / r['H'], 3), place=r['place'],
                        t='l' if f'l/{k}' in large else 'm')
        new.append(dict(place=pl, moment=nice, psm=side(kp, rp), msm=side(km, rm), auto=label, look=round(look, 3)))
        if len(new) >= a.week:
            break
    json.dump(more + new, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print(len(new), 'new pairs,', len(more + new), 'in more.json')
    for n in new:
        print(' ', n['moment'], '|', n['psm']['place'], n['psm']['date'], '|', n['msm']['place'], n['msm']['date'])
    if a.sheet:
        json.dump({'scenes': {'auto': [dict(psm=f"{n['psm']['album']}/{n['psm']['file']}", msm=f"{n['msm']['album']}/{n['msm']['file']}",
                                             look=n['look']) for n in new]},
                   'old': [], 'info': {f"{n[g]['album']}/{n[g]['file']}": dict(date=n[g]['date'], place=n[g]['place'], cap=n[g]['cap'], w=1, h=1)
                                       for n in new for g in ('psm', 'msm')}}, open(a.sheet, 'w'), indent=1)


if __name__ == '__main__':
    main()
