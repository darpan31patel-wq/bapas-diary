"""Prasang stories from the baps.org Daily Satsang page, filed under the day each one happened (Darpan, 13 Nov 2026:
"Yes to all"; English first with a small switch to the Gujarati beside each story, "because I'm not 100% confident on
your translation").

data/baps/prasang.json is keyed by the Daily Satsang page date: {d: the prasang's own date YYYY-MM-DD, place,
who: psm|msm, title, gu: [paragraphs as baps.org wrote them], en: [English translation]}.
Writes OUT/MM-DD.json = {"YYYY": [[place, who, title, [en], [gu], source url], ...]} for Today and the Calendar day box.
Website only: the daily 2pm picture never reads this.
"""
import argparse, json, re
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--prasang', default='data/baps/prasang.json')
ap.add_argument('--out', required=True)
a = ap.parse_args()

P = json.loads(Path(a.prasang).read_text()) if Path(a.prasang).exists() else {}
by = defaultdict(lambda: defaultdict(list))
seen = set()
for page, s in sorted(P.items()):
    d = s.get('d') or ''
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) or not s.get('gu'):
        continue
    key = (d, ' '.join(s['gu'])[:200])
    if key in seen:   # baps.org sometimes repeats a prasang on another day: show it once
        continue
    seen.add(key)
    y, m, dd = page.split('-')
    src = f'https://www.baps.org/Daily-Satsang.aspx?dt={int(m)}-{int(dd)}-{y}'
    by[d[5:]][d[:4]].append([s.get('place', ''), s.get('who', ''), s.get('title', ''), s.get('en') or [], s['gu'], src])

out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
for md, years in by.items():
    (out / f'{md}.json').write_text(json.dumps(years, ensure_ascii=False, separators=(',', ':')))
print(f'{sum(len(v) for y in by.values() for v in y.values())} prasangs on {len(by)} days of the year')
