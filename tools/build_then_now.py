#!/usr/bin/env python3
"""Then and now page for bapas-diary.com/then-and-now/ (Darpan typed '1 and 2 happy go live', 25 Oct 2026).

    python3 tools/build_then_now.py site/then-now-picks.json site/then-now.html OUT.html

site/then-now-picks.json holds the chosen pairs (picked by eye from tools/then_now.py's contact sheets): place, moment,
and for each guru the photo's date, caption, album and file. The page shows the photos straight from R2
(photos.bapas-diary.com/m/ALBUM/FILE). Also prints the place links for the Travels card (/then-and-now/#slug).
Website only: nothing here touches the daily picture.
"""
import json, re, sys

picks = json.load(open(sys.argv[1]))
page = open(sys.argv[2]).read().replace('__DATA__', json.dumps(picks, ensure_ascii=False, separators=(',', ':')))
open(sys.argv[3], 'w').write(page)
names = sorted({p['place'].split(',')[0] for p in picks})
print(json.dumps({n: re.sub(r'[^a-z0-9]+', '-', n.lower()) for n in names}))
