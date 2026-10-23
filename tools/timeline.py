#!/usr/bin/env python3
"""Year by year timeline mockup: one picture for every month from January 1999 to now (Darpan, 22 Oct 2026: 'scroll
along the website constantly all the way to 2026 ... one picture from every month ... what was happening in that
vicharan ... click within it, you can see more photos').

    python tools/timeline.py                    every month into preview/timeline/
    python tools/timeline.py --years 2012 2013  only those years
    python tools/timeline.py --fake             grey stand in photos, to check the output without baps.org

For each month a few of the best captioned photos are downloaded and given the daily picture's face check. The month
then gets three covers to choose between on the page: its best close darshan, its best activity, and 'mixed' (the
daily picture's own rule: a special moment when the month has one, otherwise the close darshan), plus four more
photos from other days and the captions and Telegram stories of its days. Mockup only: nothing here touches the
daily picture.

Writes preview/timeline/timeline.json (every month's facts) and per year YYYY-covers.jpg (12 rows of close, activity)
and YYYY-more.jpg (12 rows of four squares), so the page loads one year at a time.
"""
import argparse, calendar, collections, glob, json, os, random, re, sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make   # noqa: E402  the daily picture's face check, crops and caption tidying
from make import CLOSE_MIN_FACE, DOING, JUST_A_FACE, SHARP_MIN, BRIGHT_MIN, GUEST, DARSHAN, caption, caption_key, same_caption   # noqa: E402

HERE = make.HERE
OUT = os.path.join(HERE, 'preview', 'timeline')
CACHE = os.path.join(HERE, '.cache', 'timeline')
PER_MONTH = 14            # photos downloaded per month: the month's best captions, spread over its days
CW, CH = 400, 500         # a cover, 4:5
MW = 260                  # one of the four squares
MORE = 4


def all_items():
    """Every photo of every day, once each, grouped by the month it was taken in."""
    months, seen = collections.defaultdict(list), set()
    for path in sorted(glob.glob(os.path.join(HERE, 'archive', 'vicharan', '*.txt'))):
        mmdd = os.path.basename(path)[:5]
        xs = make.vicharan_items(path, mmdd, {}, per_caption=1)
        lp = os.path.join(HERE, 'archive', 'memories', mmdd + '.json')
        if os.path.exists(lp):
            xs += json.load(open(lp, encoding='utf-8'))
        for x in xs:
            d = str(x.get('d', ''))
            if len(d) == 10 and x['i'] not in seen and int(d[:4]) == x['y']:
                seen.add(x['i']); months[d[:7]].append(dict(x))
    return months


def hint(x):
    """How promising a photo looks from its caption alone, before anything is downloaded."""
    c = x.get('c') or ''
    if make.JUNK.search(c):
        return -9
    s = 1.0 if make.bapa_is_subject(c) else 0
    s += 1.2 if make.is_special(c) else 0
    s += .6 if DOING.search(c) else 0
    s += .5 if JUST_A_FACE.search(c) else 0
    s -= .8 if GUEST.search(caption(x)) else 0
    return s + random.Random(x['i']).random() * .3


def candidates(items):
    """The month's most promising photos: each day's best first, then each day's second best."""
    by = collections.defaultdict(list)
    for x in items:
        by[x['d']].append(x)
    tops = [sorted(xs, key=lambda x: -hint(x)) for xs in by.values()]
    first = sorted((t[0] for t in tops), key=lambda x: -hint(x))
    second = sorted((t[1] for t in tops if len(t) > 1), key=lambda x: -hint(x))
    third = sorted((t[2] for t in tops if len(t) > 2), key=lambda x: -hint(x))
    out = [x for x in first + second + third if hint(x) > -9]
    return out[:PER_MONTH]


def analyse(items):
    """The daily picture's face check, and how good each photo is as a close darshan and as an activity."""
    out = []
    for x in items:
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        if x.get('fake'):
            face, sim, front = x['face'], .7, .8
        else:
            face, sim = make.bapa_face(im, x['d'])
            if not face:
                continue
            front = make.LAST_FRONT[0]
        c = x.get('c') or ''
        r = face[3] / im.height
        sharp, bright = make.face_quality(im, face)
        close_ok = face[3] >= CLOSE_MIN_FACE and front >= .35 and sharp >= SHARP_MIN * .6 and bright >= BRIGHT_MIN
        special, subject = make.is_special(c), make.bapa_is_subject(c)
        doing = bool(DOING.search(c)) and not JUST_A_FACE.search(c)
        soft = .5 * max(0, 1 - sharp / (2 * SHARP_MIN)) + .5 * max(0, 1 - bright / (1.5 * BRIGHT_MIN))
        s_close = 1 + min(r, .35) + sim + .9 * (front - .6) - (.6 if not subject else 0) - (1.5 if not close_ok else 0) - soft
        s_act = (1 + sim + .6 * max(0, 1 - abs(r - .16) / .15) + (.5 if doing else 0) + (.9 if special else 0) - (.5 if r < .06 else 0)
                 - (.6 if not subject else 0) - soft - 2.5 * max(0, .3 - front) / .3)
        if GUEST.search(caption(x)):
            s_act -= 1.2
        if caption(x) == DARSHAN:
            s_act -= 1
        out.append(dict(x, face=face, close_ok=close_ok, special=special, doing=doing, s_close=s_close, s_act=s_act))
        im.close()
    return out


def fake(items):
    """Grey stand in photos with a pretend face, to check the output without baps.org."""
    os.makedirs(os.path.join(CACHE, 'fake'), exist_ok=True)
    for n, x in enumerate(items):
        rr = random.Random(x['i'])
        w, h = (1200, 800) if rr.random() < .7 else (800, 1100)
        path = os.path.join(CACHE, 'fake', f'{abs(hash(x["i"]))}.jpg')
        fx, fy, fs = w * rr.uniform(.35, .6), h * rr.uniform(.2, .35), h * rr.uniform(.12, .3)
        if not os.path.exists(path):
            im = Image.new('RGB', (w, h), tuple(rr.randint(60, 200) for _ in range(3)))
            d = ImageDraw.Draw(im)
            d.rectangle((fx - fs, fy + fs * .8, fx + fs * 2, h), fill=(214, 120, 40))
            d.ellipse((fx, fy, fx + fs, fy + fs * 1.2), fill=(150, 100, 70))
            d.text((20, 20), x['d'], fill=(255, 255, 255))
            im.save(path)
        x.update(path=path, fake=True, face=(fx, fy, fs, fs * 1.2))


def tg_lines():
    """Every dated story from both Telegram channels, by month."""
    out = collections.defaultdict(list)
    for path, ch in ((make.TG_FILE, 'Today in BAPS History'), (make.SAT_FILE, 'Satpurush in UK & Europe')):
        if not os.path.exists(path):
            continue
        for e in json.load(open(path, encoding='utf-8')):
            line = (e.get('line') or e.get('card') or '').strip()
            if line and len(e.get('date') or '') == 10:
                out[e['date'][:7]].append({'d': e['date'], 't': line, 'ch': ch, 'u': e.get('url') or ''})
    return out


def month_entry(key, items, tg):
    year, month = int(key[:4]), int(key[5:])
    by = collections.defaultdict(list)
    for x in items:
        by[x['d']].append(x)
    places = []
    for d in sorted(by):
        for x in by[d]:
            p = make.place(x)
            if p and p not in places:
                places.append(p)
    return {'key': key, 'y': year, 'm': month, 'name': f'{calendar.month_name[month]} {year}', 'photos': len(items),
            'days': len(by), 'places': places[:8], 'tg': sorted(tg.get(key, []), key=lambda e: e['d'])[:6]}


def day_facts(items, day):
    """The cover day's own captions, what the click shows."""
    caps, keys = [], []
    for x in sorted(items, key=lambda x: not make.bapa_is_subject(x.get('c') or '')):   # what Bapa did first, murtis and others after
        if x['d'] != day:
            continue
        c = caption(x)
        if not c or c == DARSHAN or make.JUNK.search(c):
            continue
        k = caption_key(c)
        if any(same_caption(k, o) for o in keys):
            continue
        keys.append(k); caps.append(c)
    return {'date': day, 'place': next((make.place(x) for x in items if x['d'] == day and make.place(x)), ''),
            'count': sum(x['d'] == day for x in items), 'captions': caps[:12]}


def pick(photos):
    """The month's close darshan, its activity, which of the two 'mixed' shows, and four more from other days."""
    close = max(photos, key=lambda x: x['s_close'] + (1.5 if x['close_ok'] else 0))
    acts = [x for x in photos if (x['doing'] or x['special']) and x['i'] != close['i']] or [x for x in photos if x['i'] != close['i']] or [close]
    act = max(acts, key=lambda x: x['s_act'])
    mixed = 'act' if act['special'] and act['s_act'] >= 2 else 'close'
    more, keys = [], [caption_key(caption(close)), caption_key(caption(act))]
    for x in sorted(photos, key=lambda x: -max(x['s_close'], x['s_act'])):
        if x['i'] in (close['i'], act['i']) or len(more) >= MORE:
            continue
        k = caption_key(caption(x))
        if any(same_caption(k, o) for o in keys):
            continue
        keys.append(k); more.append(x)
    return close, act, mixed, more


def card(x):
    return {'date': x['d'], 'cap': caption(x), 'place': make.place(x)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--years', type=int, nargs='*')
    ap.add_argument('--fake', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    months, tg = all_items(), tg_lines()
    years = a.years or sorted({int(k[:4]) for k in months})
    path = os.path.join(OUT, 'timeline.json')
    data = json.load(open(path)) if os.path.exists(path) else {'months': {}}
    for year in years:
        covers = Image.new('RGB', (2 * CW, 12 * CH), (40, 10, 18))
        more_im = Image.new('RGB', (MORE * MW, 12 * MW), (40, 10, 18))
        for month in range(1, 13):
            key = f'{year}-{month:02d}'
            items = months.get(key)
            if not items:
                data['months'].pop(key, None)
                continue
            entry = month_entry(key, items, tg)
            cands = candidates(items)
            if a.fake:
                fake(cands)
            else:
                make.download_all(cands, CACHE)
            photos = analyse([x for x in cands if 'path' in x])
            print(f'{key}: {len(items)} photos, {len(cands)} looked at, {len(photos)} with Bapa recognised', flush=True)
            if not photos:
                entry['empty'] = True
                data['months'][key] = entry
                continue
            close, act, mixed, more = pick(photos)
            for col, (x, mode) in enumerate(((close, 'close'), (act, 'frame'))):
                im = Image.open(x['path']).convert('RGB')
                covers.paste(make.crop_to(im, x['face'], CW, CH, mode), (col * CW, (month - 1) * CH))
            for col, x in enumerate(more):
                im = Image.open(x['path']).convert('RGB')
                more_im.paste(make.crop_to(im, x['face'], MW, MW, 'frame'), (col * MW, (month - 1) * MW))
            entry.update(close=card(close), act=card(act), mixed=mixed, more=[card(x) for x in more],
                         day={'close': day_facts(items, close['d']), 'act': day_facts(items, act['d'])})
            data['months'][key] = entry
        covers.save(os.path.join(OUT, f'{year}-covers.jpg'), quality=74, optimize=True, progressive=True)
        more_im.save(os.path.join(OUT, f'{year}-more.jpg'), quality=72, optimize=True, progressive=True)
        data['months'] = dict(sorted(data['months'].items()))
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(f'{year} saved', flush=True)


if __name__ == '__main__':
    main()
