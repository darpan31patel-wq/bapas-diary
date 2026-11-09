"""A special picture pack for the Studio (Darpan, 6 Nov 2026: 'I want to edit my special pictures there too').

On a day the morning run makes a second, special picture (Every Diwali, Every Annakut and the other Every <festival>
pictures from make.every_festival, or a day in BAPS history from make.compose_special), this saves what the Studio
needs to draw it again and change it:

    python tools/special_pack.py 2026-11-08 site/packs/special
writes site/packs/special/2026-11-08/pack.json, the photos beside it and real.jpg (the special picture the run makes).
Exits with 2 (and writes nothing) on a day with no special picture.

pack.json: the picture's words (title, subtitle, footer, cal_line, headline, story), which kind of special it is and its
layout, and one entry per card in the order the picture shows them: its year (and festival and day), then the photo the
picture uses first and every other photo it could use, each in the same shape as a day pack's photos.
It decides exactly as make.main() does which special picture the day gets. Read only: nothing here changes the daily
picture, the special picture, shown.json or the release."""
import datetime, json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tools'))
import make
from make import Image
import numpy as np
import dashboard_pack as dp

CACHE = os.path.join(make.HERE, '.cache')   # compose_special reads its photos from here too


def gather(day):
    """The day's photos and the picks, exactly as make.main() makes them. Returns (items, photos, stories, special)."""
    mmdd = f'{day:%m-%d}'
    items = make.day_list(mmdd)
    collected = os.path.join(make.HERE, 'archive', mmdd + '.json')
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have and x['y'] < day.year]
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
    make.settle_places(items, mmdd)
    tg_extra, tg_evs, special = make.tg_day(day, items)
    items += tg_extra
    make.settle_places(tg_extra, mmdd)
    make.download_all(items, CACHE)
    make.unframe(items)
    tall = 1 / 1.45 if len({x['y'] for x in items}) > 10 else 1 / 1.08
    aspect = make.FRAME_ASPECT.get(make.LIVE_STYLE, tall)
    photos = make.pick_one_per_year(items, seed=mmdd, aspect=aspect, day=day)
    if not photos:
        raise SystemExit('No photos could be downloaded for ' + mmdd)
    try:
        photos = make.prefer_festival(items, photos, mmdd, aspect, day)
    except Exception as e:
        print('  festival photos not checked:', e)
    make.full_size(photos)
    make.tag_festivals(photos)
    return items, photos, tg_evs, special


def which_special(day, photos, tg_evs, special):
    """The special picture make.main() makes that day, as ('festival', picture, drawn) or ('story', picture, drawn),
    drawn = what it was drawn from; None when there is none."""
    wins = 'Diwali' in make.festivals(day)
    drawn, every = {}, None
    if not special or wins:
        wide = make.compose_wide

        def watch(photos, day, **k):   # the Every <festival> picture's own cards, as it hangs them
            drawn.update(k, photos=photos)
            return wide(photos, day, **k)
        make.compose_wide = watch
        try:
            sp, every = make.every_festival(day, CACHE)
        except Exception as e:
            print('  no festival picture:', e)
            sp = None
        finally:
            make.compose_wide = wide
        if sp is not None:
            return 'festival', sp, dict(drawn, name=every[0], first=every[1], last=every[2])
    if special and every:
        special = None
    lead = None
    source = 'big day'
    if not special:
        shown = [e for e in tg_evs if not e.get('channel') and not e.get('guru') and e.get('posts')
                 and any(make.tells(x, e, make.RARE_DAYS) for x in photos)]
        special = max(shown, key=make.tg_rank, default=None)
        lead = next((x for x in photos if special and x.get('im') is not None and make.tells(x, special, make.RARE_DAYS)), None)
        source = 'year card'
    if not special:
        return None
    sp = make.compose_special(special, day, lead=lead['im'] if lead else None)
    if sp is None:
        return None
    return 'story', sp, dict(ev=special, lead=lead, source=source)


class Pool:
    """The pack's photos, joined end to end in <group>-best.jpg (the big ones) and <group>-more.jpg, as a day pack does;
    a photo offered on several cards is saved once."""

    def __init__(self, out):
        self.out, self.blobs, self.done = out, {}, {}

    def add(self, x, group, big):
        key = (group, x['i'])
        if key in self.done:
            return self.done[key]
        try:
            im = x['im'].copy() if x.get('im') is not None else Image.open(x['path']).convert('RGB')
        except Exception:
            return None
        face = x.get('face') if 'face' in x else None
        if 'face' not in x:   # a photo the picture didn't use: Bapa's face found as the daily pick finds it
            try:
                face, _ = make.bapa_face(im, str(x.get('d') or '')[:10] or f'{x["y"]}-07-01')
            except Exception:
                face = None
        s = min(1, (dp.LONG if big else dp.MORE) / max(im.size))
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        f = f'{group}-{"best" if big else "more"}.jpg'
        if f not in self.blobs:
            self.blobs[f] = open(os.path.join(self.out, f), 'wb')
        b = self.blobs[f]
        at = b.tell(); im.save(b, 'JPEG', quality=82 if big else 76)
        lo, hi = dp.album_span(x)
        c = dict(f=f, at=[at, b.tell() - at], w=im.width, h=im.height,
                 face=[round(v * s, 1) for v in face] if face else None,
                 crop=x.get('crop') or ('frame' if face else 'whole'), caption=make.caption(x), original=x.get('c') or '',
                 place=make.place(x) or x.get('p') or '', date=str(x.get('d') or '')[:10], festival=dp.festival_tag(x),
                 album_from=lo, album_to=hi, **({'nobapa': True} if not face else {}))
        self.done[key] = (c, im)
        return self.done[key]

    def close(self):
        for b in self.blobs.values():
            b.close()


def card(pool, out, label, year, group, first, others, face_first=False):
    """One card: the photo the picture shows first, then every other photo it could use, and a thumbnail sheet."""
    got = [pool.add(first, group, True)] if first is not None else []
    for k, x in enumerate(others):
        got.append(pool.add(x, group, len(got) < 6))
    got = [g for g in got if g]
    seen, cands, ims = set(), [], []
    for c, im in got:
        if (c['f'], c['at'][0]) in seen:
            continue
        seen.add((c['f'], c['at'][0])); cands.append(c); ims.append(im)
    if face_first:   # Bapa's face found first, the thumbnails in the same order
        order = sorted(range(len(cands)), key=lambda k: cands[k].get('face') is None)
        cands, ims = [cands[k] for k in order], [ims[k] for k in order]
    if ims:
        dp.thumbs(ims, [c['face'] for c in cands], os.path.join(out, f'{label}-thumbs.jpg'))
    return dict(year=year, cands=cands, thumbs=f'{label}-thumbs.jpg' if ims else None)


def festival_photos(name, photos):
    """Every other photo each year could use on an Every <festival> picture: that year's photos from its own festival
    day whose caption names the festival, then those up to 3 days either side whose caption names it (an album filed
    under a date range, such as 2002's Diwali to Annakut in Ramod). {year: [photos]}"""
    words = re.compile(make.BIG[name], re.I)
    lists, out = {}, {}
    for x in photos:
        fday = datetime.date.fromisoformat(str(x.get('fday') or x['d'])[:10])
        have, near = {x['i']}, []
        for k in sorted(range(-3, 4), key=abs):   # the day window (Darpan, 5 Nov 2026: 3 days either side)
            d = fday + datetime.timedelta(days=k)
            mmdd = f'{d:%m-%d}'
            if mmdd not in lists:
                ls = make.day_list(mmdd)
                path = os.path.join(make.HERE, 'archive', 'vicharan', mmdd + '.txt')
                if os.path.exists(path):
                    ls = ls + make.vicharan_items(path, mmdd, {})
                lists[mmdd] = ls
            for i in lists[mmdd]:
                if i['y'] != x['y'] or i['i'] in have or not words.search(i.get('c') or '') or make.JUNK.search(i.get('c') or ''):
                    continue
                try:
                    when = datetime.date.fromisoformat(str(i.get('d') or '')[:10])
                except ValueError:
                    when = d
                if abs((when - fday).days) > 3:
                    continue
                have.add(i['i']); near.append(dict(i, exact=when == fday))
        out[x['y']] = near
    every = [i for v in out.values() for i in v]
    make.album_towns(every)
    make.download_all(every, CACHE)
    dp.album_days(every)
    for y, v in out.items():
        v[:] = [i for i in v if 'path' in i]
        v.sort(key=lambda i: not i['exact'])   # the festival day itself first
    return out


def spare_years(name, day, have_years):
    """Years an Every <festival> picture has no card for, with the photos from that year's own festival day in the
    archive database (the baps.org News galleries included): those whose caption names the festival first (arti, then
    thal), then the day's other photos, each face checked when it is packed. {year: [photos]}. The Studio shows them
    as cards he can keep or take off; the morning picture is unchanged (Darpan, 9 Nov 2026: the missing Annakut years,
    'with article information too')."""
    import sqlite3
    db = os.path.join(make.HERE, 'bapas.db')
    if not os.path.exists(db):
        return {}
    make.cal_day(day)
    words, days = re.compile(make.BIG[name], re.I), dict(OLD_DAYS.get(name, {}))
    for d in sorted(make.CALENDAR):
        if d[:4].isdigit() and int(d[:4]) < day.year and int(d[:4]) not in days and name in make.festivals(d):
            days[int(d[:4])] = d
    con, out = sqlite3.connect(db), {}
    for y, d in sorted(days.items()):
        if y in have_years:
            continue
        rows = con.execute('select album, file, caption, place from photos where date = ? or (date_from = ? and date_to = ?)'
                           ' order by album, file', (d, d, d)).fetchall()
        named = [r for r in rows if words.search(r[2] or '') and not make.JUNK.search(r[2] or '')]
        own = re.compile(re.escape(name), re.I)   # the festival's own name with arti or thal first, then its name, then the rest
        rank = lambda r: (0 if own.search(r[2] or '') and re.search(r'\barti\b|\bthal', r[2] or '', re.I)
                          else 1 if own.search(r[2] or '') else 2)
        named.sort(key=rank)
        rest = [r for r in rows if r not in named and not make.JUNK.search(r[2] or '')]
        got = []
        for album, f, c, where in named[:16] + rest[:16]:
            got.append({'i': f'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{f}', 'y': y, 'd': d,
                        'p': where or '', 'c': c or name, 'fday': d})
        if got:
            out[y] = got
    every = [x for v in out.values() for x in v]
    if every:
        make.album_towns(every)
        make.download_all(every, CACHE)
        dp.album_days(every)
    out = {y: [x for x in v if 'path' in x] for y, v in out.items()}
    return {y: v for y, v in out.items() if v}


# the festival's own day in years before the calendar (2010), from the baps.org News articles of that day
OLD_DAYS = {'Annakut': {1999: '1999-11-08', 2000: '2000-10-28', 2002: '2002-11-05', 2003: '2003-10-26', 2007: '2007-11-10'}}


def jsonable(v):
    return json.loads(json.dumps(v, default=lambda o: list(o) if isinstance(o, tuple) else str(o)))


def main():
    day = datetime.date.fromisoformat(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else os.path.join('site', 'packs', 'special')
    seen = make.shown
    make.shown = lambda: {d: v for d, v in seen().items() if d < str(day)}   # only the days before it, as its own morning run sees them
    items, photos, tg_evs, special = gather(day)
    dp.album_days(items + photos)
    got = which_special(day, photos, tg_evs, special)
    if not got:
        print(f'{day}: no special picture')
        sys.exit(2)
    kind, sp, drawn = got
    out = os.path.join(root, str(day))
    os.makedirs(out, exist_ok=True)
    sp.convert('RGB').resize((2400, round(2400 * sp.height / sp.width)), Image.LANCZOS).save(os.path.join(out, 'real.jpg'), quality=85)
    pool, cards, spare_cards = Pool(out), [], []
    made = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if kind == 'festival':
        name, cal = drawn['name'], drawn.get('cal') or ('', '')
        more = festival_photos(name, drawn['photos'])
        for x in drawn['photos']:   # the order the picture hangs them: by year, row after row
            rest = more.get(x['y'], [])
            c = card(pool, out, str(x['y']), x['y'], str(x['y']), x, rest)
            c.update(festival=name, day=str(x.get('fday') or x['d'])[:10])
            cards.append(c)
        spares = spare_years(name, day, {x['y'] for x in drawn['photos']})
        for y, xs in sorted(spares.items()):   # years the picture has no card for, offered to add in the Studio (Darpan, 9 Nov 2026)
            c = card(pool, out, f'spare-{y}', y, f'spare-{y}', xs[0], xs[1:], face_first=True)
            if not c['cands']:
                continue
            c.update(festival=name, day=str(xs[0]['fday']), added=True)
            # a year where Bapa's face is found joins the picture as a card he can change or take off; the rest wait aside
            (cards if c['cands'][0].get('face') else spare_cards).append(c)
        cards.sort(key=lambda c: c['year'])
        hero = [x['y'] for x in (drawn.get('hero') or [])]
        pins = make.fest_pins(name)
        pack = dict(date=str(day), kind='every_festival', festival=name, title=drawn.get('title') or f'Every {name}',
                    subtitle='in Bapa’s Diary', footer=make.FOOTER, cal_line=cal[0], headline=None, story=None,
                    layout=dict(name='wide', style=drawn.get('style') or make.LIVE_STYLE, rows=make.WIDE[make.LIVE_STYLE]['rows'],
                                hero=hero, short_bottom=drawn.get('short_bottom', 0), dress=jsonable(make.FEST_DRESS.get(name)),
                                pinned=bool(pins), size=[make.W, make.H]),
                    first=drawn['first'], last=drawn['last'])
    else:
        ev, lead = drawn['ev'], drawn['lead']
        y = int(ev['date'][:4])
        shown = [dict(lead, crop='frame')] if lead else []
        extra = []
        for u in make.tg_photos(ev['posts'])[:8]:   # as compose_special: the channel's photos, blank frames left out
            x = {'i': u, 'y': y, 'd': ev['date'], 'p': ev.get('place') or '', 'c': ev.get('card') or ev.get('line') or '', 'tg': True}
            make.download_all([x], CACHE)
            if 'path' not in x:
                continue
            im = Image.open(x['path']).convert('RGB')
            if np.asarray(im.convert('L').resize((64, 64)), dtype=float).std() >= 25:
                x['im'] = im
                (shown if len(shown) < 5 else extra).append(x)
        year_too = [x for x in items if x['y'] == y and 'path' in x and not make.JUNK.search(x.get('c') or '')]   # that year's photos of the day
        pool_rest = extra + year_too
        for k, x in enumerate(shown):   # card 1 is the big one, cards 2 to 5 the small ones beside it under the story
            others = [o for o in shown if o is not x] + pool_rest
            c = card(pool, out, f'card{k + 1}', y, 'story', x, others)
            c.update(role='big' if k == 0 else 'small', place=ev.get('place') or '')
            cards.append(c)
        pack = dict(date=str(day), kind='story', source=drawn['source'], title=f'{day.day} {day:%B} in Bapa’s Diary',
                    subtitle='A special day in BAPS history', footer=make.FOOTER, cal_line='',
                    headline=ev.get('headline') or ev['line'],
                    story=(ev.get('whatsapp') if lead else None) or ev.get('story') or ev.get('whatsapp') or ev['line'],
                    story_date=ev['date'][:10], story_place=ev.get('place') or '',
                    layout=dict(name='story', big=[70, 200, 1180, 800], small_from=1360, size=[make.W, make.H], unit=make.SCALE))
    pool.close()
    pack.update(real='real.jpg', cards=cards, spares=spare_cards, articles=dp.articles(day), cell=dp.CELL, cols=dp.COLS, made=made)
    json.dump(pack, open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{day}: {kind} special, {len(cards)} cards, {sum(len(c["cands"]) for c in cards)} photos -> {out}')


if __name__ == '__main__':
    main()
