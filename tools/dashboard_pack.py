"""A day pack for the collage builder dashboard (Darpan, 25 Oct 2026: 'a dashboard ... I just click export').

For one date it picks photos exactly as the daily run does, then saves each year's best few photos (the one the
daily picture would show first), with Bapa's face box, caption, place and festival, plus the day's title and
calendar line, so the dashboard can swap photos, crops and text and draw the picture itself.

    python tools/dashboard_pack.py 2026-10-25 dashboard/packs
writes dashboard/packs/2026-10-25/pack.json, the photos beside it and real.jpg (the daily run's own picture).
Every photo of the year where Bapa is recognised is kept too (Darpan, 26 Oct 2026: 'let me browse ALL the photos'):
the best six in <year>-best.jpg, the rest smaller in <year>-more.jpg (photos joined end to end; pack.json gives each
one's place), with a sheet of small thumbnails per year (<year>-thumbs.jpg), so the pack stays light.
To open fast (website project, 13 Nov 2026) the pack also carries picks.jpg, one sheet with every card's chosen photo
at card size, and <year>-small.jpg, the best six again at half the size. Both are extras: nothing else changes.
Read only: nothing here changes the daily picture, shown.json or the release."""
import datetime, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import Image
from PIL import ImageOps

LONG = 1000   # the long side of each of the best six photos
MORE = 720    # the long side of every other photo of the year
SMALL = 500   # the best six again, small, for a quick first look (<year>-small.jpg)
PICK = 560    # picks.jpg: the long side of each card's chosen photo, about the size a card shows it on a screen
SHEET = 4096  # picks.jpg is never wider than this
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


def picks_sheet(picks, path):
    """One picture holding the chosen photo of every card, whole (not cut to the frame), long side PICK, laid in rows
    left to right, so the Studio can draw the day from a single file. picks: [(year entry, photo)]; each year entry
    gains pick=[x, y, w, h], its photo's place on the sheet. Returns the pack's top level 'picks' entry."""
    small, x, y, tall, wide = [], 0, 0, 0, 0
    for entry, im in picks:
        s = min(1, PICK / max(im.size))
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        if x and x + im.width > SHEET:
            x, y, tall = 0, y + tall, 0
        entry['pick'] = [x, y, im.width, im.height]
        small.append((im, (x, y)))
        x += im.width; tall = max(tall, im.height); wide = max(wide, x)
    if not small:
        return None
    sheet = Image.new('RGB', (wide, y + tall))
    for im, at in small:
        sheet.paste(im, at)
    sheet.save(path, quality=80, optimize=True, progressive=True)
    return dict(f=os.path.basename(path), w=sheet.width, h=sheet.height, long=PICK)


def festival_tag(x, reach=3):
    """The festival tab for a photo in the Studio's packs: the daily picture's own tag (make.festival_of: the photo's
    date is the festival and its caption says so), else a festival up to `reach` days either side of its date that its
    own caption names (Darpan, 6 Nov 2026: 2002's Diwali to Annakut album in Ramod is filed under 3 November, so its
    Annakut photos never got the tag). Packs only: the morning run's picture and its picks still use festival_of."""
    got = make.festival_of(x)
    if got:
        return got
    d, c = str(x.get('d') or '')[:10], x.get('c') or ''
    if not c or not re.fullmatch(r'\d{4}-\d\d-\d\d', d):
        return ''
    try:
        when = datetime.date.fromisoformat(d)
    except ValueError:
        return ''
    found = []
    for k in sorted(range(-reach, reach + 1), key=abs):
        n = str(when + datetime.timedelta(days=k))
        fs = make.festivals(n) if make.cal_day(n) else make.old_festivals(n)
        hits = [f for f in fs if f in make.TAGS and re.search(make.TAGS[f], c, re.I)]
        if {'Annakut', 'New Year'} & set(hits) and {'Annakut', 'New Year'} <= set(fs):
            hits = ['Annakut and New Year'] + [f for f in hits if f not in ('Annakut', 'New Year')]
        found += [(n, f) for f in hits if f not in [g for _, g in found]]
    names = [p for _, f in sorted(found) for p in f.split(' and ')]   # 'Diwali, Annakut and New Year'
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1] if names else ''


ALBUMS = {}   # baps.org album -> (first day, last day) from the archive database


def album_days(items):
    """Each baps.org album's own first and last day (Darpan, 6 Nov 2026: 'album covers 3 to 10 November 2002'), read
    from the archive database (bapas.db): {album: (first, last)}. Nothing when the database isn't to hand."""
    want = sorted({k[0] for k in (make.baps_key(x['i']) for x in items) if k} - set(ALBUMS))
    if want and os.path.exists(make.ARCHIVE_DB):
        try:
            db = sqlite3.connect(make.ARCHIVE_DB)
            for i in range(0, len(want), 500):
                part = want[i:i + 500]
                for a, lo, hi in db.execute(f'SELECT album, min(coalesce(date, date_from)), max(coalesce(date, date_to)) FROM photos '
                                            f'WHERE album IN ({",".join("?" * len(part))}) GROUP BY album', part):
                    ALBUMS[a] = (lo and lo[:10], hi and hi[:10])
            db.close()
        except Exception as e:
            print('  album days not read:', e)
    for a in want:
        ALBUMS.setdefault(a, (None, None))
    return ALBUMS


def album_span(x):
    """(album_from, album_to) for a photo: both None when its album is a single day or isn't known."""
    k = make.baps_key(x.get('i') or '')
    lo, hi = ALBUMS.get(k[0], (None, None)) if k else (None, None)
    return (lo, hi) if lo and hi and lo != hi else (None, None)


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
    album_days(items)
    unwatch = watch_faces()
    photos = make.pick_one_per_year(items, seed=f'{day:%m-%d}', aspect=make.FRAME_ASPECT[make.LIVE_STYLE], day=day)
    unwatch()
    make.tag_festivals(photos)
    story = make.tg_story(tg_evs, photos)
    make.compose(photos, day, seed=f'{day:%m-%d}', style=make.LIVE_STYLE, history=story).convert('RGB') \
        .resize((2400, round(2400 * make.H / make.W)), Image.LANCZOS).save(os.path.join(out, 'real.jpg'), quality=85)

    years, picks = [], []
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
        blobs = {f: open(os.path.join(out, f'{w["year"]}-{f}.jpg'), 'wb') for f in ('best', 'more', 'small')}
        for k, x in enumerate(rows[:6] + more + rest):
            try:
                im = x['im'].copy() if 'im' in x else Image.open(x['path']).convert('RGB')
            except Exception:
                continue
            s = min(1, (LONG if k < 6 else MORE) / max(im.size)); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            f = 'best' if k < 6 else 'more'
            at = blobs[f].tell(); im.save(blobs[f], 'JPEG', quality=82 if k < 6 else 76)
            ims.append(im)
            tiny = None
            if k < 6:   # the same photo again at half the size, for a quick first look
                t = min(1, SMALL / max(im.size)); sm = im.resize((max(1, round(im.width * t)), max(1, round(im.height * t))), Image.LANCZOS)
                sat = blobs['small'].tell(); sm.save(blobs['small'], 'JPEG', quality=78)
                tiny = dict(f=f'{w["year"]}-small.jpg', at=[sat, blobs['small'].tell() - sat], w=sm.width, h=sm.height)
            d = str(x.get('d') or '')[:10]
            fest = festival_tag(x)   # the daily picture's tab (Darpan, 4 Nov 2026), or a nearby festival its own caption names (6 Nov 2026)
            lo, hi = album_span(x)
            cands.append(dict(f=f'{w["year"]}-{f}.jpg', at=[at, blobs[f].tell() - at], w=im.width, h=im.height,
                              face=[round(v * s, 1) for v in x['face']] if x['face'] else None,
                              crop=x.get('crop', 'frame'), caption=make.caption(x), original=x.get('c') or '',
                              place=make.place(x), date=d, special=bool(x.get('special')), nice=bool(x.get('nice')),
                              festival=fest, album_from=lo, album_to=hi, **({'small': tiny} if tiny else {}), **({'nobapa': True} if x.get('nobapa') else {})))
        for f, b in blobs.items():
            b.close()
            if os.path.getsize(b.name) == 0:
                os.remove(b.name)
        thumbs(ims, [c['face'] for c in cands], os.path.join(out, f'{w["year"]}-thumbs.jpg'))
        years.append(dict(year=w['year'], mode=w['mode'], cands=cands, thumbs=f'{w["year"]}-thumbs.jpg'))
        if ims:
            picks.append((years[-1], ims[0]))
    sheet = picks_sheet(picks, os.path.join(out, 'picks.jpg'))
    cal = make.cal_footer(day)
    # the words the morning run puts under Darpan's 2pm WhatsApp caption (caption.txt), so the Studio can show and change them
    town = lambda e: (e['date'][:10], make.re.split(r'[,(]', e.get('place') or '')[0].strip().lower())
    pictured = {town(story)} if story else set()
    pictured |= {(f'{x["y"]}', town({'date': '', 'place': x.get('p')})[1]) for x in photos}
    cards = {x.get('post') for x in photos if x.get('post')}
    left = [e for e in tg_evs if town(e) not in pictured and e.get('url') not in cards and not any(make.tells(x, e) for x in photos)
            and not (e.get('channel') and (e['date'][:4], town(e)[1]) in pictured)]
    told = max(left, key=make.tg_rank, default=None)
    wa = make.cal_caption(day, None)
    wa = wa + (('\n' if wa else '') + make.tg_caption(told, left) if told else '')
    pack = dict(date=str(day), title=make.cal_title(day) or f'{day.day} {day:%B}', subtitle='in Bapa’s Diary',
                footer=make.FOOTER, cal_line=cal[0] if cal else '', tomorrow=cal[1] if cal else '',
                story=dict(year=story['date'][:4], line=story.get('line', '')) if story else None,
                whatsapp=wa.strip(), years=years, cell=CELL, cols=COLS, every=True, albums=True, picks=sheet, made=datetime.datetime.utcnow().isoformat(timespec='minutes') + 'Z')
    json.dump(pack, open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{day}: {len(years)} years, {sum(len(y["cands"]) for y in years)} photos -> {out}')


if __name__ == '__main__':
    main()
