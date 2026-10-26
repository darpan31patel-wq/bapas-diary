#!/usr/bin/env python3
"""Then and now page for bapas-diary.com/then-and-now/ (Darpan typed '1 and 2 happy go live', 25 Oct 2026).

    python3 tools/build_then_now.py site/then-now-picks.json site/then-now.html OUT.html [large-keys.txt]

site/then-now-picks.json holds the chosen pairs (picked by eye from tools/then_now.py's contact sheets): place, moment,
and for each guru the photo's date, caption, album and file. The page shows the photos straight from R2
(photos.bapas-diary.com/m/ALBUM/FILE). Also prints the place links for the Travels card (/then-and-now/#slug).
Website only: nothing here touches the daily picture.
"""
import json, re, sys

picks = json.load(open(sys.argv[1]))
# a 4th argument: R2's list of full screen keys (l/ALBUM/FILE, 2560 px, Darpan 26 Oct 2026: high res everywhere);
# a photo that has one is shown from l/, the rest from the web size m/
if len(sys.argv) > 4:
    large = set(l.strip() for l in open(sys.argv[4]))
    for p in picks:
        for g in ('psm', 'msm'):
            p[g]['t'] = 'l' if f"l/{p[g]['album']}/{p[g]['file']}" in large else 'm'
page = open(sys.argv[2]).read().replace('__DATA__', json.dumps(picks, ensure_ascii=False, separators=(',', ':')))
open(sys.argv[3], 'w').write(page)
names = sorted({p['place'].split(',')[0] for p in picks})
print(json.dumps({n: re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-') for n in names}))
