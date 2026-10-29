#!/usr/bin/env python3
"""Mockup helper for the thread 'Add more 1999 to 2012 photos to Through the years' (website only, never live).

    python3 tools/mock/years_more.py OLD_FACES_JSON NEW_FACES_JSON OUT

Fetches each 1999 to 2012 close up from R2's m/ copy (never baps.org) and writes
OUT/sheets/sheet-NN.jpg: every NEW pick, the whole photo with a ring round the face that was matched, numbered, to look over by eye;
OUT/sheets/list.tsv: number, day, album/file, caption;
OUT/mock/b-YEAR-N.json: small copies {album/file: base64 jpg} for the private mockup page (which can't reach R2);
OUT/counts.tsv: days and photos a year, before and after.
"""
import base64, collections, json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
import cv2, numpy as np

old, new, out = sys.argv[1:4]
def rows(p):
    r = []
    for x in json.load(open(p)):
        if x['day'] < '2013-01-01':
            r += [x] + [dict(x, **z) for z in x.get('more', [])]
    return r
O, N = rows(old), rows(new)
before = {f"{x['album']}/{x['file']}" for x in O}
cnt = collections.defaultdict(lambda: [set(), 0, set(), 0])
for x in O: c = cnt[x['day'][:4]]; c[0].add(x['day']); c[1] += 1
for x in N: c = cnt[x['day'][:4]]; c[2].add(x['day']); c[3] += 1
os.makedirs(out + '/sheets', exist_ok=True); os.makedirs(out + '/mock', exist_ok=True)
with open(out + '/counts.tsv', 'w') as f:
    f.write('year\tdays before\tphotos before\tdays after\tphotos after\n')
    for y in sorted(cnt): c = cnt[y]; f.write(f'{y}\t{len(c[0])}\t{c[1]}\t{len(c[2])}\t{c[3]}\n')

def get(x):
    key = f"{x['album']}/{x['file']}"
    for _ in range(4):
        try:
            b = urllib.request.urlopen(urllib.request.Request('https://photos.bapas-diary.com/m/' + urllib.parse.quote(key),
                                       headers={'User-Agent': 'bapas-diary-years'}), timeout=60).read()
            return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            pass
    return None
with ThreadPoolExecutor(16) as ex:
    ims = list(ex.map(get, N))

fresh = [(x, im) for x, im in zip(N, ims) if f"{x['album']}/{x['file']}" not in before and im is not None]
C, R, S = 6, 5, 300
lst = open(out + '/sheets/list.tsv', 'w')
for s in range(0, len(fresh), C * R):
    sheet = np.full((R * (S + 26), C * S, 3), 255, np.uint8)
    for i, (x, im) in enumerate(fresh[s:s + C * R]):
        n = s + i + 1
        k = min(S / im.shape[1], S / im.shape[0]); t = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        rx, ry, lx, ly = x['eyes']
        cv2.circle(t, (int((rx + lx) / 2 * k), int((ry + ly) / 2 * k + x['span'] * k * .6)), int(x['span'] * k * 1.8), (0, 220, 255), 2)
        y0, x0 = i // C * (S + 26), i % C * S
        sheet[y0:y0 + t.shape[0], x0:x0 + t.shape[1]] = t
        cv2.putText(sheet, f"{n}  {x['day']}", (x0 + 4, y0 + S + 19), cv2.FONT_HERSHEY_SIMPLEX, .55, (0, 0, 0), 1)
        lst.write(f"{n}\t{x['day']}\t{x['album']}/{x['file']}\t{x['caption']}\n")
    cv2.imwrite(f'{out}/sheets/sheet-{s // (C * R) + 1:02d}.jpg', sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
lst.close()

# the mockup's photos, a year at a time in files of at most about 10 MB
by = collections.defaultdict(dict)
for x, im in zip(N, ims):
    if im is None: continue
    k = min(1, 640 / max(im.shape[:2]))
    if k < 1: im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    by[x['day'][:4]][f"{x['album']}/{x['file']}"] = base64.b64encode(cv2.imencode('.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 70])[1]).decode()
for y, d in by.items():
    part, size, n = {}, 0, 0
    for key, b in d.items():
        part[key] = b; size += len(b)
        if size > 10e6:
            json.dump(part, open(f'{out}/mock/b-{y}-{n}.json', 'w')); part, size, n = {}, 0, n + 1
    if part: json.dump(part, open(f'{out}/mock/b-{y}-{n}.json', 'w'))
print(open(out + '/counts.tsv').read(), f'{len(fresh)} new photos on {-(-len(fresh) // (C * R))} sheets')
