#!/usr/bin/env python3
"""Photos for the BAPS calendar style poster mockups (Darpan, 23 Oct 2026). Runs on GitHub, which can load
baps.org's photos: picks a month's photos the way the month cards do (tools/month.py) and saves them small, with
their captions, places and where Bapa's face is, in preview/poster/<month>/ so the posters can be drawn anywhere.

    python tools/poster_photos.py --month 2012-01
    python tools/poster_photos.py --month 2024-02 --db bapas.db --need > need.txt      the archive copies it needs
    python tools/poster_photos.py --month 2024-02 --db bapas.db --drive archive        from Bapa's Archive, not baps.org

baps.org asked us to slow down (23 Oct 2026), so a month already in Bapa's Archive on Drive is read from there: the
biggest copy baps.org had, at the path bapas.db gives it (photos.local_path).

Mockups only: nothing here touches the daily picture.
"""
import argparse, json, os, sqlite3, sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make    # noqa: E402
import month   # noqa: E402


def save(x, out, name, long=1600):
    im = month.load(x)
    k = long / max(im.size)
    if k < 1:
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    else:
        k = 1
    im.save(os.path.join(out, name), quality=90 if long >= 1600 else 82)
    fx, fy, fw, fh = x['face']
    return dict(file=name, day=int(x['d'][8:10]), date=x['d'][:10], caption=make.caption(x), place=make.place(x) or '',
                face=[round(v * k) for v in (fx, fy, fw, fh)], size=list(im.size), close_ok=x['close_ok'],
                special=x['special'], s_close=round(x['s_close'], 2), s_act=round(x['s_act'], 2), url=x['i'],
                album=make.album(x['i']), doing=bool(x.get('doing')), subject=month.subject(x) if x.get('c') else False,
                front=round(x.get('front', 0), 2), sim=round(x.get('sim', 0), 2), unsure=bool(x.get('unsure')))


def any_face(x):
    """For a day where the face check recognised Bapa in no photo: a looser match first (similarity .35), then the
    biggest face found at all. The day is marked unsure so the poster can flag it."""
    im = month.load(x)
    face, sim = make.bapa_face(im, x['d'], need=.35)
    if not face:
        small = im.copy(); small.thumbnail((1280, 1280))
        k = im.width / small.width
        bgr = make.cv2.cvtColor(make.np.array(small), make.cv2.COLOR_RGB2BGR)
        with make.FACE_LOCK:
            make.DETECT.setInputSize((bgr.shape[1], bgr.shape[0]))
            faces = make.DETECT.detect(bgr)[1]
        if faces is None or not len(faces):
            return None
        f = max(faces, key=lambda f: f[2] * f[3])
        face, sim = tuple(float(v) * k for v in f[:4]), 0
    return dict(x, face=face, sim=sim, front=0, close_ok=False, special=False, doing=False, s_close=-5 + sim, s_act=-5, size=im.size,
                unsure=True)


def archive_paths(items, db):
    """Each photo's path in Bapa's Archive (photos.local_path in bapas.db), None when the database doesn't know it."""
    con = sqlite3.connect(db)
    out = []
    for x in items:
        r = con.execute('SELECT local_path FROM photos WHERE album = ? AND file = ? COLLATE NOCASE', (make.album(x['i']), x['i'].rsplit('/', 1)[1])).fetchone()
        out.append(r[0] if r and r[0] else None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--month', default='2012-01')
    ap.add_argument('--cache', default=os.path.join(month.HERE, '.cache', 'month'))
    ap.add_argument('--db', help='bapas.db, to find each photo in the archive')
    ap.add_argument('--need', action='store_true', help='print the archive paths this month needs, one a line')
    ap.add_argument('--drive', help='folder holding the archive copies (rclone copy --files-from the --need list)')
    a = ap.parse_args()
    y, m = map(int, a.month.split('-'))
    items = [x for x in month.month_items(y, m) if not make.JUNK.search(x.get('c') or '')]
    if a.need:
        print('\n'.join(sorted({p for p in archive_paths(items, a.db) if p})))
        return
    out = os.path.join(month.HERE, 'preview', 'poster', a.month)
    os.makedirs(out, exist_ok=True)
    if a.drive:
        got = [dict(x, path=os.path.join(a.drive, p)) for x, p in zip(items, archive_paths(items, a.db))
               if p and os.path.exists(os.path.join(a.drive, p))]
        print(f'  {len(got)} of {len(items)} photos found in the archive', flush=True)
    else:
        got = month.full_size(items, a.cache)
    if not got:
        sys.exit('No photos found for the month, so the photos saved before are kept')
    photos = month.analyse(got)
    mo = month.Month(photos, y, m)
    meta, done = dict(month=a.month, places=mo.places, count=mo.count, close={}, act={}, highlights=[], extra={}), {}

    def keep(x, tag, long=1600):
        if x['i'] not in done:
            done[x['i']] = save(x, out, f'{tag}.jpg', long)
        return done[x['i']]
    for d, x in mo.close.items():
        meta['close'][d] = keep(x, f'{d:02d}-close')
    for d, x in mo.act.items():
        meta['act'][d] = keep(x, f'{d:02d}-act')
    for i, x in enumerate(mo.highlights[:16]):
        meta['highlights'].append(keep(x, f'hl{i:02d}'))
    # every photo of the day where Bapa is recognised, best first, so the poster can pick without repeats and fall
    # back when a crop won't fit (design brief, 23 Oct 2026), and the Studio can offer them all (Darpan, 26 Oct 2026);
    # past the best six they are kept smaller
    meta['cands'] = {}
    for d, xs in mo.by.items():
        best = sorted(xs, key=lambda x: -max(x['s_close'], x['s_act']))
        meta['cands'][d] = [keep(x, f'{d:02d}-c{n}', 1600 if n < 6 else 1000) for n, x in enumerate(best)]
    # a day where Bapa was recognised in no photo still gets one (something for every day), marked unsure
    for d in range(1, month.calendar.monthrange(y, m)[1] + 1):
        if d in mo.by:
            continue
        tries = [x for x in got if x['d'][:10] == f'{a.month}-{d:02d}' and not make.JUNK.search(x.get('c') or '')]
        found = [f for f in (any_face(x) for x in tries[:12]) if f]
        found.sort(key=lambda x: (-x['sim'], -x['face'][3] / x['size'][1]))
        if found:
            meta['cands'][d] = [keep(x, f'{d:02d}-u{n}') for n, x in enumerate(found[:3])]
            meta['close'].setdefault(d, meta['cands'][d][0])
            meta['extra'].setdefault(d, sorted({make.caption(x) for x in found} - {''}))
    for d, xs in mo.by.items():      # every caption of the day, for the 'what happened' lines
        meta['extra'][d] = sorted({make.caption(x) for x in xs if make.caption(x)})
    json.dump(meta, open(os.path.join(out, 'photos.json'), 'w'), indent=1, ensure_ascii=False)
    print(mo.summary())


if __name__ == '__main__':
    main()
