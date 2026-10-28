"""A day pack for the collage builder dashboard (Darpan, 25 Oct 2026: 'a dashboard ... I just click export').

For one date it picks photos exactly as the daily run does, then saves each year's best few photos (the one the
daily picture would show first), with Bapa's face box, caption, place and festival, plus the day's title and
calendar line, so the dashboard can swap photos, crops and text and draw the picture itself.

    python tools/dashboard_pack.py 2026-10-25 dashboard/packs
writes dashboard/packs/2026-10-25/pack.json, the photos beside it and real.jpg (the daily run's own picture).
Every photo of the year where Bapa is recognised is kept too (Darpan, 26 Oct 2026: 'let me browse ALL the photos'):
the best six in <year>-best.jpg, the rest smaller in <year>-more.jpg (photos joined end to end; pack.json gives each
one's place), with a sheet of small thumbnails per year (<year>-thumbs.jpg), so the pack stays light.
Read only: nothing here changes the daily picture, shown.json or the release."""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import Image
from PIL import ImageOps

LONG = 1000   # the long side of each of the best six photos
MORE = 720    # the long side of every other photo of the year
CELL = 160    # thumbnail sheet: square cells, COLS a row
COLS = 10
FACES = {}    # path -> Bapa's face box, as the daily pick found it


def watch_faces():
    """Note every face the daily pick finds, so the photos it doesn't keep in its short list can be offered too."""
    from PIL import Image as PIL
    opened, find, last = PIL.open, make.bapa_face, [None]
    def open_(fp, *a, **k):
        last[0] = fp
        return opened(fp, *a, **k)
    def face(im, *a, **k):
        r = find(im, *a, **k)
        FACES[last[0]] = r[0]
        return r
    PIL.open, make.bapa_face = open_, face
    return lambda: (setattr(PIL, 'open', opened), setattr(make, 'bapa_face', find))


def thumbs(ims, faces, path):
    """One sheet of square thumbnails, COLS a row, each cut square around Bapa's face (or the middle)."""
    rows = -(-len(ims) // COLS)
    sheet = Image.new('RGB', (CELL * min(COLS, len(ims)), CELL * rows))
    for i, (im, f) in enumerate(zip(ims, faces)):
        mid = ((f[0] + f[2] / 2) / im.width, (f[1] + f[3] / 2) / im.height) if f else (.5, .4)
        sheet.paste(ImageOps.fit(im, (CELL, CELL), Image.LANCZOS, centering=mid), ((i % COLS) * CELL, (i // COLS) * CELL))
    sheet.save(path, quality=72)


def items_for(day, cache):
    """The day's photos, gathered as make.main() does."""
    mmdd = f'{day:%m-%d}'
    items = make.day_list(mmdd)
    collected = os.path.join(make.HERE, 'archive', mmdd + '.json')
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have and x['y'] < day.year]   # past years only, as make.main()
    combed = os.path.join(make.HERE, 'archive', 'vicharan', mmdd + '.txt')
    if os.path.exists(combed):
        have = {x['i'] for x in items}
        place = {x['y']: x.get('p', '') for x in items}
        extra = [x for x in make.vicharan_items(combed, mmdd, place) if x['y'] < day.year]
        full = {x['i']: x['c'] for x in extra}
        for x in items:
            if (x.get('c') or '').endswith('...') and x['i'] in full:
                x['c'] = full[x['i']]
        items += [x for x in extra if x['i'] not in have]
    make.album_towns(items)
    tg_extra, tg_evs, special = make.tg_day(day, items)
    items += tg_extra
    make.download_all(items, cache)
    make.unframe(items)
    return items, tg_evs


def main():
    day = datetime.date.fromisoformat(sys.argv[1])
    out = os.path.join(sys.argv[2] if len(sys.argv) > 2 else 'dashboard/packs', str(day))
    os.makedirs(out, exist_ok=True)
    seen = make.shown
    make.shown = lambda: {d: v for d, v in seen().items() if d < str(day)}   # only the days before it, as its own morning run sees them
    items, tg_evs = items_for(day, os.path.join(make.HERE, '.cache'))
    unwatch = watch_faces()
    photos = make.pick_one_per_year(items, seed=f'{day:%m-%d}', aspect=make.FRAME_ASPECT[make.LIVE_STYLE], day=day)
    unwatch()
    make.tag_festivals(photos)
    story = make.tg_story(tg_evs, photos)
    make.compose(photos, day, seed=f'{day:%m-%d}', style=make.LIVE_STYLE, history=story).convert('RGB') \
        .resize((2400, round(2400 * make.H / make.W)), Image.LANCZOS).save(os.path.join(out, 'real.jpg'), quality=85)

    years = []
    for w in make.WORKINGS:
        if w['pick'] is None:
            continue
        rows = [w['pick']] + [x for _, x, _ in w['rows'] if x is not w['pick']]
        have = {x['i'] for x in rows}
        # every other photo of the year: first those where Bapa is recognised (biggest face first), then the rest, so
        # any photo of the day can be chosen (Darpan, 28 Oct 2026: 'all the pictures available for that year')
        more, rest = [], []
        for x in items:
            if x['y'] != w['year'] or x['i'] in have or 'path' not in x or make.JUNK.search(x.get('c') or ''):
                continue
            have.add(x['i'])
            face = FACES.get(x['path'])
            (more if face else rest).append(dict(x, face=face, crop='frame' if face else 'whole', special=make.is_special(x.get('c') or ''), nobapa=not face))
        more.sort(key=lambda x: -x['face'][3])
        cands, ims = [], []
        blobs = {f: open(os.path.join(out, f'{w["year"]}-{f}.jpg'), 'wb') for f in ('best', 'more')}
        for k, x in enumerate(rows[:6] + more + rest):
            try:
                im = x['im'].copy() if 'im' in x else Image.open(x['path']).convert('RGB')
            except Exception:
                continue
            s = min(1, (LONG if k < 6 else MORE) / max(im.size)); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            f = 'best' if k < 6 else 'more'
            at = blobs[f].tell(); im.save(blobs[f], 'JPEG', quality=82 if k < 6 else 76)
            ims.append(im)
            d = str(x.get('d') or '')[:10]
            fs = make.festivals(make.cal_day(d)) if len(d) == 10 else []
            cands.append(dict(f=f'{w["year"]}-{f}.jpg', at=[at, blobs[f].tell() - at], w=im.width, h=im.height,
                              face=[round(v * s, 1) for v in x['face']] if x['face'] else None,
                              crop=x.get('crop', 'frame'), caption=make.caption(x), original=x.get('c') or '',
                              place=make.place(x), date=d, special=bool(x.get('special')), nice=bool(x.get('nice')),
                              festival=fs[0] if fs else '', **({'nobapa': True} if x.get('nobapa') else {})))
        for f, b in blobs.items():
            b.close()
            if os.path.getsize(b.name) == 0:
                os.remove(b.name)
        thumbs(ims, [c['face'] for c in cands], os.path.join(out, f'{w["year"]}-thumbs.jpg'))
        years.append(dict(year=w['year'], mode=w['mode'], cands=cands, thumbs=f'{w["year"]}-thumbs.jpg'))
    cal = make.cal_footer(day)
    pack = dict(date=str(day), title=make.cal_title(day) or f'{day.day} {day:%B}', subtitle='in Bapa’s Diary',
                footer=make.FOOTER, cal_line=cal[0] if cal else '', tomorrow=cal[1] if cal else '',
                story=dict(year=story['date'][:4], line=story.get('line', '')) if story else None,
                years=years, cell=CELL, cols=COLS, every=True, made=datetime.datetime.utcnow().isoformat(timespec='minutes') + 'Z')
    json.dump(pack, open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{day}: {len(years)} years, {sum(len(y["cands"]) for y in years)} photos -> {out}')


if __name__ == '__main__':
    main()
