#!/usr/bin/env python3
"""Bapa's Diary: one darshan of Bapa from every year on today's date, hung like polaroids on gold cords.

    python make.py                     today's date in London
    python make.py --date 2026-10-12   any date (only the day and month matter)

Writes out/bapas-diary.jpg (2796 x 1290, iPhone landscape), out/date.txt and out/summary.txt.
"""
import argparse, concurrent.futures, datetime, hashlib, json, os, random, re, threading, time, urllib.request
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = 'https://darshan-screensaver.pages.dev/memories/{mmdd}.json'
W, H = 2796, 1290
MAROON_IN, MAROON_OUT = (74, 21, 32), (18, 4, 8)
GOLD, GOLD_SOFT = (255, 207, 107), (217, 164, 65)
FRAME_TOP, FRAME_BOTTOM = (224, 196, 142), (193, 160, 104)     # between antique gold and champagne
YEAR_C, PLACE_C, FRAME_LINE = (88, 18, 30), (104, 36, 36), (135, 95, 55)
CORD, PEG, PEG_EDGE = (176, 140, 80), (150, 104, 66), (92, 58, 34)
FOOTER = 'Darpan’s Smruti Project'


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.woff2'), max(8, round(size)))

fell = lambda s: font('im-fell-dw-pica-latin-400-normal', s)
arimo = lambda s: font('arimo-latin-400-normal', s)


# ---------------------------------------------------------------- photos

def fetch(url, tries=3, timeout=40):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bapas-diary)'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            err = e
            time.sleep(2 * (i + 1))
    raise err


def download_all(items, cache):
    os.makedirs(cache, exist_ok=True)

    def one(x):
        path = os.path.join(cache, hashlib.sha1(x['i'].encode()).hexdigest() + '.jpg')
        if not os.path.exists(path):
            try:
                data = fetch(x['i'])
            except Exception as e:
                print('  could not download', x['i'], e)
                return
            if len(data) < 2000:
                return
            open(path, 'wb').write(data)
        x['path'] = path

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        list(pool.map(one, items))


MODELS = os.path.join(HERE, 'models')
DETECT = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .6, .3, 5000)
RECOGNISE = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'face_recognition_sface_2021dec.onnx'), '')
BAPA = {k: np.array(v) for k, v in json.load(open(os.path.join(MODELS, 'bapa-faces.json'))).items()}
PSM_UNTIL = '2016-08-13'   # Pramukh Swami Maharaj before this date, Mahant Swami Maharaj after
SAME_PERSON = .5           # cosine similarity; strangers and murtis score below .35
FACE_LOCK = threading.Lock()   # the face models can only look at one photo at a time


def bapa_face(im, when):
    """Bapa's face in the photo as ((x, y, w, h), similarity), or (None, 0) when he can't be recognised."""
    small = im.copy(); small.thumbnail((1280, 1280))
    k = im.width / small.width
    bgr = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2BGR)
    ref = BAPA['psm' if when < PSM_UNTIL else 'msm']
    best, best_sim = None, 0
    with FACE_LOCK:
        DETECT.setInputSize((bgr.shape[1], bgr.shape[0]))
        faces = DETECT.detect(bgr)[1]
        for f in faces if faces is not None else []:
            e = RECOGNISE.feature(RECOGNISE.alignCrop(bgr, f))[0]
            sim = float(ref @ (e / np.linalg.norm(e)))
            if sim > best_sim:
                best, best_sim = tuple(float(v) * k for v in f[:4]), sim
    return (best, best_sim) if best_sim >= SAME_PERSON else (None, best_sim)


def pick_one_per_year(items, seed):
    """Per year, a photo where Bapa is recognised, favouring a close darshan, with a touch of variety.
    Years where he can't be recognised in any photo are left out, unless that would leave fewer than five;
    then they're kept and shown whole so he isn't cropped out."""
    rnd = random.Random(seed)
    best = {}
    for x in items:
        if 'path' not in x:
            continue
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        face, sim = bapa_face(im, x.get('d', str(x['y'])))
        score = (1 + min(face[3] / im.height, .35) + sim if face else 0) + rnd.uniform(0, .04)
        if x['y'] not in best or score > best[x['y']][0]:
            best[x['y']] = (score, dict(x, im=im, face=face, sim=sim))
    years = sorted(best)
    if sum(1 for y in years if best[y][1]['face']) >= 5:
        years = [y for y in years if best[y][1]['face']]
    return [best[y][1] for y in years]


def crop_to(im, face, w, h):
    """A w:h window keeping Bapa's whole head in view (face about a third of the way down).
    Without a recognised face the whole photo is shown, softened into its own colours at the edges."""
    iw, ih = im.size
    if not face:
        fill = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        fill = Image.blend(fill, Image.new('RGB', (w, h), MAROON_OUT), .3)
        whole = im.copy(); whole.thumbnail((w, h), Image.LANCZOS)
        fill.paste(whole, ((w - whole.width) // 2, (h - whole.height) // 2))
        return fill
    cw, ch = (ih * w / h, ih) if iw / ih > w / h else (iw, iw * h / w)
    fx, fy, fw, fh = face
    head = (fx - .35 * fw, fy - .75 * fh, fx + 1.35 * fw, fy + 1.4 * fh)   # top of the head down to the chin and neck
    x0, y0 = fx + fw / 2 - cw / 2, fy + fh / 2 - ch * .38
    y0 = max(y0, head[3] - ch); y0 = min(y0, head[1])                        # never slice through the head
    x0 = min(max(0, x0), iw - cw); y0 = min(max(0, y0), ih - ch)
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- drawing helpers

def background():
    small = Image.new('RGB', (64, 64)); px = small.load()
    for j in range(64):
        for i in range(64):
            d = min(1, (((i - 32) / 32 / .8) ** 2 + ((j - 64 * .4) / 32 / .9) ** 2) ** .5)
            px[i, j] = tuple(round(a + (b - a) * d) for a, b in zip(MAROON_IN, MAROON_OUT))
    img = small.resize((W, H), Image.BICUBIC)
    # warm light behind the title
    g = Image.new('L', (W // 6, H // 6), 0)
    ImageDraw.Draw(g).ellipse(((W / 2 - 520) / 6, 0, (W / 2 + 520) / 6, 660 / 6), fill=120)
    g = g.filter(ImageFilter.GaussianBlur(27)).resize((W, H), Image.BICUBIC)
    img.paste(Image.new('RGB', (W, H), (125, 62, 30)), (0, 0), g)
    # soft gold dust
    rnd = random.Random(7)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    for _ in range(45):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.choice([2, 3, 4, 5, 7, 10]); a = rnd.randint(30, 90) if r < 6 else rnd.randint(15, 40)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 210, 130, a))
    layer = layer.filter(ImageFilter.GaussianBlur(1.8)); img.paste(layer, (0, 0), layer)
    # gentle vignette
    m = Image.new('L', (78, 36), 0); p = m.load()
    for j in range(36):
        for i in range(78):
            dd = (((i - 38.5) / 39) ** 2 + ((j - 17.5) / 18) ** 2) ** .5
            p[i, j] = int(150 * max(0, dd - .72) / .6)
    img.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), m.resize((W, H), Image.BICUBIC))
    return img


def diamond(dr, cx, cy, r, fill):
    dr.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def ornament_line(dr, y, x0, x1, side, dsize):
    """Gold rule fading outwards, with a small diamond at the inner end."""
    for xp in range(int(x0), int(x1)):
        t = (xp - x0) / (x1 - x0); a = t if side == 'L' else 1 - t
        dr.line((xp, y, xp, y + 1), fill=tuple(round(m + (g - m) * a) for m, g in zip(MAROON_OUT, GOLD_SOFT)))
    diamond(dr, x1 + 12 + dsize if side == 'L' else x0 - 12 - dsize, y + 1, dsize, GOLD)


def segments(dr, text, f):
    """IM Fell only has old style figures (a short 1 and 2, a 5 that drops below the line), so a
    leading day number is set in Cinzel, whose figures stand as tall as the month's capital."""
    m = re.match(r'^(\d+)(\s.*)$', text)
    if not m:
        return [(text, f, 0)]
    num, rest = m.groups()
    ob = dr.textbbox((0, 0), 'O', font=f, anchor='ls')
    probe = font('cinzel-latin-600-normal', 100)
    nf = font('cinzel-latin-600-normal', 100 * (-ob[1]) / -dr.textbbox((0, 0), '1', font=probe, anchor='ls')[1])
    # text is drawn from the ascender line, so match baselines by the difference in ascent
    return [(num, nf, f.getmetrics()[0] - nf.getmetrics()[0]), (rest, f, 0)]


def headline(img, parts, y, shadow=True, sp=36, reach=None, dsize=9):
    """Parts (text, font, colour) on one centred line with gold rules either side."""
    dr = ImageDraw.Draw(img)
    segs = [segments(dr, t, f) for t, f, c in parts]
    ws = [sum(dr.textlength(tt, font=ff) for tt, ff, _ in s) for s in segs]
    total = sum(ws) + sp * (len(parts) - 1)
    big = max(f.size for t, f, c in parts)
    x = (W - total) / 2
    for (t, f, c), s, w in zip(parts, segs, ws):
        yy = y + (big - f.size) * .74
        if shadow and f.size == big:
            sh = Image.new('RGBA', (int(w) + 60, big * 2), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh); xx = 30
            for tt, ff, dy in s:
                sd.text((xx, 10 + dy), tt, font=ff, fill=(0, 0, 0, 200)); xx += dr.textlength(tt, font=ff)
            sh = sh.filter(ImageFilter.GaussianBlur(8)); img.paste(sh, (int(x) - 30, int(yy)), sh)
        xx = x
        for tt, ff, dy in s:
            dr.text((xx, yy + dy), tt, font=ff, fill=c); xx += dr.textlength(tt, font=ff)
        x += w + sp
    mid = y + big * .62
    l1, r0 = (W - total) / 2 - 60, (W + total) / 2 + 60
    ornament_line(dr, mid, 110 if reach is None else l1 - reach, l1, 'L', dsize)
    ornament_line(dr, mid, r0, W - 110 if reach is None else r0 + reach, 'R', dsize)


class Card:
    """Polaroid sizes; everything scales from the photo width (262 px in the approved design)."""
    def __init__(self, pw):
        s = pw / 262
        self.s, self.PW, self.PH = s, round(262 * s), round(312 * s)
        self.B, self.BB = round(15 * s), round(118 * s)
        self.CW, self.CH = self.PW + 2 * self.B, self.PH + self.B + self.BB

    def make(self, x):
        PW, PH, B, BB, CW, CH, s = self.PW, self.PH, self.B, self.BB, self.CW, self.CH, self.s
        card = Image.new('RGBA', (CW, CH)); d = ImageDraw.Draw(card)
        for j in range(CH):
            t = j / CH
            d.line((0, j, CW, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(FRAME_TOP, FRAME_BOTTOM)) + (255,))
        card.paste(crop_to(x['im'], x['face'], PW, PH), (B, B))
        cd = ImageDraw.Draw(card)
        for i in range(7):   # bevel: light top and left edge, dark bottom and right edge
            a = int(90 * (1 - i / 7))
            cd.line((i, i, CW - 1 - i, i), fill=(255, 255, 255, a)); cd.line((i, i, i, CH - 1 - i), fill=(255, 255, 255, a))
            cd.line((i, CH - 1 - i, CW - 1 - i, CH - 1 - i), fill=(0, 0, 0, a)); cd.line((CW - 1 - i, i, CW - 1 - i, CH - 1 - i), fill=(0, 0, 0, a))
        ov = Image.new('RGBA', (CW, CH), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        for i in range(6):   # photo sits slightly inset
            a = int(110 * (1 - i / 6))
            od.line((B + i, B + i, B + PW - 1 - i, B + i), fill=(0, 0, 0, a)); od.line((B + i, B + i, B + i, B + PH - 1 - i), fill=(0, 0, 0, a))
            od.line((B - 1 - i, B + PH + i, B + PW + i, B + PH + i), fill=(255, 255, 255, a // 2)); od.line((B + PW + i, B - 1 - i, B + PW + i, B + PH + i), fill=(255, 255, 255, a // 2))
        yy, xx = np.mgrid[0:PH, 0:PW]   # gloss: soft diagonal sheen across the top left of the photo
        dist = (xx + yy * 1.15) / (PW + PH * 1.15)
        sheen = Image.new('RGBA', (PW, PH), (255, 255, 255, 0))
        sheen.putalpha(Image.fromarray(np.clip(80 * (1 - dist / .55), 0, 80).astype('uint8')))
        ov.alpha_composite(sheen, (B, B)); card.alpha_composite(ov); cd = ImageDraw.Draw(card)
        cd.rectangle((B - 7, B - 7, B + PW + 6, B + PH + 6), outline=FRAME_LINE, width=2)
        # year (bold) and place (regular, letter spaced) as a centred pair in the bottom band
        yf, yt = fell(50 * s), str(x['y'])
        pl, track, size = re.sub(r'\s*\(.*?\)', '', (x.get('p') or '').split(',')[0]).strip().upper(), 3 * s, 25 * s
        while True:
            pf = arimo(size)
            pw = sum(cd.textlength(ch, font=pf) for ch in pl) + track * max(0, len(pl) - 1)
            if pw <= CW - 24 * s or size <= 16 * s:
                break
            size -= 1
        yb = cd.textbbox((0, 0), yt, font=yf, stroke_width=1); ab = cd.textbbox((0, 0), 'A', font=pf)
        yh, plh, gap = yb[3] - yb[1], (ab[3] - ab[1]) if pl else 0, 12 * s if pl else 0
        top = B + PH + (BB - B - (yh + gap + plh)) / 2
        cd.text(((CW - cd.textlength(yt, font=yf)) / 2, top - yb[1]), yt, font=yf, fill=YEAR_C, stroke_width=1, stroke_fill=YEAR_C)
        px, py = (CW - pw) / 2, top + yh + gap - ab[1]
        for ch in pl:
            cd.text((px, py), ch, font=pf, fill=PLACE_C); px += cd.textlength(ch, font=pf) + track
        return card

    def hang(self, card, angle):
        sh = Image.new('RGBA', (self.CW + 100, self.CH + 100), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((50, 58, self.CW + 50, self.CH + 58), fill=(0, 0, 0, 175))
        sh = sh.filter(ImageFilter.GaussianBlur(12)); sh.alpha_composite(card, (50, 50))
        return sh.rotate(angle, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- the picture

def compose(photos, day, seed):
    rnd = random.Random(seed)
    img = background(); dr = ImageDraw.Draw(img)
    headline(img, [(f'{day.day} {day:%B}', fell(116), GOLD), ('in Bapa’s Diary', fell(64), GOLD_SOFT)], 30)

    n = len(photos)
    rows = [photos] if n <= 5 else [photos[:(n + 1) // 2], photos[(n + 1) // 2:]]
    cols, M, min_gap = len(rows[0]), 100, 24
    cw_max = (W - 2 * M - min_gap * (cols - 1)) / cols
    card = Card(min(262, cw_max / (1 + 30 / 262)))
    gap = min(90, (W - 2 * M - cols * card.CW) / max(1, cols - 1))
    pitch = card.CH + 66
    top_space, bottom_space = 190, H - 120
    block = (len(rows) - 1) * pitch + card.CH
    first = top_space + max(0, (bottom_space - top_space - block) / 2) + 6

    for r, row in enumerate(rows):
        y_top = first + r * pitch
        sag = lambda xp: y_top - 18 + 30 * 4 * (xp / W) * (1 - xp / W)
        dr.line([(xp, sag(xp)) for xp in range(0, W + 1, 6)], fill=CORD, width=2)
        x0 = (W - (len(row) * card.CW + (len(row) - 1) * gap)) / 2 + card.CW / 2
        for c, x in enumerate(row):
            cx = x0 + c * (card.CW + gap); cy = sag(cx)
            rot = card.hang(card.make(x), rnd.uniform(-3, 3))
            img.paste(rot, (int(cx - rot.width / 2), int(cy + card.CH / 2 + 3 - rot.height / 2)), rot)
            dr.rounded_rectangle((cx - 9, cy - 18, cx + 9, cy + 24), radius=4, fill=PEG, outline=PEG_EDGE, width=2)
            dr.line((cx, cy - 15, cx, cy + 21), fill=PEG_EDGE, width=1)

    headline(img, [(FOOTER, fell(38), GOLD_SOFT)], H - 92, shadow=False, reach=240, dsize=6)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (default: today in London)')
    ap.add_argument('--data', help='use this JSON file instead of downloading the day list')
    ap.add_argument('--cache', default=os.path.join(HERE, '.cache'))
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()

    day = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(ZoneInfo('Europe/London')).date()
    mmdd = f'{day:%m-%d}'
    items = json.load(open(a.data)) if a.data else json.loads(fetch(DATA_URL.format(mmdd=mmdd)))
    collected = os.path.join(HERE, 'archive', mmdd + '.json')      # newer years found by collect.py
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have]
    print(f'{day}: {len(items)} photos across {len({x["y"] for x in items})} years')

    download_all(items, a.cache)
    photos = pick_one_per_year(items, seed=mmdd)
    if not photos:
        raise SystemExit('No photos could be downloaded for ' + mmdd)
    for x in photos:
        print(f'  {x["y"]}  {x.get("p", "")[:28]:28}  Bapa {"%.2f" % x["sim"] if x["face"] else "not found, shown whole"}  {x.get("c", "")[:60]}')

    os.makedirs(a.out, exist_ok=True)
    compose(photos, day, seed=mmdd).save(os.path.join(a.out, 'bapas-diary.jpg'), quality=92, optimize=True)
    open(os.path.join(a.out, 'date.txt'), 'w').write(f'{day}\n')
    open(os.path.join(a.out, 'summary.txt'), 'w').write(f'{len(photos)} years: ' + ', '.join(str(x['y']) for x in photos) + '\n')
    print('saved', os.path.join(a.out, 'bapas-diary.jpg'))


if __name__ == '__main__':
    main()
