"""Every baps.org News post's own photos, for the Studio's story cards (Darpan, 24 Nov 2026: "no where on my studio all
the pictures associated with the post").

    python3 tools/studio_post_photos.py --db bapas.db --out site/darpan/posts

Writes one small file per year, read by the Studio only when that year's post is shown:
  posts/YYYY.json   {"/News/2018/...aspx": [[album, file, bapa], ...], ...}   in the post's own order; bapa 1 when Bapa is in it
The photo itself is https://photos.bapas-diary.com/s/<album>/<file> (m/ for a bigger one), the same as Search.
Run again when the News articles in bapas.db grow (same time as site/darpan/articles.json).
"""
import argparse, collections, json, os, re, sqlite3

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
db = sqlite3.connect(a.db)
rows = db.execute('SELECT ap.path, ap.album, ap.file, p.is_bapa FROM article_photos ap '
                  'LEFT JOIN photos p ON p.album = ap.album AND lower(p.file) = lower(ap.file) ORDER BY ap.rowid').fetchall()
years = collections.defaultdict(lambda: collections.defaultdict(list))
for path, album, file, bapa in rows:
    m = re.search(r'/News/(\d{4})/', path or '')
    if m:
        years[m[1]][path].append([album, file, 1 if bapa == 1 else 0])
os.makedirs(a.out, exist_ok=True)
for y, posts in sorted(years.items()):
    with open(os.path.join(a.out, f'{y}.json'), 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, separators=(',', ':'))
print(f'{sum(len(p) for p in years.values())} posts with photos in {len(years)} years, {len(rows)} photos')
