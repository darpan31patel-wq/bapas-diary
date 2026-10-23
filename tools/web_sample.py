#!/usr/bin/env python3
"""Sample photos for the website mockup (Darpan, 23 Oct 2026: an animated day page where every card turns through
all of that year's photos, and a close ups only view to see Bapa's face change through the years).

    python tools/web_sample.py --date 2026-10-23 --out web/sample

Gathers the day's photos the way make.py does, keeps those where Bapa's face is recognised, and writes small copies
(web/sample/MM-DD/*.jpg) with day.json: per year the place and a list of photos with caption, where his face sits
(so a card can centre on it) and whether it is a close up. Not part of the daily picture.
"""
import argparse, collections, datetime, json, os, sys

from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make  # noqa: E402

PER_YEAR = 10     # photos a card turns through in the mockup (the real site would show them all)
SIDE = 440        # longest side of a card photo, in pixels
FACE_SIDE = 260   # a close up crop for the face through the years strip
CLOSE = .16       # face height as a share of the photo's height from which a photo counts as a close up


def gather(day):
    mmdd = f'{day:%m-%d}'
    items = make.day_list(mmdd)
    have = {x['i'] for x in items}
    collected = os.path.join(make.HERE, 'archive', mmdd + '.json')
    if os.path.exists(collected):
        items += [x for x in json.load(open(collected)) if x['i'] not in have]
    combed = os.path.join(make.HERE, 'archive', 'vicharan', mmdd + '.txt')
    if os.path.exists(combed):
        have = {x['i'] for x in items}
        place = {x['y']: x.get('p', '') for x in items}
        items += [x for x in make.vicharan_items(combed, mmdd, place) if x['y'] < day.year and x['i'] not in have]
    make.album_towns(items)
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--out', default='web/sample')
    ap.add_argument('--cache', default='.cache')
    a = ap.parse_args()
    day = datetime.date.fromisoformat(a.date)
    out = os.path.join(a.out, f'{day:%m-%d}')
    os.makedirs(out, exist_ok=True)

    items = gather(day)
    print(f'{day}: {len(items)} photos across {len({x["y"] for x in items})} years', flush=True)
    make.download_all(items, a.cache)

    years = collections.defaultdict(list)
    for x in items:
        if 'path' not in x:
            continue
        try:
            im = ImageOps.exif_transpose(Image.open(x['path'])).convert('RGB')
        except Exception:
            continue
        face, sim = make.bapa_face(im, x.get('d') or f"{x['y']}-01-01")
        if not face:
            continue
        sharp, bright = make.face_quality(im, face)
        fx, fy, fw, fh = face
        x.update(im=im, face=face, sim=sim, sharp=sharp, bright=bright, cap=make.caption(x), share=fh / im.height)
        years[x['y']].append(x)

    data = {'date': f'{day:%m-%d}', 'title': f'{day.day} {day:%B}', 'years': []}
    for y in sorted(years):
        xs = years[y]
        good = lambda x: (x['sharp'] >= make.SHARP_MIN and x['bright'] >= make.BRIGHT_MIN, make.unique_caption(x['c']), x['sim'], x['sharp'])
        xs.sort(key=good, reverse=True)
        seen, keep = set(), []
        for x in xs:   # never the same caption twice on one card
            k = x['cap'].lower()
            if k in seen:
                continue
            seen.add(k)
            keep.append(x)
            if len(keep) == PER_YEAR:
                break
        photos = []
        for n, x in enumerate(keep, 1):
            im, (fx, fy, fw, fh) = x['im'], x['face']
            name = f'{y}-{n}.jpg'
            small = im.copy(); small.thumbnail((SIDE, SIDE), Image.LANCZOS)
            small.save(os.path.join(out, name), quality=72, optimize=True, progressive=True)
            close = x['share'] >= CLOSE and x['sharp'] >= make.SHARP_MIN and x['bright'] >= make.BRIGHT_MIN
            p = {'f': name, 'c': x['cap'], 'place': make.place(x), 'fx': round((fx + fw / 2) / im.width, 3),
                 'fy': round((fy + fh / 2) / im.height, 3), 'close': close}
            if x['sharp'] >= make.SHARP_MIN and x['bright'] >= make.BRIGHT_MIN:   # a head and shoulders crop for the face strip
                s = max(fw, fh) * 2.6
                cx, cy = fx + fw / 2, fy + fh * .62
                box = [cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2]
                face_im = im.crop(tuple(round(v) for v in box)).resize((FACE_SIDE, FACE_SIDE), Image.LANCZOS)
                p['face'] = f'{y}-{n}-face.jpg'
                face_im.save(os.path.join(out, p['face']), quality=74, optimize=True)
            photos.append(p)
        if photos:
            data['years'].append({'y': y, 'place': photos[0]['place'], 'photos': photos})
            print(f'  {y}: {len(xs)} recognised, kept {len(photos)} ({sum(p["close"] for p in photos)} close ups)', flush=True)

    json.dump(data, open(os.path.join(out, 'day.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
