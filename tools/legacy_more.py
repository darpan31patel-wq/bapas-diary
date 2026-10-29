#!/usr/bin/env python3
"""Many more Legacy pairs (Darpan, 29 Oct 2026, of the Sarangpur pradakshina and With the children pairs: "These are
PERFECT! Want more like this"). Website only, nothing downloaded, no baps.org.

    python3 tools/legacy_more.py --db bapas.db --emb emb/ --faces face/ --live live-pairs.json --out site/legacy-more-cands.json

The same in person photos as tools/legacy_match.py (face scan: Bapa there, sharp, no murti, portrait, banner or the
other guru), but the moment comes from the caption on BOTH sides (THEMES: pradakshina, garlands, the children, arti,
puja ...), then the two photos that LOOK most alike (SigLIP fingerprints) are paired, with a bonus for the same place.
Each photo is used once, never one already on the page (or nearly the same as one). Claude checks every pair by eye on
the contact sheets (tools/legacy_sheets.py) before any goes on the page.
"""
import argparse, json, re, sys, os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legacy_match as lm   # noqa: E402

# heading on the page -> caption words (both photos' captions must have them)
THEMES = {
    'Pradakshina': r'pradakshin',
    'With the children': r'\bchild|children|\bbalak|\bbalika|\bbaby\b|\bkids?\b|infant|toddler',
    'Garlanded with love': r'\bis garlanded|garlanded by|offer(s|ed)? (a )?garland|honou?red with (a )?garland',
    'Garlanding the devotees': r'\bgarlands (a|the|two|young|him|her|devotee|sant|youth)',
    'Arti': r'\barti\b|\baarti\b',
    'Morning puja': r'morning puja|\bpuja\b',
    'Abhishek': r'abhishek',
    'Murti pratishtha': r'pratishtha',
    'Darshan of Thakorji': r'darshan of (thakorji|the murtis|shri|bhagwan)|doing darshan|does darshan|engrossed in darshan',
    'Showers of petals': r'pushpanjali|showers? (of )?(flower|petal)|petals',
    'Annakut darshan': r'annakut',
    'In the hindolo': r'hindol',
    'Reading letters': r'reads? (a |the )?letters?|reading letters',
    'Writing letters': r'writes? (a |the )?letters?|writing letters|signs? letters',
    'Sanctifying the books': r'sanctif(y|ies) (a |the )?(book|publication|scripture)|(inaugurates?|releases?) (a |the )?(book|publication)',
    'Blessing the assembly': r'blesses the (assembly|sabha|gathering)|addresses the (assembly|sabha)|discourse',
    'Waving to the devotees': r'\bwaves?\b|waving',
    'Jai Swaminarayan': r'jai swaminarayan',
    'Nagar yatra': r'nagar ?yatra|procession|rath ?yatra|chariot',
    'Shilanyas': r'shilanyas|foundation stone|bhoomi ?pujan|khaat ?muhurt',
    'Yagna': r'yagna|mahapuja|maha puja',
    'Applying chandlo': r'chandlo|\btilak\b',
    'Tying rakhi': r'rakhi|raksha',
    'With the sadhus': r'with (the )?sadhus|with (the )?(senior )?sants|among the sadhus',
    'Diksha': r'diksha|parshadi|bhagwati',
    'Taking prasad': r'\bthal\b|takes? (his )?(meal|prasad|lunch|breakfast)|having (his )?(meal|lunch)|\bmeal\b',
    'Giving prasad': r'gives? prasad|distributes? prasad|gives? (sweets|fruit)|feeds?',
    'Murti pujan': r'pujan of|performs pujan|does pujan|murti pujan',
    'Pushpdolotsav': r'pushpdol|fuldol|colou?red water|holi',
    'Janmashtami': r'janmashtami|krishna',
    'Guru Purnima': r'guru ?purnima',
    'Chopda pujan': r'chopda',
    'Travelling': r'airport|aeroplane|plane|flight',
    'On the boat': r'\bboat\b|ship|cruise',
    'Blessing the youths': r'\byouths?\b|yuvak',
    'Bal din': r'bal ?din|children.s day|bal mandal',
    'Walking': r'\bwalks?\b|walking|strolls?',
    'Smiling': r'\bsmiles?\b|laughs?|joyful',
    'Blessing with his hand': r'raises (his )?hand|blesses all|showers blessings|blesses everyone',
    'Mantra': r'mantra',
    'Gaushala': r'\bcows?\b|gaushala|calf',
    'Mala': r'\bmala\b',
    'Reading the scriptures': r'vachanamrut|shikshapatri|swamini vato|scripture',
    'Thakorji': r'thakorji',
    'Opening ceremony': r'ribbon|unveil|inaugurat',
    'Lighting the lamp': r'lights? (the |a )?(lamp|diva|divo)|deep ?pragatya',
    'At the samadhi': r'samadhi|smruti mandir|akshar deri',
    'By the sea': r'\bsea\b|beach|ocean|shore',
    'Blessing the mangoes': r'mango',
    'On the swing': r'swing|jhulo|jhula',
    'Darshan from the balcony': r'balcony|window',
    'Kirtan': r'kirtan|bhajan|musicians|dhun',
}


def tidy(p):
    return re.sub(r'^\d{4},\s*', '', p or '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--emb', required=True)
    ap.add_argument('--faces', required=True)
    ap.add_argument('--live', required=True, help='every pair on the page now (PAIRS + more.json)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--per', type=int, default=8)
    a = ap.parse_args()
    live = json.load(open(a.live))
    used = {f"{p[g]['album']}/{p[g]['file']}" for p in live for g in ('psm', 'msm')}
    keep, keys, E, _ = lm.load(a, used)
    idx = {k: i for i, k in enumerate(keys)}
    U = E[[idx[k] for k in used if k in idx]]
    near = (E @ U.T).max(1)

    def good(k):
        r = keep.get(k)
        return (r and k in idx and k not in used and r['sim'] >= .5 and r['sharp'] >= 45 and .05 <= r['h'] <= .4
                and r['front'] >= .35 and near[idx[k]] <= .94)
    out, taken = {'scenes': {}, 'old': [], 'info': {}}, set()
    for label, rx in THEMES.items():
        R = re.compile(rx, re.I)
        P = [k for k, v in keep.items() if v['psm'] and R.search(v['cap']) and good(k)]
        M = [k for k, v in keep.items() if not v['psm'] and R.search(v['cap']) and good(k)]
        if not P or not M:
            continue
        S = E[[idx[k] for k in P]] @ E[[idx[k] for k in M]].T
        pp = np.array([tidy(keep[k]['place']) for k in P]); mp = np.array([tidy(keep[k]['place']) for k in M])
        same = (pp[:, None] == mp[None, :]) & (pp[:, None] != '')
        sc = S + .06 * same
        pairs = []
        for f in np.argsort(-sc, axis=None):
            i, j = divmod(int(f), len(M))
            if sc[i, j] < .8:
                break
            if P[i] in taken or M[j] in taken:
                continue
            taken |= {P[i], M[j]}
            pairs.append(dict(psm=P[i], msm=M[j], look=round(float(S[i, j]), 3), same_place=bool(same[i, j])))
            if len(pairs) >= a.per:
                break
        if pairs:
            out['scenes'][label] = pairs
        print(f'{label}: {len(P)} PSM, {len(M)} MSM, {len(pairs)} pairs', flush=True)
    for v in out['scenes'].values():
        for p in v:
            for k in (p['psm'], p['msm']):
                r = keep[k]
                out['info'][k] = dict(date=r['date'], place=tidy(r['place']), cap=r['cap'], w=r['W'], h=r['H'])
    json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
