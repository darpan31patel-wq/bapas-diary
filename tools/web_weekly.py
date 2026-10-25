"""The weekly darshan email of bapas-diary.com (Darpan, 25 Oct 2026: "people sign up and get a short email each week
with that week's photos of both Bapas", every Sunday at 10 am UK time, a pair for every day "but a few special ones too").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org. Photos come from R2
(photos.bapas-diary.com m/ALBUM/FILE), the words from bapas.db. Runs on GitHub (.github/workflows/weekly-email.yml):

    python3 tools/web_weekly.py --db bapas.db --out weekly                       make the email for this Sunday
    python3 tools/web_weekly.py --db bapas.db --out weekly --week 2026-10-25     make the email for another week
    python3 tools/web_weekly.py ... --test hello@bapas-diary.com                 send it to one address only
    python3 tools/web_weekly.py ... --broadcast                                  send it to everyone signed up, 10 am UK

Every day of the week gets one darshan of Pramukh Swami Maharaj and one of Mahant Swami Maharaj, always together
(Darpan, 24 Oct 2026), taken on that day in years gone by: Pramukh Swami Maharaj from 1999 up to 13 August 2016,
Mahant Swami Maharaj from 20 August 2016 on. The year turns each time, so the same week next year shows other years.
When the week has a big day (Diwali, either Bapa's birthday, Guru Purnima and so on, from the BAPS calendar) a
"Special this week" part adds more of both Bapas from that festival in earlier years; festivals move with the Indian
calendar, so those photos are found through the calendar's dates for the festival, not the same English date.

The email's pictures are cut to 4:3 and saved to weekly/e/WEEK/ for R2 (the workflow uploads them), so every email
app shows them the same size. weekly/email.html is the email; weekly/week.json says what was picked.
"""
import argparse, datetime, hashlib, io, json, os, re, sqlite3, sys, urllib.request
from zoneinfo import ZoneInfo

PHOTOS = 'https://photos.bapas-diary.com/'
SITE = 'https://bapas-diary.com/'
FROM = "Bapa's Diary <hello@bapas-diary.com>"
SEGMENT = 'Weekly darshan'
UK = ZoneInfo('Europe/London')
PSM_LAST, MSM_FIRST = '2016-08-13', '2016-08-20'
NAMES = ('Pramukh Swami Maharaj', 'Mahant Swami Maharaj')

# big days that bring a "Special this week" part, by the BAPS calendar's festival name (letters only, lower case)
SPECIAL = {
    'pramukhswamimaharajsjayanti': "Pramukh Swami Maharaj's birthday",
    'mahantswamimaharajjanmajayanti': "Mahant Swami Maharaj's birthday",
    'diwali': 'Diwali', 'annakutandbestuvarash': 'Annakut and the new year',
    'gurupurnima': 'Guru Purnima', 'janmashtami': 'Janmashtami',
    'ramnavmiharinombhagwanswaminarayansbirthday': "Bhagwan Swaminarayan's birthday",
    'aksharbrahmagunatitanandswamisbirthday': "Aksharbrahma Gunatitanand Swami's birthday",
    'yogijayanti': "Yogiji Maharaj's birthday", 'pramukhvarnidin': 'Pramukh Varni Din',
    'pramukhvaranidin': 'Pramukh Varni Din', 'vasantpanchmi': 'Vasant Panchmi', 'pushpadolotsav': 'Pushpadolotsav',
}

C = {'maroon': '#5a1626', 'gold': '#d9a441', 'pale': '#ffe296', 'cream': '#faf1de', 'paper': '#fffaf0',
     'ink': '#2e1a14', 'muted': '#7a5c48', 'line': '#e6d6b8', 'amber': '#a06a1c'}
SERIF = "'EB Garamond', Georgia, 'Times New Roman', serif"
SANS = 'Arimo, Arial, Helvetica, sans-serif'


def key(s):
    return re.sub('[^a-z]', '', (s or '').lower())


def score(caption):
    """Photos where Bapa himself is the darshan come first, crowds doing darshan of him last."""
    c = (caption or '').lower()
    s = 0
    if c.startswith(('swamishri', 'hh pramukh', 'param pujya mahant', 'pramukh swami', 'mahant swami')):
        s += 2
    if re.search(r"(of|before|with|to) swamishri|swamishri's|pujya \w+ swami (in|and)", c) or \
            c.startswith(('devotees', 'sadhus', 'swamis ', 'children', 'kids', 'students', 'a ')):
        s -= 3
    return s


def in_r2(album, file, cache={}):
    k = f'm/{album}/{file}'
    if k not in cache:
        try:
            req = urllib.request.Request(PHOTOS + urllib.request.quote(k), method='HEAD')
            cache[k] = urllib.request.urlopen(req, timeout=20).status == 200
        except Exception:
            cache[k] = False
    return cache[k]


def pick(rows, seed, used, shown, n=1):
    """n photos from rows (date, place, album, file, caption), a different year each, turning with the seed.
    Years not shown yet this week come first, and a year only counts when it has a photo of Bapa himself."""
    by_year = {}
    for r in rows:
        if (r[2], r[3]) not in used:
            by_year.setdefault(r[0][:4], []).append(r)
    years = sorted(by_year)
    out = []
    if not years:
        return out
    start = int(hashlib.sha1(seed.encode()).hexdigest(), 16) % len(years)
    turn = [years[(start + i) % len(years)] for i in range(len(years))]
    for least in (2, 0, -9):
        for y in sorted(turn, key=lambda y: y in shown):
            if len(out) == n:
                return out
            if any(o[0][:4] == y for o in out):
                continue
            best = sorted((r for r in by_year[y] if score(r[4]) >= least),
                          key=lambda r: (-score(r[4]), hashlib.sha1((seed + r[3]).encode()).hexdigest()))
            for r in best[:12]:
                if in_r2(r[2], r[3]):
                    out.append(r)
                    used.add((r[2], r[3]))
                    shown.add(y)
                    break
    return out


def guru_rows(db, where, args):
    return db.execute(f"SELECT date, place, album, file, caption FROM photos WHERE is_bapa = 1 AND date IS NOT NULL AND {where}", args).fetchall()


def week_data(db, sunday):
    used, shown_p, shown_m = set(), set(), set()
    days = []
    for i in range(7):
        d = sunday + datetime.timedelta(days=i)
        md = f'{d:%m-%d}'
        seed = f'{d.isoformat()}'
        psm = pick(guru_rows(db, 'substr(date, 6) = ? AND date <= ?', (md, PSM_LAST)), seed + 'p', used, shown_p)
        msm = pick(guru_rows(db, 'substr(date, 6) = ? AND date >= ? AND date < ?', (md, MSM_FIRST, d.isoformat())), seed + 'm', used, shown_m)
        cal = db.execute('SELECT indian_date, festivals FROM calendar WHERE date = ?', (d.isoformat(),)).fetchone() or ('', '')
        days.append({'date': d.isoformat(), 'indian': (cal[0] or '').split('/')[0], 'festival': cal[1] or '',
                     'psm': psm[0] if psm else None, 'msm': msm[0] if msm else None})
    special = []
    for day in days:
        for fest in re.split(r';\s*', day['festival']):
            name = SPECIAL.get(key(fest))
            if not name:
                continue
            dates = [r[0] for r in db.execute('SELECT date, festivals FROM calendar WHERE date < ?', (day['date'],))
                     if any(key(f) == key(fest) for f in re.split(r';\s*', r[1] or ''))]
            if not dates:
                continue
            q = 'date IN (%s)' % ','.join('?' * len(dates))
            seed = day['date'] + key(fest)
            psm = pick(guru_rows(db, q + ' AND date <= ?', (*dates, PSM_LAST)), seed + 'p', used, set(), 2)
            msm = pick(guru_rows(db, q + ' AND date >= ?', (*dates, MSM_FIRST)), seed + 'm', used, set(), 2)
            pairs = list(zip(psm, msm))   # always both Bapas together, never one alone
            if pairs:
                special.append({'name': name, 'date': day['date'], 'pairs': pairs})
    return {'sunday': sunday.isoformat(), 'days': days, 'special': special}


def cut(album, file, out_path, width):
    """The R2 photo cut to 4:3, a little above the middle where Bapa's face usually is."""
    from PIL import Image, ImageOps
    body = urllib.request.urlopen(PHOTOS + urllib.request.quote(f'm/{album}/{file}'), timeout=60).read()
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(body))).convert('RGB')
    w, h = im.size
    tw, th = (w, round(w * 3 / 4)) if w * 3 / 4 <= h else (round(h * 4 / 3), h)
    x = (w - tw) // 2
    y = min(max(round(h * 0.38 - th / 2), 0), h - th)
    im = im.crop((x, y, x + tw, y + th)).resize((width, round(width * 3 / 4)), Image.LANCZOS)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    im.save(out_path, 'JPEG', quality=82, optimize=True, progressive=True)


def nice(iso, fmt='%A %-d %B'):
    return datetime.date.fromisoformat(iso).strftime(fmt)


def photo_cell(r, name, src, big, link):
    y, place = r[0][:4], (r[1] or '').split(',')[0].strip()
    w = 268
    cap = f'<div style="font:italic 15px/1.3 {SERIF};color:{C["ink"]};padding-top:2px">{esc(short(r[4]))}</div>' if big else ''
    return (f'<td width="50%" valign="top" style="padding:0 5px">'
            f'<a href="{link}"><img src="{src}" width="{w}" alt="{esc(name)}, {y}, {esc(place)}" '
            f'style="display:block;width:100%;max-width:{w}px;height:auto;border:0;border-radius:6px"></a>'
            f'<div style="font:600 {17 if big else 15}px/1.2 {SERIF};color:{C["ink"]};padding-top:6px">{name}</div>'
            f'<div style="font:12px/1.4 {SANS};color:{C["muted"]}">{y} · {esc(place)}</div>{cap}</td>')


def short(caption):
    c = re.sub(r'\s*For more photos.*$', '', caption or '', flags=re.I).strip()
    c = re.sub(r',?\s*\d{1,2} [A-Z][a-z]{2,8} \d{4}$', '', c)   # "..., 8 Nov 2016": the year is already shown
    return c[:90]


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def render(data, img):
    """The email, in plain tables with the styles written on each part, the way every email app reads it."""
    days = data['days']
    first, last = days[0]['date'], days[-1]['date']
    span = f"{nice(first, '%A %-d')} to {nice(last, '%A %-d %B')}" if first[5:7] == last[5:7] else f"{nice(first)} to {nice(last)}"

    def cal_line(d):
        bits = [esc(d['indian'])] if d['indian'] else []
        if d['festival']:
            bits.append(f'<b style="color:{C["amber"]}">{esc(d["festival"])}</b>')
        return f'<div style="font:13px/1.4 {SANS};color:{C["muted"]};padding:2px 0 10px">{" · ".join(bits)}</div>' if bits else '<div style="height:8px"></div>'

    def pair(d, big):
        link = f'{SITE}day/{d["date"][5:]}/'
        cells = []
        for k, name in (('psm', NAMES[0]), ('msm', NAMES[1])):
            cells.append(photo_cell(d[k], name, img[(d['date'], k)], big, link))
        return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{"".join(cells)}</tr></table>'

    parts = []
    today = days[0]
    if today['psm'] and today['msm']:
        parts.append(f'''<tr><td style="padding:0 17px 22px;border-bottom:1px solid {C["line"]}">
<div style="font:700 11px {SANS};letter-spacing:2px;text-transform:uppercase;color:{C["maroon"]};padding:0 5px">Today · {nice(today["date"])}</div>
<div style="padding:0 5px">{cal_line(today)}</div>{pair(today, True)}
<div style="text-align:center;padding-top:16px"><a href="{SITE}day/{today["date"][5:]}/" style="display:inline-block;font:700 13px {SANS};color:#3d0e19;background:{C["gold"]};padding:11px 20px;border-radius:999px;text-decoration:none">Open {nice(today["date"], "%-d %B")} in Bapa's Diary</a></div></td></tr>''')

    for s in data['special']:
        rows = []
        for i, (p, m) in enumerate(s['pairs']):
            d = {'date': s['date'], 'psm': p, 'msm': m}
            img_d = {(s['date'], 'psm'): img[('special', p[3])], (s['date'], 'msm'): img[('special', m[3])]}
            link = f'{SITE}day/{s["date"][5:]}/'
            rows.append(f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:{10 if i else 0}px"><tr>'
                        f'{photo_cell(p, NAMES[0], img_d[(s["date"], "psm")], False, link)}{photo_cell(m, NAMES[1], img_d[(s["date"], "msm")], False, link)}</tr></table>')
        parts.append(f'''<tr><td style="padding:22px 17px;border-bottom:1px solid {C["line"]};background:#fbf0d6">
<div style="font:700 11px {SANS};letter-spacing:2px;text-transform:uppercase;color:{C["amber"]};padding:0 5px">Special this week · {nice(s["date"])}</div>
<div style="font:600 22px/1.2 {SERIF};color:{C["maroon"]};padding:4px 5px 12px">{esc(s["name"])} in years gone by</div>{"".join(rows)}</td></tr>''')

    rest = [d for d in days[1:] if d['psm'] and d['msm']]
    if rest:
        parts.append(f'<tr><td style="padding:22px 22px 4px;font:600 22px {SERIF};color:{C["maroon"]}">The rest of the week</td></tr>')
    for d in rest:
        parts.append(f'''<tr><td style="padding:12px 17px 18px;border-bottom:1px solid {C["line"]}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td style="padding:0 5px;font:600 19px {SERIF};color:{C["ink"]}">{nice(d["date"])}</td>
<td align="right" style="padding:0 5px;font:700 12px {SANS}"><a href="{SITE}day/{d["date"][5:]}/" style="color:{C["maroon"]};text-decoration:none">See the day ›</a></td></tr></table>
<div style="padding:0 5px">{cal_line(d)}</div>{pair(d, False)}</td></tr>''')

    pre = f"This week's darshan of Pramukh Swami Maharaj and Mahant Swami Maharaj, {span}."
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta name="color-scheme" content="light"><title>This week's darshan</title></head>
<body style="margin:0;padding:0;background:{C["cream"]}">
<div style="display:none;max-height:0;overflow:hidden">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C["cream"]}"><tr><td align="center" style="padding:22px 8px 30px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{C["paper"]}">
<tr><td align="center" style="background:{C["maroon"]};padding:26px 20px 22px">
<div style="font:700 11px {SANS};letter-spacing:4px;text-transform:uppercase;color:{C["gold"]}">Bapa's Diary</div>
<div style="font:600 32px/1.1 {SERIF};color:{C["pale"]};padding:8px 0 6px">This week's darshan</div>
<div style="font:italic 17px {SERIF};color:#f3e4c6">{span}</div></td></tr>
<tr><td style="padding:22px 22px 18px;font:18px/1.45 {SERIF};color:{C["ink"]}"><b style="color:{C["maroon"]};font-weight:600">Jay Swaminarayan 🙏🏽</b><br>
Here is this week in years gone by, with one darshan of Pramukh Swami Maharaj and one of Mahant Swami Maharaj for every day.</td></tr>
{"".join(parts)}
<tr><td align="center" style="padding:20px 22px 26px;font:12px/1.6 {SANS};color:{C["muted"]}">
<div style="font:italic 600 20px {SERIF};color:{C["maroon"]};padding-bottom:6px">Jay Swaminarayan</div>
You get this because you signed up on <a href="{SITE}" style="color:{C["maroon"]}">bapas-diary.com</a>.<br>
Reply to this email to write to us. <a href="{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}" style="color:{C["maroon"]}">Stop these emails</a> with one tap.</td></tr>
</table></td></tr></table></body></html>'''


def resend(path, body=None, method='POST'):
    req = urllib.request.Request('https://api.resend.com' + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'],
                                          'Content-Type': 'application/json', 'User-Agent': 'bapas-diary-weekly'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b'{}')


def segment_id():
    for s in resend('/segments', method='GET').get('data', []):
        if s.get('name') == SEGMENT:
            return s['id']
    return resend('/segments', {'name': SEGMENT})['id']


def ten_am(sunday):
    return datetime.datetime.combine(sunday, datetime.time(10), UK).astimezone(datetime.timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='weekly')
    ap.add_argument('--week', help='the Sunday that starts the week (default: this coming Sunday, or today on a Sunday)')
    ap.add_argument('--test', help='send only to this address')
    ap.add_argument('--broadcast', action='store_true', help='send to everyone signed up, at 10 am UK time')
    ap.add_argument('--upload', help='command that sends --out/e/ to R2, run before anything is sent')
    ap.add_argument('--no-photos', action='store_true', help='link the R2 photos as they are (quick look, no cutting)')
    a = ap.parse_args()

    today = datetime.datetime.now(UK).date()
    sunday = datetime.date.fromisoformat(a.week) if a.week else today + datetime.timedelta(days=(6 - today.weekday()) % 7)
    data = week_data(sqlite3.connect(a.db), sunday)
    week = sunday.isoformat()

    img = {}
    def add(k, r, width):
        if a.no_photos:
            img[k] = PHOTOS + urllib.request.quote(f'm/{r[2]}/{r[3]}')
            return
        name = f'{r[2]}-{os.path.splitext(r[3])[0]}.jpg'
        cut(r[2], r[3], os.path.join(a.out, 'e', week, name), width * 2)   # twice the size, sharp on phones
        img[k] = f'{PHOTOS}e/{week}/{urllib.request.quote(name)}'
    for d in data['days']:
        for k in ('psm', 'msm'):
            if d[k]:
                add((d['date'], k), d[k], 268)
    for s in data['special']:
        for p, m in s['pairs']:
            add(('special', p[3]), p, 268)
            add(('special', m[3]), m, 268)

    html = render(data, img)
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, 'email.html'), 'w', encoding='utf-8').write(html)
    json.dump(data, open(os.path.join(a.out, 'week.json'), 'w'), indent=1, ensure_ascii=False)
    first, last = data['days'][0]['date'], data['days'][-1]['date']
    subject = f"This week's darshan · {nice(first, '%-d %B')} to {nice(last, '%-d %B')}"
    if first[5:7] == last[5:7]:
        subject = f"This week's darshan · {nice(first, '%-d')} to {nice(last, '%-d %B')}"
    have = sum(1 for d in data['days'] if d['psm'] and d['msm'])
    print(f'{subject}: {have} of 7 days with both Bapas, {len(data["special"])} special', flush=True)
    if have < 4:
        sys.exit('Not enough photos of both Bapas in R2 for this week yet, nothing sent.')

    if a.upload and not a.no_photos:
        import subprocess
        subprocess.run(a.upload, shell=True, check=True)
    if a.test:
        r = resend('/emails', {'from': FROM, 'to': [a.test], 'subject': '[Test] ' + subject,
                               'html': html.replace('{{{RESEND_UNSUBSCRIBE_URL}}}', SITE)})
        print('Test email sent to', a.test, r.get('id'))
    if a.broadcast:
        name = 'Weekly darshan ' + week
        if any(b.get('name') == name for b in resend('/broadcasts', method='GET').get('data', [])):
            print('This week\'s email is already on its way, nothing more to do.')
            return
        when = max(ten_am(sunday), datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=2))
        r = resend('/broadcasts', {'segment_id': segment_id(), 'from': FROM, 'reply_to': 'hello@bapas-diary.com',
                                   'subject': subject, 'html': html, 'name': name, 'send': True,
                                   'scheduled_at': when.isoformat().replace('+00:00', 'Z')})
        print('Sent to everyone signed up, arriving', when.astimezone(UK).strftime('%A %-d %B %H:%M UK'), r.get('id'))


if __name__ == '__main__':
    main()
