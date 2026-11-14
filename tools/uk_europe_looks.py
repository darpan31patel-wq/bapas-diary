"""Grouped by year looks for the UK and Europe backup pictures (Darpan, 14 Nov 2026: 'i dont want it to be the exact
same as my on this day ... grouped by years ... not a timeline, just different events happening on that day').

compose_grouped(photos, day, entry, look): one block per year across the picture, each block's photos in its own
tight grid, the block as wide as its photos need. Looks:
  'album'  ivory album pages side by side, the year and town on each page, captions in dark text under each photo
  'gold'   no pages: a gold year heading over each group, plain prints with a thin gold edge, caption in a dark fade
           at the foot of each photo
  'mosaic' like gold, but the best photo of each year is a big one (two cells each way) at the top of its group"""
import math, random
import make
from make import Image, ImageDraw, ImageFilter, px, garamond, arimo_bold, W, H


def group(photos):
    out = {}
    for x in photos:
        out.setdefault(x['y'], []).append(x)
    return out


def fits(n, c, r, big):
    """Do n photos (one 2x2 when big) fit in c columns and r rows?"""
    return len(pack(n, c, r, big)) == n


def cols_for(n, r, big):
    c = 1
    while not fits(n, c, r, big):
        c += 1
    return c


def pack(n, c, r, big):
    """Which cell each photo takes: (col, row, span) with the first one 2x2 when big."""
    taken, out = set(), []
    if big and n > 1:
        out.append((0, 0, 2)); taken |= {(0, 0), (1, 0), (0, 1), (1, 1)}
    k = len(out)
    for row in range(r):
        for col in range(c):
            if k >= n:
                return out
            if (col, row) in taken:
                continue
            out.append((col, row, 1)); k += 1
    return out


def compose_grouped(photos, day, entry, look, title, subtitle, foot, heroes=()):
    """'wall': like gold with up to 48 photos packed tight, tiny one line captions. 'hero': the wall between a full height
    darshan of each guru at the sides (heroes)."""
    wall = look in ('wall', 'hero')
    big = look == 'mosaic'
    BIG_FROM = 4                                                  # a year with fewer photos than this has no big one
    page = look == 'album'
    years = group(photos)
    img = make.background().convert('RGBA'); dr = ImageDraw.Draw(img)
    make.header_one(img, title, subtitle)
    M, gap, between = px(40), (px(4) if wall else px(8)), (px(14) if wall else px(26))   # edge, between cells, between year blocks
    top, bottom = px(150), H - px(84)
    left, right = M, W - M
    if look == 'hero' and heroes:                                 # a full height darshan of each guru at the side(s)
        hw = int((bottom - top) * .6)
        for k, hx in enumerate(heroes[:2]):
            x = left if k == 0 else right - hw
            photo = make.polish(make.crop_to(hx['im'], hx['face'], hw, int(bottom - top), 'frame', at=.3))
            img.paste(photo, (int(x), int(top)))
            dr.rectangle((x - 1, top - 1, x + hw, bottom), outline=make.GOLD_SOFT, width=max(1, int(px(1.5))))
            yf = garamond(px(40), 700)
            tag = f"{hx['y']}  {make.place(hx).upper()}"
            tw = dr.textlength(tag, font=yf)
            dr.rectangle((x, bottom - px(64), x + hw, bottom), fill=(30, 8, 12))
            dr.text((x + hw / 2, bottom - px(18)), tag, font=yf, fill=make.GOLD, anchor='ms')
            if k == 0:
                left = x + hw + between * 2
            else:
                right = x - between * 2
        photos = [x for x in photos if not any(x is h for h in heroes)]
        years = group(photos)
    M2 = 0
    for y in years:                                               # the best photo first (the big one), then the rest
        years[y].sort(key=lambda x: -x['score'])
    cap_h = px(58) if page else 0                                 # room for a caption under each photo on a page
    head_h = px(46) if wall else px(74)                                               # the year heading over each block
    pad = px(16) if page else 0
    ratio = .75 if wall else .8                                   # cell photo height / width
    best = None
    for rows in range(2, 11):                                      # every block fills the height: the row count that gives the biggest photos
        grids = {y: cols_for(len(ps), rows, big and len(ps) >= BIG_FROM) for y, ps in years.items()}
        cols = sum(grids.values())
        s_w = (right - left - between * (len(years) - 1) - 2 * pad * len(years) - gap * (cols - len(years))) / cols
        s_h = ((bottom - top - head_h - 2 * pad - gap * (rows - 1)) / rows - cap_h) / ratio
        s = min(s_w, s_h)
        if best is None or s > best[0]:
            best = (s, rows, grids)
    s, rows, grids = best
    grids = {y: (c, rows) for y, c in grids.items()}
    ph = s * ratio
    widths = {y: c * s + (c - 1) * gap + 2 * pad for y, (c, r) in grids.items()}
    total = sum(widths.values()) + between * (len(years) - 1)
    x0 = left + (right - left - total) / 2
    cf, lh = (garamond(px(13), 500), px(15)) if wall else (garamond(px(17), 500), px(20))
    rnd = random.Random(day.isoformat())
    for y in sorted(years):
        ps, (c, r) = years[y], grids[y]
        bw = widths[y]
        bh = head_h + 2 * pad + r * (ph + cap_h) + (r - 1) * gap
        by = top + (bottom - top - bh) / 2
        guru = ps[0]['guru'].split(',')[0]
        town = make.place(ps[0]).upper()
        if page:                                                  # the album page
            sh = Image.new('RGBA', (int(bw) + 60, int(bh) + 60), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((30, 36, 30 + bw, 36 + bh), radius=px(10), fill=(0, 0, 0, 140))
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(px(10))), (int(x0) - 30, int(by) - 30))
            pg = Image.new('RGBA', (int(bw), int(bh)), (0, 0, 0, 0)); pd = ImageDraw.Draw(pg)
            for j in range(int(bh)):
                t = j / bh
                pd.line((0, j, bw, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(make.IVORY_TOP, make.IVORY_BOTTOM)) + (255,))
            mask = Image.new('L', pg.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw - 1, bh - 1), radius=px(10), fill=255)
            img.paste(pg, (int(x0), int(by)), mask)
            dr.rounded_rectangle((x0, by, x0 + bw, by + bh), radius=px(10), outline=make.IVORY_EDGE, width=2)
            yf, pf = garamond(px(44), 700), arimo_bold(px(15))
            yc, pc = make.YEAR_C2, make.PLACE_C2
        else:
            yf, pf = (garamond(px(30), 700), garamond(px(15), 500)) if wall else (garamond(px(46), 700), garamond(px(18), 500))
            yc, pc = make.GOLD, make.CAPTION_GOLD
            dr.line((x0, by + head_h - px(10), x0 + bw, by + head_h - px(10)), fill=make.GOLD_SOFT, width=max(1, int(px(1.2))))
        yt = str(y); yw = dr.textlength(yt, font=yf)
        line2 = f'{town}  ·  {guru}' if page else f'{town.title()}  ·  {guru}'
        while dr.textlength(line2, font=pf) > bw - 2 * pad - px(8) and pf.size > px(10):
            pf = arimo_bold(pf.size - 1) if page else garamond(pf.size - 1, 500)
        if page:
            dr.text((x0 + bw / 2, by + pad + px(40)), yt, font=yf, fill=yc, anchor='ms')
            make.draw_spaced(dr, x0 + (bw - make.spaced(dr, line2, pf, px(1.5))) / 2, by + pad + px(48), line2, pf, px(1.5), pc)
        else:
            while yw > bw - px(4) and yf.size > px(20):
                yf = garamond(yf.size - 2, 700); yw = dr.textlength(yt, font=yf)
            hy = px(30) if wall else px(38)
            dr.text((x0 + pad, by + hy), yt, font=yf, fill=yc, anchor='ls')
            if yw + px(14) + dr.textlength(line2, font=pf) <= bw:
                dr.text((x0 + pad + yw + px(14), by + hy), line2, font=pf, fill=pc, anchor='ls')
            elif not wall:                                        # a narrow block: the town under the year
                dr.text((x0 + pad, by + px(60)), line2, font=pf, fill=pc, anchor='ls')
        used = max(row + span for _, row, span in pack(len(ps), c, r, big and len(ps) >= BIG_FROM))   # rows this block really uses
        gx0, gy0 = x0 + pad, by + head_h + pad + (r - used) * (ph + cap_h + gap) / 2
        for x, (col, row, span) in zip(ps, pack(len(ps), c, r, big and len(ps) >= BIG_FROM)):
            cw = span * s + (span - 1) * gap; chh = span * ph + (span - 1) * (gap + cap_h)
            px0, py0 = gx0 + col * (s + gap), gy0 + row * (ph + cap_h + gap)
            photo = make.crop_to(x['im'], x['face'], int(cw), int(chh), x.get('crop', 'frame'), at=.3)
            photo = make.polish(photo)
            text = make.shown_caption(x)
            if page:
                img.paste(photo, (int(px0), int(py0)))
                dr.rectangle((px0 - 1, py0 - 1, px0 + cw, py0 + chh), outline=(150, 130, 100), width=1)
                if text:
                    lines = make.wrap(dr, text, cf, cw - px(6), 3 if span == 1 else 2)
                    for i, l in enumerate(lines):
                        dr.text((px0 + cw / 2, py0 + chh + px(6) + (i + .8) * lh), l, font=cf, fill=(70, 40, 40), anchor='ms')
            else:
                if text:                                           # the caption in a dark fade at the foot of the photo
                    lines = make.wrap(dr, text, cf, cw - px(10), 1 if wall else (2 if span == 1 else 1))
                    fh = int(len(lines) * lh + px(14) + chh * .12)
                    fade = Image.new('RGBA', (int(cw), fh)); fd = ImageDraw.Draw(fade)
                    for j in range(fh):
                        fd.line((0, j, cw, j), fill=(30, 8, 12, round(215 * min(1, (j / fh) / .5) ** 1.3)))
                    photo = photo.convert('RGBA'); photo.alpha_composite(fade, (0, int(chh) - fh))
                    pdr = ImageDraw.Draw(photo)
                    for i, l in enumerate(lines):
                        pdr.text((cw / 2, chh - px(8) - (len(lines) - 1 - i) * lh), l, font=cf, fill=make.CAPTION_IVORY, anchor='ms')
                    photo = photo.convert('RGB')
                img.paste(photo, (int(px0), int(py0)))
                dr.rectangle((px0 - 1, py0 - 1, px0 + cw, py0 + chh), outline=make.GOLD_SOFT, width=max(1, int(px(1))))
        x0 += bw + between
    img = img.convert('RGB')
    make.footer(img, small=True, cal=(foot, ''))
    return img
