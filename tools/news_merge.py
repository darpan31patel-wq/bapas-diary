"""Turn the baps.org News read (Darpan's Chrome, 4 to 6 Nov 2026) into crawl/news/articles.json on the database branch.

    python tools/news_merge.py bapas-news.json bapas-news-dates.json crawl/news/articles.json

bapas-news.json   every News article, keyed by its path: {t title, d date shown on the article (often empty), text,
                  own [[album, file, alt]] photos inside the article, g {gallery path: {t title, rows [[album, file, alt]]}}}
bapas-news-dates.json   the date the News list gives each article, keyed by path: "4 Nov 2006" (every article has one)

The result keeps everything and adds `date` (YYYY-MM-DD) and `place` to each article. build_archive.py reads it into
the articles and article_photos tables and adds the gallery photos to photos with source 'news'.
The daily picture never reads this file (build_db.py only reads bapas-diary-YYYY.json).
"""
import json, re, sys, urllib.parse

MONTHS = {m[:3].lower(): i for i, m in enumerate('January February March April May June July August September October '
                                                  'November December'.split(), 1)}
DAY = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+((?:19|20)\d\d)\b')
DAY_US = re.compile(r'\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+((?:19|20)\d\d)\b')


def iso(text):
    """'4 Nov 2006', '04 November  2006' or 'November 4, 2006' -> '2006-11-04' (None when there is no whole date)."""
    text = text or ''
    for m in DAY.finditer(text):
        mon = MONTHS.get(m[2][:3].lower())
        if mon and 1 <= int(m[1]) <= 31:
            return f'{m[3]}-{mon:02d}-{int(m[1]):02d}'
    for m in DAY_US.finditer(text):
        mon = MONTHS.get(m[1][:3].lower())
        if mon and 1 <= int(m[2]) <= 31:
            return f'{m[3]}-{mon:02d}-{int(m[2]):02d}'
    return None


def place(title):
    """'Satsang Shikshan Pariksha Din, London, UK' -> 'London, UK', 'Winter Convention, Los Angeles, CA, USA' -> 'Los Angeles, CA, USA'
    (the town and country at the end; a title with no comma has no place)."""
    title = re.sub(r'\s*[-–]\s*((19|20)\d\d)\s*$', '', title or '').strip()
    parts = [p.strip() for p in title.split(',') if p.strip()]
    if len(parts) < 2:
        return None
    keep = 3 if len(parts) > 3 and len(parts[-2]) <= 3 else 2   # a US state or Canadian province: 'CA', 'NJ', 'ON'
    return ', '.join(parts[1:][-keep:])


def key(p):
    return urllib.parse.unquote(p).lower()


def main(news, dates, out):
    D = json.load(open(news, encoding='utf-8'))
    L = {key(p): d for p, d in json.load(open(dates, encoding='utf-8')).items()}
    res, miss = {}, 0
    for p, a in sorted(D.items()):
        when = iso(L.get(key(p))) or iso(a.get('d')) or iso((a.get('text') or '')[:300])
        miss += not when
        gal = next(iter((a.get('g') or {}).values()), {})
        res[p] = dict(a, date=when, listed=L.get(key(p)), place=place(a.get('t')) or place(gal.get('t')))
    json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{out}: {len(res)} articles, {miss} with no date')


if __name__ == '__main__':
    main(*sys.argv[1:4])
