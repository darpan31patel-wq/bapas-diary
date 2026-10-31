"""Test only (never ship): Annakut food drawings, laddu pyramids, a tiered sweet tower and kaju katli, for the Every Annakut mockup."""
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


def display(w, h, seed=0):
    """An annakut corner: a tall sweet tower behind, laddu pyramids and kaju katli in front, drawn at 2x and shrunk."""
    k = 2; W, H = w * k, h * k
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    unit = W / 4
    tower(img, W * .5, H * .62, unit * 1.5, 7, seed)
    pyramid(img, W * .2, H * .8, unit * .17, 4, (240, 150, 30), [(255, 195, 80), (200, 110, 20)], seed)
    pyramid(img, W * .8, H * .8, unit * .17, 4, (110, 40, 18), None, seed + 1)
    katli_stack(img, W * .5, H * .93, unit * 1.1, 4)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel('A').filter(ImageFilter.GaussianBlur(k * 6)).point(lambda v: v * .5))
    out = Image.new('RGBA', img.size, (0, 0, 0, 0)); out.alpha_composite(sh, (k * 4, k * 6)); out.alpha_composite(img)
    return out.resize((w, h), Image.LANCZOS)


