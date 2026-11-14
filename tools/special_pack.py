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


def which_special(day, photos, tg_evs, special, items=()):
    """The special picture make.main() makes that day, as ('festival', picture, drawn) or ('story', picture, drawn),
    drawn = what it was drawn from; None when there is none."""
    if make.special_off(day):   # Darpan switched this day's special picture off
        return None
    chosen = make.chosen_specials(day, list(items) or photos)   # all the day's photos, so a chosen year has every one of its own
    if chosen:   # Darpan's own choice wins (the Studio pack shows the first; the others are special 2, 3...)
        sp = make.compose_special(chosen[0], day)
        if sp is not None:
            return 'story', sp, dict(ev=chosen[0], lead=None, source='chosen')
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
    options = []
    if not special and make.DAILY_SPECIAL:   # a special picture every day: the day's most special item, the others as options
        evs = make.daily_specials(day, list(items), photos, tg_evs)
        special, options, lead, source = (evs[0] if evs else None), evs[1:], None, 'daily'
    if not special:
        return None
    sp = make.compose_special(special, day, lead=lead['im'] if lead else None)
    if sp is None:
        return None
    return 'story', sp, dict(ev=special, lead=lead, source=source, options=options)


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


def card(pool, out, label, year, group, first, others):
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


def jsonable(v):
    return json.loads(json.dumps(v, default=lambda o: list(o) if isinstance(o, tuple) else str(o)))


def main():
    day = datetime.date.fromisoformat(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else os.path.join('site', 'packs', 'special')
    seen = make.shown
    make.shown = lambda: {d: v for d, v in seen().items() if d < str(day)}   # only the days before it, as its own morning run sees them
    items, photos, tg_evs, special = gather(day)
    dp.album_days(items + photos)
    got = which_special(day, photos, tg_evs, special, items)
    if not got:
        print(f'{day}: no special picture')
        sys.exit(2)
    kind, sp, drawn = got
    out = os.path.join(root, str(day))
    os.makedirs(out, exist_ok=True)
    sp.convert('RGB').resize((2400, round(2400 * sp.height / sp.width)), Image.LANCZOS).save(os.path.join(out, 'real.jpg'), quality=85)
    full = os.environ.get('SPECIAL_OUT')   # the remake run (special.yml) also wants the picture itself, as the morning run saves it
    if full:
        os.makedirs(full, exist_ok=True)
        sp.save(os.path.join(full, 'bapas-diary-special.png'), optimize=True)
        sp.convert('RGB').save(os.path.join(full, 'bapas-diary-special.jpg'), quality=95, optimize=True)
        if (drawn or {}).get('source') == 'chosen':   # his next choices of the day are special 2, 3... as the morning run makes them
            n = 1
            for ev in make.chosen_specials(day, list(items) or photos)[1:]:
                more = make.compose_special(ev, day)
                if more is not None:
                    n += 1
                    more.save(os.path.join(full, f'bapas-diary-special-{n}.png'), optimize=True)
    pool, cards = Pool(out), []
    made = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if kind == 'festival':
        name, cal = drawn['name'], drawn.get('cal') or ('', '')
        more = festival_photos(name, drawn['photos'])
        for x in drawn['photos']:   # the order the picture hangs them: by year, row after row
            rest = more.get(x['y'], [])
            c = card(pool, out, str(x['y']), x['y'], str(x['y']), x, rest)
            c.update(festival=name, day=str(x.get('fday') or x['d'])[:10])
            cards.append(c)
        hero = [x['y'] for x in (drawn.get('hero') or [])]
        pins = make.fest_pins(name)
        pack = dict(date=str(day), kind='every_festival', festival=name, title=drawn.get('title') or f'Every {name}',
                    subtitle='in Bapa’s Diary', footer=make.FOOTER, cal_line=cal[0], headline=None, story=None, whatsapp=cal[0],
                    layout=dict(name='wide', style=drawn.get('style') or make.LIVE_STYLE, rows=make.WIDE[make.LIVE_STYLE]['rows'],
                                hero=hero, short_bottom=drawn.get('short_bottom', 0), dress=jsonable(make.FEST_DRESS.get(name)),
                                pinned=bool(pins), size=[make.W, make.H]),
                    first=drawn['first'], last=drawn['last'])
    else:
        ev, lead = drawn['ev'], drawn['lead']
        y = int(ev['date'][:4])
        shown = [dict(lead, crop='frame')] if lead else []
        extra = []
        for u in (ev.get('urls') or make.tg_photos(ev.get('posts') or []))[:8]:   # as compose_special: the story's photos, blank frames left out
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
        pack = dict(date=str(day), kind='story', source=drawn['source'], title=f'{day.day} {day:%B}',
                    subtitle='A special day in BAPS history', footer=make.FOOTER, cal_line='',
                    headline=ev.get('headline') or ev['line'],
                    story='\n\n'.join(make.special_words(ev, bool(lead))),   # the channel's whole post (Darpan, 13 Nov 2026: 'stop cutting everything out')
                    story_short=ev.get('whatsapp') or ev.get('story') or ev['line'],
                    whatsapp=make.tg_caption(ev).strip(),   # the story as the 2pm caption words tell it ('On this day in ...'), Darpan, 14 Nov 2026
                    story_date=ev['date'][:10], story_place=ev.get('place') or '',
                    layout=dict(name='story', big=[70, 200, 1180, 800], small_from=1360, size=[make.W, make.H], unit=make.SCALE))
        # Darpan, 13 Nov 2026 ('if youre not sure make multiple and i will decide'): the other pictures the day could
        # have, each drawn and with the entry that makes it the day's special once it is put in archive/special-days.json
        def choice(e):
            k = e.get('kind', 'story')
            c = dict(day=str(day), kind=k)
            c.update(ref=e.get('article') or e['date'][:10]) if k in ('story', 'news') else c.update(year=int(e['date'][:4]))
            return c
        ev['article'] = ev.get('article')
        pack.update(story_kind=ev.get('kind', 'story'), choose=choice(ev), options=[])
        for n, e in enumerate(drawn.get('options') or [], 2):
            op = make.compose_special(e, day)
            if op is None:
                continue
            op.convert('RGB').resize((2400, round(2400 * op.height / op.width)), Image.LANCZOS).save(os.path.join(out, f'option-{n}.jpg'), quality=85)
            pack['options'].append(dict(picture=f'option-{n}.jpg', kind=e.get('kind', 'story'), headline=e.get('headline') or e['line'],
                                        story='\n\n'.join(make.special_words(e)), story_date=e['date'][:10], story_place=e.get('place') or '',
                                        whatsapp=make.tg_caption(e).strip(), choose=choice(e)))
    pool.close()
    pack.update(real='real.jpg', cards=cards, cell=dp.CELL, cols=dp.COLS, made=made)
    json.dump(pack, open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{day}: {kind} special, {len(cards)} cards, {sum(len(c["cands"]) for c in cards)} photos -> {out}')


if __name__ == '__main__':
    main()
