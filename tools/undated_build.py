"""The undated photos' list for Search (Darpan, 30 Oct 2026), from the checks in release undated-build:

    python3 tools/undated_build.py --undated undated.json --tags undated-tags.json --same same.json --out undated-search.json

Writes {"album": "undated", "p": [[file, tags, caption], ...]} for tools/build_search.py --undated, in the channel's
order. The caption is a word or two for what is happening (CAPTIONS), else "Darshan".
Left out:
  - repeats of another photo in the channel (undated.json dupe_of)
  - photos already in the diary with their date (same.json: SAME or more points agree with a dated photo); Search
    already has them, dated
  - pictures that are not Bapa in person, picked by eye from the contact sheets (DROP): statues and murtis, posters,
    collages, signs, a cartoon, framed portraits and drawings, photos pasted onto a landmark, buildings and scenery
    with no one to see (Darpan, 25 Oct 2026: no murtis, portraits or framed photos)
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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

# One simple caption for what is happening (Darpan, 30 Oct 2026: "just have a simple title like darshan ... blessings or
# darshan or vicharan"), from the deep tags' SigLIP numbers: each caption's words against the photo, less the word's
# bar (KEEP in tools/deep_words.py, or the top 5% where it has none). A caption needs at least its own bar below, set
# by eye on contact sheets of these photos ranked by each caption; the one furthest over its bar wins, else Darshan.
CAPTIONS = {
    'Arti': (['arti', 'lighting lamp'], .5),
    'Puja': (['puja', 'abhishek', 'pushpanjali'], 4),
    'Blessings': (['blessing', 'patting head'], 3.8),
    'Pravachan': (['speaking'], 3),
    'Reading': (['reading'], 2),
    'Writing letters': (['writing'], 3.5),
    'Vicharan': (['in a car', 'on a plane', 'on a boat', 'walking'], 3),
    'Sabha': (['assembly', 'on a stage'], 2),
    'Meeting devotees': (['shaking hands', 'hugging', 'giving prasad'], 2.7),
    'Honoured with a garland': (['garland'], 2.5),
    'With sadhus': (['saints'], 2.5),
    'With children': (['children'], 2),
    'With youths': (['youths'], 3),
}


def captions(emb, words):
    """{photo: caption} for the photos in emb (emb-undated.npz) with the word numbers of words (release deep-tags)."""
    import numpy as np
    from deep_words import KEEP
    w, z = np.load(words), np.load(emb)
    names = list(w['words'])
    L = z['emb'].astype('f4') @ w['emb'].T * float(w['scale']) + float(w['bias'])
    bars = {}
    for ws in KEEP.values():
        for n, b in ws:
            bars.setdefault(n, b)
    over = {}
    for c, (ws, need) in CAPTIONS.items():
        cols = [L[:, names.index(n)] - bars.get(n, np.percentile(L[:, names.index(n)], 95)) for n in ws]
        over[c] = np.max(np.stack(cols), 0) - need
    out = {}
    for i, k in enumerate(z['keys']):
        best = max(CAPTIONS, key=lambda c: over[c][i])
        out[str(k)] = best if over[best][i] >= 0 else 'Darshan'
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--undated'); ap.add_argument('--tags'); ap.add_argument('--same'); ap.add_argument('--out')
    ap.add_argument('--emb', help='emb-undated.npz (release undated-build)'); ap.add_argument('--words', help='words.npz (release deep-tags)')
    a = ap.parse_args()
    rows = [r for r in json.load(open(a.undated)) if r.get('name')]
    cap = captions(a.emb, a.words) if a.emb else {}
    tags = json.load(open(a.tags))
    same = json.load(open(a.same)) if a.same else {}
    keep, dated, dropped = [], 0, 0
    for r in rows:
        n = r['name']
        if n[:-4] in DROP:
            dropped += 1; continue
        if n in same and same[n][1] >= SAME:
            dated += 1; continue
        keep.append([n, tags.get(n, ''), cap.get(n, 'Darshan')])
    json.dump({'album': 'undated', 'p': keep}, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
    print(len(keep), 'undated photos,', dated, 'already in the diary with their date,', dropped, 'not Bapa in person')


if __name__ == '__main__':
    main()
