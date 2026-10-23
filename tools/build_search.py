"""Build the searchable photo database page from bapas.db (Darpan, 23 Oct 2026: search the captions for words, by year and month).

    python tools/build_search.py --db bapas.db --out search

Writes a folder that works as it is on any web host (Cloudflare Pages, or opened from a small local server):
  index.html          the search page (site/search.html wrapped as a full page)
  data/YYYY.json      one file per year of baps.org photos:
                        {"g": [[date, date_to, place, album], ...],      a group = one album on one day (or date range)
                         "p": [[group, file, caption, is_bapa], ...]}    every photo, nothing cut out
  data/telegram.json  every Telegram post with words: [[channel, id, date, place, text, photos, videos], ...]
  data/about.json     years, counts and when it was built
"""
import argparse, json, os, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, 'site', 'search.html')


def write(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='search')
    ap.add_argument('--photos', default='https://photos.bapas-diary.com/', help='where the s/ and m/ photos are (R2)')
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'data'), exist_ok=True)
    db = sqlite3.connect(a.db)

    years, counts = {}, {}
    rows = db.execute("SELECT year, date, date_from, date_to, place, album, file, caption, is_bapa FROM photos "
                      "ORDER BY coalesce(date, date_from), album, file")
    for y, date, d0, d1, place, album, file, cap, bapa in rows:
        yr = years.setdefault(y, {'g': [], 'p': [], 'at': {}})
        key = (date or d0, '' if date else (d1 or ''), place or '', album)
        if key not in yr['at']:
            yr['at'][key] = len(yr['g'])
            yr['g'].append(list(key))
        yr['p'].append([yr['at'][key], file, cap or '', 1 if bapa else 0])
    for y, yr in years.items():
        write(os.path.join(a.out, 'data', f'{y}.json'), {'g': yr['g'], 'p': yr['p']})
        counts[y] = len(yr['p'])

    tg = [[ch, i, date or (posted or '')[:10], place or '', text.strip(), ph or 0, vid or 0]
          for ch, i, posted, date, place, text, ph, vid in db.execute(
              "SELECT channel, id, posted, date, place, text, photos, videos FROM tg_posts "
              "WHERE trim(coalesce(text, '')) != '' ORDER BY coalesce(date, posted)")]
    write(os.path.join(a.out, 'data', 'telegram.json'), tg)

    built = dict(db.execute("SELECT key, value FROM about"))
    write(os.path.join(a.out, 'data', 'about.json'),
          {'built': built.get('built'), 'years': sorted(counts), 'photos': counts, 'telegram': len(tg)})

    body = open(PAGE, encoding='utf-8').read().replace('{{PHOTOS}}', a.photos)
    with open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    print(sum(counts.values()), 'photos in', len(counts), 'years,', len(tg), 'Telegram posts ->', a.out)


if __name__ == '__main__':
    main()
