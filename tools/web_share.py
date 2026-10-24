"""Share picture and site icons for the website bapas-diary.com (Darpan, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Makes, in the On this day look (maroon ground, gold
Garamond title, the photo as an ivory polaroid):

    python3 tools/web_share.py --out live

  live/share.jpg              1200 x 630, the preview card WhatsApp and others show when a link is sent
  live/icon-512.png, icon-192.png, apple-touch-icon.png (180), favicon-32.png   the site icon
The photos are site/art/preview-psm.jpg (1999, 3208/TP_1999_117_36.jpg) and preview-msm.jpg (28 Sep 2016).
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAROON_IN, MAROON_OUT = (0x42, 0x10, 0x1c), (0x16, 0x05, 0x09)
GOLD_HI, GOLD, GOLD_SOFT = (0xff, 0xe2, 0x96), (0xce, 0x98, 0x40), (0xd9, 0xa4, 0x41)
IVORY_TOP, IVORY_BOT, IVORY_EDGE = (0xfd, 0xf9, 0xf0), (0xef, 0xe4, 0xcd), (0xd3, 0xc1, 0x9c)
CAP = (0xfa, 0xf1, 0xde)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.woff2'), round(size))


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def ground(w, h, cx=0.5, cy=0.4):
    """The maroon glow of the 2pm picture: lighter in the middle, near black at the edges."""
    small = Image.new('RGB', (w // 4, h // 4))
    px = small.load()
    for y in range(small.height):
        for x in range(small.width):
            dx, dy = (x / small.width - cx) / 0.9, (y / small.height - cy) / 1.1
            px[x, y] = mix(MAROON_IN, MAROON_OUT, min(1, (dx * dx + dy * dy) ** 0.5 * 1.6))
    return small.resize((w, h), Image.BICUBIC)


def gold_text(img, xy, text, f, anchor='la', spacing=0):
    """Text filled with the gold gradient (#ffe296 to #ce9840) and a soft shadow, like the website title."""
    mask = Image.new('L', img.size)
    d = ImageDraw.Draw(mask)
    if spacing:
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=f, fill=255, anchor=anchor)
            x += f.getlength(ch) + spacing
    else:
        d.text(xy, text, font=f, fill=255, anchor=anchor)
    box = mask.getbbox()
    shadow = mask.filter(ImageFilter.GaussianBlur(3)).point(lambda v: v * 0.55)
    img.paste((0, 0, 0), (0, 0), shadow.transform(img.size, Image.AFFINE, (1, 0, 0, 0, 1, -3)))
    grad = Image.new('RGB', img.size)
    gd = ImageDraw.Draw(grad)
    for y in range(box[1], box[3] + 1):
        gd.line([(0, y), (img.width, y)], fill=mix(GOLD_HI, GOLD, (y - box[1]) / max(1, box[3] - box[1])))
    img.paste(grad, (0, 0), mask)
    return box


def spaced(d, xy, text, f, fill, spacing, anchor='mm'):
    """Arimo spaced capitals, centred on xy."""
    w = sum(f.getlength(c) for c in text) + spacing * (len(text) - 1)
    x, y = xy[0] - w / 2, xy[1]
    for c in text:
        d.text((x, y), c, font=f, fill=fill, anchor='lm')
        x += f.getlength(c) + spacing
    return w


def polaroid(photo, width):
    """The photo in a thick ivory frame, wider at the bottom, with a soft drop shadow."""
    pad = round(width * 0.06)
    pw = width - 2 * pad
    ph = round(photo.height * pw / photo.width)
    h = pad + ph + round(pad * 3.2)
    card = Image.new('RGB', (width, h))
    cd = ImageDraw.Draw(card)
    for y in range(h):
        cd.line([(0, y), (width, y)], fill=mix(IVORY_TOP, IVORY_BOT, y / h))
    cd.rectangle([0, 0, width - 1, h - 1], outline=IVORY_EDGE)
    card.paste(photo.resize((pw, ph), Image.LANCZOS), (pad, pad))
    return card


def share_card(out):
    """Pramukh Swami Maharaj (1999) and Mahant Swami Maharaj (2016) as two polaroids, a little apart and tilted,
    with the gold title and both names beside them."""
    W, H = 1200, 630
    img = ground(W, H, cx=0.66)
    shadows = Image.new('L', (W, H))
    cards = []
    for name, x, y, tilt in (('preview-psm.jpg', 46, 70, 4), ('preview-msm.jpg', 296, 92, -3.5)):
        photo = Image.open(os.path.join(HERE, 'site', 'art', name)).convert('RGB')
        card = polaroid(photo.crop((0, 0, photo.width, round(photo.width * 4 / 3))), 580).convert('RGBA')
        card = card.rotate(tilt, Image.BICUBIC, expand=True)
        card = card.resize((card.width // 2, card.height // 2), Image.LANCZOS)
        shadows.paste(card.getchannel('A').point(lambda v: v * 0.6), (x + 8, y + 16))
        cards.append((card, x, y))
    img.paste((0, 0, 0), (0, 0), shadows.filter(ImageFilter.GaussianBlur(14)))
    for card, x, y in cards:
        img.paste(card, (x, y), card)
    d = ImageDraw.Draw(img)
    mid = 880
    gold_text(img, (mid, 250), 'Bapa\u2019s Diary', font('eb-garamond-latin-700-normal', 92), anchor='ms')
    k = font('arimo-latin-700-normal', 15)
    w = spaced(d, (mid, 296), 'DARSHAN THROUGH THE YEARS', k, GOLD_SOFT, 5)
    for s in (-1, 1):
        x0 = mid + s * (w / 2 + 14)
        for i in range(36):
            d.point((x0 + s * i, 296), fill=mix(GOLD_SOFT, MAROON_IN, i / 36))
    body = font('eb-garamond-latin-500-normal', 31)
    for i, line in enumerate(('Pramukh Swami Maharaj', 'Mahant Swami Maharaj')):
        d.text((mid, 368 + i * 42), line, font=body, fill=mix(CAP, MAROON_IN, 0.15), anchor='ms')
    spaced(d, (mid, 486), 'BAPAS-DIARY.COM', font('arimo-latin-700-normal', 17), GOLD_HI, 5)
    img.save(os.path.join(out, 'share.jpg'), 'JPEG', quality=88, optimize=True, progressive=True)


ICONS = ('b', 'tilak', 'diary', 'polaroid', 'ring-words', 'seal', 'diary-words')
RED = (0xc8, 0x1e, 0x2a)


def arc_text(img, text, f, c, r, start, fill, step=None):
    """Capitals set around a circle of radius r, centre c, reading clockwise from angle start (degrees, 0 = top)."""
    import math
    widths = [f.getlength(ch) for ch in text]
    track = step or 0
    ang = math.radians(start)
    for ch, w in zip(text, widths):
        a = ang + (w / 2) / r
        tile = Image.new('RGBA', (f.size * 2, f.size * 2))
        ImageDraw.Draw(tile).text((f.size, f.size), ch, font=f, fill=fill, anchor='mm')
        tile = tile.rotate(-math.degrees(a), Image.BICUBIC)
        x, y = c + r * math.sin(a), c - r * math.cos(a)
        img.paste(tile, (round(x - f.size), round(y - f.size)), tile)
        ang += (w + track) / r


def gold_ring(d, c, r):
    for i, w in ((0, 10), (34, 3)):
        d.ellipse([c - r + i, c - r + i, c + r - i, c + r - i], outline=GOLD_SOFT, width=w)


def icon(size, style='b'):
    """The site icon on the maroon glow, full bleed so phones can round the corners.
    b: a gold Garamond B in a thin gold ring. tilak: the gold tilak with the red chandlo.
    diary: an open gold diary. polaroid: a small ivory polaroid of Bapa, a little tilted."""
    S = 1024
    img = ground(S, S, cy=0.42)
    d = ImageDraw.Draw(img)
    c = S // 2
    if style == 'b':
        r = 400
        for i, w in ((0, 10), (34, 3)):
            d.ellipse([c - r + i, c - r + i, c + r - i, c + r - i], outline=GOLD_SOFT, width=w)
        gold_text(img, (c, c + 22), 'B', font('eb-garamond-latin-700-normal', 560), anchor='mm')
    elif style == 'tilak':
        m = Image.new('L', (S, S))
        md = ImageDraw.Draw(m)
        md.rounded_rectangle([c - 230, 170, c - 150, 640], 40, fill=255)
        md.rounded_rectangle([c + 150, 170, c + 230, 640], 40, fill=255)
        md.arc([c - 230, 380, c + 230, 840], 0, 180, fill=255, width=80)
        grad = Image.new('RGB', (S, S))
        gd = ImageDraw.Draw(grad)
        for y in range(S):
            gd.line([(0, y), (S, y)], fill=mix(GOLD_HI, GOLD, y / S))
        img.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(8)).point(lambda v: v * 0.5))
        img.paste(grad, (0, 0), m)
        d.ellipse([c - 92, 470, c + 92, 654], fill=RED)
    elif style == 'diary':
        m = Image.new('L', (S, S))
        md = ImageDraw.Draw(m)
        for s in (-1, 1):
            pts = [(c, 330), (c + s * 360, 270), (c + s * 360, 720), (c, 780)]
            md.polygon(pts, fill=255)
        grad = Image.new('RGB', (S, S))
        gd = ImageDraw.Draw(grad)
        for y in range(S):
            gd.line([(0, y), (S, y)], fill=mix(GOLD_HI, GOLD, y / S))
        img.paste(grad, (0, 0), m)
        d.line([(c, 330), (c, 780)], fill=MAROON_IN, width=14)
        for s in (-1, 1):
            for i in range(5):
                y = 400 + i * 70
                d.line([(c + s * 70, y + 10 - i * 0), (c + s * 290, y - 30)], fill=mix(GOLD, MAROON_IN, 0.45), width=10)
        d.polygon([(c + 120, 300), (c + 170, 293), (c + 170, 420), (c + 145, 395), (c + 120, 420)], fill=RED)
    elif style == 'ring-words':
        gold_ring(d, c, 400)
        f = font('eb-garamond-latin-700-normal', 205)
        gold_text(img, (c, c - 22), 'Bapa\u2019s', f, anchor='ms')
        gold_text(img, (c, c + 158), 'Diary', f, anchor='ms')
        for y in (c - 250, c + 250):
            d.regular_polygon((c, y, 13), 4, rotation=45, fill=GOLD_SOFT)
    elif style == 'seal':
        gold_ring(d, c, 440)
        d.ellipse([c - 300, c - 300, c + 300, c + 300], outline=GOLD_SOFT, width=4)
        k = font('arimo-latin-700-normal', 74)
        text = 'BAPA\u2019S DIARY'
        import math
        span = sum(k.getlength(ch) for ch in text) + 22 * (len(text) - 1)
        arc_text(img, text, k, c, 352, -math.degrees(span / 352) / 2, GOLD_HI, 22)
        bottom = 'DARSHAN THROUGH THE YEARS'
        k2 = font('arimo-latin-700-normal', 40)
        span2 = sum(k2.getlength(ch) for ch in bottom) + 10 * (len(bottom) - 1)
        # the lower words read left to right along the bottom, letters upright
        ang = math.radians(180) + span2 / 352 / 2
        for ch in bottom:
            w = k2.getlength(ch)
            at = ang - (w / 2) / 352
            tile = Image.new('RGBA', (80, 80))
            ImageDraw.Draw(tile).text((40, 40), ch, font=k2, fill=GOLD_SOFT, anchor='mm')
            tile = tile.rotate(180 - math.degrees(at), Image.BICUBIC)
            x, y = c + 352 * math.sin(at), c - 352 * math.cos(at)
            img.paste(tile, (round(x - 40), round(y - 40)), tile)
            ang -= (w + 10) / 352
        for a in (90, 270):
            x, y = c + 352 * math.sin(math.radians(a)), c - 352 * math.cos(math.radians(a))
            d.regular_polygon((x, y, 14), 4, rotation=45, fill=GOLD_SOFT)
        gold_text(img, (c, c + 18), 'B', font('eb-garamond-latin-700-normal', 440), anchor='mm')
    elif style == 'diary-words':
        m = Image.new('L', (S, S))
        md = ImageDraw.Draw(m)
        for sg in (-1, 1):
            md.polygon([(c, 300), (c + sg * 400, 250), (c + sg * 400, 760), (c, 810)], fill=255)
        pages = Image.new('RGB', (S, S))
        gd = ImageDraw.Draw(pages)
        for y in range(S):
            gd.line([(0, y), (S, y)], fill=mix(IVORY_TOP, IVORY_BOT, y / S))
        img.paste((0, 0, 0), (0, 0), m.filter(ImageFilter.GaussianBlur(14)).point(lambda v: v * 0.5))
        img.paste(pages, (0, 0), m)
        for sg in (-1, 1):
            d.line([(c + sg * 400, 250), (c + sg * 400, 760)], fill=GOLD, width=10)
        d.line([(c, 300), (c, 810)], fill=IVORY_EDGE, width=8)
        f = font('eb-garamond-latin-700-normal', 128)
        ink = (0x6e, 0x14, 0x24)
        d.text((c - 200, 560), 'Bapa\u2019s', font=f, fill=ink, anchor='ms')
        d.text((c + 200, 560), 'Diary', font=f, fill=ink, anchor='ms')
        for sg in (-1, 1):
            for i in range(2):
                y = 640 + i * 46
                d.line([(c + sg * 90, y), (c + sg * 320, y - 10)], fill=mix(IVORY_EDGE, ink, 0.15), width=7)
        d.polygon([(c + 250, 236), (c + 300, 230), (c + 300, 380), (c + 275, 352), (c + 250, 380)], fill=RED)
    else:
        photo = Image.open(os.path.join(HERE, 'site', 'art', 'preview-psm.jpg')).convert('RGB')
        side = photo.width
        sq = photo.crop((40, 60, 40 + side - 80, 60 + side - 80))
        card = polaroid(sq, 640).convert('RGBA').rotate(-5, Image.BICUBIC, expand=True)
        x, y = (S - card.width) // 2, (S - card.height) // 2
        sh = Image.new('L', (S, S))
        sh.paste(card.getchannel('A').point(lambda v: v * 0.6), (x + 10, y + 22))
        img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
        img.paste(card, (x, y), card)
    return img.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, 'live'))
    ap.add_argument('--icon', choices=ICONS, default='b')
    ap.add_argument('--all-icons', action='store_true', help='also save icon-STYLE.png of every style, to choose from')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    share_card(a.out)
    for name, size in (('icon-512.png', 512), ('icon-192.png', 192), ('apple-touch-icon.png', 180), ('favicon-32.png', 32)):
        icon(size, a.icon).save(os.path.join(a.out, name), optimize=True)
    if a.all_icons:
        for style in ICONS:
            icon(512, style).save(os.path.join(a.out, f'icon-{style}.png'), optimize=True)


if __name__ == '__main__':
    main()
