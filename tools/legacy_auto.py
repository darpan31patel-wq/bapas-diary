#!/usr/bin/env python3
"""Weekly Legacy pairs with no one checking them (Darpan, 28 Oct 2026: "update every week, dont need to show me, just
go live"). Website only, no AI at run time.

Darpan, 29 Oct 2026, after the robot's first 6 pairs did not match: a pair needs the caption AND the picture to match
("not just caption though, it needs to assess the picture too. sometime picture matches, but caption doesnt or vice
versa"). So a pair only gets in when:
  - both captions name the same moment (one of TRUSTED, the caption words of tools/legacy_more.py that held up by eye),
  - the two pictures look alike (SigLIP fingerprint closeness >= LOOK, or >= LOOK_PLACE at the same place),
  - both photos show Bapa there in person, sharp, not a close up (face scan; no murti, portrait, banner, other guru),
  - neither photo is already on the page nor nearly the same as one that is (> .93),
  - at most PER_SCENE new pairs per moment and two per place, WEEK a week.
Pairs the robot added before are checked again by the same rule and dropped when they fail.

    python3 tools/legacy_auto.py --db bapas.db --emb emb/ --faces face/ --picks site/then-now-picks.json \
        --more more.json --large large-keys.txt --out more.json [--sheet cands.json]

more.json is the list of pairs added so far by this tool (same shape as site/then-now-picks.json); the live page reads
it (/then-and-now/more.json) next to its own pairs.
"""
import argparse, json, os, re, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legacy_match as lm   # noqa: E402
from legacy_more import THEMES   # noqa: E402

WEEK = 6
PER_SCENE = 2
LOOK, LOOK_PLACE = .91, .89
# moment in the caption -> heading on the page; only the moments whose pairs came out right by eye on 29 Oct
TRUSTED = {
    'Pradakshina': 'Pradakshina', 'Garlanded with love': 'Honoured with garlands', 'Arti': 'Arti',
    'Morning puja': 'Morning puja', 'Abhishek': 'Abhishek', 'Murti pratishtha': 'Murti pratishtha',
    'Darshan of Thakorji': 'Engrossed in darshan', 'Showers of petals': 'Showers of petals',
    'Annakut darshan': 'Annakut darshan', 'In the hindolo': 'Swinging Thakorji in the hindolo',
    'Reading letters': 'Reading letters from devotees', 'Writing letters': 'Writing letters',
    'Sanctifying the books': 'Sanctifying the books', 'Blessing the assembly': 'Blessing the assembly',
    'Jai Swaminarayan': 'Jai Swaminarayan to all', 'Shilanyas': 'Shilanyas vidhi', 'Applying chandlo': 'Applying the chandlo',
    'Mala': 'Turning the mala', 'Reading the scriptures': 'Reading the scriptures', 'Blessing the mangoes': 'Blessing the mangoes',
    'On the swing': 'Swinging Thakorji in the hindolo', 'Lighting the lamp': 'Lighting the lamp', 'Chopda pujan': 'Chopda pujan',
}
# flags, chandlo and the like: the caption word alone also catches 'waves' or 'tilak' on someone else, so these
# moments need the picture to be closer still
CLOSER = {'Applying chandlo': .9, 'Blessing the assembly': .93, 'Jai Swaminarayan': .95, 'Darshan of Thakorji': .94}


# a few caption words also name things Bapa only looks at ('observes hindolo decorations'): the robot needs the act
OWN = {'In the hindolo': r'swings?\b.*hindol', 'On the swing': r'swings?\b.*(hindol|swing|jhul)'}


def rx(t):
    return OWN.get(t, THEMES[t])


def tidy(place):
    """'2004, Houston' (a few tour albums put the year first) -> 'Houston'"""
    return re.sub(r'^\d{4},\s*', '', place or '')


def moments(cap):
    return {t for t in TRUSTED if re.search(rx(t), cap or '', re.I)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--emb', required=True)
    ap.add_argument('--faces', required=True)
    ap.add_argument('--picks', required=True)
    ap.add_argument('--more', default='', help='last run\'s more.json (kept when its pairs still pass)')
    ap.add_argument('--large', default='', help="R2's l/ key list, so new photos show in high res")
    ap.add_argument('--out', required=True)
    ap.add_argument('--sheet', default='', help='also write the new pairs for tools/legacy_sheets.py')
    ap.add_argument('--week', type=int, default=WEEK)
    a = ap.parse_args()
    picks = json.load(open(a.picks))
    more = json.load(open(a.more)) if a.more and os.path.exists(a.more) else []
    key = lambda s: f"{s['album']}/{s['file']}"   # noqa: E731
    keep, keys, E, _ = lm.load(a, {key(p[g]) for p in picks + more for g in ('psm', 'msm')})
    idx = {k: i for i, k in enumerate(keys)}

    def look(kp, km):
        return float(E[idx[kp]] @ E[idx[km]]) if kp in idx and km in idx else 0.

    def passes(kp, km):
        rp, rm = keep.get(kp), keep.get(km)
        if not rp or not rm:
            return None
        both = moments(rp['cap']) & moments(rm['cap'])
        same = tidy(rp['place']) == tidy(rm['place']) and tidy(rp['place']) != ''
        for t in both:
            bar = max(CLOSER.get(t, 0), LOOK_PLACE if same else LOOK)
            if look(kp, km) >= bar:
                return t
        return None
    # the robot's earlier pairs face the same rule
    old = [p for p in more if passes(key(p['psm']), key(p['msm']))]
    print(len(more) - len(old), 'earlier robot pairs dropped (caption or picture did not match)')
    used = {key(p[g]) for p in picks + old for g in ('psm', 'msm')}
    U = E[[idx[k] for k in used if k in idx]]
    near = (E @ U.T).max(1) if len(U) else np.zeros(len(keys))
    strict = {k for k in keys if k in keep and keep[k]['sim'] >= .52 and keep[k]['sharp'] >= 50 and .05 <= keep[k]['h'] <= .3
              and keep[k]['front'] >= .45 and k not in used and near[idx[k]] <= .93}
    found = []
    for t in TRUSTED:
        R = re.compile(rx(t), re.I)
        P = [k for k in strict if keep[k]['psm'] and R.search(keep[k]['cap'])]
        M = [k for k in strict if not keep[k]['psm'] and R.search(keep[k]['cap'])]
        if not P or not M:
            continue
        S = E[[idx[k] for k in P]] @ E[[idx[k] for k in M]].T
        pp = np.array([tidy(keep[k]['place']) for k in P]); mp = np.array([tidy(keep[k]['place']) for k in M])
        same = (pp[:, None] == mp[None, :]) & (pp[:, None] != '')
        bar = np.maximum(np.where(same, LOOK_PLACE, LOOK), CLOSER.get(t, 0))
        sc = np.where(S >= bar, S + .03 * same, -9)
        for _ in range(PER_SCENE):
            i, j = divmod(int(sc.argmax()), len(M))
            if sc[i, j] < 0:
                break
            found.append((float(sc[i, j]), t, P[i], M[j], float(S[i, j])))
            sc[i, :] = -9; sc[:, j] = -9
    found.sort(reverse=True)
    large = set(l.strip() for l in open(a.large)) if a.large and os.path.exists(a.large) else set()
    new, per_place, taken = [], {}, set()
    for score, t, kp, km, lk in found:
        if kp in taken or km in taken:
            continue
        rp, rm = keep[kp], keep[km]
        pl = tidy(rp['place']) if tidy(rp['place']) == tidy(rm['place']) else ''
        if pl and per_place.get(pl, 0) >= 2:
            continue
        per_place[pl] = per_place.get(pl, 0) + 1
        taken |= {kp, km}

        def side(k, r):
            al, fi = k.split('/', 1)
            return dict(date=r['date'], cap=r['cap'], album=al, file=fi, r=round(r['W'] / r['H'], 3), place=tidy(r['place']),
                        t='l' if f'l/{k}' in large or not large else 'm')
        new.append(dict(place=pl, moment=TRUSTED[t], psm=side(kp, rp), msm=side(km, rm), auto=t, look=round(lk, 3)))
        if len(new) >= a.week:
            break
    json.dump(old + new, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print(len(new), 'new pairs,', len(old + new), 'in more.json')
    for n in new:
        print(' ', n['moment'], '|', n['psm']['place'], n['psm']['date'], n['psm']['cap'][:50], '|', n['msm']['place'],
              n['msm']['date'], n['msm']['cap'][:50], n['look'])
    if a.sheet:
        json.dump({'scenes': {'auto': [dict(psm=key(n['psm']), msm=key(n['msm']), look=n['look']) for n in new]},
                   'old': [], 'info': {key(n[g]): dict(date=n[g]['date'], place=n[g]['place'], cap=n[g]['cap'], w=1, h=1)
                                       for n in new for g in ('psm', 'msm')}}, open(a.sheet, 'w'), indent=1)


if __name__ == '__main__':
    main()
