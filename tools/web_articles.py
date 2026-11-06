"""The baps.org News stories of each day, for the gold "From the baps.org story" line on Today and in the Calendar day box
(Darpan, 4 Nov 2026: "would be nice to link these articles to the calender or today"; 4 Nov 23:21 "yes to all").

    python3 tools/web_articles.py --articles articles.json --out out/data/articles

articles.json is crawl/news/articles.json on the database branch (every News article, read in his Chrome 4 to 6 Nov 2026,
each with its date). Writes one small file a day, MM-DD.json: {"2006": [[title, link], ...], ...}, at most three stories a
year, the ones about Bapa first, then the ones with the most photos.
"""
import argparse, json, os, re

BAPA = re.compile(r'Pramukh Swami|Mahant Swami|Swamishri|\bHH\b|\bHDH\b|Vicharan|Guruhari', re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--articles', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    try:
        A = json.load(open(a.articles, encoding='utf-8'))
    except (OSError, ValueError):
        A = {}
    days = {}
    for path, x in A.items():
        d, t = x.get('date'), re.sub(r'\s+', ' ', x.get('t') or '').strip()
        if not d or not t or not re.match(r'\d{4}-\d{2}-\d{2}$', d):
            continue
        n = len(x.get('own') or []) + sum(len(g.get('rows') or []) for g in (x.get('g') or {}).values())
        days.setdefault(d[5:], {}).setdefault(d[:4], []).append((not BAPA.search(t), -n, t, 'https://www.baps.org' + path))
    os.makedirs(a.out, exist_ok=True)
    for md, years in days.items():
        json.dump({y: [[t, u] for _, _, t, u in sorted(v)[:3]] for y, v in sorted(years.items())},
                  open(os.path.join(a.out, md + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{len(A)} stories on {len(days)} days of the year')


if __name__ == '__main__':
    main()
