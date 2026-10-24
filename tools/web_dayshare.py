"""Share a day for the website bapas-diary.com (Darpan typed yes, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site:

    python3 tools/web_dayshare.py --db bapas.db --out out --photos-url https://photos.bapas-diary.com/ \
        --photo-years site/photo-years.txt --tags tags.json

For each of the 366 days it makes
  out/share/day/MM-DD.jpg        1080 x 1350, the ready picture people send or save (fills a phone, fits a status)
  out/share/day/MM-DD-wide.jpg   1200 x 630, the preview WhatsApp shows under a day's link
  out/day/MM-DD/index.html       the day's link: its own preview tags, then straight on to the Today page /#MM-DD
in the On this day look: maroon glow, gold Garamond date, that day's darshan from different years as ivory polaroids
with the year and place, the Indian date this year, and in how many years there is darshan on that day.
Photos come from R2 (s/ALBUM/FILE) for the years already copied there; a day with none uses the two Gurus of the
site's share picture. The best photo of a year is the one CLIP rates most smiling and close up (tags.json).
"""
import argparse, datetime, html, io, json, os, sqlite3, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from web_share import HERE, CAP, GOLD_HI, GOLD_SOFT, MAROON_IN, font, gold_text, ground, icon, mix, polaroid, spaced
from PIL import Image, ImageDraw, ImageFilter

INK = (0x6e, 0x14, 0x24)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
LINE = 'A smruti of Bapa for every day. Open His diary to see where He was.'


def days():
    d = datetime.date(2000, 1, 1)   # 2000 has 29 February
    while d.year == 2000:
        yield d.strftime('%m-%d'), f'{d.day} {MONTHS[d.month - 1]}'
        d += datetime.timedelta(days=1)


def crop45(im, face_top=0.22, ratio=0.8):
    """A 4:5 portrait (or another width / height ratio) from any photo, kept near the top where the face usually is."""
    w, h = im.size
    if w / h > ratio:
        nw = round(h * ratio)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = round(w / ratio)
    top = max(0, min(h - nh, round(h * face_top - nh * 0.2)))
    return im.crop((0, top, w, top + nh))


def card(photo, width, label, tilt, ratio=0.8):
    """A polaroid with 'YEAR · Place' written on its frame, tilted a little; drawn at twice the size for smooth edges."""
    c = polaroid(crop45(photo, ratio=ratio), width * 2)
    size = round(width * 0.135)
    while size > 10 and font('eb-garamond-latin-700-normal', size).getlength(label) > width * 1.5:
        size -= 2
    ImageDraw.Draw(c).text((c.width // 2, c.height - round(width * 0.14)), label,
                           font=font('eb-garamond-latin-700-normal', size), fill=INK, anchor='ms')
    c = c.convert('RGBA').rotate(tilt, Image.BICUBIC, expand=True)
    return c.resize((c.width // 2, c.height // 2), Image.LANCZOS)


def lay(img, cards):
    """Paste (card, x, y) with one soft shadow under them all."""
    sh = Image.new('L', img.size)
    for c, x, y in cards:
        sh.paste(c.getchannel('A').point(lambda v: v * 0.6), (x + 9, y + 18), c.getchannel('A'))
    img.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(15)))
    for c, x, y in cards:
        img.paste(c, (x, y), c)


def kicker(d, xy, size, spacing, rule):
    w = spaced(d, xy, 'A SMRUTI OF BAPA', font('arimo-latin-700-normal', size), GOLD_SOFT, spacing)
    for s in (-1, 1):
        x0 = xy[0] + s * (w / 2 + 18)
        for i in range(rule):
            d.point((x0 + s * i, xy[1]), fill=mix(GOLD_SOFT, MAROON_IN, i / rule))


def years_line(n):
    return 'Darshan on this day in 1 year' if n == 1 else f'Darshan on this day in {n} different years'


def tall(title, indian, picks, nyears):
    W, H = 1080, 1350
    img = ground(W, H, cy=0.35)
    d = ImageDraw.Draw(img)
    kicker(d, (W // 2, 86), 22, 8, 60)
    gold_text(img, (W // 2, 222), title, font('eb-garamond-latin-700-normal', 130), anchor='ms')
    if indian:
        d.text((W // 2, 284), indian, font=font('eb-garamond-latin-500-normal', 34), fill=mix(CAP, MAROON_IN, .2), anchor='ms')
    n = len(picks)
    tilts = [3, -2.5, -2, 2.5]
    if n == 1:
        c = card(picks[0][0], 520, picks[0][1], 2)
        spots = [(c, (W - c.width) // 2, 330)]
    elif n == 2:
        cs = [card(p, 460, l, t) for (p, l), t in zip(picks, tilts)]
        spots = [(cs[0], 66, 345), (cs[1], 548, 375)]
    else:
        cs = [card(p, 330, l, t, ratio=1) for (p, l), t in zip(picks, tilts)]   # square, so two rows fit
        xs = [(150, 318), (590, 330), (170, 700), (570, 690)] if n == 4 else [(150, 318), (590, 330), (375, 700)]
        spots = [(c, x, y) for c, (x, y) in zip(cs, xs)]
    lay(img, spots)
    d = ImageDraw.Draw(img)
    base = {1: 1150, 2: 1078}.get(n, 1132)
    d.text((W // 2, base), years_line(nyears), font=font('eb-garamond-latin-500-normal', 38), fill=CAP, anchor='ms')
    m = Image.new('L', (100, 100))
    ImageDraw.Draw(m).ellipse([3, 3, 97, 97], fill=255)
    img.paste(icon(100, 'ring-words'), (W // 2 - 50, base + 46), m)
    spaced(d, (W // 2, 1300), 'BAPAS-DIARY.COM', font('arimo-latin-700-normal', 24), GOLD_HI, 6)
    return img


def wide(title, indian, picks, nyears):
    W, H = 1200, 630
    img = ground(W, H, cx=0.66)
    two = picks[:2]
    if len(two) == 1:
        c = card(two[0][0], 300, two[0][1], 3)
        spots = [(c, (580 - c.width) // 2, (H - c.height) // 2)]
    else:
        spots = [(card(two[0][0], 280, two[0][1], 3.5), 46, 64), (card(two[1][0], 280, two[1][1], -3), 318, 88)]
    lay(img, spots)
    d = ImageDraw.Draw(img)
    mid = 885
    spaced(d, (mid, 196), 'A SMRUTI OF BAPA', font('arimo-latin-700-normal', 16), GOLD_SOFT, 6)
    gold_text(img, (mid, 300), title, font('eb-garamond-latin-700-normal', 92 if len(title) < 13 else 80), anchor='ms')
    if indian:
        d.text((mid, 356), indian, font=font('eb-garamond-latin-500-normal', 30), fill=mix(CAP, MAROON_IN, .2), anchor='ms')
    d.text((mid, 420), years_line(nyears).replace(' different', ''), font=font('eb-garamond-latin-500-normal', 30), fill=CAP, anchor='ms')
    spaced(d, (mid, 500), 'BAPAS-DIARY.COM', font('arimo-latin-700-normal', 17), GOLD_HI, 5)
    return img


def link_page(mmdd, title):
    t = html.escape(f"{title} · Bapa's Diary", quote=True)
    img = f'https://bapas-diary.com/share/day/{mmdd}-wide.jpg'
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{LINE}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Bapa's Diary">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{LINE}">
<meta property="og:url" content="https://bapas-diary.com/day/{mmdd}/">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://bapas-diary.com/#{mmdd}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url=/#{mmdd}">
<script>location.replace('/#{mmdd}')</script>
</head>
<body style="background:#160509;color:#faf1de;font:20px Georgia,serif;text-align:center;padding:40px">
<a style="color:#ffe296" href="/#{mmdd}">{html.escape(title)} in Bapa's Diary</a>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--photos-url', default='https://photos.bapas-diary.com/')
    ap.add_argument('--photo-years', default=os.path.join(HERE, 'site', 'photo-years.txt'))
    ap.add_argument('--tags', help='tags.json from release website-mockup, to choose the most smiling photo')
    ap.add_argument('--days', nargs='*', help='only these MM-DD (for a quick test)')
    ap.add_argument('--local', help='read photos from this folder (ALBUM/FILE) instead of the photos address')
    a = ap.parse_args()

    have = {int(x) for x in open(a.photo_years).read().split() if x.strip().isdigit()}
    score = {}
    if a.tags:
        t = json.load(open(a.tags))
        want = [t['tags'].index(x) for x in ('smiling', 'close up') if x in t['tags']]
        score = {k: sum(v[i] for i in want) for k, v in t['photos'].items()}
    db = sqlite3.connect(a.db)
    this_year = datetime.date.today().year

    plan = {}
    for mmdd, title in days():
        if a.days and mmdd not in a.days:
            continue
        rows = db.execute('SELECT year, place, album, file, is_bapa FROM photos WHERE substr(date, 6) = ? AND date IS NOT NULL',
                          (mmdd,)).fetchall()
        nyears = len({r[0] for r in rows})
        best = {}
        for y, place, album, file, bapa in rows:
            if y not in have:
                continue
            k = (bool(bapa), score.get(f'{album}/{file}', 0))
            if y not in best or k > best[y][0]:
                best[y] = (k, f'{y} · {(place or "").split(",")[0].strip()}'.rstrip(' ·'), f'{album}/{file}')
        ys = sorted(best)
        if len(ys) > 4:
            ys = [ys[round(i * (len(ys) - 1) / 3)] for i in range(4)]
        cal = None
        try:
            cal = db.execute('SELECT indian_date FROM calendar WHERE date = ?', (f'{this_year}-{mmdd}',)).fetchone()
        except sqlite3.OperationalError:
            pass
        indian = f'{cal[0]} this year' if cal and cal[0] else ''
        plan[mmdd] = (title, indian, [(best[y][2], best[y][1]) for y in ys], nyears)

    def fetch(key):
        try:
            if a.local:
                return key, Image.open(os.path.join(a.local, key)).convert('RGB')
            with urllib.request.urlopen(a.photos_url + 's/' + key, timeout=30) as r:
                return key, Image.open(io.BytesIO(r.read())).convert('RGB')
        except Exception as e:
            print('photo missing:', key, e)
            return key, None

    keys = sorted({k for p in plan.values() for k, _ in p[2]})
    with ThreadPoolExecutor(8) as pool:
        photos = dict(pool.map(fetch, keys))
    gurus = [(Image.open(os.path.join(HERE, 'site', 'art', f)).convert('RGB'), l)
             for f, l in (('preview-psm.jpg', 'Pramukh Swami Maharaj'), ('preview-msm.jpg', 'Mahant Swami Maharaj'))]

    os.makedirs(os.path.join(a.out, 'share', 'day'), exist_ok=True)
    for mmdd, (title, indian, picks, nyears) in plan.items():
        got = [(photos[k], l) for k, l in picks if photos.get(k)] or gurus
        tall(title, indian, got, nyears).save(os.path.join(a.out, 'share', 'day', f'{mmdd}.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
        wide(title, indian, got, nyears).save(os.path.join(a.out, 'share', 'day', f'{mmdd}-wide.jpg'), 'JPEG', quality=84, optimize=True, progressive=True)
        os.makedirs(os.path.join(a.out, 'day', mmdd), exist_ok=True)
        with open(os.path.join(a.out, 'day', mmdd, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(link_page(mmdd, title))
    print('share a day:', len(plan), 'days,', sum(1 for p in photos.values() if p), 'photos')


if __name__ == '__main__':
    main()
