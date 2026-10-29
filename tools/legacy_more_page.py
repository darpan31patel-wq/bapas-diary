#!/usr/bin/env python3
"""Puts the eye checked pairs from tools/legacy_more.py on the live Legacy page, and takes off the pairs that do not
truly show the same thing (Darpan, 29 Oct 2026: the In the car pair "doesnt work or make sense").

    python3 tools/legacy_more_page.py live/then-and-now/index.html site/legacy-more-cands.json \
        site/legacy-more-picks.txt site/legacy-live-pairs.json OUT.html

picks: SCENE|NUMBER|HEADING per line (NUMBER = the pair's row on that scene's contact sheet). DROP: rows of
site/legacy-live-pairs.json (the page's own pairs, then the weekly more.json ones) that come off.
"""
import json, re, sys

DROP = {12, 15, 55, 57, 59, 61, 64, 65, 66, 68, 70, 72, 82, 83, 87, 88, 89, 90, 91, 97, 98, 99, 100, 101, 102}
RENAME = {52: 'Blessing a child'}


def main():
    page, cands, picks, live, out = sys.argv[1:6]
    s = open(page).read()
    m = re.search(r'const PAIRS = (\[.*?\]);\n', s, re.S)
    P = json.loads(m.group(1))
    L = json.load(open(live))
    n = len(P)
    keep = []
    for k, p in enumerate(P):
        if k in DROP:
            continue
        if k in RENAME:
            p['moment'] = RENAME[k]
        keep.append(p)
    gone = [f"{L[k]['psm']['file']}|{L[k]['msm']['file']}" for k in sorted(DROP) if k >= n]
    c = json.load(open(cands))
    have = {p[g]['file'] for p in keep for g in ('psm', 'msm')}
    for line in open(picks):
        if not line.strip():
            continue
        scene, num, heading = line.strip().split('|')
        q = c['scenes'][scene][int(num)]
        sides = {}
        for g in ('psm', 'msm'):
            al, fi = q[g].split('/', 1)
            r = c['info'][q[g]]
            sides[g] = dict(date=r['date'], cap=r['cap'], album=al, file=fi, r=round(r['w'] / r['h'], 3), place=r['place'], t='l')
        if sides['psm']['file'] in have or sides['msm']['file'] in have:
            continue
        have |= {sides['psm']['file'], sides['msm']['file']}
        same = sides['psm']['place'] if sides['psm']['place'] == sides['msm']['place'] else ''
        keep.append(dict(place=same, moment=heading, **sides))
    s = s[:m.start(1)] + json.dumps(keep, ensure_ascii=False) + s[m.end(1):]
    old = "  const have = new Set(PAIRS.map(p => p.psm.file + p.msm.file));"
    assert old in s
    s = s.replace(old, old + "\n  // weekly pairs taken off by eye (Darpan, 29 Oct 2026: both photos must truly show what the heading says)\n"
                  f"  {json.dumps(gone)}.forEach(k => have.add(k.replace('|', '')));")
    open(out, 'w').write(s)
    print(len(P), 'pairs on the page before,', n - len([k for k in DROP if k < n]), 'kept,', len(keep), 'now;',
          len(gone), 'weekly pairs held back')


if __name__ == '__main__':
    main()
