#!/usr/bin/env python3
"""Contact sheets for the Legacy pairs that tools/legacy_match.py found by what is in the photos, so Claude can check
each pair by eye before it goes on the page. Website only; photos come from R2 (m/ALBUM/FILE) only.

    python3 tools/legacy_sheets.py site/legacy-cands.json legacy

Writes legacy/photos/ALBUM/FILE (at most 1200 px), legacy/sheets/SCENE.jpg (one row per pair: Pramukh Swami
Maharaj left, Mahant Swami Maharaj right, with the pair number, years and how alike they look) and
legacy/sheets/old.jpg (the pairs already on the page, least alike first).
"""
import concurrent.futures, json, os, re, sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r2 import get   # noqa: E402

T = 300


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def tile(path, label):
    t = np.full((T, int(T * 4 / 3), 3), 40, np.uint8)
    im = cv2.imread(path) if os.path.exists(path) else None
    if im is not None:
        k = min(t.shape[0] / im.shape[0], t.shape[1] / im.shape[1])
        im = cv2.resize(im, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        y, x = (t.shape[0] - im.shape[0]) // 2, (t.shape[1] - im.shape[1]) // 2
        t[y:y + im.shape[0], x:x + im.shape[1]] = im
    cv2.rectangle(t, (0, 0), (t.shape[1], 22), (0, 0, 0), -1)
    cv2.putText(t, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 255), 1)
    return t


def sheet(rows, path):
    if not rows:
        return
    gap = np.full((T, 10, 3), 255, np.uint8)
    lines = [np.hstack([a, gap, b]) for a, b in rows]
    cv2.imwrite(path, np.vstack([np.vstack([l, np.zeros((6, l.shape[1], 3), np.uint8)]) for l in lines]),
                [cv2.IMWRITE_JPEG_QUALITY, 82])


def main():
    cands, out = json.load(open(sys.argv[1])), sys.argv[2]
    photos = os.path.join(out, 'photos')
    keys = {p[g] for v in cands['scenes'].values() for p in v for g in ('psm', 'msm')}
    keys |= {p[g] for p in cands['old'] for g in ('psm', 'msm')}

    def fetch(k):
        dst = os.path.join(photos, k)
        if not os.path.exists(dst):
            try:
                get('m/' + k, dst)
                im = cv2.imread(dst)
                k_ = 1200 / max(im.shape[:2])
                if k_ < 1:
                    cv2.imwrite(dst, cv2.resize(im, None, fx=k_, fy=k_, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
            except Exception as e:
                print('missing', k, e)
    with concurrent.futures.ThreadPoolExecutor(8) as ex:
        list(ex.map(fetch, sorted(keys)))
    os.makedirs(os.path.join(out, 'sheets'), exist_ok=True)
    info = cands['info']
    for label, pairs in cands['scenes'].items():
        rows = []
        for i, p in enumerate(pairs):
            a, b = info[p['psm']], info[p['msm']]
            rows.append((tile(os.path.join(photos, p['psm']), f"{i} psm {a['date'][:4]} {a['place'][:18]}"),
                         tile(os.path.join(photos, p['msm']), f"{i} msm {b['date'][:4]} {b['place'][:18]} look {p['look']}")))
        sheet(rows, os.path.join(out, 'sheets', slug(label) + '.jpg'))
    old = sorted(enumerate(cands['old']), key=lambda x: x[1]['look'] if x[1]['look'] is not None else -1)
    for n in range(0, len(old), 12):
        sheet([(tile(os.path.join(photos, p['psm']), f"{i} {p['place'][:16]} {p['moment'][:18]}"),
                tile(os.path.join(photos, p['msm']), f"look {p['look']}")) for i, p in old[n:n + 12]],
              os.path.join(out, 'sheets', f'old-{n // 12}.jpg'))
    print(len(keys), 'photos,', len(cands['scenes']), 'scenes')


if __name__ == '__main__':
    main()
