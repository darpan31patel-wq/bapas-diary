"""Share picture and site icons for the website bapas-diary.com (Darpan, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Makes, in the On this day look (maroon ground, gold
Garamond title, the photo as an ivory polaroid):

    python3 tools/web_share.py --out live

  live/share.jpg              1200 x 630, the preview card WhatsApp and others show when a link is sent
  live/icon-512.png, icon-192.png, apple-touch-icon.png (180), favicon-32.png   the site icon
The photo is site/art/preview-photo.jpg (a 1999 darshan, 3208/TP_1999_117_36.jpg).
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
    W, H = 1200, 630
    img = ground(W, H, cx=0.62)
    photo = Image.open(os.path.join(HERE, 'site', 'art', 'preview-photo.jpg')).convert('RGB')
    card = polaroid(photo, 372)
    cx, cy = 70, (H - card.height) // 2
    sh = Image.new('L', (W, H))
    ImageDraw.Draw(sh).rectangle([cx + 6, cy + 14, cx + card.width + 6, cy + card.height + 14], fill=150)
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(14)))
    img.paste(card, (cx, cy))
    d = ImageDraw.Draw(img)
    mid = (cx + card.width + W) // 2 + 10
    gold_text(img, (mid, 222), 'Bapa\u2019s Diary', font('eb-garamond-latin-700-normal', 104), anchor='ms')
    k = font('arimo-latin-700-normal', 17)
    w = spaced(d, (mid, 272), 'DARSHAN THROUGH THE YEARS', k, GOLD_SOFT, 6)
    for s in (-1, 1):
        x0 = mid + s * (w / 2 + 18)
        for i in range(60):
            d.point((x0 + s * i, 272), fill=mix(GOLD_SOFT, MAROON_IN, i / 60))
    body = font('eb-garamond-latin-500-normal', 33)
    for i, line in enumerate(('Daily darshan of Pramukh Swami Maharaj', 'and Mahant Swami Maharaj, any day you choose')):
        d.text((mid, 350 + i * 44), line, font=body, fill=mix(CAP, MAROON_IN, 0.18), anchor='ms')
    spaced(d, (mid, 500), 'BAPAS-DIARY.COM', font('arimo-latin-700-normal', 19), GOLD_HI, 5)
    img.save(os.path.join(out, 'share.jpg'), 'JPEG', quality=88, optimize=True, progressive=True)


def icon(size):
    """A gold Garamond B on the maroon glow, inside a thin gold ring. Full bleed, so phones can round the corners."""
    S = 1024
    img = ground(S, S, cy=0.42)
    d = ImageDraw.Draw(img)
    r, c = 400, S // 2
    for i, w in ((0, 10), (34, 3)):
        d.ellipse([c - r + i, c - r + i, c + r - i, c + r - i], outline=GOLD_SOFT, width=w)
    gold_text(img, (c, c + 22), 'B', font('eb-garamond-latin-700-normal', 560), anchor='mm')
    return img.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, 'live'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    share_card(a.out)
    for name, size in (('icon-512.png', 512), ('icon-192.png', 192), ('apple-touch-icon.png', 180), ('favicon-32.png', 32)):
        icon(size).save(os.path.join(a.out, name), optimize=True)


if __name__ == '__main__':
    main()
