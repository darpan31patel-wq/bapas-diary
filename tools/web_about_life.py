#!/usr/bin/env python3
"""Bapa's life in pictures on the About page (baps.org find 5; Darpan, 13 Nov 2026 "Yes to all", mockup 17 Nov 2026).

Website only (bapas-diary.com). Nothing here touches the daily 2pm picture.

Pramukh Swami Maharaj's row: pramukhswami.org's own life timeline photos (copied into live/about/life/, every detail
kept in data/baps/psm-life.json), each with its year and one short line in our own words, English dates only.
Mahant Swami Maharaj's row beside it (the two gurus always together): one clear darshan for each year since
13 August 2016 from the diary's own photos (bapa.db, Bapa recognised by face), linking to that year's Year in review.
No source line is shown on the page (Darpan, 13 Nov 2026).

    python3 tools/web_about_life.py --life data/baps/psm-life.json --db bapa.db --photo-years photo-years.txt --out out
"""
import argparse, datetime, html, json, os, re, sqlite3

MSM_FROM = '2016-08-13'
CSS = """<style id="life-css">
.life{margin:56px auto 0;max-width:1100px}
.life h2{text-align:center;margin:0}
.life h3{margin:30px 0 14px;font:600 14px/1.3 Cinzel,Georgia,serif;letter-spacing:.2em;text-transform:uppercase;color:#d9a441;text-align:center}
.life .row{display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px 2px 16px;scrollbar-width:thin}
.life figure{flex:0 0 190px;margin:0;scroll-snap-align:start;background:linear-gradient(#fdf9f0,#efe4cd);padding:8px 8px 10px;border-radius:6px;box-shadow:0 10px 26px rgba(0,0,0,.4)}
.life figure img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;object-position:50% 30%;border-radius:3px;background:#e9dcc4}
.life figcaption{margin-top:8px;text-transform:none;letter-spacing:0}
.life figcaption b{display:block;font:700 17px/1.1 Lora,Georgia,serif;color:#8a1c2b}
.life figcaption span{display:block;font:400 13px/1.35 Poppins,system-ui,sans-serif;color:#3b1219}
.life figcaption i{display:block;font:italic 400 12px/1.3 Lora,Georgia,serif;color:#7a5a3a;margin-top:2px}
.life a{color:inherit;text-decoration:none}
@media (max-width:600px){.life figure{flex-basis:160px}}
</style>"""

esc = lambda s: html.escape(str(s or ''), quote=True)


def msm_row(db, photos_url, years_in_r2):
    out = []
    try:
        con = sqlite3.connect(db)
        this = datetime.date.today().year
        for y in range(2016, this + 1):
            if years_in_r2 and y not in years_in_r2:
                continue
            r = con.execute(
                "SELECT p.album, p.file, p.caption, p.place, coalesce(p.date, p.date_from) FROM photos p JOIN bapa_pick b USING (album, file) "
                "WHERE p.year = ? AND coalesce(p.date, p.date_from) >= ? AND coalesce(p.caption, '') != '' "
                "ORDER BY b.close DESC, b.rank, b.sim DESC LIMIT 1", (y, MSM_FROM)).fetchone()
            if not r:
                continue
            al, fi, cap, place, day = r
            cap = re.split(r'(?<=[a-z])\. ', cap.strip())[0].rstrip('.')
            out.append((y, f'{photos_url}m/{al}/{fi}', cap[:90], (place or '').split(',')[0].strip(), f'/year/{y}/'))
    except sqlite3.Error as e:
        print('Mahant Swami Maharaj row: database not read,', e)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--life', default='data/baps/psm-life.json')
    ap.add_argument('--db', default='bapa.db')
    ap.add_argument('--photo-years', default='')
    ap.add_argument('--photos-url', default='https://photos.bapas-diary.com/')
    ap.add_argument('--out', default='out')
    a = ap.parse_args()
    page = os.path.join(a.out, 'about', 'index.html')
    if not os.path.exists(page):
        print('no About page, nothing done'); return
    life = json.load(open(a.life))
    have = set()
    if a.photo_years and os.path.exists(a.photo_years):
        have = {int(x) for x in open(a.photo_years).read().split() if x.isdigit()}
    msm = msm_row(a.db, a.photos_url, have)
    fig = lambda src, y, line, sub='': (f'<figure><img src="{esc(src)}" alt="{esc(line)}" loading="lazy" decoding="async">'
                                        f'<figcaption><b>{esc(y)}</b><span>{esc(line)}</span>{f"<i>{esc(sub)}</i>" if sub else ""}</figcaption></figure>')
    psm = ''.join(fig('/about/' + r['file'], r['year'], r['line'], r.get('date', '')) for r in life)
    ms = ''.join(f'<a href="{esc(link)}">{fig(src, y, cap, place)}</a>' for y, src, cap, place, link in msm)
    sec = (f'<section class="life" id="life" aria-labelledby="life-h"><h2 id="life-h">Bapa\'s life in pictures</h2>'
           f'<h3>Pramukh Swami Maharaj, 1921 to 2016</h3><div class="row" translate="no">{psm}</div>'
           + (f'<h3>Mahant Swami Maharaj, guru since 2016</h3><div class="row" translate="no">{ms}</div>' if ms else '') + '</section>')
    t = open(page, encoding='utf-8').read()
    if 'id="life"' in t:
        print('About already has the life pictures'); return
    i = t.find('<div class="card">')   # straight under the card, before the weekly darshan sign up
    j = t.find('<!-- The weekly darshan', i) if i >= 0 else -1
    if j < 0:
        j = t.find('<section class="weekly-signup"', i) if i >= 0 else -1
    if j < 0:
        print('About: no place found, nothing done'); return
    t = t[:j] + sec + t[j:]
    t = t.replace('</head>', CSS + '</head>', 1)
    open(page, 'w', encoding='utf-8').write(t)
    print(f'About: {len(life)} Pramukh Swami Maharaj pictures, {len(msm)} Mahant Swami Maharaj years')


if __name__ == '__main__':
    main()
