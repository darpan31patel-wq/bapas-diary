"""Every photo of each day of the year for Darpan's private Studio (/darpan/), not only the ones the face checker
picked for the public Today page (Darpan, 18 Nov 2026: the Studio said "2000, 1 photo of this day" for a story with 90
photos; "everything for the special feature, needs to be FROM THIS DAY").

    python3 tools/web_studio_days.py --db bapas.db --public out/data/day --out out/darpan/days

Writes out/darpan/days/MM-DD.json in the shape of the public data/day files:
  {"date": "11-30", "years": [{"y": 2000, "place": "Anand", "p": [[album, file, caption, bapa, face, short, found], ...]}]}
found is 1 when the face checker found Bapa (the photo is on the public Today card), else 0; those come first, in the
Today card's order. The files sit behind the Studio password (functions/darpan/_middleware.js) and are website only:
nothing here touches the daily 2pm picture. Run it on the build's copy of the database after news_ready.py --prune,
so a News photo whose file is not in the photo store yet never shows as an empty tile.
"""
import argparse, json, os, sqlite3, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'tools')]
from web_places import town_of   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--public', default='out/data/day', help='the public Today day files (face checked photos)')
    ap.add_argument('--out', default='out/darpan/days')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    db = sqlite3.connect(a.db)
    days, places = {}, {}
    for date, y, place, album, file, cap, bapa in db.execute(
            "SELECT date, year, place, album, file, caption, is_bapa FROM photos WHERE date IS NOT NULL "
            "ORDER BY date, album, file"):
        mmdd, y = date[5:10], int(date[:4])
        days.setdefault(mmdd, {}).setdefault(y, []).append([album, file, cap or '', bapa or 0, None, '', 0])
        if place:
            places.setdefault((mmdd, y), {}).setdefault(town_of(place), 0)
            places[(mmdd, y)][town_of(place)] += 1
    total = found_all = 0
    for mmdd, years in sorted(days.items()):
        pub = {}
        try:
            for Y in json.load(open(os.path.join(a.public, mmdd + '.json')))['years']:
                pub[int(Y['y'])] = Y
        except (OSError, ValueError, KeyError):
            pass
        out = []
        for y in sorted(years, reverse=True):
            rows, P = years[y], pub.get(y, {})
            first = []
            for p in P.get('p', []):   # the Today card's photos, face found, in its order, with its face box
                first.append([p[0], p[1], p[2] if len(p) > 2 else '', p[3] if len(p) > 3 else 0,
                              p[4] if len(p) > 4 else None, p[5] if len(p) > 5 else '', 1])
            seen = {(p[0], p[1].lower()) for p in first}
            rest = [r for r in rows if (r[0], r[1].lower()) not in seen]
            rest.sort(key=lambda r: -r[3])   # captions about Bapa before the others, album order kept within each
            pl = P.get('place') or max(places.get((mmdd, y), {'': 0}).items(), key=lambda kv: kv[1])[0]
            out.append({'y': y, 'place': pl, 'p': first + rest})
            total += len(first) + len(rest)
            found_all += len(first)
        json.dump({'date': mmdd, 'years': out}, open(os.path.join(a.out, mmdd + '.json'), 'w'), ensure_ascii=False,
                  separators=(',', ':'))
    print(f'Studio days: {total:,} photos on {len(days)} days, {found_all:,} of them with Bapa\'s face found')


if __name__ == '__main__':
    main()
