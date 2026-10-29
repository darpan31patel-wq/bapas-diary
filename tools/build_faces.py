#!/usr/bin/env python3
"""Builds the "Bapa through the years" page from tools/faces_years.py's frames (website only).

    python3 tools/build_faces.py --faces faces --db bapas.db --out site-faces

Writes OUT/index.html (site/faces.html with every day's facts and its BAPS calendar line filled in). A day found by
faces_years.py --years shows R2's own copies (photos.bapas-diary.com m/ for the photo, s/ for the strip), so thousands
of days add no files to the website; older days bring OUT/f/ (small lined up close ups for the strip) and OUT/p/ (the
day's whole photo). The page lines up his eyes.
Each day's link goes to the search page for that date, so a tap shows all its photos.
"""
import argparse, json, os, shutil, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def opener(x):
    """How good this day is to open its year with (Darpan, 28 Oct 2026: not the year's first day): the same score that
    chose the day's photo (close, straight at the camera, sharp), plus a little for a big, sharp face."""
    return round(x.get('score', 0) + .5 * min(x.get('span', 0), 200) / 200 + .3 * min(x.get('sharp', 0), 600) / 600, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--faces', default='faces')
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='site-faces')
    ap.add_argument('--site', action='store_true', help='a whole page for bapas-diary.com (a mockup page gets its skeleton when published)')
    a = ap.parse_args()
    days = json.load(open(os.path.join(a.faces, 'faces.json'), encoding='utf-8'))
    db = sqlite3.connect(a.db)
    cal = {r[0]: r[1:] for r in db.execute('SELECT date, indian_date, festivals FROM calendar')}
    rows = []
    days = [y for x in days for y in [x] + [dict(x, **z) for z in x.get('more', [])]]   # an early day's other close ups after its best
    for x in days:
        m = x.get('src') == 'm'   # measured on R2's m/ copy, which the page shows itself; older days have their own p/ and f/
        if 'eyes' not in x or not (m or os.path.exists(os.path.join(a.faces, 'p', x['day'] + '.jpg'))):
            continue
        tithi, fest = cal.get(x['day'], ('', ''))
        rows.append([x['day'], x.get('to') or '', x['place'].replace(', India', ''), x['caption'], x['photos'],
                     x['guru'], tithi or '', fest or ''] + x['eyes'] + [x['span'], x['w'], x['h'], f"{x['album']}/{x['file']}" if m else '',
                     opener(x)])
    for d in 'fp':
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
        for r in rows:
            if not r[15]:
                shutil.copy(os.path.join(a.faces, d, r[0] + '.jpg'), os.path.join(a.out, d, r[0] + '.jpg'))
    page = open(os.path.join(HERE, 'site', 'faces.html'), encoding='utf-8').read()
    page = page.replace('/*DAYS*/[]', json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
    if a.site:
        page = '<!doctype html>\n<html lang="en">\n' + page + '\n</html>\n'
    open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8').write(page)
    print(f'{len(rows)} days into {a.out}')


if __name__ == '__main__':
    main()
