#!/usr/bin/env python3
"""Builds the "Bapa through the years" page from tools/faces_years.py's frames (website only).

    python3 tools/build_faces.py --faces faces --db bapas.db --out site-faces

Writes OUT/index.html (site/faces.html with every day's facts and its BAPS calendar line filled in) and OUT/f/
(small lined up close ups for the strip) and OUT/p/ (each day's whole photo; the page lines up his eyes).
Each day's link goes to the search page for that date, so a tap shows all its photos.
"""
import argparse, json, os, shutil, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--faces', default='faces')
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='site-faces')
    a = ap.parse_args()
    days = json.load(open(os.path.join(a.faces, 'faces.json'), encoding='utf-8'))
    db = sqlite3.connect(a.db)
    cal = {r[0]: r[1:] for r in db.execute('SELECT date, indian_date, festivals FROM calendar')}
    rows = []
    for x in days:
        if 'eyes' not in x or not os.path.exists(os.path.join(a.faces, 'p', x['day'] + '.jpg')):
            continue
        tithi, fest = cal.get(x['day'], ('', ''))
        rows.append([x['day'], x.get('to') or '', x['place'].replace(', India', ''), x['caption'], x['photos'],
                     x['guru'], tithi or '', fest or ''] + x['eyes'] + [x['span'], x['w'], x['h']])
    for d in 'fp':
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
        for r in rows:
            shutil.copy(os.path.join(a.faces, d, r[0] + '.jpg'), os.path.join(a.out, d, r[0] + '.jpg'))
    page = open(os.path.join(HERE, 'site', 'faces.html'), encoding='utf-8').read()
    page = page.replace('/*DAYS*/[]', json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
    open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8').write(page)
    print(f'{len(rows)} days into {a.out}')


if __name__ == '__main__':
    main()
