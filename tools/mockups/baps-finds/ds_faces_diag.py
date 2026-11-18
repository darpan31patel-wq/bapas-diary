"""Why Through the years leaves out baps.org's daily darshan photos (18 Nov 2026): runs faces_years.py's own checks on the
1990 to 1998 photos and prints each one's facts. Website only; reads photos.bapas-diary.com; changes nothing."""
import json, sys, urllib.parse, urllib.request
import cv2, numpy as np
sys.path.insert(0, sys.argv[1])
import faces_years as F
rows = [r for r in json.load(open(sys.argv[2])) if r['year'] < 1999]
like = F.Likeness()
for r in rows:
    key = f"{r['album']}/{r['file']}"
    try:
        body = urllib.request.urlopen(urllib.request.Request('https://photos.bapas-diary.com/m/' + urllib.parse.quote(key), headers={'User-Agent': 'bapas-diary-years'}), timeout=30).read()
    except Exception as e:
        print(key, 'NOT IN STORE', e); continue
    bgr = cv2.imdecode(np.frombuffer(body, np.uint8), cv2.IMREAD_COLOR)
    f, sim = F.bapa(bgr, 'psm')
    if f is None:
        print(key, r['date_from'], bgr.shape, 'no Bapa face, sim', round(float(sim), 2)); continue
    s, facts = F.score(bgr, f, sim)
    fake = like(bgr, f)
    why = [n for n, ok in (('gap', facts['gap'] >= F.MIN_SPAN or (facts['gap'] >= F.min_span(r['date_from'], bgr) and facts['close'] >= F.MORE_CLOSE)),
                           ('front', facts['front'] >= F.FRONT_MIN), ('sharp', facts['sharp'] >= F.SHARP_MIN),
                           ('bright', facts['bright'] >= F.BRIGHT_MIN), ('picture of him', fake <= F.LIKENESS_MAX)) if not ok]
    print(key, r['date_from'], bgr.shape, 'PASS' if not why else 'fails ' + ','.join(why), {k: round(float(v), 2) for k, v in facts.items()}, 'fake', round(float(fake), 2))
