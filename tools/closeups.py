#!/usr/bin/env python3
"""Close up face shots of Bapa for every year of a date: contact sheets to choose from.

    python tools/closeups.py --date 2026-10-18            (on GitHub Actions; this needs baps.org)
    python tools/closeups.py --data list.json --cache dir  (offline, items that already have a 'path')

Every photo of the day where Bapa is recognised is cropped as a close darshan (the same crop the wide
cards use) and laid out one row per year, best first, numbered, with what the face check saw under each:
face height in pixels, how face on he is (front), how sharp the face is, and the match score. Faces that
the current rules would not allow as a close up (too small, a profile, head cut by the photo's edge) are
still shown, greyed, so nothing is hidden. Writes to out/close-ups/<date>/:
    sheet-1.jpg, sheet-2.jpg ...   seven years per sheet
    best-per-year.jpg              the top face of every year, as it would hang on the picture
    close-ups.txt                  the same numbers plus each photo's address, for pinning a choice
"""
import argparse, collections, datetime, json, os, sys
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import (CLOSE_MIN_FACE, FRAME_ASPECT, GOLD, JUST_A_FACE, LAST_FRONT, bapa_face, bapa_is_subject, caption,
                  crop_to, download_all, fetch, garamond, arimo_bold, vicharan_items, wrap)

IVORY, DIM, DARK = (250, 241, 222), (150, 120, 112), (40, 10, 18)
SHARP_REF = 250.0   # Laplacian variance of a face scaled to 160 px tall: a crisp recent photo is well above this, a soft 2001 scan well below
FRONT_MIN = .35     # the current rule's face on threshold (make.pick_one_per_year)


def load_items(day, data=None, only_data=False):
    """The same photo list make.py builds for the day: the day list, collect.py's finds and every vicharan photo."""
    mmdd = f'{day:%m-%d}'
    items = json.load(open(data)) if data else json.loads(fetch(make.DATA_URL.format(mmdd=mmdd)))
    if only_data:
        return items
    collected = os.path.join(make.HERE, 'archive', mmdd + '.json')
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have]
    combed = os.path.join(make.HERE, 'archive', 'vicharan', mmdd + '.txt')
    if os.path.exists(combed):
        have = {x['i'] for x in items}
        place = {x['y']: x.get('p', '') for x in items}
        items += [x for x in vicharan_items(combed, mmdd, place) if x['y'] < day.year and x['i'] not in have]
    seen, out = set(), []
    for x in items:   # one entry per photo
        if x['i'] not in seen:
            seen.add(x['i']); out.append(x)
    return out


def sharpness(im, face):
    """How crisp the face is: variance of the Laplacian over the face, scaled to 160 px tall first so a
    big face and a small one are compared fairly (a blown up small face stays soft)."""
    fx, fy, fw, fh = face
    box = (max(0, fx), max(0, fy), min(im.width, fx + fw), min(im.height, fy + fh))
    crop = im.crop(box)
    if crop.height < 8 or crop.width < 8:
        return 0
    crop = crop.resize((max(8, round(crop.width * 160 / crop.height)), 160), Image.LANCZOS)
    g = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def head_cut(im, face):
    """True when the top of his head or the side of his face runs off the photo's edge (a tight portrait whose
    crown is just in is fine: the detector's box starts about a quarter of a face below the top of the head)."""
    fx, fy, fw, fh = face
    return fy - .2 * fh < 0 or fx - .05 * fw < 0 or fx + 1.05 * fw > im.width or fy + .9 * fh > im.height


def look(items):
    """Every photo where Bapa is recognised, with the numbers a close darshan depends on and a close score."""
    out = []
    for x in items:
        if 'path' not in x:
            continue
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        face, sim = bapa_face(im, x.get('d', str(x['y'])))
        if not face:
            continue
        front = LAST_FRONT[0]
        fh = face[3]
        sharp = sharpness(im, face)
        cut = head_cut(im, face)
        c = x.get('c') or ''
        ok = fh >= CLOSE_MIN_FACE and front >= FRONT_MIN and not cut
        # proposed close score: a face turned to the camera, really big in pixels, crisp, and recognised with confidence
        score = (sim + .9 * front + .6 * min(1, np.log2(max(fh, 1) / CLOSE_MIN_FACE) / 2.5) + .5 * min(1, sharp / SHARP_REF)
                 + .2 * min(1, fh / im.height / .35) + (.2 if JUST_A_FACE.search(c) else 0) - (.4 if not bapa_is_subject(c) else 0))
        out.append(dict(x, im=im, face=face, sim=sim, front=front, fh=round(fh), sharp=round(sharp), cut=cut, ok=ok,
                        score=round(float(score) - (0 if ok else 2), 2), crop='close'))
    return out


def sheets(day, byyear, picks, out, per_year=6, per_sheet=7):
    aspect = FRAME_ASPECT['W2']
    tw, th, pad, lab = 340, round(340 / aspect), 22, 230
    years = sorted(byyear)
    cf, sf, nf, yf, tf = garamond(21, 500), arimo_bold(15), arimo_bold(20), garamond(50, 600), garamond(56)
    for s in range(0, len(years), per_sheet):
        page = years[s:s + per_sheet]
        Wd, Hd = lab + per_year * (tw + pad) + pad, 130 + len(page) * (th + 150)
        img = Image.new('RGB', (Wd, Hd), DARK); d = ImageDraw.Draw(img)
        d.text((Wd / 2, 60), f'{day.day} {day:%B}: close up faces, {page[0]} to {page[-1]}', font=tf, fill=GOLD, anchor='mm')
        for r, y in enumerate(page):
            y0 = 130 + r * (th + 150)
            d.text((pad, y0 + 16), str(y), font=yf, fill=GOLD, anchor='la')
            rows = byyear[y]
            d.text((pad, y0 + 86), f'{len(rows)} faces found', font=sf, fill=DIM, anchor='la')
            d.text((pad, y0 + 110), f'{sum(1 for v in rows if v["ok"])} allowed now', font=sf, fill=DIM, anchor='la')
            for c, v in enumerate(rows[:per_year]):
                x0 = lab + c * (tw + pad)
                tile = crop_to(v['im'], v['face'], tw, th, 'close')
                if not v['ok']:
                    tile = Image.blend(tile, Image.new("RGB", tile.size, DARK), .3)
                img.paste(tile, (x0, y0))
                on_picture = v['i'] == picks.get(y)
                colour = GOLD if on_picture else (IVORY if v['ok'] else DIM)
                if on_picture:
                    d.rectangle((x0 - 4, y0 - 4, x0 + tw + 3, y0 + th + 3), outline=GOLD, width=4)
                d.rectangle((x0 + tw - 36, y0 + th - 30, x0 + tw, y0 + th), fill=DARK)
                d.text((x0 + tw - 18, y0 + th - 15), str(c + 1), font=nf, fill=GOLD, anchor='mm')
                why = ('on the picture now' if on_picture else '') if v['ok'] else ' '.join(
                    w for w, bad in (('face too small', v['fh'] < CLOSE_MIN_FACE), ('side on', v['front'] < FRONT_MIN), ('head cut', v['cut'])) if bad)
                d.text((x0, y0 + th + 8), f'#{c + 1}  score {v["score"]:.2f}  {why}'.rstrip(), font=sf, fill=colour, anchor='la')
                d.text((x0, y0 + th + 30), f'{v["fh"]}px  front {v["front"]:.2f}  sharp {v["sharp"]}  match {v["sim"]:.2f}', font=sf, fill=colour, anchor='la')
                for i, line in enumerate(wrap(d, caption(v) or '(no caption)', cf, tw, 2)):
                    d.text((x0, y0 + th + 58 + i * 25), line, font=cf, fill=colour, anchor='la')
        img.save(os.path.join(out, f'sheet-{s // per_sheet + 1}.jpg'), quality=88, optimize=True)

    # the top face of every year, hung like the picture's cards
    cols = 9
    tw, th, pad = 280, round(280 / aspect), 26
    n = len(years)
    rows_n = (n + cols - 1) // cols
    Wd, Hd = pad + cols * (tw + pad), 120 + rows_n * (th + 70)
    img = Image.new('RGB', (Wd, Hd), DARK); d = ImageDraw.Draw(img)
    d.text((Wd / 2, 58), f'{day.day} {day:%B}: the best close up face of each year', font=tf, fill=GOLD, anchor='mm')
    for k, y in enumerate(years):
        v = byyear[y][0]
        x0, y0 = pad + (k % cols) * (tw + pad), 120 + (k // cols) * (th + 70)
        img.paste(crop_to(v['im'], v['face'], tw, th, 'close'), (x0, y0))
        d.text((x0 + tw / 2, y0 + th + 30), f'{y}   #1' + ('' if v['ok'] else '  (not allowed now)'), font=garamond(30, 600), fill=GOLD if v['ok'] else DIM, anchor='mm')
    img.save(os.path.join(out, 'best-per-year.jpg'), quality=90, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (default: today in London)')
    ap.add_argument('--data', help='use this JSON file instead of downloading the day list')
    ap.add_argument('--cache', default=os.path.join(make.HERE, '.cache'))
    ap.add_argument('--out', default=os.path.join(make.HERE, 'out', 'close-ups'))
    ap.add_argument('--per-year', type=int, default=6)
    ap.add_argument('--only-data', action='store_true', help='offline test: just the --data photos, no archive')
    a = ap.parse_args()
    day = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(ZoneInfo('Europe/London')).date()
    items = load_items(day, a.data, a.only_data)
    print(f'{day}: {len(items)} photos across {len({x["y"] for x in items})} years')
    download_all([x for x in items if 'path' not in x], a.cache)
    seen = look(items)
    byyear = collections.defaultdict(list)
    for v in seen:
        byyear[v['y']].append(v)
    for y in byyear:
        byyear[y].sort(key=lambda v: -v['score'])
    # what the current rules hang on the wide picture, to mark on the sheets
    picks = {x['y']: x['i'] for x in make.pick_one_per_year(items, seed=f'{day:%m-%d}', aspect=FRAME_ASPECT['W2'])}
    out = os.path.join(a.out, str(day)); os.makedirs(out, exist_ok=True)
    sheets(day, byyear, picks, out, a.per_year)
    with open(os.path.join(out, 'close-ups.txt'), 'w') as f:
        f.write(f'{day:%d %B}: close up faces per year, best first. Allowed = passes the current close up rule '
                f'(face >= {CLOSE_MIN_FACE}px, front >= {FRONT_MIN}, head not cut by the photo edge).\n')
        for y in sorted(byyear):
            f.write(f'\n{y}: {len(byyear[y])} faces, {sum(1 for v in byyear[y] if v["ok"])} allowed\n')
            for n, v in enumerate(byyear[y][:a.per_year * 2], 1):
                f.write(f'  #{n:<2} score {v["score"]:5.2f}  face {v["fh"]:4}px  front {v["front"]:.2f}  sharp {v["sharp"]:4}  match {v["sim"]:.2f}'
                        f'  {"allowed " if v["ok"] else "blocked "}{"ON PICTURE  " if v["i"] == picks.get(y) else ""}{caption(v) or "(no caption)"}  {v["i"]}\n')
    print('saved', out, ':', sorted(os.listdir(out)))


if __name__ == '__main__':
    main()
