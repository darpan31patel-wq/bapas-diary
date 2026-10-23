#!/usr/bin/env python3
"""Photos for the BAPS calendar style poster mockups (Darpan, 23 Oct 2026). Runs on GitHub, which can load
baps.org's photos: picks a month's photos the way the month cards do (tools/month.py) and saves them small, with
their captions, places and where Bapa's face is, in preview/poster/<month>/ so the posters can be drawn anywhere.

    python tools/poster_photos.py --month 2012-01

Mockups only: nothing here touches the daily picture.
"""
import argparse, json, os, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make    # noqa: E402
import month   # noqa: E402


def save(x, out, name):
    im = month.load(x)
    k = 1600 / max(im.size)
    if k < 1:
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    else:
        k = 1
    im.save(os.path.join(out, name), quality=90)
    fx, fy, fw, fh = x['face']
    return dict(file=name, day=int(x['d'][8:10]), date=x['d'][:10], caption=make.caption(x), place=make.place(x) or '',
                face=[round(v * k) for v in (fx, fy, fw, fh)], size=list(im.size), close_ok=x['close_ok'],
                special=x['special'], s_close=round(x['s_close'], 2), s_act=round(x['s_act'], 2), url=x['i'],
                album=make.album(x['i']), doing=bool(x.get('doing')), subject=month.subject(x) if x.get('c') else False,
                front=round(x.get('front', 0), 2), sim=round(x.get('sim', 0), 2), unsure=bool(x.get('unsure')))


def any_face(x):
    """For a day where the face check recognised Bapa in no photo: a looser match first (similarity .35), then the
    biggest face found at all. The day is marked unsure so the poster can flag it."""
    im = month.load(x)
    face, sim = make.bapa_face(im, x['d'], need=.35)
    if not face:
        small = im.copy(); small.thumbnail((1280, 1280))
        k = im.width / small.width
        bgr = make.cv2.cvtColor(make.np.array(small), make.cv2.COLOR_RGB2BGR)
        with make.FACE_LOCK:
            make.DETECT.setInputSize((bgr.shape[1], bgr.shape[0]))
            faces = make.DETECT.detect(bgr)[1]
        if faces is None or not len(faces):
            return None
        f = max(faces, key=lambda f: f[2] * f[3])
        face, sim = tuple(float(v) * k for v in f[:4]), 0
    return dict(x, face=face, sim=sim, front=0, close_ok=False, special=False, doing=False, s_close=-5 + sim, s_act=-5, size=im.size,
                unsure=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', default='2012-01')
    ap.add_argument('--cache', default=os.path.join(month.HERE, '.cache', 'month'))
    a = ap.parse_args()
    y, m = map(int, a.month.split('-'))
    out = os.path.join(month.HERE, 'preview', 'poster', a.month)
    os.makedirs(out, exist_ok=True)
    got = month.full_size(month.month_items(y, m), a.cache)
    photos = month.analyse(got)
    mo = month.Month(photos, y, m)
    meta, done = dict(month=a.month, places=mo.places, count=mo.count, close={}, act={}, highlights=[], extra={}), {}

    def keep(x, tag):
        if x['i'] not in done:
            done[x['i']] = save(x, out, f'{tag}.jpg')
        return done[x['i']]
    for d, x in mo.close.items():
        meta['close'][d] = keep(x, f'{d:02d}-close')
    for d, x in mo.act.items():
        meta['act'][d] = keep(x, f'{d:02d}-act')
    for i, x in enumerate(mo.highlights[:16]):
        meta['highlights'].append(keep(x, f'hl{i:02d}'))
    # every day's best few photos, so the poster can pick without repeats and fall back when a crop won't fit
    # (Darpan's design brief, 23 Oct 2026)
    meta['cands'] = {}
    for d, xs in mo.by.items():
        best = sorted(xs, key=lambda x: -max(x['s_close'], x['s_act']))[:6]
        meta['cands'][d] = [keep(x, f'{d:02d}-c{n}') for n, x in enumerate(best)]
    # a day where Bapa was recognised in no photo still gets one (something for every day), marked unsure
    for d in range(1, month.calendar.monthrange(y, m)[1] + 1):
        if d in mo.by:
            continue
        tries = [x for x in got if x['d'][:10] == f'{a.month}-{d:02d}' and not make.JUNK.search(x.get('c') or '')]
        found = [f for f in (any_face(x) for x in tries[:12]) if f]
        found.sort(key=lambda x: (-x['sim'], -x['face'][3] / x['size'][1]))
        if found:
            meta['cands'][d] = [keep(x, f'{d:02d}-u{n}') for n, x in enumerate(found[:3])]
            meta['close'].setdefault(d, meta['cands'][d][0])
            meta['extra'].setdefault(d, sorted({make.caption(x) for x in found} - {''}))
    for d, xs in mo.by.items():      # every caption of the day, for the 'what happened' lines
        meta['extra'][d] = sorted({make.caption(x) for x in xs if make.caption(x)})
    json.dump(meta, open(os.path.join(out, 'photos.json'), 'w'), indent=1, ensure_ascii=False)
    print(mo.summary())


if __name__ == '__main__':
    main()
