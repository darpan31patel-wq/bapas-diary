#!/usr/bin/env python3
"""BAPS calendar style posters, mixed with Bapa's Diary's own look (Darpan, 23 Oct 2026). Mockups to choose from.

    python tools/poster.py --month 2012-01 --day 9      every design into preview/poster/2012-01/

Day posters: the calendar's day (date, the Indian date, festival, notes; never the muhurat timings), our darshan
of Bapa that day with where he was, and underneath what happened: that day's photo captions and the Telegram
history channels for the same date. Month posters: the BAPS calendar grid with a box for every day (left plain when
there is no photo, so no day goes missing) where the photos come first; and a second card for the month's
special moments.

Photos come from preview/poster/<month>/photos.json (tools/poster_photos.py, run on GitHub), the calendar from
calendar/baps-calendar.json (tools/baps_calendar.py). Nothing here touches the daily picture.
"""
import argparse, calendar, datetime, json, math, os, random, re, sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools'))
sys.path.insert(0, HERE)
FOOTER = 'Darpan’s Smruti Project'
W, H = 2160, 2700

# baps.org's calendar colours
TAN, TAN_DARK = (201, 160, 118), (168, 124, 84)
RUST, SUN_RED = (186, 98, 44), (166, 28, 32)
CREAM, CELL, LINE = (246, 239, 226), (255, 253, 248), (222, 208, 186)
EKADASHI, AMAS = (253, 241, 196), (214, 210, 204)
INK, GREY, LINK = (52, 44, 40), (118, 104, 96), (40, 92, 170)
# Bapa's Diary's colours
MAROON, MAROON_DEEP = (96, 20, 32), (40, 8, 14)
GOLD, GOLD_SOFT, IVORY = (233, 190, 110), (214, 176, 112), (248, 242, 228)
SAFFRON = (232, 128, 38)


def font(name, size):
    files = {'serif': 'eb-garamond-latin-600-normal', 'serif-bold': 'eb-garamond-latin-700-normal',
             'serif-med': 'eb-garamond-latin-500-normal', 'sans': 'arimo-latin-700-normal',
             'light': 'Inter-Light.otf', 'regular': 'Inter-Regular.otf', 'medium': 'Inter-Medium.otf'}
    f = files[name]
    return ImageFont.truetype(os.path.join(HERE, 'fonts', f if '.' in f else f + '.woff2'), max(8, round(size)))


def spaced(d, xy, text, f, fill, gap, anchor='mm'):
    """Letter spaced capitals, centred on xy (anchor 'mm') or starting at xy (anchor 'lm')."""
    widths = [d.textlength(c, font=f) for c in text]
    total = sum(widths) + gap * (len(text) - 1)
    x = xy[0] - total / 2 if anchor == 'mm' else xy[0]
    for c, w in zip(text, widths):
        d.text((x, xy[1]), c, font=f, fill=fill, anchor='lm')
        x += w + gap
    return total


def wrap(d, text, f, maxw, lines=3):
    words, out = text.split(), []
    while words and len(out) < lines:
        line = words.pop(0)
        while words and d.textlength(line + ' ' + words[0], font=f) <= maxw:
            line += ' ' + words.pop(0)
        out.append(line)
    if words:
        last = out[-1]
        while last and d.textlength(last + '…', font=f) > maxw:
            last = last.rsplit(' ', 1)[0] if ' ' in last else last[:-1]
        out[-1] = last.rstrip(',;:') + '…'
    return out


def crop(path, face, w, h, tight=True):
    """The photo cut to w x h around Bapa: tight keeps his head and shoulders, otherwise as much of the scene as fits."""
    im = Image.open(path).convert('RGB')
    iw, ih = im.size
    fx, fy, fw, fh = face
    a = w / h
    if tight:
        ch = min(ih, fh / .30)
        cw = ch * a
        if cw > iw:
            cw = iw; ch = cw / a
    else:
        cw, ch = (ih * a, ih) if iw / ih > a else (iw, iw / a)
    cx = min(max(fx + fw / 2 - cw / 2, 0), iw - cw)
    cy = min(max(fy - ch * (.16 if tight else .22), 0), ih - ch)
    return im.crop((round(cx), round(cy), round(cx + cw), round(cy + ch))).resize((round(w), round(h)), Image.LANCZOS)


def shadow(img, box, r=40, blur=30, alpha=110, off=(0, 18)):
    sh = Image.new('L', img.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([box[0] + off[0], box[1] + off[1], box[2] + off[0], box[3] + off[1]], r, fill=alpha)
    img.paste(Image.new('RGB', img.size, (0, 0, 0)), (0, 0), sh.filter(ImageFilter.GaussianBlur(blur)))


def rounded(img, photo, xy, r):
    m = Image.new('L', photo.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, photo.width - 1, photo.height - 1], r, fill=255)
    img.paste(photo, xy, m)


def paper(size, top=CREAM, bottom=(238, 226, 204)):
    w, h = size
    g = Image.linear_gradient('L').resize((w, h))
    return Image.composite(Image.new('RGB', size, bottom), Image.new('RGB', size, top), g)


def maroon_bg(size):
    w, h = size
    base = paper(size, (110, 26, 38), MAROON_DEEP)
    glow = Image.new('L', size, 0)
    ImageDraw.Draw(glow).ellipse([w * .1, -h * .25, w * .9, h * .45], fill=120)
    return Image.composite(Image.new('RGB', size, (150, 52, 52)), base, glow.filter(ImageFilter.GaussianBlur(w * .12)))


def foot(img, y, colour):
    d = ImageDraw.Draw(img)
    f = font('serif', 46)
    d.text((img.width / 2, y), f'·  {FOOTER}  ·', font=f, fill=colour, anchor='mm')


# ---------------------------------------------------------------- the day's facts

class Day:
    def __init__(self, cal, photos, date):
        self.date = date
        self.cal = cal.get(date.isoformat(), {})
        d = date.day
        self.close = photos['close'].get(str(d))
        self.act = photos['act'].get(str(d))
        self.captions = photos['extra'].get(str(d), [])
        self.dir = photos['dir']
        self.history = history(date)

    @property
    def tithi(self):
        return self.cal.get('indian_date', '')

    @property
    def samvat(self):
        return f"Vikram Samvat {self.cal['vikram_samvat']}" if self.cal.get('vikram_samvat') else ''

    @property
    def festivals(self):
        return [f['name'] for f in self.cal.get('festivals', [])]

    @property
    def about(self):
        return next((f['about'] for f in self.cal.get('festivals', []) if f['about']), '')

    @property
    def notes(self):
        skip = re.compile(r'^\(?fast\)?$|^smart$|vruddhi|kshay', re.I)
        return [n for n in self.cal.get('notes', []) if not skip.search(n)]

    @property
    def place(self):
        return (self.close or self.act or {}).get('place', '')

    def path(self, x):
        return os.path.join(self.dir, x['file'])

    def happened(self, n=4):
        """What happened that day, from the photo captions: the ones that say what Bapa did, longest first."""
        seen, out = set(), []
        for c in sorted(self.captions, key=lambda c: -len(c)):
            k = re.sub(r'[^a-z ]', '', c.lower())[:40]
            if k in seen or len(c) < 18:
                continue
            seen.add(k)
            out.append(c[0].upper() + c[1:])
        return out[:n]


def history(date):
    """Other years on this date from the two Telegram history channels."""
    out = []
    for f in ('telegram/events.json', 'telegram/satpurush/events.json'):
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        for e in json.load(open(p, encoding='utf-8')):
            if e.get('date', '')[5:] == date.strftime('%m-%d') and e.get('line') and e['date'][:4] != str(date.year):
                out.append((int(e['date'][:4]), e['line'], e.get('place') or ''))
    return sorted(set(out))


# ---------------------------------------------------------------- day posters

def d1_leaf(day):
    """A tear off calendar leaf: the big date and the Indian date on the left, the darshan hung on the right."""
    img = paper((W, H))
    d = ImageDraw.Draw(img)
    # the calendar's tan band and the maroon weekday strip
    d.rectangle([0, 0, W, 190], fill=TAN)
    d.text((W / 2, 98), f"{day.date:%B %Y}  ·  {day.cal.get('lunar_months', '').replace('-', ' · ')}  ·  {day.samvat}",
           font=font('serif', 62), fill='white', anchor='mm')
    d.rectangle([0, 190, W, 262], fill=SUN_RED if day.date.weekday() == 6 else RUST)
    spaced(d, (W / 2, 226), day.date.strftime('%A').upper(), font('sans', 40), 'white', 14)
    # left column: the date as the calendar prints it
    lx = 120
    d.text((lx + 330, 640), str(day.date.day), font=font('serif-bold', 560), fill=SUN_RED if day.date.weekday() == 6 else MAROON, anchor='ms')
    d.line([lx, 730, lx + 660, 730], fill=GOLD_SOFT, width=4)
    d.text((lx + 330, 820), day.tithi, font=font('serif-bold', 78), fill=MAROON, anchor='mm')
    y = 900
    for fest in day.festivals[:2]:
        f = font('serif-bold', 62 if len(fest) < 26 else 50)
        lines = wrap(d, fest, f, 600, 3)
        bh = 40 + 70 * len(lines)
        d.rounded_rectangle([lx, y, lx + 660, y + bh], 22, fill=SAFFRON)
        for i, ln in enumerate(lines):
            d.text((lx + 330, y + 55 + 70 * i), ln, font=f, fill='white', anchor='mm')
        y += bh + 24
    if day.about:
        for ln in wrap(d, day.about, font('serif-med', 44), 640, 5):
            d.text((lx + 10, y + 30), ln, font=font('serif-med', 44), fill=GREY, anchor='lm'); y += 56
        y += 20
    for n in day.notes[:3]:
        d.text((lx + 10, y + 30), '•  ' + n, font=font('serif-med', 46), fill=INK, anchor='lm'); y += 62
    # right column: the darshan as one of the diary's ivory polaroids, the place on its band
    x = day.close or day.act
    px, py, pw, ph = 860, 330, 1160, 1380
    shadow(img, (px, py, px + pw, py + ph), r=10, blur=34, alpha=120, off=(0, 26))
    d.rectangle([px, py, px + pw, py + ph], fill=IVORY, outline=(214, 198, 168), width=2)
    if x:
        img.paste(crop(day.path(x), x['face'], pw - 80, ph - 220), (px + 40, py + 40))
    d.text((px + pw / 2, py + ph - 95), day.place or ' ', font=font('serif-bold', 70), fill=MAROON, anchor='mm')
    spaced(d, (px + pw / 2, py + ph - 38), 'WHERE BAPA WAS', font('sans', 26), GREY, 8)
    happenings(img, day, 1800)
    foot(img, H - 60, TAN_DARK)
    return img


def happenings(img, day, y, dark=False, x0=120, x1=W - 120):
    """The bottom: what happened that day (captions) and the same date in history (Telegram)."""
    d = ImageDraw.Draw(img)
    head, ink, sub = (GOLD, IVORY, GOLD_SOFT) if dark else (MAROON, INK, GREY)
    mid = (x0 + x1) / 2
    d.line([x0, y, x1, y], fill=GOLD_SOFT, width=3)
    spaced(d, (x0, y + 60), 'WHAT HAPPENED THAT DAY', font('sans', 34), head, 8, anchor='lm')
    spaced(d, (mid + 50, y + 60), 'ON THIS DATE IN HISTORY', font('sans', 34), head, 8, anchor='lm')
    f, fy = font('serif-med', 46), font('serif-bold', 46)
    yy = y + 130
    for c in day.happened(4):
        for i, ln in enumerate(wrap(d, c, f, mid - x0 - 80, 2)):
            d.text((x0 + (0 if i == 0 else 34), yy), ('•  ' if i == 0 else '') + ln, font=f, fill=ink, anchor='lm'); yy += 58
        yy += 14
    if not day.happened():
        d.text((x0, yy), 'No photos of Bapa saved for this day', font=f, fill=sub, anchor='lm')
    yy = y + 130
    for yr, line, place in day.history[:4]:
        d.text((mid + 50, yy), str(yr), font=fy, fill=head, anchor='lm')
        for i, ln in enumerate(wrap(d, line + (f' ({place})' if place and place not in line else ''), f, x1 - mid - 210, 2)):
            d.text((mid + 190, yy), ln, font=f, fill=ink, anchor='lm'); yy += 58
        yy += 14
    if not day.history:
        d.text((mid + 50, yy), 'Nothing in the Telegram channels for this date', font=f, fill=sub, anchor='lm')


def d2_cell(day):
    """One square of the baps.org calendar, blown up: the number and tithi in the corner, the darshan filling it."""
    img = paper((W, H))
    d = ImageDraw.Draw(img)
    d.text((110, 120), f'{day.date:%B %Y}', font=font('serif-bold', 110), fill=(181, 54, 28), anchor='lm')
    d.text((W - 110, 120), day.samvat, font=font('serif', 60), fill=GREY, anchor='rm')
    d.rectangle([110, 210, W - 110, 300], fill=TAN)
    d.text((W / 2, 255), f"{day.date:%B %Y}  {day.cal.get('lunar_months', '')}, {day.samvat}", font=font('serif', 56), fill='white', anchor='mm')
    sun = day.date.weekday() == 6
    d.rectangle([110, 300, W - 110, 380], fill=SUN_RED if sun else RUST)
    spaced(d, (W / 2, 340), day.date.strftime('%A').upper(), font('sans', 38), 'white', 14)
    cx0, cy0, cx1, cy1 = 110, 380, W - 110, 1820
    fill = EKADASHI if day.cal.get('ekadashi') else CELL
    d.rectangle([cx0, cy0, cx1, cy1], fill=fill, outline=LINE, width=3)
    x = day.close or day.act
    if x:
        ph = crop(day.path(x), x['face'], cx1 - cx0 - 640, cy1 - cy0 - 80, tight=False)
        img.paste(ph, (cx0 + 600, cy0 + 40))
    d.text((cx0 + 290, cy0 + 330), str(day.date.day), font=font('serif-bold', 360), fill=SUN_RED if sun else INK, anchor='ms')
    d.text((cx0 + 290, cy0 + 430), day.tithi.replace(' Sud ', '\nSud ').replace(' Vad ', '\nVad '), font=font('serif', 64),
           fill=GREY, anchor='mm', align='center')
    y = cy0 + 590
    for fest in day.festivals[:2]:
        for ln in wrap(d, fest, font('serif-bold', 56), 500, 4):
            d.text((cx0 + 290, y), ln, font=font('serif-bold', 56), fill=LINK, anchor='mm'); y += 66
        y += 20
    for n in day.notes[:3]:
        for ln in wrap(d, n, font('serif-med', 46), 500, 2):
            d.text((cx0 + 290, y), ln, font=font('serif-med', 46), fill=INK, anchor='mm'); y += 56
    if day.place:
        d.rounded_rectangle([cx0 + 60, cy1 - 170, cx0 + 520, cy1 - 70], 50, fill=MAROON)
        d.text((cx0 + 290, cy1 - 120), '📍 ' * 0 + day.place, font=font('serif-bold', 58), fill=GOLD, anchor='mm')
    happenings(img, day, 1900)
    foot(img, H - 60, TAN_DARK)
    return img


def d3_maroon(day):
    """Bapa's Diary's maroon and gold, with the calendar's facts set like a temple calendar's header."""
    img = maroon_bg((W, H))
    d = ImageDraw.Draw(img)
    x = day.close or day.act
    ph_w, ph_h = 1500, 1500
    px, py = (W - ph_w) // 2, 560
    if x:
        photo = crop(day.path(x), x['face'], ph_w, ph_h)
        m = Image.new('L', (ph_w, ph_h), 0)
        ImageDraw.Draw(m).ellipse([0, 0, ph_w, ph_h], fill=255)
        ring = 26
        d.ellipse([px - ring, py - ring, px + ph_w + ring, py + ph_h + ring], fill=GOLD)
        d.ellipse([px - 8, py - 8, px + ph_w + 8, py + ph_h + 8], fill=MAROON_DEEP)
        img.paste(photo, (px, py), m)
    sun = day.date.weekday() == 6
    spaced(d, (W / 2, 110), f'{day.date:%A}'.upper(), font('sans', 40), GOLD_SOFT, 16)
    d.text((W / 2, 300), f'{day.date.day} {day.date:%B %Y}', font=font('serif-bold', 170), fill=GOLD, anchor='ms')
    d.text((W / 2, 400), f'{day.tithi}  ·  {day.samvat}', font=font('serif', 70), fill=IVORY, anchor='mm')
    if day.festivals:
        f = font('serif-bold', 64)
        t = '  ·  '.join(day.festivals[:2])
        tw = min(d.textlength(t, font=f), 1800)
        d.rounded_rectangle([W / 2 - tw / 2 - 50, 450, W / 2 + tw / 2 + 50, 540], 45, fill=SAFFRON)
        d.text((W / 2, 495), wrap(d, t, f, 1800, 1)[0], font=f, fill='white', anchor='mm')
    if day.place:
        f = font('serif-bold', 66)
        tw = d.textlength(day.place, font=f)
        d.rounded_rectangle([W / 2 - tw / 2 - 60, py + ph_h - 40, W / 2 + tw / 2 + 60, py + ph_h + 70], 55, fill=IVORY)
        d.text((W / 2, py + ph_h + 15), day.place, font=f, fill=MAROON, anchor='mm')
    happenings(img, day, 2170, dark=True)
    foot(img, H - 50, GOLD_SOFT)
    return img


# ---------------------------------------------------------------- month posters

def month_grid(cal, photos, y, m, style):
    """The BAPS month grid with a box for every day; a day with a photo shows it, a day without stays plain."""
    img = paper((W, H)) if style == 'baps' else maroon_bg((W, H))
    d = ImageDraw.Draw(img)
    first = cal[f'{y}-{m:02d}-01']
    last = cal[f'{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}']
    lunar = first['lunar_months'] if first['lunar_months'] == last['lunar_months'] else f"{first['lunar_months']}"
    title = f'{calendar.month_name[m]} {y}'
    if style == 'baps':
        d.text((90, 115), title, font=font('serif-bold', 120), fill=(181, 54, 28), anchor='lm')
        d.text((W - 90, 115), 'Bapa’s Diary', font=font('serif-bold', 64), fill=TAN_DARK, anchor='rm')
        d.rectangle([90, 200, W - 90, 290], fill=TAN)
        d.text((W / 2, 245), f"{title}  {lunar.replace('-', ' · ')},  Vikram Samvat {first['vikram_samvat']}", font=font('serif', 58), fill='white', anchor='mm')
        top = 290
    else:
        d.text((W / 2, 170), title, font=font('serif-bold', 170), fill=GOLD, anchor='ms')
        d.text((W / 2, 250), f"{lunar.replace('-', ' · ')}  ·  Vikram Samvat {first['vikram_samvat']}", font=font('serif', 62), fill=IVORY, anchor='mm')
        top = 300
    gx0, gx1 = 90, W - 90
    cw = (gx1 - gx0) / 7
    for i, wd in enumerate(['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']):
        if style == 'baps':
            d.rectangle([gx0 + i * cw, top, gx0 + (i + 1) * cw, top + 76], fill=SUN_RED if i == 0 else RUST, outline=CELL, width=2)
            spaced(d, (gx0 + (i + .5) * cw, top + 38), wd, font('sans', 34), 'white', 8)
        else:
            spaced(d, (gx0 + (i + .5) * cw, top + 38), wd, font('sans', 34), GOLD if i else (255, 150, 120), 8)
    start = (datetime.date(y, m, 1).weekday() + 1) % 7      # Sunday first, like baps.org
    nd = calendar.monthrange(y, m)[1]
    rows = (start + nd + 6) // 7
    gy0, gy1 = top + 90, H - 150
    ch = (gy1 - gy0) / rows
    pad = 8
    for d_ in range(1, nd + 1):
        k = start + d_ - 1
        r, c = divmod(k, 7)
        x0, y0 = gx0 + c * cw + pad, gy0 + r * ch + pad
        x1, y1 = x0 + cw - 2 * pad, y0 + ch - 2 * pad
        info = cal[f'{y}-{m:02d}-{d_:02d}']
        ph = photos['close'].get(str(d_))
        fest = info['festivals'][0]['name'] if info['festivals'] else ''
        sun = c == 0
        strip = 92
        if style == 'baps':
            bg = EKADASHI if info['ekadashi'] else AMAS if info['amas'] else CELL
            d.rectangle([x0, y0, x1, y1], fill=bg, outline=LINE, width=2)
        else:
            d.rounded_rectangle([x0, y0, x1, y1], 18, fill=(70, 16, 24) if not ph else IVORY)
        if ph:
            # a festival day shows the activity photo when there is one, like baps.org shows a picture for it
            pick = photos['act'].get(str(d_)) if fest and photos['act'].get(str(d_)) else ph
            pic = crop(os.path.join(photos['dir'], pick['file']), pick['face'], x1 - x0 - (0 if style == 'baps' else 12),
                       y1 - y0 - strip - (0 if style == 'baps' else 6), tight=pick is ph)
            if style == 'baps':
                img.paste(pic, (round(x0), round(y0)))
            else:
                rounded(img, pic, (round(x0 + 6), round(y0 + 6)), 14)
            nf = font('serif-bold', 60)
            tx, ty = x0 + 18, y0 + 48
            for o in ((2, 2), (-1, -1), (2, -1), (-1, 2)):
                d.text((tx + o[0], ty + o[1]), str(d_), font=nf, fill=(0, 0, 0), anchor='lm')
            d.text((tx, ty), str(d_), font=nf, fill='white', anchor='lm')
        else:
            d.text((x0 + 18, y0 + 50), str(d_), font=font('serif-bold', 72),
                   fill=(SUN_RED if sun else INK) if style == 'baps' else ((255, 150, 120) if sun else GOLD_SOFT), anchor='lm')
        # the strip under the photo: the tithi, and the festival in the calendar's blue
        sy = y1 - strip
        if style == 'baps':
            d.rectangle([x0, sy, x1, y1], fill=bg)
        tcol = GREY if style == 'baps' else ((150, 120, 100) if ph else IVORY)
        tithi = info['indian_date'].split(' ', 1)[-1] if d_ > 1 and not info['indian_date'].startswith(('Adhik',)) and \
            info['month'] == cal.get(f'{y}-{m:02d}-{d_ - 1:02d}', {}).get('month') else info['indian_date']
        d.text(((x0 + x1) / 2, sy + (28 if fest else 46)), tithi, font=font('serif-med', 36 if len(tithi) < 16 else 30), fill=tcol, anchor='mm')
        if fest:
            short = re.sub(r'\s*\(.*?\)', '', fest)
            if len(short) > 18 and ',' in short:
                short = short.rsplit(',', 1)[1].strip()
            d.text(((x0 + x1) / 2, sy + 66), wrap(d, short, font('serif-bold', 34), x1 - x0 - 16, 1)[0], font=font('serif-bold', 34),
                   fill=LINK if style == 'baps' else SAFFRON, anchor='mm')
    places = photos.get('places') or []
    if places:
        d.text((W / 2, H - 112), 'Bapa was in ' + ', '.join(places[:4]), font=font('serif-bold', 50),
               fill=MAROON if style == 'baps' else GOLD, anchor='mm')
    foot(img, H - 50, TAN_DARK if style == 'baps' else GOLD_SOFT)
    return img


def m4_wide(cal, photos, y, m, S=2):
    """The month as baps.org draws it, 16:9 (Darpan, 23 Oct 2026: closer to the BAPS calendar): the tan band, the
    weekday row, white boxes with a thin number and the Indian date under it. A day with a photo shows it the way
    baps.org shows a festival picture, with the Indian date on a pale fade at the bottom. Sizes are in 1920 x 1080 units."""
    img = Image.new('RGB', (1920 * S, 1080 * S), (247, 241, 230))
    d = ImageDraw.Draw(img)
    s = lambda *v: [round(x * S) for x in v]
    first = cal[f'{y}-{m:02d}-01']
    band = f"{calendar.month_name[m]} {y} {first['lunar_months']}, Vikram Samvat {first['vikram_samvat']}"
    d.rectangle(s(30, 20, 1890, 80), fill=(214, 186, 144))
    d.text(s(1866, 51), band, font=font('light', 40 * S), fill='white', anchor='rm')
    d.text(s(56, 52), 'Bapa’s Diary', font=font('serif', 36 * S), fill='white', anchor='lm')
    cw = 1860 / 7
    for i, wd in enumerate(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']):
        d.rectangle(s(30 + i * cw, 92, 30 + (i + 1) * cw, 130), fill=(140, 24, 20) if i == 0 else (166, 86, 40))
        if i:
            d.line(s(30 + i * cw, 92, 30 + i * cw, 130), fill=(196, 132, 92), width=S)
        d.text(s(30 + (i + .5) * cw, 111), wd, font=font('regular', 22 * S), fill='white', anchor='mm')
    start = (datetime.date(y, m, 1).weekday() + 1) % 7
    nd = calendar.monthrange(y, m)[1]
    rows = (start + nd + 6) // 7
    gy0, gy1 = 140, 1036
    ch = (gy1 - gy0) / rows
    gap = 9
    prev_month = None
    for k in range(rows * 7):
        r, c = divmod(k, 7)
        x0, y0 = 30 + c * cw + gap / 2, gy0 + r * ch + gap / 2
        x1, y1 = x0 + cw - gap, y0 + ch - gap
        box = s(x0, y0, x1, y1)
        dn = k - start + 1
        if not 1 <= dn <= nd:
            d.rounded_rectangle(box, 4 * S, fill='white', outline=(228, 220, 206), width=S)
            continue
        info = cal[f'{y}-{m:02d}-{dn:02d}']
        bg = (252, 241, 206) if info['ekadashi'] else (190, 190, 190) if info['amas'] else (255, 255, 255)
        shadow(img, box, r=4 * S, blur=3 * S, alpha=40, off=(0, S))
        d.rounded_rectangle(box, 4 * S, fill=bg, outline=(228, 220, 206) if bg[0] == 255 else None, width=S)
        tithi = info['indian_date'] if info['month'] != prev_month else info['indian_date'].split(' ', 1)[-1]
        prev_month = info['month']
        fests = [re.sub(r'\s*\(.*?\)', '', f['name']) for f in info['festivals']]
        notes = [n for n in info['notes'] if not re.search(r'^smart$', n, re.I)]
        red = c == 0
        ph = photos['close'].get(str(dn))
        if ph:
            pick = photos['act'].get(str(dn)) if fests and photos['act'].get(str(dn)) else ph
            w, h = box[2] - box[0], box[3] - box[1]
            pic = crop(os.path.join(photos['dir'], pick['file']), pick['face'], w, h, tight=pick is ph)
            # the pale fade at the bottom, as on baps.org's picture days
            fade_h = round(h * (.42 if fests else .3))
            g = Image.linear_gradient('L').resize((w, fade_h)).point(lambda v: min(255, v * 1.6))
            mask = Image.new('L', (w, h), 0)
            mask.paste(g, (0, h - fade_h))
            pic = Image.composite(Image.new('RGB', (w, h), bg), pic, mask)
            rounded(img, pic, (box[0], box[1]), 4 * S)
            short = [f.rsplit(',', 1)[1].strip() if len(f) > 24 and ',' in f else f for f in fests[:1]]
            lines = [(tithi, font('regular', 17 * S), (60, 60, 64))] + [(f, font('medium', 17 * S), (36, 64, 130)) for f in short]
            ty = y1 - 12 - 22 * (len(lines) - 1)
            for t, f, col in lines:
                t = wrap(d, t, f, (x1 - x0 - 12) * S, 1)[0]
                d.text(s((x0 + x1) / 2, ty), t, font=f, fill=col, anchor='mm')
                ty += 22
            # the date in a small white chip, top left
            nf = font('regular', 26 * S)
            tw = d.textlength(str(dn), font=nf) / S
            chip = Image.new('RGBA', img.size, (0, 0, 0, 0))
            ImageDraw.Draw(chip).rounded_rectangle(s(x0 + 6, y0 + 6, x0 + 18 + tw, y0 + 40), 6 * S, fill=(255, 255, 255, 225))
            img.paste(chip, (0, 0), chip)
            d.text(s(x0 + 12 + tw / 2, y0 + 23), str(dn), font=nf, fill=(214, 40, 30) if red else (50, 50, 54), anchor='mm')
        else:
            big = min(58, ch * .36)
            d.text(s((x0 + x1) / 2, y0 + 10 + big * .62), str(dn), font=font('light', big * S),
                   fill=(214, 40, 30) if red else (50, 50, 54), anchor='mm')
            ty = y0 + 22 + big * 1.25
            f = font('regular', 16 * S)
            for t in ([tithi] + fests + notes):
                for line in wrap(d, t, f, (x1 - x0 - 14) * S, 2):
                    if ty > y1 - 10:
                        break
                    d.text(s((x0 + x1) / 2, ty), line, font=f, fill=(40, 40, 44), anchor='mm')
                    ty += 21
    places = photos.get('places') or []
    where = ('Bapa was in ' + ', '.join(places[:4]) + '   ·   ') if places else ''
    d.text(s(960, 1058), where + FOOTER, font=font('serif', 26 * S), fill=(150, 112, 76), anchor='mm')
    return img


def m4_mix(cal, photos, y, m, kind):
    """The BAPS calendar grid in the M4 month card's look (Darpan, 23 Oct 2026): the diary's maroon, the month and
    where Bapa was across the top, one ivory card per day hanging on a cord per week, every day with its Indian date.
    Each photo is shown whole in a 4:3 frame (never cut). kind 'close' shows the close darshans, 'act' the activities
    with their captions, 'mixed' the day's special moment or else its darshan (his pick). 16:9, 3840 x 2160."""
    import month as mc, make
    W2, H2 = 3840, 2160
    img = mc.canvas((W2, H2), glow=.45, jali=.08)
    d = ImageDraw.Draw(img)
    first = cal[f'{y}-{m:02d}-01']
    M = 110
    # the top line: the month on the left, where Bapa was on the right, both large
    tf = make.garamond(118, 700)
    make.gold_text(img, (M, 22), f'{calendar.month_name[m]} {y}', tf)
    sf = make.garamond(30, 600)
    sub = f"{first['lunar_months'].replace('-', ' · ')}  ·  Vikram Samvat {first['vikram_samvat']}".upper()
    make.draw_spaced(d, M + 4, 168, sub, sf, 6, mc.CREAM)
    places = [re.sub(r',\s*India$', '', p) for p in (photos.get('places') or [])]
    seen = [re.sub(r',\s*India$', '', v.get('place', '')) for _, v in sorted(photos['close'].items(), key=lambda kv: int(kv[0]))]
    places.sort(key=lambda p: seen.index(p) if p in seen else 99)      # in the order he went
    if places:
        where = 'Bapa was in ' + (places[0] if len(places) == 1 else ', '.join(places[:-1]) + ' and ' + places[-1])
        size = 96
        while size > 50 and d.textlength(where, font=make.garamond(size, 700)) > W2 / 2 - M - 40:
            size -= 4
        wf = make.garamond(size, 700)
        make.gold_text(img, (W2 - M - d.textlength(where, font=wf), 22 + (118 - size) * .7), where, wf)
    cw = (W2 - 2 * M) / 7
    for i, wd in enumerate(['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']):
        f = make.arimo_bold(24)
        sw = make.spaced(d, wd, f, 7)
        make.draw_spaced(d, M + (i + .5) * cw - sw / 2, 232, wd, f, 7, (255, 160, 130) if i == 0 else mc.CREAM)
    start = (datetime.date(y, m, 1).weekday() + 1) % 7
    nd = calendar.monthrange(y, m)[1]
    rows = 5            # a sixth week goes into the first week's empty boxes, as printed calendars do
    gy0, gy1 = 272, H2 - 18
    rh = (gy1 - gy0) / rows
    border = 11
    band = 104 if kind != 'close' else 74
    card_h = rh - 22
    ph = round(card_h - border - band)
    card_w = round(cw * .92)
    pw = card_w - 2 * border          # the photo sits whole and centred in this window, on the card's ivory
    rnd = random.Random(7)
    prev_month = None
    for r in range(rows):
        cy = gy0 + r * rh + 8
        mc.rope(img, mc.sag(M - 40, W2 - M + 40, cy, 80, 12), 6)
        for c in range(7):
            dn = r * 7 + c - start + 1
            if r == 0 and dn < 1 and dn + 35 <= nd:
                dn += 35
            if not 1 <= dn <= nd:
                continue
            info = cal[f'{y}-{m:02d}-{dn:02d}']
            tithi = info['indian_date'] if info['month'] != prev_month else info['indian_date'].split(' ', 1)[-1]
            prev_month = info['month']
            fest = [re.sub(r'\s*\(.*?\)', '', f['name']) for f in info['festivals']]
            fest = [f.rsplit(',', 1)[1].strip() if len(f) > 26 and ',' in f else f for f in fest]
            close, act = photos['close'].get(str(dn)), photos['act'].get(str(dn))
            if kind == 'close':
                x = close
            elif kind == 'act':
                x = act or close
            else:
                x = act if act and act.get('special') and act.get('s_act', 0) >= 2 else close
            show_cap = x is not None and kind != 'close' and (x is act or kind == 'act')
            card = mc.ivory(card_w, card_h).convert('RGBA')
            cd = ImageDraw.Draw(card)
            cd.rectangle((0, 0, card.width - 1, card.height - 1), outline=mc.IVORY_EDGE, width=2)
            if x:
                # the whole photo, fitted inside the window, never cut
                im = Image.open(os.path.join(photos['dir'], x['file'])).convert('RGB')
                im = make.polish(ImageOps.contain(im, (pw, ph), Image.LANCZOS))
                fx, fy = border + (pw - im.width) // 2, border + (ph - im.height) // 2
                card.paste(im, (fx, fy))
                frame = (fx, fy, fx + im.width, fy + im.height)
            else:
                frame = (border + (pw - ph * 4 / 3) / 2, border, border + (pw + ph * 4 / 3) / 2, border + ph)
                cd.rectangle(frame, fill=(232, 220, 198))
                make.diamond(cd, card.width / 2, border + ph / 2, 10, (200, 176, 136))
            cd.rectangle((frame[0] - 1, frame[1] - 1, frame[2], frame[3]), outline=(150, 130, 100), width=2)
            # under the photo: the date and the Indian date, then the festival (saffron) and the caption, smaller
            by = border + ph
            nf, tf2 = make.garamond(40, 700), make.garamond(28, 600)
            num = str(dn)
            nw, tw = cd.textlength(num, font=nf), cd.textlength(tithi, font=tf2)
            x0 = (card.width - nw - 12 - tw) / 2
            cd.text((x0, by + 40), num, font=nf, fill=(170, 34, 34) if c == 0 else MAROON, anchor='ls')
            cd.text((x0 + nw + 12, by + 39), tithi, font=tf2, fill=(110, 70, 56), anchor='ls')
            lines = []
            if fest:
                lines.append((fest[0], make.garamond(24, 700), (196, 96, 22)))
            if show_cap and x.get('caption'):
                cf = make.garamond(22, 500)
                for t in wrap(cd, x['caption'], cf, card.width - 2 * border - 4, 2 - len(lines)):
                    lines.append((t, cf, (88, 34, 34)))
            ly = by + 66
            for t, f, col in lines[:2 if kind != 'close' else 1]:
                cd.text((card.width / 2, ly), t, font=f, fill=col, anchor='ms')
                ly += 25
            card = card.rotate(rnd.uniform(-1, 1), Image.BICUBIC, expand=True)
            cx = M + (c + .5) * cw
            dip = cy + 12 * math.sin(math.pi * (cx - M + 40) / (W2 - 2 * M + 80))
            mc.drop_card(img, card, cx, dip + card.height / 2 - 4)
            mc.peg(img, cx, dip, 1.0)
    return img


ASPECT = 3 / 2      # every day's photo window: one fixed landscape shape (the brief suggests 4:3; 3:2 gives captions room)
SPELLING = {'asembly': 'assembly', 'Swamianrayan': 'Swaminarayan', 'Swaminaryan': 'Swaminarayan', 'blesess': 'blesses',
            'Swamsihri': 'Swamishri'}
VERBS = r'(?:bids|blesses|performs|reads|greets|offers|meets|honours|honors|sanctifies|inaugurates|lights|applies|listens|watches)'


def clean_caption(c):
    """The brief's caption fixes the website's text still needs: spelling slips, the name left in when it was misspelt,
    and two captions run together ('Reads Shikshapatri bids Jai Swaminarayan to all': only the first is kept)."""
    for a_, b_ in SPELLING.items():
        c = re.sub(rf'\b{a_}\b', b_, c)
    c = re.sub(r'^Swamishri\s+(\w)', lambda m: m.group(1).upper(), c)
    parts = re.split(rf'(?<!\band)(?<!\bwho)(?<!,) (?={VERBS}\b)', c, maxsplit=1)
    if len(parts) == 2 and len(parts[0].split()) >= 2:
        c = parts[0]
    return c
ROUTINE = re.compile(r'(?i)\b(puja|tilak|mala|discourse|assembly|meditation|reads?|listens|light moment|greets|welcome|darshan)\b')
NOT_FESTIVAL = re.compile(r'^\(?fast\)?$|^smart$|vruddhi|kshay|shraddh|\b(sud|vad)\b', re.I)   # a note that only repeats a tithi is not a festival


def head_fits(x, w, h, mode):
    """The crop window make.crop_to would use for this photo in a w x h frame, or None when Bapa's whole head
    would not fit in it (make.crop_to then shows the whole photo on a blurred fill, which the calendar never does)."""
    iw, ih = x['size']
    fx, fy, fw, fh = x['face']
    cw, ch = (ih * w / h, ih) if iw / ih > w / h else (iw, iw * h / w)
    if mode == 'close':
        ch = min(ch, fh / (.38 if w > h else .30)); cw = min(cw, ch * w / h); ch = cw * h / w
    # 'snug' (a tight portrait in a wide frame): the whole head and chin, the neck may go
    head = (fx - .35 * fw, fy - .5 * fh, fx + 1.35 * fw, fy + (1.15 if mode == 'snug' else 1.4) * fh)
    if mode == 'top':   # last resort, a face too big for the window: keep the top of his head, let the chin go
        x0 = min(max(0, fx + fw / 2 - cw / 2), iw - cw); y0 = min(max(0, head[1] - ch * .04), ih - ch)
        return x0, y0, x0 + cw, y0 + ch
    if head[3] - head[1] > ch * .98 or head[2] - head[0] > cw * .98:
        return None
    x0, y0 = fx + fw / 2 - cw / 2, fy + fh / 2 - ch * ((.42 if h >= w else .36) if mode == 'close' else .38)
    y0 = max(y0, head[3] - ch); y0 = min(y0, head[1])
    y0 = max(y0, head[1] - ch * (.07 if mode == 'close' else .14))
    x0 = min(max(0, x0), iw - cw); y0 = min(max(0, y0), ih - ch)
    return x0, y0, x0 + cw, y0 + ch


def pick_month(photos, aspect):
    """One photo a day by the design brief (23 Oct 2026): a close darshan, or an action shot only when the moment is
    special and really nice; special days are picked first; no photo twice, and the same moment (album and caption)
    or the same caption on another day loses; a photo whose crop would cut Bapa's head is passed over."""
    import make
    cands = {int(k): v for k, v in photos.get('cands', {}).items()}
    nice = lambda x: (x.get('special') and x['s_act'] >= 2 and x.get('subject') and not x.get('unsure')
                      and not make.EVERYDAY.search(x.get('caption') or '') and not ROUTINE.search(x.get('caption') or '') and not make.GUEST.search(x.get('caption') or ''))
    order = sorted(cands, key=lambda d: (-max([x['s_act'] for x in cands[d] if nice(x)] or [-9]), d))
    chosen, used = {}, set()
    for d in order:
        best = None
        for x in cands[d]:
            if x['url'] in used:
                continue
            act = nice(x)
            modes = (['frame', 'snug'] if act or x.get('unsure') else ['close', 'frame', 'snug']) + ['top']
            mode = next((m for m in modes if head_fits(x, aspect, 1, m)), None)
            if not mode:
                continue
            score = (x['s_act'] if act else x['s_close'] - (0 if mode == 'close' else .5)) - {'snug': .3, 'top': 1}.get(mode, 0)
            score -= 6 if x.get('unsure') and x.get('sim', 0) < .35 else 0     # a murti or someone else: only when nothing has Bapa
            k = make.caption_key(x['caption'])
            for c in chosen.values():
                if make.same_caption(k, make.caption_key(c['caption'])):
                    score -= 3 if c.get('album') == x.get('album') else 1.5
            if best is None or score > best[0]:
                best = (score, x, act, mode)
        if best:
            chosen[d] = dict(best[1], kind='act' if best[2] else 'close', mode=best[3])
            used.add(best[1]['url'])
    return chosen


def fitted(d, text, maxw, lines=2):
    """The caption on at most `lines` lines: whole, then a little smaller (90%, then 82%), then said shorter at a
    natural break. Never trails off."""
    import make
    for size in (22, 20, 18):
        f = make.garamond(size, 500)
        out = make.wrap(d, text, f, maxw, lines, shorten=False)
        if not out[-1].endswith('…'):
            return out, f
    for least in (math.ceil(len(text.split()) * 2 / 3), 0):    # keep at least two thirds of it if that can fit
        out = make.wrap(d, text, f, maxw, lines, min_words=least)
        if not out[-1].endswith('…'):
            return out, f
    out[-1] = out[-1].rstrip('…').rstrip(' ,;:')
    return out, f


def m6_calendar(cal, photos, y, m):
    """The month calendar by Darpan's design brief (23 Oct 2026): the M4 look (maroon, gold, ivory cards on a cord
    per week), the month on the left and where Bapa was on the right, every photo window the same 3:2 size and filled
    with a head aware crop, a caption on every card, the tithi and festival on every day, and the first week's empty
    boxes used for where Bapa went that month. 16:9, 3840 x 2160."""
    import month as mc, make
    W2, H2 = 3840, 2160
    img = mc.canvas((W2, H2), glow=.45, jali=.08)
    d = ImageDraw.Draw(img)
    nd = calendar.monthrange(y, m)[1]
    first = cal[f'{y}-{m:02d}-01']
    picks = pick_month(photos, ASPECT)
    # where he went, in order: runs of days in one place
    runs = []
    for dn in range(1, nd + 1):
        pl = re.sub(r',\s*India$', '', (picks.get(dn) or {}).get('place', ''))
        if not pl:
            continue
        if runs and runs[-1][0] == pl:
            runs[-1][2] = dn
        else:
            runs.append([pl, dn, dn])
    places = list(dict.fromkeys(r[0] for r in runs))
    M = 110
    tf = make.garamond(118, 700)
    make.gold_text(img, (M, 22), f'{calendar.month_name[m]} {y}', tf)
    sub = f"{first['lunar_months'].replace('-', ' · ')}  ·  Vikram Samvat {first['vikram_samvat']}".upper()
    make.draw_spaced(d, M + 4, 168, sub, make.garamond(30, 600), 6, mc.CREAM)
    if places:
        where = 'Bapa was in ' + (places[0] if len(places) == 1 else ', '.join(places[:-1]) + ' and ' + places[-1])
        size = 96
        while size > 50 and d.textlength(where, font=make.garamond(size, 700)) > W2 / 2 - M - 40:
            size -= 4
        wf = make.garamond(size, 700)
        make.gold_text(img, (W2 - M - d.textlength(where, font=wf), 22 + (118 - size) * .7), where, wf)
    cw = (W2 - 2 * M) / 7
    for i, wd in enumerate(['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']):
        f = make.arimo_bold(24)
        make.draw_spaced(d, M + (i + .5) * cw - make.spaced(d, wd, f, 7) / 2, 232, wd, f, 7, (255, 160, 130) if i == 0 else mc.CREAM)
    start = (datetime.date(y, m, 1).weekday() + 1) % 7
    rows = 5
    gy0, gy1 = 272, H2 - 18
    rh = (gy1 - gy0) / rows
    border, band = 11, 114
    card_h = rh - 22
    ph = round(card_h - border - band)
    pw = round(ph * ASPECT)
    card_w = pw + 2 * border
    rnd = random.Random(7)
    wrapped = [dn for dn in range(36 - start, nd + 1)] if start + nd > 35 else []
    empty = [c for c in range(start) if c >= len(wrapped)]           # first week boxes with no day in them
    prev_month = None
    for r in range(rows):
        cy = gy0 + r * rh + 8
        mc.rope(img, mc.sag(M - 40, W2 - M + 40, cy, 80, 12), 6)
        if r == 0 and len(empty) >= 2:   # where Bapa went that month, on a note hung across the empty boxes
            x0n, x1n = M + empty[0] * cw + 24, M + (empty[-1] + 1) * cw - 24
            note = mc.ivory(x1n - x0n, card_h).convert('RGBA')
            nd_ = ImageDraw.Draw(note)
            nd_.rectangle((0, 0, note.width - 1, note.height - 1), outline=mc.IVORY_EDGE, width=2)
            hf = make.arimo_bold(24)
            make.draw_spaced(nd_, (note.width - make.spaced(nd_, 'WHERE BAPA WAS', hf, 7)) / 2, 48, 'WHERE BAPA WAS', hf, 7, (150, 104, 60))
            lf, df = make.garamond(44, 700), make.garamond(32, 600)
            ly = 120
            step = min(70, (note.height - 130) / max(1, len(runs)))
            for pl, a, b in runs[:6]:
                when = f'{a} {calendar.month_name[m]}' if a == b else f'{a} to {b} {calendar.month_name[m]}'
                tw = nd_.textlength(pl, font=lf) + 24 + nd_.textlength(when, font=df)
                xx = (note.width - tw) / 2
                nd_.text((xx, ly), pl, font=lf, fill=MAROON, anchor='ls')
                nd_.text((xx + nd_.textlength(pl, font=lf) + 24, ly), when, font=df, fill=(110, 70, 56), anchor='ls')
                ly += step
            mc.drop_card(img, note, (x0n + x1n) / 2, cy + 6 + note.height / 2 - 4)
            for px in (x0n + 60, x1n - 60):
                mc.peg(img, px, cy + 12 * math.sin(math.pi * (px - M + 40) / (W2 - 2 * M + 80)), 1.0)
        for c in range(7):
            dn = r * 7 + c - start + 1
            extra = False
            if r == 0 and dn < 1 and c < len(wrapped):
                dn, extra = wrapped[c], True
            if not 1 <= dn <= nd:
                continue
            info = cal[f'{y}-{m:02d}-{dn:02d}']
            tithi = info['indian_date'] if info['month'] != prev_month or extra else info['indian_date'].split(' ', 1)[-1]
            if not extra:
                prev_month = info['month']
            fest = [re.sub(r'\s*\(.*?\)', '', f['name']) for f in info['festivals']] + \
                   [n for n in info['notes'] if not NOT_FESTIVAL.search(n)]
            fest = [f.rsplit(',', 1)[1].strip() if len(f) > 26 and ',' in f else f for f in fest]
            x = picks.get(dn)
            card = mc.ivory(card_w, card_h).convert('RGBA')
            cd = ImageDraw.Draw(card)
            cd.rectangle((0, 0, card.width - 1, card.height - 1), outline=mc.IVORY_EDGE, width=2)
            if x:
                im = Image.open(os.path.join(photos['dir'], x['file'])).convert('RGB')
                box = head_fits(x, ASPECT, 1, x['mode'])
                card.paste(make.polish(im.crop(box).resize((pw, ph), Image.LANCZOS)), (border, border))
            else:
                cd.rectangle((border, border, border + pw, border + ph), fill=(232, 220, 198))
                make.diamond(cd, card.width / 2, border + ph / 2, 10, (200, 176, 136))
            cd.rectangle((border - 1, border - 1, border + pw, border + ph), outline=(150, 130, 100), width=2)
            by = border + ph
            nf, tf2 = make.garamond(40, 700), make.garamond(28, 600)
            num = f'{dn} {calendar.month_abbr[m]}' if extra else str(dn)
            nw, tw = cd.textlength(num, font=nf), cd.textlength(tithi, font=tf2)
            x0 = (card.width - nw - 12 - tw) / 2
            cd.text((x0, by + 38), num, font=nf, fill=(170, 34, 34) if c == 0 else MAROON, anchor='ls')
            cd.text((x0 + nw + 12, by + 37), tithi, font=tf2, fill=(110, 70, 56), anchor='ls')
            ly = by + 62
            if fest:
                cd.text((card.width / 2, ly), wrap(cd, fest[0], make.garamond(24, 700), card.width - 2 * border, 1)[0],
                        font=make.garamond(24, 700), fill=(176, 40, 30), anchor='ms')
                ly += 24
            if x and x.get('caption'):
                cap = clean_caption(x['caption'])
                lines, cf = fitted(cd, cap, card.width - 2 * border - 4, 2)
                for t in lines:
                    cd.text((card.width / 2, ly), t, font=cf, fill=(88, 34, 34), anchor='ms')
                    ly += 22
            if extra:   # the month's last days, carried into the first week's empty boxes, sit back a little
                card.putalpha(card.split()[3].point(lambda v: v * 4 // 5))
            card = card.rotate(rnd.uniform(-1, 1), Image.BICUBIC, expand=True)
            cx = M + (c + .5) * cw
            dip = cy + 12 * math.sin(math.pi * (cx - M + 40) / (W2 - 2 * M + 80))
            mc.drop_card(img, card, cx, dip + card.height / 2 - 4)
            mc.peg(img, cx, dip, 1.0)
    img.info['picks'] = picks
    return img


def m3_special(cal, photos, y, m):
    """The second card: the month's special moments, each with its date and Indian date."""
    img = paper((W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 330], fill=MAROON)
    spaced(d, (W / 2, 95), 'SPECIAL MOMENTS', font('sans', 46), GOLD_SOFT, 18)
    d.text((W / 2, 250), f'{calendar.month_name[m]} {y}', font=font('serif-bold', 150), fill=GOLD, anchor='ms')
    hl, seen = [], set()
    for x in photos['highlights']:
        if x['day'] in seen:
            continue
        seen.add(x['day']); hl.append(x)
        if len(hl) == 6:
            break
    hl.sort(key=lambda x: x['day'])
    cols, gap = 2, 50
    cw = (W - 2 * 100 - gap) / cols
    chh = (H - 330 - 160 - 2 * gap) / 3
    for i, x in enumerate(hl):
        r, c = divmod(i, cols)
        x0, y0 = 100 + c * (cw + gap), 390 + r * (chh + gap)
        shadow(img, (x0, y0, x0 + cw, y0 + chh), r=8, blur=20, alpha=90, off=(0, 12))
        d.rectangle([x0, y0, x0 + cw, y0 + chh], fill=IVORY, outline=(214, 198, 168), width=2)
        pic = crop(os.path.join(photos['dir'], x['file']), x['face'], cw - 40, chh - 230, tight=False)
        img.paste(pic, (round(x0 + 20), round(y0 + 20)))
        info = cal[x['date']]
        fest = info['festivals'][0]['name'] if info['festivals'] else ''
        date = datetime.date.fromisoformat(x['date'])
        d.text((x0 + 30, y0 + chh - 170), f'{date.day} {date:%B}', font=font('serif-bold', 54), fill=MAROON, anchor='lm')
        d.text((x0 + cw - 30, y0 + chh - 170), info['indian_date'], font=font('serif', 40), fill=GREY, anchor='rm')
        line = x['caption'][0].upper() + x['caption'][1:]
        for j, ln in enumerate(wrap(d, (fest + ': ' if fest else '') + line, font('serif-med', 40), cw - 60, 2)):
            d.text((x0 + 30, y0 + chh - 105 + 50 * j), ln, font=font('serif-med', 40), fill=INK, anchor='lm')
    foot(img, H - 60, TAN_DARK)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', default='2012-01')
    ap.add_argument('--day', type=int, default=9)
    a = ap.parse_args()
    y, m = map(int, a.month.split('-'))
    folder = os.path.join(HERE, 'preview', 'poster', a.month)
    photos = json.load(open(os.path.join(folder, 'photos.json'), encoding='utf-8'))
    photos['dir'] = folder
    photos['close'] = {str(k): v for k, v in photos['close'].items()}
    photos['act'] = {str(k): v for k, v in photos['act'].items()}
    photos['extra'] = {str(k): v for k, v in photos['extra'].items()}
    cal = {x['date']: x for x in json.load(open(os.path.join(HERE, 'calendar', 'baps-calendar.json'), encoding='utf-8'))['days']}
    out = os.path.join(folder, 'designs')
    os.makedirs(out, exist_ok=True)
    day = Day(cal, photos, datetime.date(y, m, a.day))
    for name, fn in [('d1-calendar-leaf', d1_leaf), ('d2-baps-square', d2_cell), ('d3-maroon-medallion', d3_maroon)]:
        fn(day).save(os.path.join(out, f'{name}-{a.day:02d}.jpg'), quality=88)
    month_grid(cal, photos, y, m, 'baps').save(os.path.join(out, 'm1-baps-grid.jpg'), quality=88)
    month_grid(cal, photos, y, m, 'diary').save(os.path.join(out, 'm2-diary-grid.jpg'), quality=88)
    m4_wide(cal, photos, y, m).save(os.path.join(out, 'm4-baps-wide.jpg'), quality=88)
    for k in ('close', 'act', 'mixed'):
        m4_mix(cal, photos, y, m, k).convert('RGB').save(os.path.join(out, f'm5-calendar-cords-{k}.jpg'), quality=88)
    if photos.get('cands'):
        cal_img = m6_calendar(cal, photos, y, m)
        cal_img.convert('RGB').save(os.path.join(out, 'm6-calendar.jpg'), quality=88)
        for dn, x in sorted(cal_img.info['picks'].items()):
            print(f"{dn:2d} {x['kind']:5s} {x['mode']:5s} {'UNSURE ' if x.get('unsure') else ''}{x['caption']}")
    m3_special(cal, photos, y, m).save(os.path.join(out, 'm3-special-moments.jpg'), quality=88)
    print('made', sorted(os.listdir(out)))


if __name__ == '__main__':
    main()
