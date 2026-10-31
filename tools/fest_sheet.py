"""Test only (never ship): contact sheets of the festival candidates (preview/fest/cands.json), one row a year, so the
photos can be looked at before any is chosen. python tools/fest_sheet.py thumbs_folder out_folder"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

thumbs, out = sys.argv[1:3]
only = sys.argv[3:]   # just these festivals (a wider look: up to 16 a year, two lines of 8)
os.makedirs(out, exist_ok=True)
font = ImageFont.load_default(size=15)
big = ImageFont.load_default(size=26)
TW, TH, LAB = 300, 225, 38
for k, fest in json.load(open('preview/fest/cands.json')).items():
    if only and k not in only:
        continue
    years, per, lines = fest['years'], (6 if only else 12), (2 if only else 1)
    for part in range(0, len(years), per):
        ys = years[part:part + per]
        img = Image.new('RGB', (110 + 8 * TW, len(ys) * lines * (TH + LAB)), (30, 30, 30)); d = ImageDraw.Draw(img)
        for r, y in enumerate(ys):
            top0 = r * lines * (TH + LAB)
            d.text((8, top0 + 8), str(y['y']), font=big, fill=(255, 220, 120))
            for i, x in enumerate(y['c'][:8 * lines]):
                p = os.path.join(thumbs, f"{x['a']}-{x['f'].split('/')[-1]}")
                top = top0 + (i // 8) * (TH + LAB)
                left = 110 + (i % 8) * TW
                try:
                    t = Image.open(p).convert('RGB'); t.thumbnail((TW - 6, TH - 4)); img.paste(t, (left, top + 2))
                except Exception:
                    d.text((left + 10, top + 90), 'missing', font=font, fill=(255, 80, 80))
                tag = f"{chr(97 + i)} t{x['t']} {x['c'][:34]}"
                d.text((left, top + TH + 2), tag, font=font, fill=(255, 255, 255))
                d.text((left, top + TH + 19), x['c'][34:70], font=font, fill=(200, 200, 200))
        img.save(os.path.join(out, f'{k}{"-wide" if only else ""}-{part // per + 1}.jpg'), quality=80)
