"""Special picture looks (Darpan, 17 Nov 2026, ideas from good design and photo websites):

 1. like a magazine, not a grid: one hero photo, a clear headline, plenty of quiet space, two fonts only
 5. the hero photo: Bapa close up, doing the action, on a calm background, from that exact day and the story's place
 6. two or three looks of the day's special every day, so he chooses rather than rebuilds:
      'hero'   one big photo, the headline and the whole story beside it
      'strip'  the headline and the whole story, a strip of that day's photos along the bottom
      'then'   then and now: the story's photo beside Bapa on the same date in a recent year (the same town first)
 7. every picture checked before it goes to Drive: no cut words, no cut heads or paghs, faces sharp, nothing off the edge
 8. a phone sized version, and a check that it reads on a WhatsApp screen

Every look uses the style kit (style.py) and never leaves out a word of the story: a long story gets smaller photos and
smaller words, and a look that still can't hold every word is not offered that day."""
import datetime, os, re

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import make
import style
from make import W, H, px, garamond, arimo_bold, gold_text, draw_spaced, spaced, diamond, story_block, balanced, special_card, card_strip

LOOKS = ('hero', 'strip', 'then')
LOOK_NAMES = {'hero': 'One big photo', 'strip': 'Story with a strip of photos', 'then': 'Then and now', 'phone': 'Phone version'}
PHONE_DP = 360          # a phone screen is about 360 points across; WhatsApp shows a picture that wide when it is tapped
PHONE_MIN_DP = 8        # the smallest words must be at least this many points tall on that screen to read without zooming
EDGE = 24               # layout pixels: nothing may come nearer the edge of the picture than this
SHARP = make.SHARP_MIN  # a face blurrier than this (Laplacian variance at 160 px) is not sharp


def learned():
    """What tools/learn.py learned from his Studio changes (archive/learned.json), {} before the first week."""
    try:
        import json
        return json.load(open(os.path.join(make.HERE, 'archive', 'learned.json')))
    except (OSError, ValueError):
        return {}


def his_sizes(sizes):
    """The word sizes to try, starting near the size he usually picks (idea 4); every smaller one is still there."""
    s = learned().get('story_size')
    if not s:
        return sizes
    keep = tuple(v for v in sizes if v <= s + 2)
    return keep or sizes[-1:]


# ---------------------------------------------------------------- the photos (idea 5)

def calm(im, face):
    """0 to 1: how quiet the photo is around Bapa (few busy edges away from his face)."""
    g = cv2.cvtColor(np.array(im.convert('RGB').resize((400, round(400 * im.height / im.width)))), cv2.COLOR_RGB2GRAY)
    e = cv2.Canny(g, 80, 180) > 0
    if face:
        k = 400 / im.width
        x, y, w, h = [v * k for v in face]
        e[max(0, int(y - h)):int(y + 3 * h), max(0, int(x - w)):int(x + 2 * w)] = False   # his face and body are meant to be busy
    return float(max(0, 1 - e.mean() / .12))


def judge(ph):
    """Each photo's Bapa face, how close and sharp it is and how calm the background, and one score for the hero."""
    im, when = ph['im'], ph.get('date') or '2000-01-01'
    face, sim = make.bapa_face(im, when, make.TG_SAME_PERSON if ph.get('tg') else make.SAME_PERSON)
    front = make.LAST_FRONT[0] if face else 0
    sharp, bright = make.face_quality(im, face)
    share = face[3] / im.height if face else 0
    q = calm(im, face)
    score = (3 if face else 0) + min(share, .35) * 8 + (.8 if sharp >= SHARP else 0) + q * 1.2 + front * .6
    score += .6 if make.DOING.search(ph.get('caption') or '') else 0   # Bapa doing something (arti, puja, blessing...)
    ph.update(face=face, sim=sim, sharp=sharp, calm=q, score=score)
    return ph


def best_first(photos):
    """The photos with the best hero first: Bapa recognised, close, sharp, doing something, a calm background."""
    for ph in photos:
        if 'score' not in ph:
            judge(ph)
    return sorted(photos, key=lambda p: -p['score'])


def varied(photos, n):
    """Up to n photos, best first, with no two near the same (the same moment shot twice) while others are left."""
    tiny = lambda im: np.asarray(im.convert('L').resize((16, 16)), dtype=float)
    out, seen, said = [], [], set()
    for ph in photos:   # first one photo for each thing that happened (its caption), then the rest
        t, c = tiny(ph['im']), frozenset(make.caption_key(ph.get('caption') or '')) or id(ph)
        if c not in said and not any(np.abs(t - s).mean() < 22 for s in seen):
            out.append(ph); seen.append(t); said.add(c)
    for ph in photos:
        t = tiny(ph['im'])
        if ph not in out and not any(np.abs(t - s).mean() < 22 for s in seen):
            out.append(ph); seen.append(t)
    out += [ph for ph in photos if ph not in out]   # only when there are too few different ones
    return out[:n]


def no_dashes(paras):   # Darpan's rule: no dashes in picture text ('assembly - Bapa' reads 'assembly, Bapa')
    return [re.sub(r'\s+[-–—]+\s+', ', ', p) for p in paras]


def framed(im, face, w, h, zoom_to=.16):
    """The part of the photo shown in a w x h frame: Bapa's face across the middle, the top of his head (and pagh) well
    inside, zoomed in when he is small (his face at least zoom_to of the frame's height, never past twice the photo).
    Returns the crop box in the photo's own pixels."""
    a = w / h
    cw, ch = (im.width, im.width / a) if im.width / im.height < a else (im.height * a, im.height)
    if face:
        fx, fy, fw, fh = face
        z = min(2.0, max(1.0, zoom_to * ch / fh)) if fh / ch < zoom_to else 1.0
        z = max(1.0, min(z, 2.2 * cw / w))   # never zoomed past the photo's own sharpness (22 Nov test: a small old photo went blocky)
        cw, ch = cw / z, ch / z
        cx = fx + fw / 2
        top = fy - .5 * fh - .14 * ch            # the detector's box starts at the brow: half a face more for the head and pagh
        x0 = min(max(0, cx - cw / 2), im.width - cw)
        y0 = min(max(0, top), im.height - ch)
    else:
        x0, y0 = (im.width - cw) / 2, (im.height - ch) * .3
    return (x0, y0, x0 + cw, y0 + ch)


def card_of(ph, w, h, label=True, zoom_to=.16):
    """An ivory card of the photo, w x h, with its year and town, and the record the picture check reads."""
    label = label and ph.get('label', True)
    box = framed(ph['im'], ph.get('face'), w, h, zoom_to)
    crop = ph['im'].crop(tuple(round(v) for v in box)).resize((round(w), round(h)), Image.LANCZOS)
    c = special_card(crop, round(w), round(h), ph.get('year') if label else '', (ph.get('place') or '').upper() if label else '', label)
    return c, dict(kind='photo', box=box, face=ph.get('face'), sharp=ph.get('sharp', 0), src=ph['im'].size, url=ph.get('url'),
                   label={'year': str(ph.get('year') or ''), 'place': ph.get('place') or ''} if label else False, date=ph.get('date'),
                   scale=w / (box[2] - box[0]), name=f"{ph.get('year') or ''} {ph.get('caption') or ''}".strip())


def put(img, rec, c, x, y, items):
    img.paste(c, (round(x), round(y)), c)
    m = round(px(30))   # special_card's shadow margin
    rec['at'] = (x + m, y + m, x + c.width - m, y + c.height - m)
    items.append(rec)


def pick_now(items, ev):
    """The 'now' of a then and now: Bapa on this same date in a recent year (at least five years after the story), from
    the story's own town first, recognised and as close and sharp as can be. None when there is no such photo."""
    y0 = int(ev['date'][:4])
    town = (make.town_of(ev.get('place')) or '').lower()
    cands = [x for x in items if x.get('path') and int(x.get('y') or 0) >= y0 + 5 and not make.JUNK.search(x.get('c') or '')
             and not (make.GUEST.search(x.get('c') or '') and not make.western(x.get('c') or ''))   # never a meeting photo
             and not re.search(r'in conversation|converses|talks with', x.get('c') or '', re.I)]
    here = lambda x: (make.town_of(make.place(x) or x.get('p')) or '').lower() == town
    cands.sort(key=lambda x: (not (town and here(x)), -int(x['y'])))
    best = None
    for x in cands[:16]:
        try:
            im = Image.open(x['path']).convert('RGB')
        except OSError:
            continue
        ph = judge(dict(im=im, year=int(x['y']), place=make.town_of(make.place(x) or x.get('p')) or '', date=str(x.get('d') or '')[:10] or f"{x['y']}-01-01",
                        caption=x.get('c') or ''))
        if ph['face'] and (best is None or (here(x), ph['year'], ph['score']) > (best[0], best[1]['year'], best[1]['score'])):
            best = (here(x), ph)
            if here(x) or not town:
                break
    return best[1] if best else None


# ---------------------------------------------------------------- words

def kicker(dr, x, y, text, f, fill=style.CREAM, align='left', track=None):
    """A short line of spaced capitals (the date, 'THEN AND NOW')."""
    track = px(6) if track is None else track
    w = spaced(dr, text, f, track)
    x = x - w / 2 if align == 'center' else x
    draw_spaced(dr, x, y, text, f, track, fill)
    return dict(kind='text', at=(x, y, x + w, y + f.size), size=f.size, text=text, role='kicker', font='sans', weight=700,
                track=track, color=fill, align=align)


def words(img, paras, x, y, w, room, sizes, align='left'):
    """The whole story set as large as fits room; returns (records, height used) or None when not every word fits."""
    dr = ImageDraw.Draw(img)
    got = story_block(dr, paras, w, room, sizes)
    lines, bf, lh, gap, whole = got
    if not whole:
        return None
    recs, yy = [], y + bf.size
    for l in lines:
        if l is None:
            yy += gap; continue
        lw = dr.textlength(l, font=bf)
        lx = x + (w - lw) / 2 if align == 'center' else x
        dr.text((lx, yy), l, font=bf, fill=style.IVORY_TEXT, anchor='ls')
        recs.append(dict(kind='text', at=(lx, yy - bf.size * .8, lx + lw, yy + bf.size * .25), size=bf.size, text=l, role='story',
                         weight=500, color=style.IVORY_TEXT, align=align, lh=lh, para=False))
        yy += lh
    for k, l in enumerate(lines):   # where a new paragraph starts, for the Studio's copy of the design
        if l is None:
            n = sum(1 for v in lines[:k] if v is not None)
            if n < len(recs):
                recs[n]['para'] = True
    return recs, yy - lh - y + bf.size * .3, bf.size


def headline(img, text, x, y, w, sizes=(76, 70, 64, 58, 52), lines=3, align='left'):
    dr = ImageDraw.Draw(img)
    for s in sizes:
        hf = garamond(px(s), 700)
        hs = balanced(dr, text, hf, w, lines)
        if ' '.join(hs) == text.strip() and len(hs) <= lines:
            break
    recs, yy = [], y
    for l in hs:
        lw = dr.textlength(l, font=hf)
        lx = x + (w - lw) / 2 if align == 'center' else x
        gold_text(img, (lx, yy), l, hf)
        recs.append(dict(kind='text', at=(lx, yy, lx + lw, yy + hf.size), size=hf.size, text=l, role='headline', weight=700,
                         color='gold', align=align, lh=hf.size * 1.12))
        yy += hf.size * 1.12
    return recs, yy - y


def rule(img, x, y, length=px(120), align='left'):
    dr = ImageDraw.Draw(img)
    x0 = x - length / 2 if align == 'center' else x
    dr.line((x0, y, x0 + length, y), fill=style.GOLD_SOFT, width=max(1, round(px(2))))
    diamond(dr, x0 + length + px(16), y + px(1), px(5), style.GOLD)


def small_footer(img, items, x=None, align='right'):
    dr = ImageDraw.Draw(img)
    f = garamond(px(26), 500)
    w = dr.textlength(style.FOOTER, font=f)
    x = W - px(70) - w if x is None else x - (w / 2 if align == 'center' else 0)
    y = H - px(52)
    dr.text((x, y), style.FOOTER, font=f, fill=style.FOOTER_GOLD)
    diamond(dr, x - px(22), y + f.size * .62, px(5), style.GOLD)
    items.append(dict(kind='text', at=(x, y, x + w, y + f.size), size=f.size, text=style.FOOTER, role='footer', weight=500,
                      color=style.FOOTER_GOLD, align='left'))


def date_line(day, ev):
    """'21 NOVEMBER  ·  2010  ·  BOCHASAN'"""
    town = make.town_of(ev.get('place')) or ev.get('place') or ''
    return '   ·   '.join(p for p in (f'{day.day} {day:%B}'.upper(), ev['date'][:4], town.upper()) if p)


# ---------------------------------------------------------------- the looks

def hero(ev, day, photos, paras):
    """One big photo at the left, all the way down; the date, headline and whole story beside it in quiet space."""
    ph = photos[0]
    a = min(1.25, max(.72, ph['im'].width / ph['im'].height))
    for ch in (1150, 1060, 980, 900, 820):   # a long story makes the photo smaller, never the story shorter
        img = make.background(); dr = ImageDraw.Draw(img); items = []
        h = px(ch - 12 * 2 - 0) - card_strip(px(ch) * a)
        w = min(px(1500), h * a, ph['im'].width * 3)   # a small photo stays a smaller card, the rest is quiet space
        h = min(h, w / a)
        c, rec = card_of(ph, w, h)
        y = (H - c.height + px(30) * 2) / 2 - px(30) - px(6)
        put(img, rec, c, px(70) - px(30), y, items)
        make.peg(img, px(70) + c.width / 2 - px(30), y + px(30) + px(28), px(1.5))
        x0 = px(70) + c.width - px(60) + px(120); tw = min(W - x0 - px(120), px(1350))   # short lines read easily
        x0 += (W - px(120) - x0 - tw) / 2   # the words in the middle of the space beside the photo
        # the date, headline and story as one block, in the middle of the height beside the photo (quiet space above and below)
        probe = img.copy()
        hr, hh = headline(probe, ev.get('headline') or ev['line'], x0, 0, tw)
        top0 = px(110) + px(60) + hh + px(80)
        got = words(probe, paras, x0, top0, tw * .94, H - px(140) - top0, his_sizes((36, 34, 32, 30, 28, 26)))
        if got:
            block = top0 - px(110) + got[1]
            size = round(got[2] / make.SCALE)
            y0 = max(px(110), (H - block) / 2 - px(10))
            items.append(kicker(dr, x0, y0, date_line(day, ev), arimo_bold(px(24))))
            hr, hh = headline(img, ev.get('headline') or ev['line'], x0, y0 + px(60), tw)
            items += hr
            rule(img, x0, y0 + px(60) + hh + px(26))
            top = y0 + px(60) + hh + px(80)
            got = words(img, paras, x0, top, tw * .94, H - px(140) - top, tuple(v for v in (36, 34, 32, 30, 28, 26) if v <= size + 1))
            items += got[0]
            small_footer(img, items)
            return img, items
    return None, []


def strip(ev, day, photos, paras):
    """The date as the title, the headline and the whole story in the middle, a strip of the day's photos along the bottom."""
    for n, sh in ((6, 330), (6, 290), (7, 250), (8, 220), (8, 190)):
        row = varied(photos, n)
        img = make.background(); dr = ImageDraw.Draw(img); items = []
        tf = garamond(px(92), 700); t = f'{day.day} {day:%B}'
        gold_text(img, ((W - dr.textlength(t, font=tf)) / 2, px(4)), t, tf)
        items.append(kicker(dr, W / 2, px(118), '   ·   '.join(p for p in (ev['date'][:4], (make.town_of(ev.get('place')) or ev.get('place') or '').upper()) if p), arimo_bold(px(24)), align='center'))
        hr, hh = headline(img, ev.get('headline') or ev['line'], px(300), px(168), W - px(600), sizes=(62, 56, 52, 48), lines=2, align='center')
        items += hr
        gap = px(40)
        cw = min(px(sh) / .75, (W - px(140) - gap * (len(row) - 1)) / len(row))
        chh = cw * .75
        strip_h = chh + px(24) + card_strip(cw)
        y_strip = H - px(80) - strip_h
        top = px(168) + hh + px(28)
        got = words(img, paras, px(420), top, W - px(840), y_strip - px(40) - top, his_sizes((34, 32, 30, 28, 26, 24)), align='center')
        if not got:
            continue
        items += got[0]
        across = len(row) * cw + (len(row) - 1) * gap
        x = (W - across) / 2
        for ph in row:
            c, rec = card_of(ph, cw, chh, zoom_to=.2)
            put(img, rec, c, x - px(30) - px(12), y_strip - px(30) - px(12), items)
            make.peg(img, x + cw / 2, y_strip + px(16), px(1))
            x += cw + gap
        small_footer(img, items, W / 2, 'center')
        return img, items
    return None, []


def then_and_now(ev, day, photos, paras, now):
    """The story's photo and Bapa on the same date in a recent year, side by side, the whole story beside them."""
    then = photos[0]
    # only when it means something: Bapa is in the story's photo, or the 'now' is from the story's own town
    if not now or not (then.get('face') or (make.town_of(ev.get('place')) or '').lower() == (now.get('place') or '').lower()):
        return None, []
    for ch in (900, 820, 740, 660):
        img = make.background(); dr = ImageDraw.Draw(img); items = []
        w = px(ch) * .78; h = px(ch) - card_strip(w)
        y = (H - px(ch)) / 2 + px(20)
        x = px(70)
        for k, ph in enumerate((then, now)):
            c, rec = card_of(ph, w, h, zoom_to=.2)
            items.append(kicker(dr, x + px(12) + w / 2, y - px(58), ('THEN' if k == 0 else 'NOW'), arimo_bold(px(26)), fill=style.GOLD, align='center', track=px(10)))
            put(img, rec, c, x - px(30), y - px(30), items)
            x += w + px(24) + px(60)
        x0 = x + px(60); tw = W - x0 - px(110)
        items.append(kicker(dr, x0, px(150), f'{day.day} {day:%B}'.upper() + '   ·   THEN AND NOW', arimo_bold(px(24))))
        hr, hh = headline(img, ev.get('headline') or ev['line'], x0, px(210), tw, sizes=(68, 62, 56, 50))
        items += hr
        rule(img, x0, px(210) + hh + px(26))
        top = px(210) + hh + px(80)
        got = words(img, paras, x0, top, tw, H - px(140) - top, his_sizes((34, 32, 30, 28, 26, 24)))
        if got:
            items += got[0]
            small_footer(img, items)
            return img, items
    return None, []


def phone(ev, day, photos, paras):
    """A tall version for a phone screen (idea 8): the hero photo across the top, the date, headline and whole story
    under it at a size that reads when the picture fills a phone. As tall as the story needs (never a word left off)."""
    PW = round(px(1290)); f = PW / px(1290)
    probe = Image.new('RGB', (PW, 10)); dr = ImageDraw.Draw(probe)
    tw = px(1290 - 2 * 90)
    bf = garamond(px(40), 500)
    got = story_block(dr, paras, tw, 10 ** 6, (40,))
    lines, bf, lh, gap, _ = got
    words_h = sum(gap if l is None else lh for l in lines)
    ph = photos[0]
    ch = px(1000)
    hf = garamond(px(70), 700)
    heads = balanced(dr, ev.get('headline') or ev['line'], hf, tw, 4)
    PH = round(px(70) + ch + px(90) + px(60) + len(heads) * hf.size * 1.12 + px(70) + words_h + px(140))
    PH = max(PH, round(PW * 16 / 9))
    img = make.background().resize((PW, PH), Image.BICUBIC)
    d = ImageDraw.Draw(img); items = []
    w = px(1290 - 2 * 70); h = ch - card_strip(w)
    c, rec = card_of(ph, w, h, zoom_to=.18)
    put(img, rec, c, px(70) - px(30), px(70) - px(30), items)
    y = px(70) + c.height - px(60) + px(70)
    items.append(kicker(d, PW / 2, y, f'{day.day} {day:%B}'.upper() + '   ·   ' + ev['date'][:4], arimo_bold(px(30)), align='center'))
    y += px(70)
    for l in heads:
        lw = d.textlength(l, font=hf)
        gold_text(img, ((PW - lw) / 2, y), l, hf)
        items.append(dict(kind='text', at=((PW - lw) / 2, y, (PW + lw) / 2, y + hf.size), size=hf.size, text=l))
        y += hf.size * 1.12
    y += px(40)
    rule(img, PW / 2, y, align='center'); y += px(50)
    yy = y + bf.size
    for l in lines:
        if l is None:
            yy += gap; continue
        lw = d.textlength(l, font=bf)
        d.text(((PW - lw) / 2, yy), l, font=bf, fill=style.IVORY_TEXT, anchor='ls')
        items.append(dict(kind='text', at=((PW - lw) / 2, yy - bf.size * .8, (PW + lw) / 2, yy + bf.size * .25), size=bf.size, text=l))
        yy += lh
    fo = garamond(px(30), 500); fw = d.textlength(style.FOOTER, font=fo)
    d.text(((PW - fw) / 2, PH - px(70)), style.FOOTER, font=fo, fill=style.FOOTER_GOLD)
    items.append(dict(kind='text', at=((PW - fw) / 2, PH - px(70), (PW + fw) / 2, PH - px(70) + fo.size), size=fo.size, text=style.FOOTER))
    return img, items


# ---------------------------------------------------------------- the picture check (ideas 7 and 8)

def check(img, items, paras=None):
    """What is wrong with a finished picture, in plain words ([] when nothing): words cut or off the edge, a head or
    pagh cut by its frame, a blurry face, anything too near the edge, and how the smallest words read on a phone."""
    faults = []
    iw, ih = img.size
    e = px(EDGE)
    for it in items:
        x0, y0, x1, y1 = it['at']
        if x0 < e - 1 or y0 < e - 1 or x1 > iw - e + 1 or y1 > ih - e + 1:
            faults.append(f"too near the edge: {it.get('text') or it.get('name')}"[:90])
        if it['kind'] == 'photo' and it.get('face'):
            fx, fy, fw, fh = it['face']; bx0, by0, bx1, by1 = it['box']
            if fy - .5 * fh < by0 - 1 and by0 > 1:   # cut by our frame (not a photo taken that way)
                faults.append(f"head or pagh cut at the top: {it['name']}"[:90])
            if fx < bx0 - 1 or fx + fw > bx1 + 1 or fy + fh > by1 + 1:
                faults.append(f"face cut by the frame: {it['name']}"[:90])
            if it.get('sharp', 0) < SHARP and it['scale'] * fh > px(90):
                faults.append(f"face not sharp ({it['sharp']:.0f}): {it['name']}"[:90])
        if it['kind'] == 'photo' and it.get('scale', 0) * 1 > 1.6:
            faults.append(f"photo blown up {it['scale']:.1f} times, may look soft: {it['name']}"[:90])
    if paras is not None:
        shown = re.sub(r'\W+', '', ' '.join(it['text'] for it in items if it['kind'] == 'text'))
        missing = [w for w in re.findall(r'\w+', ' '.join(paras)) if w not in shown]
        if missing:
            faults.append(f'{len(missing)} words of the story missing')
    texts = [it['size'] for it in items if it['kind'] == 'text']
    small = min(texts) if texts else 0
    dp = small * PHONE_DP / iw
    return faults, round(dp, 1)


def whatsapp_view(img, name='Family'):
    """How the picture looks on a phone in a WhatsApp chat (idea 8): the chat bubble, then the picture tapped open."""
    S = 3; sw, sh = 360 * S, 760 * S
    def screen(inner, chat):
        s = Image.new('RGB', (sw, sh), (11, 20, 26) if chat else (0, 0, 0)); d = ImageDraw.Draw(s)
        d.rectangle((0, 0, sw, 56 * S), fill=(31, 44, 52))
        d.text((16 * S, 18 * S), name if chat else '', font=arimo_bold(16 * S), fill=(233, 237, 239))
        if chat:
            bw = 300 * S; k = bw / inner.width; bh = min(round(inner.height * k), 420 * S)
            pic = inner.resize((bw, round(inner.height * k)), Image.LANCZOS).crop((0, 0, bw, bh))
            bx, by = sw - bw - 14 * S, 90 * S
            d.rounded_rectangle((bx - 4 * S, by - 4 * S, bx + bw + 4 * S, by + bh + 22 * S), 8 * S, fill=(0, 92, 75))
            s.paste(pic, (bx, by))
            d.text((bx + bw - 4 * S, by + bh + 16 * S), '2:00 pm', font=garamond(11 * S, 500), fill=(200, 220, 210), anchor='rs')
        else:
            k = sw / inner.width; ph = round(inner.height * k)
            pic = inner.resize((sw, ph), Image.LANCZOS)
            if ph > sh - 56 * S:
                k = (sh - 56 * S) / inner.height; pic = inner.resize((round(inner.width * k), sh - 56 * S), Image.LANCZOS)
            s.paste(pic, ((sw - pic.width) // 2, 56 * S + (sh - 56 * S - pic.height) // 2))
        return s
    a, b = screen(img, True), screen(img, False)
    out = Image.new('RGB', (sw * 2 + 40 * S, sh + 40 * S), (240, 236, 228))
    for k, s in enumerate((a, b)):
        m = Image.new('L', s.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, s.width, s.height), 30 * S, fill=255)
        out.paste(s, (20 * S + k * (sw + 0 * S) + k * 0, 20 * S), m)
    return out


# ---------------------------------------------------------------- all of them

def make_looks(ev, day, photos, now=None, paras=None, only=None):
    """Every look of the day's special: {look: dict(img, faults, phone_dp)}; a look that can't hold the whole story or
    has no 'now' photo is left out. photos: [{im, year, place, date, caption, tg}] of the story's own day and place."""
    paras = paras if paras is not None else make.special_words(ev)
    paras = no_dashes(paras)
    photos = best_first(list(photos))
    if now:
        judge(now)
    out = {}
    for name, fn in (('hero', lambda: hero(ev, day, photos, paras)), ('strip', lambda: strip(ev, day, photos, paras)),
                     ('then', lambda: then_and_now(ev, day, photos, paras, now)), ('phone', lambda: phone(ev, day, photos, paras))):
        if only and name != only:
            continue
        img, items = fn()
        if img is None:
            continue
        faults, dp = check(img, items, paras)
        img.info['design'] = design_of(items, img.size)
        img.info['faults'] = faults
        out[name] = dict(img=img, faults=faults, phone_dp=dp, design=img.info['design'])
    return out


# ---------------------------------------------------------------- his Final layouts as templates (idea 3)

KINDS = [   # what sort of day a special is, from its headline and story
    ('festival', r'diwali|annakut|new year|janmashtami|jayanti|navmi|purnima|holi|fuldol|pushpadol|utsav|festival|mahotsav|samaiyo|ekadashi|parva'),
    ('departure', r'depart|leaves|left for|farewell|flies|flew|sets off|set off|send.?off|bids? farewell|returns? to india|journey'),
    ('mandir opening', r'pratishtha|inaugurat|opening|opens|consecrat|murti|shilanyas|foundation stone|mandir'),
    ('birthday', r'birth|janm|birthday|born|anniversary|diksha'),
]


def kind_of(text):
    """'festival', 'departure', 'mandir opening', 'birthday' or 'other'."""
    for k, rx in KINDS:
        if re.search(rx, text or '', re.I):
            return k
    return 'other'


def layout_text(lay):
    return ' '.join(str(i.get('text') or ' '.join(str(v) for v in i.get('lines') or [] if v)) for i in lay.get('items') or []
                    if isinstance(i, dict) and i.get('type') == 'text' and i.get('role') in ('headline', 'story', None))


def templates():
    """His Final layouts (layout version 2, pressed Final in the Studio), newest day first, each with its kind of day."""
    out = []
    for c in make.special_choices()['add']:
        lay = c.get('layout')
        if isinstance(lay, dict) and lay.get('final') and lay.get('items'):
            text = ' '.join(str(c.get(k) or '') for k in ('headline', 'story', 'note')) + ' ' + layout_text(lay)
            out.append(dict(day=str(c['day']), kind=kind_of(text), layout=lay, photos=sum(1 for i in lay['items'] if i.get('type') == 'photo')))
    return sorted(out, key=lambda t: t['day'], reverse=True)


def from_template(t, ev, day, urls):
    """His saved layout filled with today's special: its photo places get today's photos in order (the same frames,
    crops in the middle), its headline and story boxes today's words, smaller where today's story is longer (never cut)."""
    import copy
    num = lambda v, d=0.0: float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else d
    lay = copy.deepcopy(t['layout']); lay.pop('final', None)
    urls = list(urls)
    head = ev.get('headline') or ev['line']
    story = '\n\n'.join(no_dashes(make.special_words(ev)))
    probe = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    for i in lay['items']:
        if i.get('type') == 'photo':
            if urls:
                i.update(photo=urls.pop(0), date=ev['date'][:10], place=ev.get('place') or '', label=i.get('label') and True, focus=[.5, .3], zoom=100)
            else:
                i['skip'] = True
        elif i.get('type') == 'text':
            role = i.get('role')
            new = {'headline': head, 'story': story, 'title': f'{day.day} {day:%B}'}.get(role)
            if new is None:
                continue
            i.pop('lines', None); i['text'] = new
            size = num(i.get('size'), 34)   # smaller until every word fits its box
            lhm = num(i.get('line_height'), 1.3)
            for k in range(30):
                f = make.any_font('sans' if i.get('font') == 'sans' else 'serif', num(i.get('weight'), 500), px(size))
                n = sum(len(make.wrap(probe, row, f, px(num(i.get('w'), 300)), 999, shorten=False) or ['']) + .5 for row in new.split('\n\n'))
                if n * px(lhm * size) <= px(num(i.get('h'), 200)) or size <= 14:
                    break
                size *= .95
            i['size'] = round(size, 1)
    lay['items'] = [i for i in lay['items'] if not i.get('skip')]
    lay['template_from'] = t['day']
    return lay


# ---------------------------------------------------------------- the look as a Studio design (layout version 2)

def design_of(items, canvas=(W, H)):
    """The finished look as a Studio design (layout version 2, the same kind the Studio's designer makes), so the Studio
    opens exactly the drawing that goes out (Darpan, 17 Nov 2026: 'one source of truth'). Lengths in layout units."""
    u = lambda v: round(v / make.SCALE, 1)
    hexc = lambda c: c if isinstance(c, str) else '#%02x%02x%02x' % tuple(c)
    out = []
    for it in items:
        if it['kind'] != 'photo':
            continue
        x0, y0, x1, y1 = it['at']; bx0, by0, bx1, by1 = it['box']; sw, sh = it['src']
        cover = max((bx1 - bx0) / sw, (by1 - by0) / sh)   # how much of the photo the frame shows across, 1 = the whole width or height
        out.append(dict(type='photo', role='photo', photo=it.get('url') or '', date=it.get('date'), x=u(x0), y=u(y0), w=u(x1 - x0), h=u(y1 - y0),
                        frame=True, label=it.get('label') or False, peg=True,
                        focus=[round(bx0 / max(1, sw - (bx1 - bx0)), 3) if sw > bx1 - bx0 + 1 else .5,
                               round(by0 / max(1, sh - (by1 - by0)), 3) if sh > by1 - by0 + 1 else .5],
                        zoom=round(100 / max(cover, .01))))
    groups = []
    for it in items:   # the lines of one headline, story or date line become one text item
        if it['kind'] != 'text':
            continue
        g = groups[-1] if groups and groups[-1][0]['role'] == it.get('role') and it.get('role') in ('headline', 'story') else None
        if g is None:
            groups.append([it])
        else:
            g.append(it)
    for g in groups:
        a = g[0]
        x0 = min(i['at'][0] for i in g); x1 = max(i['at'][2] for i in g)
        y0 = min(i['at'][1] for i in g); y1 = max(i['at'][3] for i in g)
        lines = []
        for i in g:
            if i.get('para') and lines:
                lines.append('')
            lines.append(i['text'])
        size = u(a['size'])
        out.append(dict(type='text', role={'kicker': 'subtitle'}.get(a.get('role'), a.get('role') or 'text'), text='\n'.join(lines).replace('\n\n\n', '\n\n'),
                        lines=lines, x=u(x0), y=u(y0 - a['size'] * .15), w=u(x1 - x0) + 2, h=u(y1 - y0 + a['size'] * .5),
                        size=size, font=a.get('font', 'serif'), weight=a.get('weight', 500), color=hexc(a.get('color', 'ivory')),
                        align=a.get('align', 'left'), line_height=round(a['lh'] / a['size'], 2) if a.get('lh') else 1.3,
                        letter_spacing=u(a['track']) if a.get('track') else 0, upper=a.get('role') == 'kicker'))
    return {'version': 2, 'auto': True, 'look': True, 'size': [u(canvas[0]), u(canvas[1])], 'items': out}
