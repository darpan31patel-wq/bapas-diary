"""The UK and Europe backup special pictures (Darpan, 14 Nov 2026, through his website project): "a UK and Europe
special picture kept ready, as a backup, for every calendar day on which Bapa was in the UK or Europe in 2 or more
years ... as much of a collage as possible, with as many nice photos as possible from every year Bapa was there on that
date, and show each photo's caption ... the photos should show exactly what Bapa was doing on that day. Show the year
and place for each year. Only photos with Bapa clearly visible. English date only. Where a day has years with both
gurus, show Pramukh Swami Maharaj and Mahant Swami Maharaj together."

    python tools/uk_europe.py 05-01,06-14 out/uk-europe
writes for each day  out/uk-europe/05-01/1 May UK and Europe.png  (the picture, the name it has in Drive),
picture.jpg (a lighter copy for the Studio) and pack.json (what is on it and what was left out, and why).
Exits 2 when none of the days asked for could be made.

The days and their photos come from the website project's list (bapas-diary.com/uk-europe-days.json, UKEU_LIST for
another address or a file). Every photo is looked at again here: only one in which Bapa's face is found, and big
enough to be seen, goes on the picture. The years before 1999 have only the two channels' photos, read by post number
from our own copy of the channels (telegram/), on the exact day only. Read only: nothing here touches the daily
picture, the day's special picture, shown.json, the release or the 2pm send."""
import datetime, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import make
from make import Image

LIST = os.environ.get('UKEU_LIST', 'https://bapas-diary.com/uk-europe-days.json')
CACHE = os.path.join(HERE, '.cache')
MAX_CARDS = 30        # as many as the three cords hold while a card can still be read on a phone (the Annakut picture has 29)
MIN_FACE = .035       # his face at least this much of the photo's width, or he is not clearly seen
MIN_SHARP = 12        # a face blurrier than this (a tiny old video still) is not a darshan
STYLE = 'UKEU'        # the live cards on three cords, with a third line of room under each so a whole caption fits
make.WIDE[STYLE] = dict(make.WIDE[make.LIVE_STYLE], lines=3, pill=3)
make.FRAME_ASPECT[STYLE] = make.FRAME_ASPECT[make.LIVE_STYLE]
ELSEWHERE = re.compile(r"[A-Z][a-z]+(?: [A-Z][a-z]+)?")   # a plain town name (not an album's title)
HONORIFIC = re.compile(r'\b(?:Pragat\s+)?Brahmaswarup\s+(?=Pramukh|Mahant|Yogiji|Shastriji)')


def the_list():
    if os.path.exists(LIST):
        return json.load(open(LIST, encoding='utf-8'))
    return json.loads(make.fetch(LIST, tries=3, timeout=60))


def name_of(mmdd):
    """'1 May UK and Europe': the picture's name in Drive. No year in it, so the 2pm send (which takes
    '<d MMMM yyyy>.png' and '<d MMMM yyyy> special....png') can never take it for a picture of the day."""
    d = datetime.date(2000, int(mmdd[:2]), int(mmdd[3:]))
    return f'{d.day} {d:%B} UK and Europe'


def channel_posts():
    """post number -> [(channel, event)] from our own copy of the two channels."""
    out = {}
    for e in make.tg_all():
        for n in e.get('posts') or []:
            out.setdefault(n, []).append((e.get('channel') or 'TodayinBAPShistory', e))
    return out


def gather(entry, log, towns_there=()):
    """Every photo the list gives for the day, as the picture maker's items. A photo whose own place is a town outside
    the UK and Europe (the Ahmedabad album of the day he flew to London) is left out and said. The older photos are
    found by the post number in their folder's name; one our channel copy has under another date is left out and said."""
    items, posts, away = [], channel_posts(), {}
    for yr in entry['years']:
        y, d = yr['year'], yr['date']
        towns = ', '.join(yr.get('places') or [])
        for k, p in enumerate(yr.get('photos') or []):
            if not p.get('large'):
                continue
            town = make.town_of(p.get('place'))
            if town and town not in towns_there:
                if ELSEWHERE.fullmatch(town):
                    away[(y, town)] = away.get((y, town), 0) + 1
                    continue
                town = ''   # an album's title, not a place
            items.append(dict(y=y, d=d, p=town or towns, c=HONORIFIC.sub('', p.get('caption') or ''),
                              i=p['large'], small=p.get('small'), look=p.get('look') or '', rank=p.get('rank'),
                              exact=bool(p.get('exact_day')), order=k, guru=yr['guru']))
        seen = set()
        for o in yr.get('older_photos') or []:
            m = re.search(r'\(post (\d+)\)\s*$', o.get('folder') or '')
            if not m:
                log.append(f'{y}: older folder without a post number, left out: {o.get("folder")}')
                continue
            n = int(m.group(1))
            ours = [(ch, e) for ch, e in posts.get(n, []) if e['date'] == d]
            if not ours:
                other = sorted({e['date'] for _, e in posts.get(n, [])})
                log.append(f'{y}: older folder "{o["folder"]}" left out: ' + (f'our channel copy has post {n} under {", ".join(other)}, not {d}' if other else f'post {n} is not in our channel copy'))
                continue
            for ch, e in ours:
                if (ch, n) in seen:
                    continue
                seen.add((ch, n))
                sat = ch == 'SatpurushInUKEurope'
                own = (e.get('cards') or {}).get(str(n)) or {}
                urls = make.tg_photos([n], ch, pairs=True) if sat else make.tg_photos([n], ch, numbered=True)
                for k, (_, u) in enumerate(urls):
                    items.append(dict(y=y, d=d, p=own.get('place') or e.get('place') or towns,
                                      c=said(own.get('card') or o.get('caption') or e.get('line') or '', own.get('place') or e.get('place') or towns), i=u, tg=True,
                                      unframe=sat, look='', rank=None, exact=True, order=100 + k, guru=yr['guru'], post=n, folder=o['folder']))
    for (y, town), n in sorted(away.items()):
        log.append(f'{y}: {n} photos taken in {town}, not in the UK or Europe, left out')
    return items


def said(c, town):
    """'Pramukh Swami Maharaj in London: Morning Satsang sabha' -> 'Morning Satsang sabha' (the card already says London)."""
    c = HONORIFIC.sub('', c)
    return re.sub(rf'^(?:{make.NAME}\s+)?in {re.escape(town)}:\s*', '', c, flags=re.I) if town else c


def look_at(items, log):
    """Open each photo and find Bapa in it. Returns the ones in which he is clearly seen."""
    make.download_all(items, CACHE)
    make.unframe(items)
    good = []
    for x in items:
        tag = f'{x["y"]} {x.get("folder") or x["i"].rsplit("/", 1)[-1]}'
        if 'path' not in x:
            log.append(f'{tag}: the photo could not be read, left out')
            continue
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            log.append(f'{tag}: the photo would not open, left out')
            continue
        if x['y'] == 1970:   # Yogiji Maharaj's visit: the main face of an old photo (never a later photo put in the post)
            face, sim = make.guru_face(im)
            if face and make.colour(im) > make.GURU_COLOUR:
                face = None
        else:
            face, sim = make.bapa_face(im, x['d'], need=make.TG_SAME_PERSON if x.get('tg') else make.SAME_PERSON)
            if not face and not x.get('tg'):   # the website's own check already found him in it: a side view counts
                face, sim = make.bapa_face(im, x['d'], need=make.TG_SAME_PERSON)
        if not face:
            log.append(f'{tag}: Bapa not found in it, left out')
            continue
        if face[2] / im.width < MIN_FACE:
            log.append(f'{tag}: Bapa too small to be clearly seen, left out')
            continue
        sharp = make.face_quality(im, face)[0]
        if sharp < MIN_SHARP:
            log.append(f'{tag}: his face too blurred, left out')
            continue
        x.update(im=im, face=face, sim=sim, sharp=sharp, front=make.LAST_FRONT[0], fw=face[2] / im.width)
        fa = make.FRAME_ASPECT[STYLE]
        if x['look'] == 'close up' or (x.get('tg') and x['fw'] > .16):
            x['crop'] = 'close' if face[2] * 1200 / max(im.size) >= make.CLOSE_MIN_FACE else 'frame'
        else:   # what he is doing stays in the frame
            x['crop'] = 'frame' if make.frame_keep(im, face, fa) >= make.ACTION_KEEP else 'whole'
        x['score'] = (2 if x['exact'] else 0) + (1 if x['rank'] == 0 else 0) - .05 * min(x['rank'] or 0, 10) + x['sim'] \
            + min(x['sharp'] / 400, .5) + (.3 if x['look'] == 'activity' and make.is_special(x['c']) else 0) - (.6 if x.get('tg') else 0) - .002 * x['order']
        good.append(x)
    return good


def choose(good, limit=MAX_CARDS):
    """As many as fit, shared out between the years: each year's best first, a different moment before a second photo
    of the same one, then round the years again until the cords are full."""
    by, taken = {}, []
    for x in sorted(good, key=lambda x: -x['score']):
        q = by.setdefault(x['y'], [])
        if any(make.same_photo(make.fingerprint(x), make.fingerprint(o)) for o in q):
            continue
        q.append(x)
    for y, q in by.items():   # a year's photos in turn: a new caption each time while there is one
        order, keys = [], []
        rest = list(q)
        while rest:
            nxt = next((x for x in rest if not any(make.same_caption(make.caption_key(x['c']), k) for k in keys)), None)
            if nxt is None:
                keys = []; nxt = rest[0]
            order.append(nxt); rest.remove(nxt); keys.append(make.caption_key(nxt['c']))
        by[y] = order
    k = 0
    while len(taken) < limit and any(len(q) > k for q in by.values()):
        for y in sorted(by):
            if len(by[y]) > k and len(taken) < limit:
                taken.append(by[y][k])
        k += 1
    return sorted(taken, key=lambda x: (x['y'], -x['score']))


def heroes(photos):
    """The big cards in the middle: the best close darshan of each guru the day has, side by side when it has both."""
    out = []
    for g in ('Pramukh Swami Maharaj', 'Mahant Swami Maharaj'):
        mine = [x for x in photos if x['guru'] == g and x['fw'] >= .08 and x['sharp'] >= 40]
        if mine:
            best = max(mine, key=lambda x: x['sim'] + x['front'] + min(x['fw'], .3) * 2 + (.4 if x['look'] == 'close up' else 0) + min(x['sharp'] / 400, .5))
            out.append(best)
    return out


def foot_line(entry):
    """'Pramukh Swami Maharaj 1974, 1990, 2004   ·   Mahant Swami Maharaj 2017, 2023': every year Bapa was there."""
    groups = {}
    for yr in entry['years']:
        groups.setdefault(yr['guru'].split(',')[0], []).append(str(yr['year']))
    return '   ·   '.join(f'{g} {", ".join(ys)}' for g, ys in groups.items())


def build(mmdd, entry, out, towns_there=()):
    log = []
    day = datetime.date(2000, int(mmdd[:2]), int(mmdd[3:]))   # a year with no festival dress and no 29 February trouble
    items = gather(entry, log, towns_there)
    good = look_at(items, log)
    photos = choose(good)
    years, have = [yr['year'] for yr in entry['years']], sorted({x['y'] for x in photos})
    for y in years:
        if y not in have:
            log.append(f'{y}: no photo with Bapa clearly seen ({sum(1 for x in items if x["y"] == y)} looked at), the year is named in the line at the foot only')
    print(f'{mmdd}: {len(items)} photos looked at, {len(good)} with Bapa clearly seen, {len(photos)} on the picture, years {have} of {years}', flush=True)
    for l in log:
        print('   ', l)
    if len(have) < 2:
        print(f'{mmdd}: fewer than 2 years have a photo of Bapa, no picture made')
        return False
    make.full_size(photos)
    hero = heroes(photos)
    title = f'{day.day} {day:%B}'
    img = make.compose_wide(photos, day, seed='uk-europe-' + mmdd, style=STYLE, title=title, subtitle='in the UK and Europe',
                            cal=(foot_line(entry), ''), hero=hero)
    folder = os.path.join(out, mmdd)
    os.makedirs(folder, exist_ok=True)
    name = name_of(mmdd)
    img.convert('RGB').save(os.path.join(folder, name + '.png'), optimize=True)
    small = img.convert('RGB'); small.thumbnail((2400, 2400), Image.LANCZOS)
    small.save(os.path.join(folder, 'picture.jpg'), quality=88)
    pack = dict(day=mmdd, title=title, subtitle='in the UK and Europe', name=name, drive=f'UK and Europe backups/{name}.png',
                made=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'), list_made=None,
                both_gurus=entry.get('both_gurus', False), foot=foot_line(entry), years=years, years_shown=have,
                cards=[dict(year=x['y'], place=make.place(x), caption=make.shown_caption(x), guru=x['guru'].split(',')[0],
                            hero=any(x is h for h in hero), exact_day=x['exact'], look=x['look'],
                            **({'post': x['post']} if x.get('tg') else {'photo': x['i'], 'small': x.get('small')})) for x in photos],
                left_out=log)
    json.dump(pack, open(os.path.join(folder, 'pack.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return True


def stamp(entry):
    """Changes when the list's entry for the day changes, so a picture is remade only then."""
    return hashlib.sha1(json.dumps(entry, sort_keys=True).encode()).hexdigest()[:12]


def main():
    want, out = sys.argv[1], sys.argv[2]
    L = the_list()
    days = {k: v for k, v in L['days'].items() if v.get('backup')}
    if want == 'list':   # every backup day and its stamp, for the run that decides which to make
        json.dump({k: stamp(v) for k, v in sorted(days.items())}, open(out, 'w'), indent=0)
        print(len(days), 'backup days in the list made', L.get('made'))
        return 0
    towns_there = {p for v in L['days'].values() for yr in v['years'] for p in yr.get('places') or []} | {'Lisbon', 'South London'}
    made = 0
    for mmdd in [w.strip() for w in want.split(',') if w.strip()]:
        if mmdd not in days:
            print(f'{mmdd}: not a backup day in the list')
            continue
        try:
            if build(mmdd, days[mmdd], out, towns_there):
                f = os.path.join(out, mmdd, 'pack.json')
                p = json.load(open(f, encoding='utf-8')); p['list_made'] = L.get('made'); p['stamp'] = stamp(days[mmdd])
                json.dump(p, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
                made += 1
        except Exception as e:   # one bad day never stops the others
            import traceback; traceback.print_exc()
            print(f'{mmdd}: failed, {e}')
    return 0 if made else 2


if __name__ == '__main__':
    sys.exit(main())
