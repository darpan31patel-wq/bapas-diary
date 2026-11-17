"""Before and after pictures for a test branch (Darpan, 17 Nov 2026: see every change before saying yes).

python tools/before_after.py <date> <before.jpg> <after.jpg> <folder>
writes <folder>/<date>-side-by-side.jpg (the whole picture as main makes it, then as the branch makes it)
and <folder>/<date>-close-up.jpg (the middle of both, side by side, at the size people see when they zoom in on a phone).
daily.yml calls it for every date of a 'before:' run on a test branch; it works on any two pictures of the same size."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD, NIGHT = (240, 220, 170), (24, 16, 16)


def font(size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', 'arimo-latin-700-normal.woff2'), size)


def side_by_side(d, a, b):
    k = 2400 / a.width
    a, b = (im.resize((2400, round(im.height * k)), Image.LANCZOS) for im in (a, b))
    out = Image.new('RGB', (2400, a.height + b.height + 160), NIGHT)
    dr = ImageDraw.Draw(out)
    dr.text((30, 16), f'{d}  BEFORE: the picture as main makes it today', font=font(44), fill=GOLD)
    out.paste(a, (0, 80))
    dr.text((30, a.height + 96), f'{d}  AFTER: as this test branch makes it', font=font(44), fill=GOLD)
    out.paste(b, (0, a.height + 160))
    return out


def close_up(d, a, b):
    """The middle third of each picture at full size: what a phone shows after two pinches."""
    w, h = a.size
    box = (round(w * .36), 0, round(w * .64), h)
    a, b = a.crop(box), b.crop(box)
    k = 1180 / a.width
    a, b = (im.resize((1180, round(im.height * k)), Image.LANCZOS) for im in (a, b))
    out = Image.new('RGB', (2400, a.height + 90), NIGHT)
    dr = ImageDraw.Draw(out)
    dr.text((14, 20), f'{d}  BEFORE (close up)', font=font(40), fill=GOLD)
    dr.text((1234, 20), 'AFTER (close up)', font=font(40), fill=GOLD)
    out.paste(a, (0, 90)); out.paste(b, (1220, 90))
    return out


def main(d, before, after, folder):
    a, b = (Image.open(p).convert('RGB') for p in (before, after))
    if b.size != a.size:
        b = b.resize(a.size, Image.LANCZOS)
    os.makedirs(folder, exist_ok=True)
    side_by_side(d, a, b).save(os.path.join(folder, f'{d}-side-by-side.jpg'), quality=90)
    close_up(d, a, b).save(os.path.join(folder, f'{d}-close-up.jpg'), quality=90)


if __name__ == '__main__':
    main(*sys.argv[1:5])
