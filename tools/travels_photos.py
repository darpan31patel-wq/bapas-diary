#!/usr/bin/env python3
"""Travels globe: one close up of Bapa for each place on the route (Darpan, 23 Oct 2026: 'a photo from that
location, for each place, in the text box corner. a nice close up').

Website only (bapas-diary.com). Nothing here touches the daily 2pm picture: it only reads the face models.

    python3 tools/travels_photos.py --stops site/travels-stops.json --out travels

site/travels-stops.json is {year: [stop, ...]}, each stop with 'try': [[album, file], ...] photos of Bapa taken there.
For each stop it fetches those web photos from baps.org one at a time (the Drive archive's polite fetch), finds Bapa
with YuNet and SFace (as models/README.md) and keeps the closest, sharpest face looking at the camera, cut as a square
close up: travels/YEAR-N.jpg (N counts the year's stops from 0) and travels/picks.json (which photo each one is).
"""
import argparse, json, os, sys, time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(HERE, 'models')
sys.path.insert(0, os.path.join(HERE, 'tools'))
from archive_download import SITE, get   # one at a time, stops at a check page

PSM_UNTIL = '2016-08-13'   # Pramukh Swami Maharaj before this date, Mahant Swami Maharaj after
SAME_PERSON = .5
SIDE = 320                 # the close up, square
DETECT = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .6, .3, 5000)
RECOGNISE = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'face_recognition_sface_2021dec.onnx'), '')
BAPA = {k: np.array(v) for k, v in json.load(open(os.path.join(MODELS, 'bapa-faces.json'))).items()}


def front_view(f):
    x, y, w, h, rx, ry, lx, ly, nx, ny = [float(v) for v in f[:10]]
    eyes = abs(lx - rx) / max(w, 1)
    centred = 1 - min(1, abs(nx - (lx + rx) / 2) / max(abs(lx - rx) / 2, 1))
    return max(0, min(1, (eyes - .18) / .25)) * (.5 + .5 * centred)


def find(bgr, guru):
    k = 2.0 if max(bgr.shape[:2]) < 900 else 1.0
    big = cv2.resize(bgr, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC) if k != 1 else bgr
    DETECT.setInputSize((big.shape[1], big.shape[0]))
    faces = DETECT.detect(big)[1]
    best, best_sim = None, 0
    for f in faces if faces is not None else []:
        e = RECOGNISE.feature(RECOGNISE.alignCrop(big, f))[0]
        sim = float(BAPA[guru] @ (e / np.linalg.norm(e)))
        if sim > best_sim:
            best, best_sim = f.copy(), sim
    if best is None or best_sim < SAME_PERSON:
        return None, 0
    best[:14] /= k
    return best, best_sim


def score(bgr, f, sim):
    x, y, w, h = [int(v) for v in f[:4]]
    crop = bgr[max(0, y):y + h, max(0, x):x + w]
    if crop.shape[0] < 8 or crop.shape[1] < 8:
        return -9
    g = cv2.cvtColor(cv2.resize(crop, (160, 160)), cv2.COLOR_BGR2GRAY).astype(np.float32)
    sharp, bright = float(cv2.Laplacian(g, cv2.CV_32F).var()), float(g.mean())
    return (min(h / min(bgr.shape[:2]), .5) * 3 + min(w, 160) / 160 + sim
            - 3 * max(0, .6 - front_view(f)) - .8 * max(0, 1 - sharp / 40) - .8 * max(0, 1 - bright / 70))


def close_up(bgr, f):
    """A square around his face, a little below it so the shoulders show, kept inside the photo."""
    x, y, w, h = [float(v) for v in f[:4]]
    side = min(max(w, h) * 2.6, *bgr.shape[:2])
    cx, cy = x + w / 2, y + h * .62
    left = int(min(max(0, cx - side / 2), bgr.shape[1] - side))
    top = int(min(max(0, cy - side / 2), bgr.shape[0] - side))
    crop = bgr[top:top + int(side), left:left + int(side)]
    return cv2.resize(crop, (SIDE, SIDE), interpolation=cv2.INTER_AREA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stops', default='site/travels-stops.json')
    ap.add_argument('--out', default='travels')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    picks = {}
    for year, stops in json.load(open(a.stops)).items():
        for n, s in enumerate(stops):
            guru = 'psm' if s['a'] < PSM_UNTIL else 'msm'
            best = None
            for album, file in s['try']:
                body, _ = get(SITE.format(album=album, size='WebImages', file=file), may_be_missing=True)
                time.sleep(.6)
                if not body:
                    continue
                bgr = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
                if bgr is None:
                    continue
                f, sim = find(bgr, guru)
                if f is None:
                    continue
                sc = score(bgr, f, sim)
                if best is None or sc > best[0]:
                    best = (sc, album, file, close_up(bgr, f))
                if sc > 2.6:   # close, sharp and looking at the camera: good enough, spare baps.org the rest
                    break
            key = f'{year}-{n}'
            if best:
                cv2.imwrite(os.path.join(a.out, key + '.jpg'), best[3], [cv2.IMWRITE_JPEG_QUALITY, 82])
                picks[key] = {'album': best[1], 'file': best[2], 'score': round(best[0], 2)}
            print(key, s['p'], picks.get(key, 'no face found'), flush=True)
    json.dump(picks, open(os.path.join(a.out, 'picks.json'), 'w'), indent=1)
    print(f'{len(picks)} close ups', flush=True)


if __name__ == '__main__':
    main()
