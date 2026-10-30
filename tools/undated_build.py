"""The undated photos' list for Search (Darpan, 30 Oct 2026), from the checks in release undated-build:

    python3 tools/undated_build.py --undated undated.json --tags undated-tags.json --same same.json --out undated-search.json

Writes {"album": "undated", "p": [[file, tags], ...]} for tools/build_search.py --undated, in the channel's order.
Left out:
  - repeats of another photo in the channel (undated.json dupe_of)
  - photos already in the diary with their date (same.json: SAME or more points agree with a dated photo); Search
    already has them, dated
  - pictures that are not Bapa in person, picked by eye from the contact sheets (DROP): statues and murtis, posters,
    collages, signs, a cartoon, framed portraits and drawings, photos pasted onto a landmark, buildings and scenery
    with no one to see (Darpan, 25 Oct 2026: no murtis, portraits or framed photos)
"""
import argparse, json

SAME = 100   # points that agree with a dated photo: by eye on the same-*.jpg sheets, 50 and over are the same photo
             # (cropped or touched up) and under 50 mostly another photo of the same moment; 100 leaves no doubt
# by eye, 30 Oct 2026, on the sheets of every photo with no clear face of Bapa or with a statue, poster ... score
DROP = {
    # statues and murtis
    'u0200', 'u0227', 'u0269', 'u0356', 'u0359', 'u0377', 'u0406', 'u0411', 'u0758', 'u0784', 'u0785', 'u0786',
    'u0796', 'u0799', 'u0821', 'u0923', 'u0964', 'u1007', 'u1009', 'u1019', 'u1039', 'u1285', 'u1292', 'u1305',
    'u1437', 'u1514', 'u1515', 'u1572', 'u1581', 'u1590', 'u1633', 'u1658', 'u0063', 'u0347', 'u0348', 'u1568',
    # posters, collages, signs, a cartoon, a drawing
    'u0098', 'u0134', 'u0528', 'u0854', 'u0733', 'u0734', 'u0735', 'u0736', 'u0018', 'u0761', 'u0410', 'u0886',
    # framed portraits
    'u0558', 'u0581',
    # pasted onto a landmark (Big Ben, the Eiffel Tower, Akshardham)
    'u0520', 'u0738', 'u0834', 'u1670', 'u0801',
    # buildings and scenery with no one to see
    'u0069', 'u0485', 'u0618', 'u1434', 'u1436', 'u1657', 'u0721',
    # Bapa hidden (only the top of his turban shows)
    'u0006',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--undated'); ap.add_argument('--tags'); ap.add_argument('--same'); ap.add_argument('--out')
    a = ap.parse_args()
    rows = [r for r in json.load(open(a.undated)) if r.get('name')]
    tags = json.load(open(a.tags))
    same = json.load(open(a.same)) if a.same else {}
    keep, dated, dropped = [], 0, 0
    for r in rows:
        n = r['name']
        if n[:-4] in DROP:
            dropped += 1; continue
        if n in same and same[n][1] >= SAME:
            dated += 1; continue
        keep.append([n, tags.get(n, '')])
    json.dump({'album': 'undated', 'p': keep}, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
    print(len(keep), 'undated photos,', dated, 'already in the diary with their date,', dropped, 'not Bapa in person')


if __name__ == '__main__':
    main()
