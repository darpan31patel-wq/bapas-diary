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
                special=x['special'], s_close=round(x['s_close'], 2), s_act=round(x['s_act'], 2), url=x['i'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', default='2012-01')
    ap.add_argument('--cache', default=os.path.join(month.HERE, '.cache', 'month'))
    a = ap.parse_args()
    y, m = map(int, a.month.split('-'))
    out = os.path.join(month.HERE, 'preview', 'poster', a.month)
    os.makedirs(out, exist_ok=True)
    photos = month.analyse(month.full_size(month.month_items(y, m), a.cache))
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
    for d, xs in mo.by.items():      # every caption of the day, for the 'what happened' lines
        meta['extra'][d] = sorted({make.caption(x) for x in xs if make.caption(x)})
    json.dump(meta, open(os.path.join(out, 'photos.json'), 'w'), indent=1, ensure_ascii=False)
    print(mo.summary())


if __name__ == '__main__':
    main()
