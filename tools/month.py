#!/usr/bin/env python3
"""Month cards: one month of Bapa's vicharan on a single picture for a public channel (Darpan, 22 Oct 2026:
'January 2012 ... a close up one, an activities one, and mixed ... 15, 20 different pictures').

    python tools/month.py --month 2012-01                 every design into preview/month/2012-01/
    python tools/month.py --month 2012-01 --fake          grey stand in photos, to check layouts without baps.org

Photos come from archive/vicharan (every captioned photo of every day) and archive/memories (the screensaver's
lists), only those taken in that month. Each photo gets the daily picture's face check, then per day the best
close darshan and the best activity are picked. Mockups only: nothing here touches the daily picture.
"""
import argparse, calendar, datetime, glob, json, math, os, random, re, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make   # noqa: E402  the daily picture's face check, crops, fonts and caption tidying
from make import (ACTION_KEEP, CLOSE_MIN_FACE, DOING, JUST_A_FACE, SHARP_MIN, BRIGHT_MIN, GUEST, caption, caption_key,
                  crop_to, frame_keep, gold_text, garamond, arimo_bold, spaced, draw_spaced, polish, wrap, is_special,
                  bapa_is_subject, same_caption, DARSHAN)   # noqa: E402

HERE = make.HERE
IVORY_TOP, IVORY_BOTTOM, IVORY_EDGE = make.IVORY_TOP, make.IVORY_BOTTOM, make.IVORY_EDGE
MAROON, MAROON_DEEP = (96, 20, 32), (22, 5, 10)
GOLD, GOLD_SOFT, CREAM = (255, 207, 107), (226, 184, 104), (240, 214, 160)
FOOTER = make.FOOTER
SQ, PT, ST, LS = (2160, 2160), (2160, 2700), (1620, 2880), (3240, 1495)   # square, 4:5 portrait, phone story, the diary's own wide shape


# ---------------------------------------------------------------- the month's photos

def month_items(year, month):
    """Every photo listed for that month, once each, with the day it was taken."""
    want, out, seen = f'{year}-{month:02d}', [], set()
    nxt = datetime.date(year + month // 12, month % 12 + 1, 1)
    days = [f'{month:02d}-{d:02d}' for d in range(1, calendar.monthrange(year, month)[1] + 1)] + [f'{nxt:%m}-{d:02d}' for d in range(1, 4)]
    for mmdd in days:
        path = os.path.join(HERE, 'archive', 'vicharan', mmdd + '.txt')
        lists = []
        if os.path.exists(path):
            lists += make.vicharan_items(path, mmdd, {}, per_caption=6)
        lp = os.path.join(HERE, 'archive', 'memories', mmdd + '.json')
        if os.path.exists(lp):
            lists += json.load(open(lp, encoding='utf-8'))
        for x in lists:
            if str(x.get('d', '')).startswith(want) and x['i'] not in seen and x['y'] == year:
                seen.add(x['i']); out.append(dict(x))
    return out


def full_size(items, cache):
    """Try baps.org's full size copy of each photo first (the cards are big), the web copy when there is none."""
    big = [dict(x, i=x['i'].replace('/WebImages/', '/FullSizeImages/'), web=x['i']) for x in items]
    make.download_all(big, os.path.join(cache, 'full'))
    got = sum('path' in x for x in big)
    print(f'  full size copies: {got} of {len(big)}', flush=True)
    rest = [dict(x, i=x['web']) for x in big if 'path' not in x]
    if rest:
        make.download_all(rest, cache)
    out = [x for x in big if 'path' in x] + [x for x in rest if 'path' in x]
    for x in out:
        x['i'] = x.pop('web', x['i'])
    return out


def analyse(items):
    """The daily picture's face check on every photo, and how good it is as a close darshan and as an activity."""
    out = []
    for x in items:
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        if make.JUNK.search(x.get('c') or ''):
            continue
        face, sim = make.bapa_face(im, x['d'])
        if not face:
            continue
        front = make.LAST_FRONT[0]
        r = face[3] / im.height
        c = x.get('c') or ''
        sharp, bright = make.face_quality(im, face)
        scale = im.height / 800   # the full size copies are bigger than the web ones the limits were set on
        close_ok = face[3] >= CLOSE_MIN_FACE * scale ** .5 and front >= .35 and sharp >= SHARP_MIN * .6 and bright >= BRIGHT_MIN
        special, subject = is_special(c), bapa_is_subject(c)
        doing = bool(DOING.search(c)) and not JUST_A_FACE.search(c)
        keep = frame_keep(im, face, 1.4)
        soft = .5 * max(0, 1 - sharp / (2 * SHARP_MIN)) + .5 * max(0, 1 - bright / (1.5 * BRIGHT_MIN))
        s_close = 1 + min(r, .35) + sim + .9 * (front - .6) - (.6 if not subject else 0) - (1.5 if not close_ok else 0) - soft
        s_close += .2 if JUST_A_FACE.search(c) else 0
        s_act = (1 + sim + .6 * max(0, 1 - abs(r - .16) / .15) + (.5 if doing else 0) + (.9 if special else 0) - (.5 if r < .06 else 0)
                 - (.6 if not subject else 0) - (0 if keep >= ACTION_KEEP else .4) - soft - 2.5 * max(0, .3 - front) / .3)
        if GUEST.search(caption(x)):
            s_act -= 1.2
        if caption(x) == DARSHAN:
            s_act -= 1
        im.thumbnail((2400, 2400))
        k = im.width / Image.open(x['path']).width
        out.append(dict(x, face=tuple(v * k for v in face), sim=sim, front=front, close_ok=close_ok, special=special,
                        doing=doing, s_close=s_close, s_act=s_act, size=im.size))
        im.close()
    return out


def fake_items(items, year, month):
    """Grey stand in photos with a pretend face, so the layouts can be checked without baps.org."""
    rnd = random.Random(1)
    folder = os.path.join(HERE, '.cache', 'fake'); os.makedirs(folder, exist_ok=True)
    out = []
    for n, x in enumerate(items):
        path = os.path.join(folder, f'{n}.jpg')
        w, h = (1200, 800) if rnd.random() < .7 else (800, 1100)
        if not os.path.exists(path):
            im = Image.new('RGB', (w, h), tuple(rnd.randint(60, 200) for _ in range(3)))
            d = ImageDraw.Draw(im)
            fx, fy, fs = w * rnd.uniform(.35, .6), h * rnd.uniform(.2, .35), h * rnd.uniform(.12, .3)
            d.rectangle((fx - fs, fy + fs * .8, fx + fs * 2, h), fill=(214, 120, 40))
            d.ellipse((fx, fy, fx + fs, fy + fs * 1.2), fill=(150, 100, 70))
            d.text((20, 20), f'{x["d"]} {n}', fill=(255, 255, 255))
            im.save(path)
        im = Image.open(path)
        w, h = im.size
        rr = random.Random(n)
        fx, fy, fs = w * rr.uniform(.35, .6), h * rr.uniform(.2, .35), h * rr.uniform(.12, .3)
        c = x.get('c') or ''
        out.append(dict(x, path=path, face=(fx, fy, fs, fs * 1.2), sim=.7, front=.8, close_ok=fs > 120, special=is_special(c),
                        doing=bool(DOING.search(c)), s_close=fs / h + rr.random() * .2, s_act=(1 if is_special(c) else 0) + rr.random(), size=(w, h)))
    return out


class Month:
    """The month's picks: per day the best close darshan and the best activity, the month's highlights."""

    def __init__(self, photos, year, month):
        self.year, self.month = year, month
        self.name = f'{calendar.month_name[month]} {year}'
        self.days = calendar.monthrange(year, month)[1]
        by = {}
        for x in photos:
            by.setdefault(int(x['d'][8:10]), []).append(x)
        self.by = by
        self.close, self.act, self.mixed = {}, {}, {}
        used = set()
        for d, xs in sorted(by.items()):
            cs = sorted(xs, key=lambda x: -(x['s_close'] + (1.5 if x['close_ok'] else 0) + (.8 if fits(x, 1) else 0)))
            self.close[d] = cs[0]
            told = [caption_key(caption(a)) for a in self.act.values()]   # an activity already shown on an earlier day loses
            acts = sorted([x for x in xs if x['doing'] or x['special']],
                          key=lambda x: -(x['s_act'] + (.8 if subject(x) else 0) - (1.5 if any(same_caption(caption_key(caption(x)), k) for k in told) else 0)))
            acts = [x for x in acts if x['i'] != cs[0]['i']] or acts
            if acts:
                self.act[d] = acts[0]
            # mixed: the daily picture's own rule, a special moment when the day has one, otherwise a close darshan
            sp = [x for x in acts if x['special'] and x['s_act'] >= 2]
            self.mixed[d] = dict(sp[0], kind='act') if sp else dict(cs[0], kind='close')
            used.add(cs[0]['i'])
        # highlights: the month's best activities, no two telling the same thing, at most two from one day
        hl, per = [], {}
        for x in sorted((x for xs in by.values() for x in xs if (x['doing'] or x['special']) and subject(x)), key=lambda x: -(x['s_act'] + .6 * x['special'])):
            d = int(x['d'][8:10]); k = caption_key(caption(x))
            if per.get(d, 0) >= 2 or any(same_caption(k, caption_key(caption(h))) for h in hl):
                continue
            hl.append(x); per[d] = per.get(d, 0) + 1
        self.highlights = hl
        self.best_close = sorted(self.close.values(), key=lambda x: -x['s_close'])

        places = {}
        for x in photos:
            p = make.place(x)
            if p:
                places[p] = places.get(p, 0) + 1
        self.places = sorted(places, key=lambda p: -places[p])
        self.count = len(photos)

    def hero(self, aspect):
        """The month's best close darshan that fills a window of that shape (width / height)."""
        ok = [x for xs in self.by.values() for x in xs if x['close_ok'] and fits(x, aspect)]
        return max(ok, key=lambda x: x['s_close'] + x['size'][1] / 4000) if ok else self.best_close[0]

    def summary(self):
        out = [f'{self.name}: {self.count} photos of Bapa on {len(self.by)} days, places {", ".join(self.places)}']
        for d in sorted(self.by):
            c, a = self.close[d], self.act.get(d)
            out.append(f'{d:2d}  close {c["i"].rsplit("/", 1)[1]} ({c["s_close"]:.2f})   activity: {caption(a) if a else "-"}')
        out.append('highlights:')
        out += [f'  {int(x["d"][8:10]):2d}  {caption(x)}  ({x["s_act"]:.2f}{" special" if x["special"] else ""})' for x in self.highlights[:16]]
        return '\n'.join(out)


# ---------------------------------------------------------------- drawing helpers

def canvas(size, glow=.55, jali=.11):
    """The diary's maroon: a soft radial glow, warm lamp light from the top, paper grain, a faint jali at the edges."""
    w, h = size
    sw, sh = w // 8, h // 8
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    d = np.clip(np.hypot((xx - sw / 2) / (sw / 2 * .9), (yy - sh * .45) / (sh / 2 * .95)), 0, 1)[..., None]
    inner, outer = np.array([66, 16, 28]), np.array(MAROON_DEEP)
    a = inner + (outer - inner) * d
    top = np.clip(1 - np.hypot((xx - sw / 2) / (sw * .5), (yy - sh * .02) / (sh * .32)), 0, 1) ** 1.6
    a += np.array([132, 74, 34]) * top[..., None] * glow
    img = Image.fromarray(a.clip(0, 255).astype('uint8')).resize((w, h), Image.BICUBIC)
    noise = Image.effect_noise((w // 2, h // 2), 10).resize((w, h)).convert('L')
    img = Image.composite(Image.new('RGB', (w, h)), img, noise.point(lambda v: max(0, v - 118) // 3))
    if jali:
        R = round(w / 40)
        m = Image.new('L', (w, h)); md = ImageDraw.Draw(m)
        for cy in range(-R, h + R, R):
            for cx in range(-R, w + R, R):
                md.ellipse((cx - R, cy - R, cx + R, cy + R), outline=255, width=max(1, round(w / 1400)))
        xs = np.minimum(np.arange(w), w - 1 - np.arange(w)); ys = np.minimum(np.arange(h), h - 1 - np.arange(h))
        fade = np.clip(1 - np.minimum(xs[None, :], ys[:, None]) / (w * .07), 0, 1) ** 1.3
        mask = Image.fromarray((np.asarray(m, np.float32) * fade * jali).astype('uint8'))
        img.paste(Image.new('RGB', (w, h), (160, 84, 74)), (0, 0), mask)
    return img


def load(x):
    im = Image.open(x['path']).convert('RGB')
    im.thumbnail((2400, 2400))
    return im


def fits(x, aspect, mode='close'):
    """True when crop_to can cut this photo to that shape without falling back to the whole photo on a blurred fill
    (a tight portrait in a wide window): his whole head has to fit inside the window."""
    iw, ih = x['size']
    fx, fy, fw, fh = x['face']
    cw, ch = (ih * aspect, ih) if iw / ih > aspect else (iw, iw / aspect)
    if mode == 'close':
        ch = min(ch, fh / (.38 if aspect > 1 else .30)); cw = min(cw, ch * aspect); ch = cw / aspect
    return 1.9 * fh <= ch * .98 and 1.7 * fw <= cw * .98


def subject(x):
    """Strictly about Bapa: the website's caption starts with his name or with what he does."""
    c = make.about_bapa(re.sub(r'\s+', ' ', x.get('c') or '').strip())
    return c[:1].islower() or bool(re.match(make.NAME, c))


def shot(x, w, h, mode='frame'):
    """The photo cut to w x h: 'close' a tight darshan, 'frame' filling the frame around Bapa, 'whole' all of it."""
    w, h = round(w), round(h)
    im = load(x)
    if mode == 'close' and not (x['close_ok'] and fits(x, w / h)):
        mode = 'frame'
    if mode == 'frame' and not fits(x, w / h, 'frame'):
        mode = 'whole'
    if mode == 'frame' and frame_keep(im, x['face'], w / h) < .62:   # an activity would lose what Bapa is doing: show it all
        mode = 'whole'
    return polish(crop_to(im, x['face'], w, h, mode))


def shadow(img, box, radius, blur, alpha=150, offset=(0, 0), round_=0, ellipse=False):
    x0, y0, x1, y1 = [round(v) for v in box]
    pad = round(blur * 3)
    m = Image.new('L', (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad))
    md = ImageDraw.Draw(m)
    shape = (pad, pad, pad + x1 - x0, pad + y1 - y0)
    md.ellipse(shape, fill=alpha) if ellipse else md.rounded_rectangle(shape, round_, fill=alpha)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    img.paste(Image.new('RGB', m.size), (x0 - pad + round(offset[0]), y0 - pad + round(offset[1])), m)


def paste_round(img, photo, xy, r, shade=True):
    """A photo with rounded corners and a soft shadow."""
    w, h = photo.size
    if shade:
        shadow(img, (xy[0], xy[1], xy[0] + w, xy[1] + h), 0, w * .02 + 6, 160, (0, round(w * .012 + 3)), round(r))
    m = Image.new('L', photo.size); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), round(r), fill=255)
    img.paste(photo, (round(xy[0]), round(xy[1])), m)


def ivory(w, h):
    card = Image.new('RGB', (round(w), round(h))); d = ImageDraw.Draw(card)
    for j in range(card.height):
        t = j / card.height
        d.line((0, j, card.width, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)))
    return card


def polaroid(photo, border, band, tilt=0, label=None, sub=None, label_size=None):
    """The diary's ivory polaroid around a photo, with a label (the date) and a smaller line under it in the band."""
    pw, ph = photo.size
    cw, ch = pw + 2 * border, ph + border + band
    card = ivory(cw, ch).convert('RGBA'); d = ImageDraw.Draw(card)
    d.rectangle((0, 0, cw - 1, ch - 1), outline=IVORY_EDGE, width=2)
    card.paste(photo, (border, border))
    d.rectangle((border - 1, border - 1, border + pw, border + ph), outline=(150, 130, 100), width=2)
    if label:
        ls = label_size or band * .42
        f = garamond(ls, 600)
        lines = [label]
        if sub:
            sf = garamond(ls * .62, 500)
            sub_lines = wrap(d, sub, sf, cw - 2 * border, 2)
            gap = ls * .78
            total = ls * .8 + gap * len(sub_lines)
        else:
            total = ls * .8
        top = border + ph + (band - total) / 2 + ls * .78
        d.text((cw / 2, top), label, font=f, fill=MAROON, anchor='ms')
        if sub:
            for i, s in enumerate(sub_lines):
                d.text((cw / 2, top + gap * (i + 1)), s, font=sf, fill=(88, 34, 34), anchor='ms')
    if tilt:
        card = card.rotate(tilt, Image.BICUBIC, expand=True)
    return card


def drop_card(img, card, cx, cy, soft=None):
    """Paste an RGBA card centred at cx, cy over a soft shadow."""
    w, h = card.size
    x, y = round(cx - w / 2), round(cy - h / 2)
    soft = soft or w * .03 + 4
    sh = card.split()[3].filter(ImageFilter.GaussianBlur(soft)).point(lambda v: v * 150 // 255)
    img.paste(Image.new('RGB', card.size), (x, y + round(soft * .6)), sh)
    img.paste(card, (x, y), card)


def title(img, text, y, size, sub=None, sub_size=None, x=None, anchor='m'):
    """Gold EB Garamond title, the diary's spaced capital line under it."""
    d = ImageDraw.Draw(img)
    f = garamond(size, 700)
    tw = d.textlength(text, font=f)
    tx = (img.width - tw) / 2 if x is None else (x if anchor == 'l' else x - tw / 2)
    gold_text(img, (tx, y), text, f)
    if sub:
        sf = garamond(sub_size or size * .3, 600); track = (sub_size or size * .3) * .24
        s = sub.upper(); sw = spaced(d, s, sf, track)
        sx = (img.width - sw) / 2 if x is None else (x if anchor == 'l' else x - sw / 2)
        draw_spaced(d, sx, y + size * 1.26, s, sf, track, CREAM)
    return y + size * 1.26 + (sub_size or size * .3) * 1.3


def foot(img, size=None, y=None):
    d = ImageDraw.Draw(img)
    f = garamond(size or img.width * .016, 500)
    w = d.textlength(FOOTER, font=f)
    y = img.height - f.size * 2.2 if y is None else y
    d.text(((img.width - w) / 2, y), FOOTER, font=f, fill=GOLD_SOFT)
    box = d.textbbox(((img.width - w) / 2, y), 'Dp', font=f)
    mid = (box[1] + box[3]) / 2
    r = f.size * .14
    make.diamond(d, (img.width - w) / 2 - f.size * .7, mid, r, GOLD); make.diamond(d, (img.width + w) / 2 + f.size * .7, mid, r, GOLD)


def day_word(m, d, short=True):
    wd = datetime.date(m.year, m.month, d).strftime('%a' if short else '%A')
    return wd


def date_label(m, d):
    return f'{d} {calendar.month_name[m.month]}'


def short_caption(d, x, f, maxw, lines=2):
    return wrap(d, caption(x), f, maxw, lines)


def mask_circle(photo):
    m = Image.new('L', (photo.width * 2, photo.height * 2)); ImageDraw.Draw(m).ellipse((0, 0, m.width - 1, m.height - 1), fill=255)
    return m.resize(photo.size, Image.LANCZOS)


def mask_arch(w, h):
    """A mandir window: straight sides and a pointed arch on top."""
    k = 2; W_, H_ = w * k, h * k
    m = Image.new('L', (W_, H_)); d = ImageDraw.Draw(m)
    rise = W_ * .62
    d.rectangle((0, rise, W_, H_), fill=255)
    pts = []
    R = W_ * .85                                   # two arcs meeting in a point at the top centre
    for i in range(41):
        t = i / 40
        xL = t * W_ / 2
        cxL = R                                    # left arc centred on the right edge side
        y = rise - math.sqrt(max(0, R ** 2 - (xL - cxL) ** 2)) + math.sqrt(max(0, R ** 2 - (0 - cxL) ** 2))
        pts.append((xL, y))
    pts += [(W_ - x, y) for x, y in reversed(pts)]
    top = min(y for _, y in pts)
    pts = [(x, (y - top) * rise / max(1, rise - top)) for x, y in pts]
    d.polygon(pts + [(W_, rise), (W_, H_), (0, H_), (0, rise)], fill=255)
    return m.resize((w, h), Image.LANCZOS)


def scrim(img, box, strength=200, up=True):
    """A soft dark fade over the bottom (or top) of a box, so ivory text reads over a photo."""
    x0, y0, x1, y1 = [round(v) for v in box]
    h = y1 - y0
    g = Image.new('L', (1, h))
    for j in range(h):
        t = j / max(1, h - 1)
        g.putpixel((0, j), round(strength * ((t if up else 1 - t) ** 1.6)))
    g = g.resize((x1 - x0, h))
    img.paste(Image.new('RGB', (x1 - x0, h), (26, 6, 10)), (x0, y0), g)


def text_c(d, xy, text, f, fill, anchor='ms'):
    d.text((round(xy[0]), round(xy[1])), text, font=f, fill=fill, anchor=anchor)


def peg(img, cx, cy, s):
    make.peg(img, cx, cy, s)


def rope(img, pts, w):
    make.rope(img, pts, w)


def sag(x0, x1, y, n, dip):
    """n evenly spaced points along a cord from x0 to x1 dipping by `dip` in the middle."""
    return [(x0 + (x1 - x0) * i / (n - 1), y + dip * math.sin(math.pi * i / (n - 1))) for i in range(n)]


def stat(d, cx, y, big, small, u):
    f, sf = garamond(78 * u, 700), arimo_bold(15 * u)
    text_c(d, (cx, y), big, f, GOLD)
    s = small.upper(); sw = spaced(d, s, sf, 4 * u)
    draw_spaced(d, cx - sw / 2, y + 20 * u, s, sf, 4 * u, CREAM)


# ---------------------------------------------------------------- designs: close darshan

def c1_calendar(m):
    """A calendar of darshan: every day's close up in its square, the day's number in the corner."""
    img = canvas(PT); w, h = PT; u = w / 1080; d = ImageDraw.Draw(img)
    y = title(img, m.name, 46 * u, 112 * u, "A month of darshan", 30 * u)
    first = calendar.weekday(m.year, m.month, 1)                      # Monday 0; the grid starts on Sunday
    start = (first + 1) % 7
    rows = math.ceil((start + m.days) / 7)
    M, gap = 44 * u, 10 * u
    cell = (w - 2 * M - 6 * gap) / 7
    hf = arimo_bold(15 * u)
    top = y + 34 * u
    for i, wd in enumerate(['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']):
        sw = spaced(d, wd, hf, 3 * u)
        draw_spaced(d, M + i * (cell + gap) + (cell - sw) / 2, top - 30 * u, wd, hf, 3 * u, CREAM)
    nf = garamond(30 * u, 700)
    ch = min(cell * 1.4, (h - top - 110 * u) / rows - gap)
    for day in range(1, m.days + 1):
        k = start + day - 1; r, c = divmod(k, 7)
        x0, y0 = M + c * (cell + gap), top + r * (ch + gap)
        if day in m.close:
            ph = shot(m.close[day], cell, ch, 'close')
            paste_round(img, ph, (x0, y0), 10 * u)
            scrim(img, (x0, y0, x0 + cell * .5, y0 + cell * .32), 150, up=False)
            ImageDraw.Draw(img).text((x0 + 12 * u, y0 + 6 * u), str(day), font=nf, fill=(255, 240, 210))
        else:
            ImageDraw.Draw(img).rounded_rectangle((x0, y0, x0 + cell, y0 + ch), 10 * u, fill=(52, 13, 21))
            ImageDraw.Draw(img).text((x0 + 12 * u, y0 + 6 * u), str(day), font=nf, fill=(150, 96, 84))
    foot(img)
    return img


def c2_medallions(m):
    """Round medallions of Bapa's face, one per day, in rows, the date under each."""
    img = canvas(SQ); w, h = SQ; u = w / 1080; d = ImageDraw.Draw(img)
    y = title(img, m.name, 40 * u, 104 * u, "Darshan day by day", 28 * u)
    days = sorted(m.close)
    cols = 6 if len(days) > 20 else 5
    rows = math.ceil(len(days) / cols)
    M = 60 * u
    cw = (w - 2 * M) / cols
    avail = h - y - 110 * u
    ch = avail / rows
    dia = min(cw * .84, ch - 40 * u)
    df = garamond(24 * u, 600)
    for n, day in enumerate(days):
        r, c = divmod(n, cols)
        in_row = min(cols, len(days) - r * cols)
        x_off = (cols - in_row) * cw / 2
        cx = M + x_off + c * cw + cw / 2; cy = y + 20 * u + r * ch + dia / 2
        ph = shot(m.close[day], dia, dia, 'close')
        ring = dia * .045
        shadow(img, (cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), 0, 10 * u, 170, (0, 6 * u), ellipse=True)
        ImageDraw.Draw(img).ellipse((cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), fill=IVORY_TOP)
        img.paste(ph, (round(cx - dia / 2), round(cy - dia / 2)), mask_circle(ph))
        text_c(ImageDraw.Draw(img), (cx, cy + dia / 2 + ring + 30 * u), f'{day_word(m, day)} {day}', df, CREAM)
    foot(img)
    return img


def c3_hero_strip(m):
    """One large darshan of the month, then a strip of the other days' faces underneath."""
    img = canvas(PT); w, h = PT; u = w / 1080; d = ImageDraw.Draw(img)
    M = 56 * u
    hero = m.hero((w - 2 * M) / (640 * u))
    y = title(img, m.name, 34 * u, 104 * u, "In Bapa's Diary", 28 * u)
    hw, hh = w - 2 * M, 640 * u
    ph = shot(hero, hw, hh, 'close')
    paste_round(img, ph, (M, y + 10 * u), 14 * u)
    hd = int(hero['d'][8:10])
    scrim(img, (M, y + 10 * u + hh * .7, M + hw, y + 10 * u + hh), 190)
    text_c(ImageDraw.Draw(img), (M + hw / 2, y + 10 * u + hh - 26 * u), f'{day_word(m, hd, False)} {date_label(m, hd)}', garamond(34 * u, 600), (255, 240, 214))
    rest = [x for x in sorted(m.close.values(), key=lambda x: x['d']) if x['i'] != hero['i']]
    cols = 8
    rows = math.ceil(len(rest) / cols)
    top = y + hh + 40 * u
    gap = 10 * u
    cell = (w - 2 * M - (cols - 1) * gap) / cols
    room = h - top - 90 * u
    cell_h = min(cell * 1.25, room / max(1, rows) - 34 * u)
    df = garamond(20 * u, 600)
    for n, x in enumerate(rest):
        r, c = divmod(n, cols)
        x0, y0 = M + c * (cell + gap), top + r * (cell_h + 34 * u + gap)
        paste_round(img, shot(x, cell, cell_h, 'close'), (x0, y0), 8 * u)
        text_c(ImageDraw.Draw(img), (x0 + cell / 2, y0 + cell_h + 26 * u), f'{int(x["d"][8:10])} Jan' if m.month == 1 else str(int(x['d'][8:10])), df, CREAM)
    foot(img)
    return img


def c4_polaroids(m):
    """The diary's ivory polaroids, nine close darshans scattered and pegged, the date in each band."""
    img = canvas(SQ); w, h = SQ; u = w / 1080
    y = title(img, m.name, 36 * u, 108 * u, "Darshan in Bapa's Diary", 28 * u)
    picks = sorted(m.best_close[:9], key=lambda x: x['d'])
    rnd = random.Random(7)
    cols, rows = 3, 3
    M = 60 * u
    cw = (w - 2 * M) / cols; ch = (h - y - 110 * u) / rows
    pw = min(cw * .78, (ch - 60 * u) / 1.22)
    for n, x in enumerate(picks):
        r, c = divmod(n, cols)
        day = int(x['d'][8:10])
        card = polaroid(shot(x, pw, pw * 1.05, 'close'), round(pw * .05), round(pw * .2), rnd.uniform(-3, 3), f'{day_word(m, day)} {day}', label_size=pw * .1)
        cx, cy = M + c * cw + cw / 2, y + 20 * u + r * ch + ch / 2
        drop_card(img, card, cx, cy)
        peg(img, cx, cy - card.height / 2 + 14 * u, 1.1 * u / make.SCALE * 2)
    foot(img)
    return img


def c5_arches(m):
    """Mandir arch windows, each framing a close darshan."""
    img = canvas(PT); w, h = PT; u = w / 1080; d = ImageDraw.Draw(img)
    y = title(img, m.name, 40 * u, 108 * u, "Darshan through the month", 28 * u)
    picks = sorted(m.best_close[:12], key=lambda x: x['d'])
    cols = 4; rows = math.ceil(len(picks) / cols)
    M, gap = 56 * u, 22 * u
    aw = (w - 2 * M - (cols - 1) * gap) / cols
    room = h - y - 120 * u
    ah = min(aw * 1.55, room / rows - 46 * u)
    df = garamond(24 * u, 600)
    for n, x in enumerate(picks):
        r, c = divmod(n, cols)
        x0, y0 = M + c * (aw + gap), y + 16 * u + r * (ah + 46 * u)
        ph = shot(x, aw, ah, 'close')
        mk = mask_arch(round(aw), round(ah))
        sh = mk.filter(ImageFilter.GaussianBlur(10 * u)).point(lambda v: v * 160 // 255)
        img.paste(Image.new('RGB', mk.size), (round(x0), round(y0 + 8 * u)), sh)
        border = mask_arch(round(aw + 12 * u), round(ah + 12 * u))
        img.paste(ivory(aw + 12 * u, ah + 12 * u), (round(x0 - 6 * u), round(y0 - 6 * u)), border)
        img.paste(ph, (round(x0), round(y0)), mk)
        day = int(x['d'][8:10])
        text_c(ImageDraw.Draw(img), (x0 + aw / 2, y0 + ah + 36 * u), f'{day_word(m, day)} {day}', df, CREAM)
    foot(img)
    return img


def c6_timeline(m):
    """The diary's wide shape: the month as a gold line from the 1st to the last day, a face above or below each day."""
    img = canvas(LS); w, h = LS; u = h / 1290 * 1.0
    d = ImageDraw.Draw(img)
    title(img, m.name, 26 * u, 100 * u, "Darshan day by day", 26 * u)
    days = sorted(m.close)
    M = 110 * u
    mid = h * .58
    x_of = lambda day: M + (w - 2 * M) * (day - 1) / (m.days - 1)
    d.line((M - 20 * u, mid, w - M + 20 * u, mid), fill=GOLD_SOFT, width=round(4 * u))
    for day in range(1, m.days + 1):
        make.diamond(d, x_of(day), mid, (9 if day in m.close else 5) * u, GOLD if day in m.close else (150, 100, 70))
    dia = min(1.9 * (w - 2 * M) / m.days, 250 * u)
    nf = garamond(30 * u, 700)
    for n, day in enumerate(days):
        cx = x_of(day); up = n % 2 == 0
        cy = mid - (dia / 2 + 70 * u) if up else mid + (dia / 2 + 70 * u)
        ImageDraw.Draw(img).line((cx, mid, cx, cy + (dia / 2 if up else -dia / 2)), fill=GOLD_SOFT, width=round(2 * u))
        ph = shot(m.close[day], dia, dia, 'close')
        ring = dia * .05
        shadow(img, (cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), 0, 10 * u, 170, (0, 6 * u), ellipse=True)
        ImageDraw.Draw(img).ellipse((cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), fill=IVORY_TOP)
        img.paste(ph, (round(cx - dia / 2), round(cy - dia / 2)), mask_circle(ph))
        ty = cy - dia / 2 - ring - 14 * u if up else cy + dia / 2 + ring + 38 * u
        text_c(ImageDraw.Draw(img), (cx, ty), str(day), nf, GOLD)
    foot(img, 24 * u)
    return img


# ---------------------------------------------------------------- designs: activities

def a1_magazine(m):
    """A feature page: the month's most special moment large, three more beneath, each with its date and caption."""
    img = canvas(PT); w, h = PT; u = w / 1080; d = ImageDraw.Draw(img)
    y = title(img, m.name, 36 * u, 108 * u, "Highlights from Bapa's Diary", 28 * u)
    hl = m.highlights
    M = 56 * u
    big = hl[0]
    bw, bh = w - 2 * M, 500 * u
    paste_round(img, shot(big, bw, bh, 'frame'), (M, y + 6 * u), 14 * u)
    scrim(img, (M, y + 6 * u + bh * .55, M + bw, y + 6 * u + bh), 215)
    dd = ImageDraw.Draw(img)
    day = int(big['d'][8:10])
    bf = garamond(44 * u, 600)
    lines = short_caption(dd, big, bf, bw - 68 * u)
    base = y + 6 * u + bh - 36 * u - (len(lines) - 1) * 50 * u   # the first caption line; the date sits above it
    draw_spaced(dd, M + 34 * u, base - 74 * u, date_label(m, day).upper(), arimo_bold(17 * u), 4 * u, GOLD)
    for i, line in enumerate(lines):
        dd.text((M + 34 * u, base + i * 50 * u), line, font=bf, fill=(255, 244, 222), anchor='ls')
    top = y + bh + 40 * u
    gap = 26 * u
    tw = (w - 2 * M - 2 * gap) / 3; th = h - top - 110 * u - 130 * u
    cf = garamond(25 * u, 600)
    for n, x in enumerate(hl[1:4]):
        x0, y0 = M + n * (tw + gap), top
        paste_round(img, shot(x, tw, th, 'frame'), (x0, y0), 12 * u)
        dd = ImageDraw.Draw(img); day = int(x['d'][8:10])
        draw_spaced(dd, x0, y0 + th + 22 * u, date_label(m, day).upper(), arimo_bold(14 * u), 3 * u, GOLD)
        for i, line in enumerate(short_caption(dd, x, cf, tw, 3)):
            dd.text((x0, y0 + th + 64 * u + i * 30 * u), line, font=cf, fill=CREAM, anchor='ls')
    foot(img)
    return img


def a2_cords(m):
    """The diary's own look: ivory polaroids pegged on two curved cords, eight activities with date and caption."""
    img = canvas(LS); w, h = LS; u = h / 1290
    title(img, m.name, 18 * u, 96 * u, "Highlights in Bapa's Diary", 26 * u)
    picks = sorted(m.highlights[:10], key=lambda x: x['d'])
    rows = [picks[:5], picks[5:10]]
    M = 90 * u
    pw = (w - 2 * M) / 5 * .8
    ph = pw / 1.33
    rnd = random.Random(3)
    for r, row in enumerate(rows):
        if not row:
            continue
        cy = 330 * u + r * 470 * u
        pts = sag(M - 40 * u, w - M + 40 * u, cy, 60, 50 * u)
        rope(img, pts, round(6 * u))
        for n, x in enumerate(row):
            cx = M + (w - 2 * M) * (n + .5) / len(row)
            dip = cy + 50 * u * math.sin(math.pi * (cx - M + 40 * u) / (w - 2 * M + 80 * u))
            day = int(x['d'][8:10])
            card = polaroid(shot(x, pw, ph, 'frame'), round(pw * .045), round(pw * .3), rnd.uniform(-1.6, 1.6),
                            date_label(m, day), caption(x), label_size=pw * .085)
            drop_card(img, card, cx, dip + card.height / 2 - 14 * u)
            peg(img, cx, dip, 1.0)
    foot(img, 24 * u)
    return img


def a3_calendar(m):
    """A calendar of moments: each day's activity in its square, the day's number and a few words."""
    img = canvas(PT); w, h = PT; u = w / 1080
    y = title(img, m.name, 46 * u, 112 * u, "A month in Bapa's Diary", 30 * u)
    first = calendar.weekday(m.year, m.month, 1); start = (first + 1) % 7
    rows = math.ceil((start + m.days) / 7)
    M, gap = 40 * u, 8 * u
    cell = (w - 2 * M - 6 * gap) / 7
    top = y + 34 * u
    d = ImageDraw.Draw(img); hf = arimo_bold(15 * u)
    for i, wd in enumerate(['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']):
        sw = spaced(d, wd, hf, 3 * u)
        draw_spaced(d, M + i * (cell + gap) + (cell - sw) / 2, top - 30 * u, wd, hf, 3 * u, CREAM)
    nf, cf = garamond(26 * u, 700), garamond(15 * u, 600)
    ch = min(cell * 1.5, (h - top - 110 * u) / rows - gap)
    for day in range(1, m.days + 1):
        k = start + day - 1; r, c = divmod(k, 7)
        x0, y0 = M + c * (cell + gap), top + r * (ch + gap)
        x = m.act.get(day) or m.close.get(day)
        if x:
            card = ivory(cell, ch); img.paste(card, (round(x0), round(y0)))
            pad = 5 * u
            img.paste(shot(x, cell - 2 * pad, ch - 52 * u, 'frame'), (round(x0 + pad), round(y0 + pad)))
            dd = ImageDraw.Draw(img)
            dd.text((x0 + 10 * u, y0 + 4 * u), str(day), font=nf, fill=(255, 244, 222), stroke_width=round(2 * u), stroke_fill=(40, 10, 14))
            lines = wrap(dd, caption(x), cf, cell - 12 * u, 2)
            for i, line in enumerate(lines):
                dd.text((x0 + cell / 2, y0 + ch - 30 * u + i * 18 * u), line, font=cf, fill=MAROON, anchor='ms')
        else:
            ImageDraw.Draw(img).rectangle((x0, y0, x0 + cell, y0 + ch), fill=(52, 13, 21))
            ImageDraw.Draw(img).text((x0 + 10 * u, y0 + 4 * u), str(day), font=nf, fill=(150, 96, 84))
    foot(img)
    return img


def a4_journal(m):
    """A diary page: the month's moments listed by date on the left, three photos stacked on the right."""
    img = canvas(PT); w, h = PT; u = w / 1080
    y = title(img, m.name, 40 * u, 104 * u, "From Bapa's Diary", 28 * u, x=60 * u, anchor='l')
    M = 60 * u
    split = w * .5
    hl = sorted(m.highlights[:12], key=lambda x: x['d'])
    d = ImageDraw.Draw(img)
    nf, cf = garamond(40 * u, 700), garamond(24 * u, 500)
    yy = y + 30 * u
    step = (h - yy - 120 * u) / len(hl)
    for x in hl:
        day = int(x['d'][8:10])
        d.text((M + 52 * u, yy + 34 * u), str(day), font=nf, fill=GOLD, anchor='rs')
        draw_spaced(d, M + 70 * u, yy + 2 * u, day_word(m, day).upper(), arimo_bold(12 * u), 3 * u, GOLD_SOFT)
        for i, line in enumerate(wrap(d, caption(x), cf, split - M - 90 * u, 2)):
            d.text((M + 70 * u, yy + 38 * u + i * 28 * u), line, font=cf, fill=CREAM, anchor='ls')
        yy += step
    side = sorted(m.highlights[:3], key=lambda x: x['d'])
    pw = w - split - M
    gap = 30 * u
    ph = (h - y - 130 * u - 2 * gap) / 3
    for n, x in enumerate(side):
        y0 = y + 10 * u + n * (ph + gap)
        paste_round(img, shot(x, pw, ph, 'frame'), (split, y0), 12 * u)
        day = int(x['d'][8:10])
        dd = ImageDraw.Draw(img)
        dd.rounded_rectangle((split + 16 * u, y0 + 16 * u, split + 120 * u, y0 + 60 * u), 8 * u, fill=(40, 10, 14))
        text_c(dd, (split + 68 * u, y0 + 48 * u), f'{day} {calendar.month_abbr[m.month]}', garamond(24 * u, 700), GOLD)
    foot(img)
    return img


def a5_grid(m):
    """Six moments as equal tiles, the date large in gold and the caption on a soft band."""
    img = canvas(PT); w, h = PT; u = w / 1080
    y = title(img, m.name, 36 * u, 108 * u, "Six moments in Bapa's Diary", 28 * u)
    picks = sorted(m.highlights[:6], key=lambda x: x['d'])
    M, gap = 48 * u, 20 * u
    tw = (w - 2 * M - gap) / 2
    th = (h - y - 110 * u - 2 * gap) / 3
    for n, x in enumerate(picks):
        r, c = divmod(n, 2)
        x0, y0 = M + c * (tw + gap), y + 10 * u + r * (th + gap)
        dd = ImageDraw.Draw(img); day = int(x['d'][8:10])
        cf, nf = garamond(26 * u, 600), garamond(64 * u, 700)
        lines = wrap(dd, caption(x), cf, tw - 48 * u, 2)
        lift = (len(lines) - 1) * 32 * u   # a two line caption sits higher so both lines show
        img.paste(shot(x, tw, th, 'frame'), (round(x0), round(y0)))
        scrim(img, (x0, y0 + th * .45, x0 + tw, y0 + th), 230)
        dd = ImageDraw.Draw(img)
        dd.text((x0 + 24 * u, y0 + th - 66 * u - lift), str(day), font=nf, fill=GOLD, anchor='ls')
        lx = x0 + 24 * u + dd.textlength(str(day), font=nf) + 14 * u
        draw_spaced(dd, lx, y0 + th - 108 * u - lift, calendar.month_name[m.month].upper(), arimo_bold(13 * u), 3 * u, CREAM)
        for i, line in enumerate(lines):
            dd.text((x0 + 24 * u, y0 + th - 26 * u - lift + i * 32 * u), line, font=cf, fill=(255, 244, 222), anchor='ls')
    foot(img)
    return img


def a6_story(m):
    """A phone story: a gold line down the middle, moments on alternate sides with their date and caption."""
    img = canvas(ST); w, h = ST; u = w / 1080
    y = title(img, m.name, 60 * u, 120 * u, "Bapa's Diary", 32 * u)
    picks = sorted(m.highlights[:7], key=lambda x: x['d'])
    d = ImageDraw.Draw(img)
    cx = w / 2
    top, bottom = y + 40 * u, h - 130 * u
    d.line((cx, top, cx, bottom), fill=GOLD_SOFT, width=round(3 * u))
    step = (bottom - top) / len(picks)
    pw = w * .42; ph = min(pw / 1.4, step - 40 * u)
    pw = ph * 1.4
    for n, x in enumerate(picks):
        cy = top + step * (n + .5)
        left = n % 2 == 0
        x0 = cx - 34 * u - pw if left else cx + 34 * u
        paste_round(img, shot(x, pw, ph, 'frame'), (x0, cy - ph / 2), 12 * u)
        dd = ImageDraw.Draw(img)
        make.diamond(dd, cx, cy, 11 * u, GOLD)
        tx = cx + 40 * u if left else cx - 40 * u
        anchor = 'ls' if left else 'rs'
        day = int(x['d'][8:10])
        dd.text((tx, cy - 30 * u), f'{day} {calendar.month_abbr[m.month]}', font=garamond(48 * u, 700), fill=GOLD, anchor=anchor)
        cf = garamond(27 * u, 500)
        for i, line in enumerate(wrap(dd, caption(x), cf, w / 2 - 80 * u, 3)):
            dd.text((tx, cy + 14 * u + i * 32 * u), line, font=cf, fill=CREAM, anchor=anchor)
    foot(img, 26 * u)
    return img


# ---------------------------------------------------------------- designs: mixed

def m1_cover_calendar(m):
    """A cover: the month's best darshan across the top with the title over it, the calendar of mixed days below."""
    img = canvas(PT); w, h = PT; u = w / 1080
    hh = 700 * u
    hero = m.hero(w / hh)
    img.paste(shot(hero, w, hh, 'close'), (0, 0))
    scrim(img, (0, hh * .45, w, hh), 255)
    g = Image.new('L', (1, round(160 * u)))
    for j in range(g.height):
        g.putpixel((0, j), round(255 * (1 - j / g.height) ** 1.5 * .7))
    img.paste(Image.new('RGB', (w, g.height), (26, 6, 10)), (0, 0), g.resize((w, g.height)))
    title(img, m.name, hh - 230 * u, 120 * u, "In Bapa's Diary", 30 * u)
    first = calendar.weekday(m.year, m.month, 1); start = (first + 1) % 7
    M, gap = 60 * u, 8 * u
    cell = (w - 2 * M - 6 * gap) / 7
    top = hh + 30 * u
    nf = garamond(22 * u, 700)
    rows = math.ceil((start + m.days) / 7)
    cell_h = min(cell, (h - top - 110 * u) / rows - gap)
    for day in range(1, m.days + 1):
        k = start + day - 1; r, c = divmod(k, 7)
        x0, y0 = M + c * (cell + gap), top + r * (cell_h + gap)
        x = m.mixed.get(day)
        if x:
            paste_round(img, shot(x, cell, cell_h, 'close' if x['kind'] == 'close' else 'frame'), (x0, y0), 8 * u, shade=False)
            ImageDraw.Draw(img).text((x0 + 8 * u, y0 + 3 * u), str(day), font=nf, fill=(255, 244, 222), stroke_width=round(2 * u), stroke_fill=(40, 10, 14))
        else:
            ImageDraw.Draw(img).rounded_rectangle((x0, y0, x0 + cell, y0 + cell_h), 8 * u, fill=(52, 13, 21))
            ImageDraw.Draw(img).text((x0 + 8 * u, y0 + 3 * u), str(day), font=nf, fill=(150, 96, 84))
    foot(img)
    return img


def m2_bento(m):
    """Tiles of different sizes: a tall darshan, a wide moment, smaller ones around them."""
    img = canvas(SQ); w, h = SQ; u = w / 1080
    y = title(img, m.name, 34 * u, 100 * u, "In Bapa's Diary", 26 * u)
    M, g = 44 * u, 16 * u
    W_, H_ = w - 2 * M, h - y - 100 * u
    c1 = W_ * .38
    closes = m.best_close
    acts = m.highlights
    tiles = [(M, y, c1, H_ * .62, closes[0], 'close'),
             (M, y + H_ * .62 + g, c1, H_ * .38 - g, acts[3] if len(acts) > 3 else closes[3], 'frame'),
             (M + c1 + g, y, W_ - c1 - g, H_ * .44, acts[0], 'frame'),
             (M + c1 + g, y + H_ * .44 + g, (W_ - c1 - 2 * g) / 2, H_ * .28 - g, closes[1], 'close'),
             (M + c1 + g + (W_ - c1 - 2 * g) / 2 + g, y + H_ * .44 + g, (W_ - c1 - 2 * g) / 2, H_ * .28 - g, acts[1], 'frame'),
             (M + c1 + g, y + H_ * .72 + g, (W_ - c1 - 2 * g) / 2, H_ * .28 - g, acts[2], 'frame'),
             (M + c1 + g + (W_ - c1 - 2 * g) / 2 + g, y + H_ * .72 + g, (W_ - c1 - 2 * g) / 2, H_ * .28 - g, closes[2], 'close')]
    for x0, y0, tw, th, x, mode in tiles:
        paste_round(img, shot(x, tw, th, mode), (x0, y0), 14 * u)
        day = int(x['d'][8:10])
        dd = ImageDraw.Draw(img)
        lab = f'{day} {calendar.month_abbr[m.month]}'
        f = garamond(22 * u, 700); lw = dd.textlength(lab, font=f)
        dd.rounded_rectangle((x0 + 14 * u, y0 + th - 50 * u, x0 + 34 * u + lw, y0 + th - 14 * u), 8 * u, fill=(36, 9, 13))
        dd.text((x0 + 24 * u, y0 + th - 22 * u), lab, font=f, fill=GOLD, anchor='ls')
    foot(img)
    return img


def m3_numbers(m):
    """The month in numbers beside a darshan, four moments along the bottom."""
    img = canvas(SQ); w, h = SQ; u = w / 1080
    M = 56 * u
    hw = w * .46
    hero = m.hero(hw / (600 * u))
    hh = 600 * u
    paste_round(img, shot(hero, hw, hh, 'close'), (M, 56 * u), 14 * u)
    d = ImageDraw.Draw(img)
    rx = M + hw + 50 * u
    gold_text(img, (rx, 46 * u), calendar.month_name[m.month], garamond(96 * u, 700))
    gold_text(img, (rx, 150 * u), str(m.year), garamond(96 * u, 700))
    draw_spaced(d, rx, 282 * u, "IN BAPA'S DIARY", garamond(24 * u, 600), 6 * u, CREAM)
    specials = sum(1 for x in m.highlights if x['special'])
    stats = [(str(len(m.by)), 'days of darshan'), (str(m.count), 'photos'), (str(len(m.places)), 'city' if len(m.places) == 1 else 'cities')]
    sy = 400 * u
    for i, (big, small) in enumerate(stats):
        d.text((rx, sy + i * 92 * u), big, font=garamond(66 * u, 700), fill=GOLD, anchor='ls')
        bw = d.textlength(big, font=garamond(66 * u, 700))
        draw_spaced(d, rx + bw + 18 * u, sy + i * 92 * u - 10 * u, small.upper(), arimo_bold(15 * u), 3 * u, CREAM)
    d.text((rx, sy + 3 * 92 * u - 20 * u), ', '.join(m.places[:3]), font=garamond(28 * u, 500), fill=GOLD_SOFT, anchor='ls')
    picks = sorted(m.highlights[:4], key=lambda x: x['d'])
    top = 56 * u + hh + 50 * u
    gap = 20 * u
    tw = (w - 2 * M - 3 * gap) / 4; th = tw * .8
    cf = garamond(20 * u, 600)
    for n, x in enumerate(picks):
        x0 = M + n * (tw + gap)
        paste_round(img, shot(x, tw, th, 'frame'), (x0, top), 10 * u)
        dd = ImageDraw.Draw(img); day = int(x['d'][8:10])
        draw_spaced(dd, x0, top + th + 30 * u, date_label(m, day).upper(), arimo_bold(12 * u), 3 * u, GOLD)
        for i, line in enumerate(wrap(dd, caption(x), cf, tw, 3)):
            dd.text((x0, top + th + 60 * u + i * 25 * u), line, font=cf, fill=CREAM, anchor='ls')
    foot(img)
    return img


def m4_diary(m):
    """The daily picture's look for a month: ivory cards on three cords, one day each, close ups and moments mixed."""
    img = canvas(LS); w, h = LS; u = h / 1290
    title(img, m.name, 14 * u, 92 * u, "In Bapa's Diary", 24 * u)
    days = sorted(m.mixed)
    rows = 3
    per = math.ceil(len(days) / rows)
    M = 70 * u
    row_h = (h - 190 * u - 60 * u) / rows
    pw = min((w - 2 * M) / per * .84, (row_h - 30 * u) / (.82 + .05 + .36))
    ph = pw * .82
    rnd = random.Random(11)
    for r in range(rows):
        row = days[r * per:(r + 1) * per]
        if not row:
            continue
        cy = 190 * u + r * row_h
        rope(img, sag(M - 30 * u, w - M + 30 * u, cy, 60, 26 * u), round(5 * u))
        for n, day in enumerate(row):
            x = m.mixed[day]
            cx = M + (w - 2 * M) * (n + .5) / per
            dip = cy + 26 * u * math.sin(math.pi * (cx - M + 30 * u) / (w - 2 * M + 60 * u))
            card = polaroid(shot(x, pw, ph, 'close' if x['kind'] == 'close' else 'frame'), round(pw * .05), round(pw * .36),
                            rnd.uniform(-2, 2), f'{day_word(m, day)} {day}', caption(x) if x['kind'] == 'act' else None, label_size=pw * .11)
            drop_card(img, card, cx, dip + card.height / 2 - 10 * u)
            peg(img, cx, dip, .8)
    foot(img, 22 * u)
    return img


def m5_medallion_ring(m):
    """A large round darshan in the middle, the month's moments around it."""
    img = canvas(SQ); w, h = SQ; u = w / 1080
    y = title(img, m.name, 30 * u, 96 * u, "In Bapa's Diary", 26 * u)
    tw, th = 236 * u, 168 * u
    ch_ = th + 8 * u + 44 * u
    top, bottom = y + 10 * u, h - 90 * u
    cx, cy = w / 2, (top + bottom) / 2
    acts = sorted(m.highlights[:6], key=lambda x: x['d'])
    Ry = (bottom - top) / 2 - ch_ / 2 - 6 * u
    Rx = w / 2 - 60 * u - (tw + 16 * u) / 2
    R = Ry
    cf = garamond(18 * u, 600)
    for n, x in enumerate(acts):
        a = -math.pi / 2 + 2 * math.pi * (n + .5) / len(acts)
        px_, py_ = cx + Rx * math.cos(a), cy + Ry * math.sin(a)
        day = int(x['d'][8:10])
        card = polaroid(shot(x, tw, th, 'frame'), round(8 * u), round(44 * u), 0, f'{day} {calendar.month_abbr[m.month]}', label_size=24 * u)
        drop_card(img, card, px_, py_)
    dia = R * .95
    hero = m.hero(1)
    ring = dia * .04
    shadow(img, (cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), 0, 18 * u, 200, (0, 10 * u), ellipse=True)
    ImageDraw.Draw(img).ellipse((cx - dia / 2 - ring, cy - dia / 2 - ring, cx + dia / 2 + ring, cy + dia / 2 + ring), fill=IVORY_TOP)
    ph = shot(hero, dia, dia, 'close')
    img.paste(ph, (round(cx - dia / 2), round(cy - dia / 2)), mask_circle(ph))
    foot(img)
    return img


def m6_weeks(m):
    """Week by week: each row a week, a close darshan first, then that week's moments."""
    img = canvas(PT); w, h = PT; u = w / 1080
    y = title(img, m.name, 34 * u, 104 * u, "Week by week in Bapa's Diary", 26 * u)
    weeks = []
    for d0 in range(1, m.days + 1, 7):
        rng = list(range(d0, min(m.days, d0 + 6) + 1))
        days = [d for d in rng if d in m.by]
        if days:
            weeks.append((rng, days))
    M, gap = 48 * u, 12 * u
    row_h = (h - y - 110 * u) / len(weeks)
    ph = row_h - 62 * u
    for r, (rng, days) in enumerate(weeks):
        y0 = y + r * row_h
        d = ImageDraw.Draw(img)
        lab = f'{rng[0]} to {rng[-1]} {calendar.month_name[m.month]}'.upper()
        draw_spaced(d, M, y0 + 22 * u, lab, arimo_bold(15 * u), 4 * u, GOLD)
        best_c = max((m.close[d] for d in days), key=lambda x: x['s_close'])
        acts = sorted((m.act[d] for d in days if d in m.act and m.act[d]['i'] != best_c['i']), key=lambda x: -x['s_act'])[:2]
        x0 = M
        cw = ph * .8
        paste_round(img, shot(best_c, cw, ph, 'close'), (x0, y0 + 40 * u), 10 * u)
        x0 += cw + gap
        aw = (w - M - x0 - gap * (max(1, len(acts)) - 1)) / max(1, len(acts))
        for x in acts:
            paste_round(img, shot(x, aw, ph, 'frame'), (x0, y0 + 40 * u), 10 * u)
            scrim(img, (x0, y0 + 40 * u + ph * .6, x0 + aw, y0 + 40 * u + ph), 210)
            dd = ImageDraw.Draw(img); day = int(x['d'][8:10])
            lines = wrap(dd, f'{day}  ' + caption(x), garamond(22 * u, 600), aw - 30 * u, 2)
            for i, line in enumerate(lines):
                dd.text((x0 + 16 * u, y0 + 40 * u + ph - 18 * u - (len(lines) - 1 - i) * 26 * u), line, font=garamond(22 * u, 600), fill=(255, 244, 222), anchor='ls')
            x0 += aw + gap
    foot(img)
    return img


DESIGNS = [
    ('close', 'c1-calendar', c1_calendar), ('close', 'c2-medallions', c2_medallions), ('close', 'c3-hero-strip', c3_hero_strip),
    ('close', 'c4-polaroids', c4_polaroids), ('close', 'c5-arches', c5_arches), ('close', 'c6-timeline', c6_timeline),
    ('activities', 'a1-magazine', a1_magazine), ('activities', 'a2-cords', a2_cords), ('activities', 'a3-calendar', a3_calendar),
    ('activities', 'a4-journal', a4_journal), ('activities', 'a5-six-tiles', a5_grid), ('activities', 'a6-story', a6_story),
    ('mixed', 'm1-cover-calendar', m1_cover_calendar), ('mixed', 'm2-tiles', m2_bento), ('mixed', 'm3-in-numbers', m3_numbers),
    ('mixed', 'm4-diary-cords', m4_diary), ('mixed', 'm5-medallion', m5_medallion_ring), ('mixed', 'm6-weeks', m6_weeks),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', default='2012-01')
    ap.add_argument('--out', default=None)
    ap.add_argument('--cache', default=os.path.join(HERE, '.cache', 'month'))
    ap.add_argument('--fake', action='store_true', help='stand in photos, no downloads')
    ap.add_argument('--only', default='', help='comma separated design names')
    a = ap.parse_args()
    year, month = map(int, a.month.split('-'))
    out = a.out or os.path.join(HERE, 'preview', 'month', a.month)
    os.makedirs(out, exist_ok=True)
    items = month_items(year, month)
    print(f'{len(items)} photos listed for {a.month}', flush=True)
    photos = fake_items(items, year, month) if a.fake else analyse(full_size(items, a.cache))
    print(f'{len(photos)} with Bapa recognised', flush=True)
    m = Month(photos, year, month)
    open(os.path.join(out, 'picks.txt'), 'w').write(m.summary() + '\n')
    print(m.summary(), flush=True)
    for group, name, fn in DESIGNS:
        if a.only and name not in a.only.split(','):
            continue
        try:
            img = fn(m)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('  could not make', name, e)
            continue
        img.convert('RGB').save(os.path.join(out, f'{name}.jpg'), quality=88, optimize=True)
        print('  made', name, img.size, flush=True)


if __name__ == '__main__':
    main()
