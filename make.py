#!/usr/bin/env python3
"""Bapa's Diary: one darshan of Bapa from every year on today's date, hung like ivory polaroids on cords.

    python make.py                     today's date in London
    python make.py --date 2026-10-12   any date (only the day and month matter)

Writes out/bapas-diary.jpg (2796 x 1290, iPhone landscape), out/date.txt and out/summary.txt.
"""
import argparse, concurrent.futures, datetime, hashlib, json, os, random, re, threading, time, urllib.request
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = 'https://darshan-screensaver.pages.dev/memories/{mmdd}.json'
W, H = 2796, 1290
MAROON_OUT = (18, 4, 8)
GOLD, GOLD_SOFT = (255, 207, 107), (217, 164, 65)
FOOTER = 'Darpan’s Smruti Project'
GLOW = .5           # soft lamp light behind the title (0 = none)
JALI = .13          # faint carved lattice at the edges (0 = none)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.woff2'), max(8, round(size)))



# ---------------------------------------------------------------- photos

def fetch(url, tries=3, timeout=25):
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

    def one(x, timeout=25, quiet=True):
        path = os.path.join(cache, hashlib.sha1(x['i'].encode()).hexdigest() + '.jpg')
        if not os.path.exists(path):
            try:
                data = fetch(x['i'], tries=2, timeout=timeout)
            except Exception as e:
                if not quiet:
                    print('  could not download', x['i'], e)
                return
            if len(data) < 2000:
                return
            open(path, 'wb').write(data)
        x['path'] = path

    with concurrent.futures.ThreadPoolExecutor(4) as pool:   # baps.org gets slow when asked for too much at once
        list(pool.map(one, items))
    have_years = {x['y'] for x in items if 'path' in x}
    missed = sorted((x for x in items if 'path' not in x), key=lambda x: x['y'] in have_years)   # empty years first
    if missed:   # give the slow ones a second, gentler go (unless baps.org is plainly down)
        print(f'  {len(missed)} photos were slow, trying {min(len(missed), 40)} of them again', flush=True)
        time.sleep(20)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda x: one(x, timeout=60, quiet=False), missed[:40]))


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


DOING = re.compile(r'arti|puja|pujan|bless|greet|shower|lights?\b|sanctif|plays?|walk|pradakshina|parikrama|reads?|offer|appl|'
                   r'address|discourse|mala|meets?|inaugurat|pratishtha|ritual|perform|bows|thal|sprinkl|writ|garland|honou?r|'
                   r'welcom|darshan|meditat|pray|arriv|visit|abhishek|lamp|tilak', re.I)
JUST_A_FACE = re.compile(r'divine|jovial|\bmood\b|^\s*(HH|Param Pujya)?\s*(Pramukh|Mahant) Swami( Maharaj)?\s*$', re.I)


BAPA_WORDS = re.compile(r"\b(HH|H\.H\.|Param Pujya|P\.P\.|Pramukh|Mahant|Swami|Swamishri|Maharaj|Bapa|his|the|a|an|of|to|and|in|on|at|with|by|for|all)\b", re.I)
STANDARD = re.compile(r"divine|jovial|\bmood\b|morning puja|\bpuja\b|bless\w* (all|the assembly|everyone|devotees)\s*$|"
                      r"^\W*bless\w*\W*$|greet\w* (all|everyone|devotees)|folded hands|shikshapatri|satsang diksha|"
                      r"darshan of (the )?(shrine|murtis?|thakorji)|tapni mala|\bmala\b|\bdarshan\s*$|engaged in|"
                      r"listens|seated|in thought|smil|^\W*\w+ (performs|performing|does) (the )?(arti|aarti)\W*$", re.I)


def unique_caption(c):
    """True when the caption tells of something that happened that day (a visitor, a ceremony, balaks
    dressed as sadhus, playing the drum) rather than an everyday line (divine mood, morning puja,
    blesses all, greets all with folded hands, reads the Shikshapatri)."""
    c = re.sub(r"\s+", " ", c or "").strip()
    if not c or STANDARD.search(c):
        return False
    rest = re.findall(r"[A-Za-z][A-Za-z.]+", BAPA_WORDS.sub(" ", c))
    return len(rest) >= 2


STOP = {'the', 'a', 'an', 'of', 'to', 'and', 'in', 'on', 'at', 'with', 'by', 'for', 'his', 'all', 'bapa', 'during'}


def caption_key(c):
    """Rough word stems of a caption, so 'Greets all with folded hands' and 'Greeting all with folded hands' match."""
    words = re.findall(r"[a-z]+", c.lower())
    return {w[:5] for w in words if w not in STOP}


def same_caption(a, b):
    return bool(a and b) and len(a & b) / len(a | b) >= .7


def pick_one_per_year(items, seed, unique=False):
    """Per year, a photo where Bapa is recognised. Most years show what he is doing (arti, puja, blessing,
    greeting) with him at a medium size; about one year in three is a close darshan of his face, spread out.
    No two years share the same caption: when a year's best photo repeats an earlier year's caption
    (three years of 'reads the Shikshapatri'), its next best photo with a different caption is used, and if
    it has none the year is left out.
    Years where he can't be recognised in any photo are left out, unless that would leave fewer than five;
    then they're kept and shown whole so he isn't cropped out."""
    rnd = random.Random(seed)
    cands = {}
    for x in items:
        if 'path' not in x:
            continue
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        face, sim = bapa_face(im, x.get('d', str(x['y'])))
        x = dict(x, im=im, face=face, sim=sim)
        r = face[3] / im.height if face else 0
        c = x.get('c') or ''
        jitter = rnd.uniform(0, .04) + (1.2 if unique and face and unique_caption(c) else 0)
        s_close = (1 + min(r, .35) + sim if face else 0) + jitter
        s_doing = (1 + sim + .6 * max(0, 1 - abs(r - .15) / .15) + (.4 if DOING.search(c) and not JUST_A_FACE.search(c) else 0)
                   if face else 0) + jitter
        lst = cands.setdefault(x['y'], [])
        lst.append((s_close, s_doing, x))
        if len(lst) > 16:   # keep memory down: only the best few of each kind stay
            keep = {id(v) for v in sorted(lst, key=lambda v: -v[0])[:8] + sorted(lst, key=lambda v: -v[1])[:8]}
            lst[:] = [v for v in lst if id(v) in keep]
    years = sorted(cands)
    if sum(1 for y in years if any(v[2]['face'] for v in cands[y])) >= 5:
        years = [y for y in years if any(v[2]['face'] for v in cands[y])]
    picked, used = [], []
    for i, y in enumerate(years):
        k = 0 if i % 3 == 1 else 1
        ranked = sorted(cands[y], key=lambda v: -v[k])
        if ranked[0][2]['face']:
            ranked = [v for v in ranked if v[2]['face']]
        for v in ranked:
            key = caption_key(caption(v[2]))
            if not any(same_caption(key, u) for u in used):
                picked.append(v[2]); used.append(key)
                break
    if len(picked) < 5:   # too few left once repeats are skipped: fall back to the plain best per year
        picked = [sorted(cands[y], key=lambda v: -v[0 if i % 3 == 1 else 1])[0][2] for i, y in enumerate(years)]
    return picked


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


# ---------------------------------------------------------------- drawing

def diamond(dr, cx, cy, r, fill):
    dr.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


IVORY_TOP, IVORY_BOTTOM, IVORY_EDGE = (248, 242, 228), (234, 223, 200), (196, 178, 146)
YEAR_C2, PLACE_C2 = (96, 20, 32), (88, 34, 34)
garamond = lambda s, w=700: font(f'eb-garamond-latin-{w}-normal', s)
arimo_bold = lambda s: font('arimo-latin-700-normal', s)


def gold_text(img, xy, text, f, shadow=True, top=(255, 226, 150), bottom=(206, 152, 64)):
    """Text filled with a soft top to bottom gold gradient, over a faint dark shadow."""
    x, y = round(xy[0]), round(xy[1])
    box = [round(v) for v in ImageDraw.Draw(img).textbbox((x, y), text, font=f)]
    w, h = box[2] - box[0] + 40, box[3] - box[1] + 40
    mask = Image.new('L', (w, h), 0); ImageDraw.Draw(mask).text((x - box[0] + 20, y - box[1] + 20), text, font=f, fill=255)
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh.putalpha(mask.point(lambda v: v * 170 // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(7)); img.paste(sh, (box[0] - 20, box[1] - 20 + 4), sh)
    grad = Image.new('RGB', (w, h)); gd = ImageDraw.Draw(grad)
    for j in range(h):
        t = min(1, max(0, (j - 20) / max(1, h - 40)))
        gd.line((0, j, w, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    img.paste(grad, (box[0] - 20, box[1] - 20), mask)


def spaced(dr, text, f, track):
    return sum(dr.textlength(ch, font=f) for ch in text) + track * (len(text) - 1)


def draw_spaced(dr, x, y, text, f, track, fill):
    for ch in text:
        dr.text((x, y), ch, font=f, fill=fill); x += dr.textlength(ch, font=f) + track


def thin_rule(dr, y, x0, x1, fade_to_left):
    for xp in range(int(x0), int(x1)):
        t = (xp - x0) / (x1 - x0); a = t if fade_to_left else 1 - t
        dr.line((xp, y, xp, y + 1), fill=tuple(round(m + (g - m) * a) for m, g in zip(MAROON_OUT, GOLD_SOFT)))


def header(img, title, subtitle):
    """Big bold gold title, then a smaller spaced capital line between two thin gold rules."""
    dr = ImageDraw.Draw(img)
    tf = garamond(118)
    tw = dr.textlength(title, font=tf)
    gold_text(img, ((W - tw) / 2, 4), title, tf)
    sf, track = garamond(40, 600), 9
    sub = subtitle.upper()
    sw = spaced(dr, sub, sf, track)
    sy = 142
    draw_spaced(dr, (W - sw) / 2, sy, sub, sf, track, (240, 214, 160))
    mid = sy + 24
    thin_rule(dr, mid, (W - sw) / 2 - 50 - 330, (W - sw) / 2 - 50, True)
    thin_rule(dr, mid, (W + sw) / 2 + 50, (W + sw) / 2 + 50 + 330, False)


def footer(img):
    dr = ImageDraw.Draw(img)
    f = garamond(40, 500)
    w = dr.textlength(FOOTER, font=f)
    y = H - 88
    dr.text(((W - w) / 2, y), FOOTER, font=f, fill=(226, 184, 104))
    mid = y + 27
    thin_rule(dr, mid, (W - w) / 2 - 40 - 220, (W - w) / 2 - 40, True)
    thin_rule(dr, mid, (W + w) / 2 + 40, (W + w) / 2 + 40 + 220, False)
    diamond(dr, (W - w) / 2 - 28, mid + 1, 5, GOLD); diamond(dr, (W + w) / 2 + 28, mid + 1, 5, GOLD)


def background():
    small = Image.new('RGB', (64, 64)); px = small.load()
    inner, outer = (66, 16, 28), (22, 5, 10)
    for j in range(64):
        for i in range(64):
            d = min(1, (((i - 32) / 32 / .85) ** 2 + ((j - 64 * .45) / 32 / .95) ** 2) ** .5)
            px[i, j] = tuple(round(a + (b - a) * d) for a, b in zip(inner, outer))
    img = small.resize((W, H), Image.BICUBIC)
    noise = Image.effect_noise((W // 2, H // 2), 10).resize((W, H)).convert('L')     # faint paper grain, stops banding
    img = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), img, noise.point(lambda v: max(0, v - 118) // 3))
    m = Image.new('L', (78, 36), 0); p = m.load()
    for j in range(36):
        for i in range(78):
            dd = (((i - 38.5) / 39) ** 2 + ((j - 17.5) / 18) ** 2) ** .5
            p[i, j] = int(140 * max(0, dd - .7) / .6)
    img.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), m.resize((W, H), Image.BICUBIC))
    return jali_edge(warm_glow(img))


def warm_glow(img):
    """Soft lamp light from above the title, and a fainter warmth along the bottom."""
    sw, sh = W // 8, H // 8
    yy, xx = np.mgrid[0:sh, 0:sw]
    top = np.clip(1 - np.hypot((xx - sw / 2) / (sw * .42), (yy - sh * .06) / (sh * .42)), 0, 1) ** 1.6
    bottom = np.clip(1 - np.hypot((xx - sw / 2) / (sw * .55), (yy - sh * 1.02) / (sh * .30)), 0, 1) ** 1.6 * .45
    light = np.array([132, 74, 34]) * np.clip(top + bottom, 0, 1)[..., None] * GLOW
    return ImageChops.add(img, Image.fromarray(light.astype('uint8')).resize((W, H), Image.BICUBIC))


def jali_edge(img, R=54):
    """The four petal lattice of a carved mandir jali (overlapping circles), faint and only near the edges."""
    k = 2
    m = Image.new('L', (W * k, H * k), 0); d = ImageDraw.Draw(m)
    for cy in range(-R, H + R, R):
        for cx in range(-R, W + R, R):
            d.ellipse(((cx - R) * k, (cy - R) * k, (cx + R) * k, (cy + R) * k), outline=255, width=3)
    xs = np.minimum(np.arange(W), W - 1 - np.arange(W)); ys = np.minimum(np.arange(H), H - 1 - np.arange(H))
    fade = np.clip(1 - np.minimum(xs[None, :], ys[:, None]) / 190, 0, 1) ** 1.3          # gone before the photos
    mask = ImageChops.multiply(m.resize((W, H), Image.LANCZOS), Image.fromarray((fade * 255 * JALI).astype('uint8')))
    img.paste(Image.new('RGB', (W, H), (160, 84, 74)), (0, 0), mask)
    return img


NAME = r"(?:(?:H\.?\s?H\.?|Param Pujya|P\.?\s?P\.?)\s+)?(?:Pramukh Swami(?: Maharaj)?|Mahant Swami(?: Maharaj)?|Swamishri|Bapa)"


def caption(x):
    """The caption without the name repeated on every card: 'Swamishri blesses all' becomes 'Blesses all'.
    Where dropping the name wouldn't read well ('Swamishri's divine gestures', 'Sadhus honour Swamishri'),
    the name becomes 'Bapa'."""
    c = re.sub(r'\s+', ' ', x.get('c') or '').strip()
    m = re.match(rf'^{NAME}[\s,]+(.+)$', c)
    if m and not re.match(r"(and|with|along|together|'s|’s)\b", m.group(1), re.I):
        c = m.group(1)[0].upper() + m.group(1)[1:]
    c = re.sub(NAME, 'Bapa', c)
    return c


def place(x):
    return re.sub(r'\s*\(.*?\)', '', (x.get('p') or '').split(',')[0]).strip()


def wrap(d, text, f, maxw, lines):
    """Up to `lines` lines no wider than maxw; whatever doesn't fit ends in an ellipsis."""
    words, out = text.split(), []
    while words and len(out) < lines:
        line = words.pop(0)
        while words and d.textlength(line + ' ' + words[0], font=f) <= maxw:
            line += ' ' + words.pop(0)
        out.append(line)
    cut = bool(words) or any(d.textlength(l, font=f) > maxw for l in out)
    if cut and out:
        last = out[-1]
        while last and d.textlength(last + '…', font=f) > maxw:
            last = last[:-1]
        out[-1] = last.rstrip(' ,;:') + '…'
    return out


CAPTION_IVORY, CAPTION_GOLD = (250, 241, 222), (240, 214, 160)


class Card:
    """Ivory polaroid: thin border, nearly square photo, year and place in the bottom band.
    style: None (live look), 'B' caption on a soft band over the photo, 'C' year and caption in the band,
    'D' a small number on the photo for the caption list underneath ('A' draws its caption outside the card)."""
    def __init__(self, pw, aspect=1.08, band=.32, style=None):
        self.PW, self.PH = round(pw), round(pw * aspect)
        self.B, self.BB = max(6, round(pw * .045)), round(pw * band)
        self.CW, self.CH = self.PW + 2 * self.B, self.PH + self.B + self.BB
        self.style = style

    def make(self, x, num=None):
        PW, PH, B, BB, CW, CH = self.PW, self.PH, self.B, self.BB, self.CW, self.CH
        card = Image.new('RGBA', (CW, CH)); d = ImageDraw.Draw(card)
        for j in range(CH):
            t = j / CH
            d.line((0, j, CW, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)) + (255,))
        d.rectangle((0, 0, CW - 1, CH - 1), outline=IVORY_EDGE, width=1)
        card.paste(crop_to(x['im'], x['face'], PW, PH), (B, B))
        if self.style == 'B' and caption(x):
            self.soft_band(card, caption(x))
        if self.style == 'D' and num is not None:
            r = PW * .085; cx, cy = B + r + PW * .035, B + r + PW * .035
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(96, 20, 32), outline=(226, 184, 104), width=max(1, round(PW * .008)))
            nf = garamond(r * 1.25, 700)
            d.text((cx, cy + r * .06), str(num), font=nf, fill=GOLD, anchor='mm')
        d.rectangle((B - 1, B - 1, B + PW, B + PH), outline=(150, 130, 100), width=1)
        if self.style == 'C':
            return self.year_and_caption(card, d, x)
        if self.style == 'E':
            return self.year_caption_place(card, d, x)
        if self.style == 'G':
            return self.quote_then_year(card, d, x)
        yf, yt = garamond(PW * .16, 600), str(x['y'])
        pl = place(x).upper()
        size, track = PW * .08, PW * .014
        while size > PW * .04 and spaced(d, pl, arimo_bold(size), track) > CW - 2 * B - 4:
            size -= 1
        pf = arimo_bold(size)
        yb = d.textbbox((0, 0), yt, font=yf, anchor='ls'); ab = d.textbbox((0, 0), 'A', font=pf, anchor='ls')
        yh, ph, gap = -yb[1], (-ab[1]) if pl else 0, PW * .055 if pl else 0
        top = B + PH + (BB - (yh + gap + ph)) / 2 - B * .2
        d.text(((CW - d.textlength(yt, font=yf)) / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ls')
        draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, top + yh + gap + ph - pf.getmetrics()[0], pl, pf, track, PLACE_C2)
        return card

    def soft_band(self, card, text):
        """Caption in ivory over a soft dark fade across the bottom of the photo."""
        PW, PH, B = self.PW, self.PH, self.B
        d = ImageDraw.Draw(card); f = garamond(PW * .085, 500)
        lines = wrap(d, text, f, PW * .92, 2)
        lh = PW * .098
        h = round(len(lines) * lh + PW * .16)
        fade = Image.new('RGBA', (PW, h)); fd = ImageDraw.Draw(fade)
        for j in range(h):
            t = j / h
            fd.line((0, j, PW, j), fill=(30, 8, 12, round(205 * min(1, t / .55) ** 1.4)))
        card.alpha_composite(fade, (B, B + PH - h))
        y = B + PH - PW * .045 - (len(lines) - 1) * lh
        for i, line in enumerate(lines):
            d.text((B + PW / 2, y + i * lh), line, font=f, fill=CAPTION_IVORY, anchor='ms')

    def year_and_caption(self, card, d, x):
        """Year, then the caption in the polaroid band (the place when there's no caption)."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        yf, yt = garamond(PW * .14, 600), str(x['y'])
        cf = garamond(PW * .08, 500); lh = PW * .093
        lines = wrap(d, caption(x) or place(x), cf, CW - 2 * B - PW * .04, 3)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        block = yh + PW * .05 + len(lines) * lh
        top = B + PH + (BB - block) / 2
        d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
        for i, line in enumerate(lines):
            d.text((CW / 2, top + yh + PW * .05 + (i + .8) * lh), line, font=cf, fill=PLACE_C2, anchor='ms')
        return card

    def year_caption_place(self, card, d, x):
        """Style E: year, caption, then the place in small spaced capitals, all in the polaroid band."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        yf, yt = garamond(PW * .13, 600), str(x['y'])
        cf = garamond(PW * .078, 500); lh = PW * .09
        pf, track = arimo_bold(PW * .05), PW * .012
        pl = place(x).upper()
        lines = wrap(d, caption(x), cf, CW - 2 * B - PW * .04, 2)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1] if pl else 0
        block = yh + PW * .04 + len(lines) * lh + (PW * .04 + ph if pl else 0)
        top = B + PH + (BB - block) / 2
        d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
        y = top + yh + PW * .04
        for i, line in enumerate(lines):
            d.text((CW / 2, y + (i + .8) * lh), line, font=cf, fill=PLACE_C2, anchor='ms')
        y += len(lines) * lh + PW * .04 + ph
        if pl:
            draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, y - pf.getmetrics()[0], pl, pf, track, (150, 96, 80))
        return card

    def quote_then_year(self, card, d, x):
        """Style G: the caption leads, in quotes, with the year and place underneath in small capitals."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        cf = garamond(PW * .084, 500); lh = PW * .097
        pf, track = arimo_bold(PW * .056), PW * .012
        c = caption(x)
        lines = wrap(d, f'“{c}”' if c else '', cf, CW - 2 * B - PW * .04, 3)
        tag = f'{x["y"]}  ·  {place(x).upper()}' if place(x) else str(x['y'])
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1]
        block = len(lines) * lh + (PW * .05 if lines else 0) + ph
        top = B + PH + (BB - block) / 2
        for i, line in enumerate(lines):
            d.text((CW / 2, top + (i + .8) * lh), line, font=cf, fill=YEAR_C2, anchor='ms')
        y = top + len(lines) * lh + (PW * .05 if lines else 0) + ph
        draw_spaced(d, (CW - spaced(d, tag, pf, track)) / 2, y - pf.getmetrics()[0], tag, pf, track, PLACE_C2)
        return card

    def hang(self, card):
        sh = Image.new('RGBA', (self.CW + 80, self.CH + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((40, 48, self.CW + 40, self.CH + 46), fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(13)); sh.alpha_composite(card, (40, 40))
        return sh


def peg(dr, cx, cy, s):
    w, h = 9 * s, 30 * s
    dr.rounded_rectangle((cx - w, cy - h * .45, cx + w, cy + h * .55), radius=3 * s, fill=(138, 94, 58), outline=(84, 52, 30), width=max(1, round(2 * s)))
    dr.line((cx - w + 3 * s, cy - h * .45 + 3 * s, cx - w + 3 * s, cy + h * .55 - 3 * s), fill=(176, 128, 84), width=max(1, round(2 * s)))
    dr.line((cx, cy - h * .4, cx, cy + h * .5), fill=(84, 52, 30), width=1)


def caption_list(img, photos, y0, y1):
    """Style D: the numbered captions in three columns between the photos and the footer."""
    dr = ImageDraw.Draw(img)
    cols = 3; per = -(-len(photos) // cols)
    nf, cf = garamond(25, 700), garamond(25, 500)
    lh = min(36, (y1 - y0) / per)
    colw = (W - 2 * 120) / cols
    for i, x in enumerate(photos):
        c, r = divmod(i, per)
        xl, yb = 120 + c * colw, y0 + (r + .8) * lh
        lead = f'{i + 1}.'
        dr.text((xl + 30, yb), lead, font=nf, fill=GOLD, anchor='rs')
        yt = f'{x["y"]}'
        dr.text((xl + 42, yb), yt, font=nf, fill=(226, 184, 104), anchor='ls')
        tx = xl + 42 + dr.textlength(yt, font=nf) + 16
        text = wrap(dr, caption(x) or place(x), cf, xl + colw - 30 - tx, 1)
        dr.text((tx, yb), text[0] if text else '', font=cf, fill=CAPTION_GOLD, anchor='ls')


# style H with bigger frames: H2 narrower margins and two line captions, H3 one line captions and polaroids may overlap a little
LAYOUT = {'H2': dict(M=70, min_gap=14, row_gap=40, lines=2, cap=360, top=212, bottom=H - 100),
          'H3': dict(M=60, min_gap=-14, row_gap=34, lines=1, cap=360, top=210)}


def under_card(x, card, gap, f, lh, style, rnd):
    """Style F: a small ivory paper tag on a short thread under the polaroid.
    Style H: ivory caption on a soft dark plate under the polaroid."""
    probe = ImageDraw.Draw(Image.new('L', (1, 1)))
    if style == 'F':
        lines = wrap(probe, caption(x), f, card.CW * .86 - 20, 3)
        tw = max(probe.textlength(l, font=f) for l in lines) + 30
        th = len(lines) * lh + 18
        im = Image.new('RGBA', (int(tw) + 40, int(th) + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cx = im.width / 2
        d.line((cx, 0, cx, 26), fill=(170, 132, 78), width=2)                          # the thread
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 30, 20 + tw, 30 + th), radius=6, fill=(0, 0, 0, 120))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        d.rounded_rectangle((20, 24, 20 + tw, 24 + th), radius=6, fill=IVORY_TOP + (255,), outline=IVORY_EDGE)
        d.ellipse((cx - 4, 30, cx + 4, 38), fill=(150, 120, 90))                         # the hole
        for i, line in enumerate(lines):
            d.text((cx, 24 + 14 + (i + .8) * lh), line, font=f, fill=YEAR_C2, anchor='ms')
        return im.rotate(rnd.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True), 2
    lines = wrap(probe, caption(x), f, card.CW + min(gap, 30) - 50, LAYOUT.get(style, {}).get('lines', 3))
    tw = max(probe.textlength(l, font=f) for l in lines) + 34
    th = len(lines) * lh + 16
    im = Image.new('RGBA', (int(tw), int(th)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, tw - 1, th - 1), radius=int(th / 2) if len(lines) == 1 else 14, fill=(30, 8, 12, 150))
    for i, line in enumerate(lines):
        d.text((tw / 2, 8 + (i + .5) * lh), line, font=f, fill=CAPTION_IVORY, anchor='mm')
    return im, 14


def compose(photos, day, seed, style=None):
    rnd = random.Random(seed)
    img = background(); dr = ImageDraw.Draw(img)
    header(img, f'{day.day} {day:%B}', 'in Bapa’s Diary')

    n = len(photos)
    rows = [photos] if n <= 5 else [photos[:(n + 1) // 2], photos[(n + 1) // 2:]]
    lay = LAYOUT.get(style, {})
    cols, M, min_gap = len(rows[0]), lay.get('M', 100), lay.get('min_gap', 30)
    list_h = (-(-n // 3) * 36 + 30) if style == 'D' else 0     # room for the numbered caption list
    top_space, bottom_space = lay.get('top', 222), lay.get('bottom', H - 128) - list_h
    row_gap = lay.get('row_gap', 58)
    band = {'C': .52, 'E': .6, 'G': .56}.get(style, .32)
    cf_a = garamond(24, 500); lh_a = 29
    below = {'A': 3 * lh_a + 16, 'F': 3 * lh_a + 52, 'H': 3 * lh_a + 34}.get(style, 0)   # room under each card
    if style in LAYOUT:
        below = lay['lines'] * lh_a + 30
    pw_w = ((W - 2 * M - min_gap * (cols - 1)) / cols) / 1.09
    row_h = (bottom_space - top_space - row_gap * (len(rows) - 1)) / len(rows) - below
    pw = min(lay.get('cap', 300), pw_w, row_h / (1.08 + .045 + band))
    # on busy days the cards are narrower, so let the photos grow taller to fill the height instead
    card = Card(pw, max(1.08, min(1.45, row_h / pw - .045 - band)), band, style)
    gap = min(70, (W - 2 * M - cols * card.CW) / max(1, cols - 1))
    pitch = card.CH + below + row_gap
    block = (len(rows) - 1) * pitch + card.CH + below
    first = top_space + max(0, (bottom_space - top_space - block) / 2)
    s = card.PW / 220

    num = 0
    for r, row in enumerate(rows):
        y_top = first + r * pitch
        sag = lambda xp: y_top - 4 + 12 * 4 * (xp / W) * (1 - xp / W)
        dr.line([(xp, sag(xp)) for xp in range(0, W + 1, 6)], fill=(170, 132, 78), width=2)
        x0 = (W - (len(row) * card.CW + (len(row) - 1) * gap)) / 2
        for c, x in enumerate(row):
            cx = x0 + c * (card.CW + gap) + card.CW / 2
            # each polaroid swings a little on its peg, like a real one would
            a = rnd.uniform(-2.2, 2.2); t = np.radians(a)
            num += 1
            hung = card.hang(card.make(x, num)).rotate(a, resample=Image.BICUBIC, expand=True)
            px, py = cx, y_top                                  # the peg holds the middle of the top edge
            mx, my = px + card.CH / 2 * np.sin(t), py + card.CH / 2 * np.cos(t)
            img.paste(hung, (int(mx - hung.width / 2), int(my - hung.height / 2)), hung)
            peg(dr, cx, sag(cx) + 4, s)
            if style == 'A' and caption(x):
                lines = wrap(dr, caption(x), cf_a, card.CW + gap - 14, 3)
                ty = y_top + card.CH + 18
                for i, line in enumerate(lines):
                    dr.text((cx, ty + (i + .8) * lh_a), line, font=cf_a, fill=CAPTION_GOLD, anchor='ms')
            if style and style[0] in 'FH' and caption(x):
                tag, pos = under_card(x, card, gap, cf_a, lh_a, style, rnd)
                bx, by = px + card.CH * np.sin(t), py + card.CH * np.cos(t)   # middle of the tilted card's bottom edge
                img.paste(tag, (int(bx - tag.width / 2), int(by + pos)), tag)

    if style == 'D':
        caption_list(img, photos, bottom_space + 18, H - 112)
    footer(img)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (default: today in London)')
    ap.add_argument('--data', help='use this JSON file instead of downloading the day list')
    ap.add_argument('--cache', default=os.path.join(HERE, '.cache'))
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--compare', action='store_true', help='also make original.jpg and unique.jpg (captions shown) and captions.txt')
    ap.add_argument('--styles', default='', help='also make caption mockups, e.g. A,B,C,D (out/caption-A.jpg ...)')
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
        print(f'  {x["y"]}  {x.get("p", "")[:28]:28}  Bapa {"%.2f" % x["sim"] if x["face"] else "not found, shown whole"}  {caption(x)}')

    os.makedirs(a.out, exist_ok=True)
    compose(photos, day, seed=mmdd).save(os.path.join(a.out, 'bapas-diary.jpg'), quality=92, optimize=True)
    for st in filter(None, a.styles.split(',')):
        compose(photos, day, seed=mmdd, style=st).save(os.path.join(a.out, f'caption-{st}.jpg'), quality=92, optimize=True)
    if a.compare:
        photos_u = pick_one_per_year(items, seed=mmdd, unique=True)
        compose(photos, day, seed=mmdd, style='A').save(os.path.join(a.out, 'original.jpg'), quality=92, optimize=True)
        compose(photos_u, day, seed=mmdd, style='A').save(os.path.join(a.out, 'unique.jpg'), quality=92, optimize=True)
        with open(os.path.join(a.out, 'captions.txt'), 'w') as f:
            for name, ps in (('original', photos), ('unique', photos_u)):
                f.write(f'{name}:\n')
                for x in ps:
                    f.write(f'  {x["y"]}  {"UNIQUE  " if unique_caption(caption(x)) else "standard"}  {caption(x)}\n')
    open(os.path.join(a.out, 'date.txt'), 'w').write(f'{day}\n')
    open(os.path.join(a.out, 'summary.txt'), 'w').write(f'{len(photos)} years: ' + ', '.join(str(x['y']) for x in photos) + '\n')
    print('saved', os.path.join(a.out, 'bapas-diary.jpg'))


if __name__ == '__main__':
    main()
