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
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = 'https://darshan-screensaver.pages.dev/memories/{mmdd}.json'
W, H = 2796, 1290
MAROON_OUT = (18, 4, 8)
GOLD, GOLD_SOFT = (255, 207, 107), (217, 164, 65)
FOOTER = 'Darpan’s Smruti Project'


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
    return img


class Card:
    """Ivory polaroid: thin border, nearly square photo, year and place in the bottom band."""
    def __init__(self, pw, aspect=1.08):
        self.PW, self.PH = round(pw), round(pw * aspect)
        self.B, self.BB = max(6, round(pw * .045)), round(pw * .32)
        self.CW, self.CH = self.PW + 2 * self.B, self.PH + self.B + self.BB

    def make(self, x):
        PW, PH, B, BB, CW, CH = self.PW, self.PH, self.B, self.BB, self.CW, self.CH
        card = Image.new('RGBA', (CW, CH)); d = ImageDraw.Draw(card)
        for j in range(CH):
            t = j / CH
            d.line((0, j, CW, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)) + (255,))
        d.rectangle((0, 0, CW - 1, CH - 1), outline=IVORY_EDGE, width=1)
        card.paste(crop_to(x['im'], x['face'], PW, PH), (B, B))
        d.rectangle((B - 1, B - 1, B + PW, B + PH), outline=(150, 130, 100), width=1)
        yf, yt = garamond(PW * .16, 600), str(x['y'])
        pl = re.sub(r'\s*\(.*?\)', '', (x.get('p') or '').split(',')[0]).strip().upper()
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


def compose(photos, day, seed):
    rnd = random.Random(seed)
    img = background(); dr = ImageDraw.Draw(img)
    header(img, f'{day.day} {day:%B}', 'in Bapa’s Diary')

    n = len(photos)
    rows = [photos] if n <= 5 else [photos[:(n + 1) // 2], photos[(n + 1) // 2:]]
    cols, M, min_gap = len(rows[0]), 100, 30
    top_space, bottom_space = 222, H - 128
    row_gap = 58
    pw_w = ((W - 2 * M - min_gap * (cols - 1)) / cols) / 1.09
    row_h = (bottom_space - top_space - row_gap * (len(rows) - 1)) / len(rows)
    pw = min(300, pw_w, row_h / (1.08 + .045 + .32))
    # on busy days the cards are narrower, so let the photos grow taller to fill the height instead
    card = Card(pw, max(1.08, min(1.45, row_h / pw - .045 - .32)))
    gap = min(70, (W - 2 * M - cols * card.CW) / max(1, cols - 1))
    pitch = card.CH + row_gap
    block = (len(rows) - 1) * pitch + card.CH
    first = top_space + max(0, (bottom_space - top_space - block) / 2)
    s = card.PW / 220

    for r, row in enumerate(rows):
        y_top = first + r * pitch
        sag = lambda xp: y_top - 4 + 12 * 4 * (xp / W) * (1 - xp / W)
        dr.line([(xp, sag(xp)) for xp in range(0, W + 1, 6)], fill=(170, 132, 78), width=2)
        x0 = (W - (len(row) * card.CW + (len(row) - 1) * gap)) / 2
        for c, x in enumerate(row):
            cx = x0 + c * (card.CW + gap) + card.CW / 2
            # each polaroid swings a little on its peg, like a real one would
            a = rnd.uniform(-2.2, 2.2); t = np.radians(a)
            hung = card.hang(card.make(x)).rotate(a, resample=Image.BICUBIC, expand=True)
            px, py = cx, y_top                                  # the peg holds the middle of the top edge
            mx, my = px + card.CH / 2 * np.sin(t), py + card.CH / 2 * np.cos(t)
            img.paste(hung, (int(mx - hung.width / 2), int(my - hung.height / 2)), hung)
            peg(dr, cx, sag(cx) + 4, s)

    footer(img)
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
