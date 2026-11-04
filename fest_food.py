"""Annakut food drawings for the Every Annakut picture: laddu pyramids, tiered sweet towers, jalebis, kaju katli and bowls, stacked in the free corners (Darpan, 31 Oct 2026: stacked food like in the photos, fuller, nothing on the cards)."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def ball(r, col, dots=None, seed=0):
    """A shaded round sweet (laddu, jamun): lit from the top left, a soft shadow edge, optional boondi grain."""
    n = 2 * r + 2
    yy, xx = np.mgrid[0:n, 0:n] - r
    d = np.hypot(xx, yy) / r
    lx, ly = (xx + r * .35) / r, (yy + r * .4) / r
    light = np.clip(1 - np.hypot(lx, ly) * .75, 0, 1)
    c = np.array(col, float)
    rgb = c * (.55 + .6 * light[..., None]) + 60 * np.clip(light - .7, 0, 1)[..., None] * 3
    a = np.clip((1 - d) * r * 1.5, 0, 1) * 255
    im = Image.fromarray(np.dstack([rgb.clip(0, 255), a]).astype('uint8'), 'RGBA')
    if dots:
        dr = ImageDraw.Draw(im); rnd = random.Random(seed)
        for _ in range(int(r * r * .5)):
            t, q = rnd.uniform(0, 2 * math.pi), r * math.sqrt(rnd.uniform(0, .8))
            x, y = r + math.cos(t) * q, r + math.sin(t) * q; s = max(1, r * .06)
            dr.ellipse((x - s, y - s, x + s, y + s), fill=rnd.choice(dots))
        im.putalpha(Image.fromarray(a.astype('uint8')))
    return im


def plate(d, cx, y, w):
    """A brass plate seen from the side."""
    d.ellipse((cx - w / 2, y - w * .09, cx + w / 2, y + w * .09), fill=(176, 120, 36), outline=(120, 78, 20), width=max(1, int(w * .012)))
    d.ellipse((cx - w * .44, y - w * .07, cx + w * .44, y + w * .05), fill=(222, 168, 70))


def pyramid(img, cx, base, r, rows, col, dots, seed):
    """Laddus stacked in a pyramid on a brass plate, as at a real annakut."""
    d = ImageDraw.Draw(img)
    plate(d, cx, base + r * .2, r * 2 * rows + r * 1.2)
    sp = ball(r, col, dots, seed)
    for k, n in enumerate(range(rows, 0, -1)):
        y = base - r - k * r * 1.62
        for i in range(n):
            x = cx + (i - (n - 1) / 2) * r * 1.9
            img.alpha_composite(sp, (int(x - r), int(y - r)))


def tower(img, cx, base, w, tiers, seed):
    """A tiered sweet tower: rings of coloured sweets getting smaller to the top, like the stacked annakut towers."""
    d = ImageDraw.Draw(img)
    cols = [(236, 72, 120), (250, 205, 60), (92, 170, 70), (250, 245, 230), (240, 140, 40), (180, 90, 200)]
    rnd = random.Random(seed)
    plate(d, cx, base + w * .04, w * 1.2)
    y = base
    for t in range(tiers):
        ww = w * (1 - t / (tiers + 1.5)); hh = w * .16; c = cols[(t + seed) % len(cols)]
        dark = tuple(int(v * .72) for v in c)
        d.rectangle((cx - ww / 2, y - hh, cx + ww / 2, y), fill=c)
        d.ellipse((cx - ww / 2, y - hh * .35, cx + ww / 2, y + hh * .35), fill=dark)
        d.rectangle((cx - ww / 2, y - hh, cx + ww / 2, y - hh * .1), fill=c)
        for i in range(int(ww / (hh * .55))):   # the round sweets the ring is made of
            x = cx - ww / 2 + (i + .5) * hh * .55; s = hh * .2
            d.ellipse((x - s, y - hh * .55 - s, x + s, y - hh * .55 + s), fill=tuple(min(255, v + 35) for v in c), outline=dark)
        d.ellipse((cx - ww / 2, y - hh - hh * .35, cx + ww / 2, y - hh + hh * .35), fill=tuple(min(255, v + 20) for v in c), outline=dark)
        y -= hh
    s = w * .09
    d.ellipse((cx - s, y - 2 * s, cx + s, y), fill=(255, 215, 0), outline=(170, 120, 0))


def katli_stack(img, cx, base, w, n):
    """Kaju katli diamonds stacked in layers, silver topped."""
    d = ImageDraw.Draw(img)
    plate(d, cx, base + w * .05, w * 1.25)
    h = w * .09
    for k in range(n):
        ww = w * (1 - k * .14); y = base - k * h
        d.polygon([(cx - ww / 2, y - h * .5), (cx, y - h * .5 - ww * .18), (cx + ww / 2, y - h * .5), (cx, y - h * .5 + ww * .18)], fill=(236, 226, 205), outline=(170, 150, 120))
        d.polygon([(cx - ww / 2, y - h * .5), (cx, y - h * .5 + ww * .18), (cx, y + h * .5 + ww * .18), (cx - ww / 2, y + h * .5)], fill=(214, 198, 168))
        d.polygon([(cx + ww / 2, y - h * .5), (cx, y - h * .5 + ww * .18), (cx, y + h * .5 + ww * .18), (cx + ww / 2, y + h * .5)], fill=(196, 178, 146))
    d.polygon([(cx - w * .2, base - (n - 1) * h - h * .5), (cx, base - (n - 1) * h - h * .5 - w * .07), (cx + w * .2, base - (n - 1) * h - h * .5), (cx, base - (n - 1) * h - h * .5 + w * .07)], fill=(232, 236, 240))


def jalebi_heap(img, cx, base, w, seed):
    """A heap of jalebis on a brass plate."""
    d = ImageDraw.Draw(img); rnd = random.Random(seed)
    plate(d, cx, base + w * .04, w * 1.15)
    for k in range(14):
        r = w * .13
        x = cx + rnd.uniform(-.38, .38) * w * (1 - k / 18); y = base - r * .5 - (k / 14) ** .8 * w * .45
        pts = [(x + math.cos(t) * r * t / 12, y + math.sin(t) * r * t / 12 * .7) for t in [i / 6 for i in range(3, 72)]]
        d.line(pts, fill=(190, 85, 8), width=max(2, int(w * .045)), joint='curve')
        d.line(pts, fill=(255, 158, 28), width=max(1, int(w * .03)), joint='curve')
        d.line(pts, fill=(255, 210, 110), width=max(1, int(w * .01)), joint='curve')


def bowl(img, cx, base, w, col, seed):
    """A brass bowl heaped with something (shrikhand, halwa, dry fruit)."""
    d = ImageDraw.Draw(img); rnd = random.Random(seed)
    d.pieslice((cx - w / 2, base - w * .55, cx + w / 2, base + w * .35), 0, 180, fill=(176, 120, 36), outline=(120, 78, 20))
    d.ellipse((cx - w / 2, base - w * .22, cx + w / 2, base - w * .02), fill=(150, 100, 30))
    d.pieslice((cx - w * .46, base - w * .5, cx + w * .46, base + w * .1), 180, 360, fill=col)
    for _ in range(int(w * .12)):
        x, y = cx + rnd.uniform(-.35, .35) * w, base - w * .12 - rnd.uniform(0, .16) * w; r = w * .025
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice([(150, 95, 40), (120, 170, 60), (240, 230, 210)]))


LADDU = [((240, 150, 30), [(255, 195, 80), (200, 110, 20)]), ((110, 40, 18), None), ((250, 215, 60), [(255, 240, 140), (220, 170, 30)]),
         ((235, 130, 170), [(255, 190, 210)]), ((140, 190, 90), [(190, 225, 140)]), ((245, 235, 215), [(255, 250, 240)])]


def display(w, h, seed=0):
    """A full annakut corner, like the real ones: tall sweet towers at the back, pyramids of laddus, pedas and
    jamuns in the middle, jalebis, kaju katli and bowls in front, every row overlapping the one behind it."""
    k = 2; W, H = w * k, h * k
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    rnd = random.Random(seed)
    u = W / 3.2
    for i, fx in enumerate((.18, .5, .82)):   # back: towers, the middle one tallest
        tower(img, W * fx, H * (.5 if i == 1 else .56), u * (1.05 if i == 1 else .85), 8 if i == 1 else 6, seed * 3 + i)
    for i, fx in enumerate((.1, .36, .64, .9)):   # middle: pyramids
        col, dots = LADDU[(i + seed) % len(LADDU)]
        pyramid(img, W * fx, H * .74, u * .1, 4 + (i % 2), col, dots, seed + i)
    jalebi_heap(img, W * .22, H * .88, u * 1.1, seed)
    katli_stack(img, W * .52, H * .9, u * .8, 5)
    bowl(img, W * .8, H * .9, u * .8, (250, 225, 120), seed)
    for i, fx in enumerate((.04, .96)):   # little laddu heaps at the front corners
        col, dots = LADDU[(i + 2 + seed) % len(LADDU)]
        pyramid(img, W * fx, H * .97, u * .07, 3, col, dots, seed + 9 + i)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel('A').filter(ImageFilter.GaussianBlur(k * 6)).point(lambda v: v * .5))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0)); out.alpha_composite(sh, (k * 4, k * 6)); out.alpha_composite(img)
    return out.resize((w, h), Image.LANCZOS)
