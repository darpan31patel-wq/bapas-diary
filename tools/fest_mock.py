"""Test only (never ship): the 'Every Diwali' picture drawn from the website's festival list (bapas-diary.com/data/fest),
each year on its own Indian date, with the website's Diwali dress: a night sky with fireworks at the sides, a string of
little coloured lights along each cord, and a lit diya at the foot of every card. Darpan chose this mockup, 30 Oct 2026.

python tools/fest_mock.py preview/fest/diwali.json preview/fest/diwali out.jpg [--plain]"""
import datetime, glob, json, math, os, random, re, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import W, H, px

BULBS = [(255, 70, 60), (255, 190, 40), (90, 220, 110), (80, 170, 255), (255, 110, 200)]
FIRE = [(255, 205, 90), (255, 120, 170), (120, 220, 255), (255, 150, 60), (190, 255, 140)]


def night():
    """Night sky: deep blue black at the top, warming to the usual maroon below, a soft diya glow along the bottom."""
    sw, sh = W // 8, H // 8
    yy, xx = np.mgrid[0:sh, 0:sw] / np.array([sh, sw])[:, None, None]
    top, low = np.array([10, 8, 26]), np.array([46, 12, 22])
    t = np.clip(yy ** 1.2, 0, 1)[..., None]
    a = top * (1 - t) + low * t
    glow = np.clip(1 - np.hypot((xx - .5) / .6, (yy - 1.05) / .32), 0, 1) ** 1.5
    a = a + np.array([150, 80, 20]) * glow[..., None] * .55
    img = Image.fromarray(a.clip(0, 255).astype('uint8')).resize((W, H), Image.BICUBIC)
    rnd = random.Random(8)
    d = ImageDraw.Draw(img)
    for _ in range(260):   # faint stars, thinning towards the bottom
        x, y = rnd.uniform(0, W), rnd.uniform(0, H) ** 1.6 / H ** .6
        r = px(rnd.choice((1, 1, 1.4, 2)))
        v = rnd.randint(120, 230)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(v, v, min(255, v + 20)))
    return fireworks(img)


def burst(layer, cx, cy, R, col, rnd):
    d = ImageDraw.Draw(layer)
    n = rnd.randint(22, 30)
    for i in range(n):
        a = i / n * 2 * math.pi + rnd.uniform(-.05, .05)
        rr = R * rnd.uniform(.82, 1.05)
        for k in range(9):   # a streak of sparks, brighter and bigger at its tip
            f = (k + 1) / 9
            x, y = cx + math.cos(a) * rr * f, cy + math.sin(a) * rr * f + R * .12 * f * f
            s = px(1.2 + 2.6 * f)
            d.ellipse((x - s, y - s, x + s, y + s), fill=col + (int(60 + 190 * f),))
    s = px(6)
    d.ellipse((cx - s, cy - s, cx + s, cy + s), fill=(255, 250, 220, 230))


def fireworks(img):
    """Bursts in the free corners beside the title and down the sides, kept off where the cards hang."""
    rnd = random.Random(11)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    spots = [(.06, .10, 120), (.17, .06, 80), (.94, .10, 125), (.83, .06, 78), (.035, .45, 70), (.965, .5, 72)]
    for i, (fx, fy, r) in enumerate(spots):
        burst(layer, W * fx, H * fy, px(r), FIRE[i % len(FIRE)], rnd)
    glow = layer.filter(ImageFilter.GaussianBlur(px(10)))
    img = img.convert('RGBA')
    img.alpha_composite(glow); img.alpha_composite(glow); img.alpha_composite(layer)
    return img.convert('RGB')


def lit_rope(img, pts, w=None):
    """The usual jute cord with a little coloured bulb hanging every so often, each with its own glow."""
    plain_rope(img, pts, w)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    step, k, i, acc = px(46), 0, 0, 0
    bulbs = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0); acc += seg
        if acc >= step:
            acc = 0; bulbs.append((x1, y1, BULBS[i % len(BULBS)])); i += 1
    for x, y, c in bulbs:
        r = px(13)
        d.ellipse((x - r, y + px(4) - r, x + r, y + px(4) + r), fill=c + (150,))
    glow = layer.filter(ImageFilter.GaussianBlur(px(9)))
    out = img.convert('RGBA'); out.alpha_composite(glow)
    d = ImageDraw.Draw(out)
    for x, y, c in bulbs:
        d.rectangle((x - px(3), y, x + px(3), y + px(5)), fill=(60, 50, 40))
        r = px(6.5)
        d.ellipse((x - r, y + px(4), x + r, y + px(4) + 2.4 * r), fill=c)
        d.ellipse((x - r * .45, y + px(4) + r * .5, x - r * .05, y + px(4) + r * 1.2), fill=(255, 255, 255, 170))
    img.paste(out.convert('RGB'))


def diya(size):
    """A lit clay diya with a soft glow, drawn at 4x and shrunk so it stays smooth."""
    k = 4; s = size * k
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    g = Image.new('RGBA', (s, s), (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    gd.ellipse((s * .18, s * .02, s * .82, s * .62), fill=(255, 170, 40, 150))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(s * .08)))
    d.polygon([(s * .5, s * .06), (s * .6, s * .3), (s * .6, s * .42), (s * .5, s * .5), (s * .4, s * .42), (s * .4, s * .3)], fill=(255, 150, 30))
    d.polygon([(s * .5, s * .18), (s * .555, s * .34), (s * .5, s * .46), (s * .445, s * .34)], fill=(255, 238, 150))
    d.chord((s * .08, s * .22, s * .92, s * .92), 0, 180, fill=(170, 70, 30))
    d.chord((s * .14, s * .34, s * .86, s * .84), 0, 180, fill=(205, 100, 40))
    d.ellipse((s * .08, s * .5, s * .92, s * .64), fill=(150, 55, 25))
    d.ellipse((s * .14, s * .52, s * .86, s * .6), fill=(110, 40, 20))
    d.line((s * .2, s * .72, s * .8, s * .72), fill=(255, 210, 120), width=s // 40)
    return im.resize((size, size), Image.LANCZOS)


def dressed(make_card):
    """The usual card, then its band redrawn: a diya at each foot corner and the year and town fitted between them."""
    def go(self, x, num=None):
        card = make_card(self, x, num)
        B, PW, PH, BB, CW, CH = self.B, self.PW, self.PH, self.BB, self.CW, self.CH
        d = ImageDraw.Draw(card)
        for j in range(B + PH + 1, CH - 1):   # wipe the band back to plain ivory
            t = j / CH
            d.line((1, j, CW - 2, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(make.IVORY_TOP, make.IVORY_BOTTOM)) + (255,))
        s = round(BB * .9)
        dy = diya(s)
        y = CH - s - round(BB * .04)
        card.alpha_composite(dy, (round(B * .5), y))
        card.alpha_composite(dy, (CW - s - round(B * .5), y))
        yf, yt = make.garamond(PW * .15, 700), str(x['y'])
        pl = make.place(x).upper()
        pf, track = make.arimo_bold(PW * .06), PW * .012
        room = CW - 2 * (s + B) - (d.textlength(yt, font=yf) + PW * .035)
        while pf.size > max(8, PW * .03) and make.spaced(d, pl, pf, track) > room:
            pf = make.arimo_bold(pf.size - 1)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1] if pl else 0
        yw, pw_ = d.textlength(yt, font=yf), make.spaced(d, pl, pf, track)
        sp = PW * .035 if pl else 0
        x0 = (CW - (yw + sp + pw_)) / 2
        base = B + PH + BB / 2 + yh / 2
        d.text((x0, base), yt, font=yf, fill=make.YEAR_C2, anchor='ls')
        make.draw_spaced(d, x0 + yw + sp, base - (yh - ph) / 2 - pf.getmetrics()[0], pl, pf, track, make.PLACE_C2)
        return card
    return go


def items(fest, folder):
    out = []
    for y in fest['years']:
        files = sorted(glob.glob(os.path.join(folder, f"{y['y']}-*")), key=lambda f: int(os.path.basename(f).split('-')[1]))
        for p in y['p']:
            f = next((f for f in files if f.endswith('-' + p[1].split('/')[-1])), None)
            if not f:
                continue
            im = Image.open(f).convert('RGB'); iw, ih = im.size
            box = p[4] if len(p) > 4 and p[4] else None
            face = (box[2] * iw, box[3] * ih, box[4] * iw, box[5] * ih) if box else None
            short = re.sub(r'\bs (?=diwali)', 'a ', p[5] if len(p) > 5 and p[5] else p[2], flags=re.I)   # 'Sanctifies s diwali card'
            out.append(dict(y=y['y'], d=y['d'], im=im, face=face, c=short, town=y.get('place') or '',
                            crop='close' if box and box[7] else 'frame', i=p[1]))
            break
    return out


def main():
    src, folder, dest = sys.argv[1:4]
    plain = '--plain' in sys.argv
    fest = json.load(open(src, encoding='utf-8'))
    photos = items(fest, folder)
    make.place = lambda x: x.get('town', '')
    make.caption = lambda x: x.get('c', '')
    if not plain:
        make.background = night
        global plain_rope
        plain_rope = make.rope
        make.rope = lit_rope
        make.WideCard.make = dressed(make.WideCard.make)
    day = datetime.date(2026, 11, 8)
    line = f'One darshan from each Diwali, {photos[0]["y"]} to {photos[-1]["y"]}, each on its own Indian date'
    img = make.compose_wide(photos, day, seed='Diwali', style='W2', title='Every Diwali', cal=(line, ''))
    img.convert('RGB').save(dest, quality=92)
    print(len(photos), 'years:', ', '.join(f"{x['y']} ({x['d'][5:]})" for x in photos))


if __name__ == '__main__':
    main()
