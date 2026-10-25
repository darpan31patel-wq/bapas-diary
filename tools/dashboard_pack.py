"""A day pack for the collage builder dashboard (Darpan, 25 Oct 2026: 'a dashboard ... I just click export').

For one date it picks photos exactly as the daily run does, then saves each year's best few photos (the one the
daily picture would show first), with Bapa's face box, caption, place and festival, plus the day's title and
calendar line, so the dashboard can swap photos, crops and text and draw the picture itself.

    python tools/dashboard_pack.py 2026-10-25 dashboard/packs
writes dashboard/packs/2026-10-25/pack.json, the photos beside it and real.jpg (the daily run's own picture).
Read only: nothing here changes the daily picture, shown.json or the release."""
import datetime, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import Image

LONG = 1000   # the long side of each saved photo


def items_for(day, cache):
    """The day's photos, gathered as make.main() does."""
    mmdd = f'{day:%m-%d}'
    items = make.day_list(mmdd)
    collected = os.path.join(make.HERE, 'archive', mmdd + '.json')
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have]
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
    photos = make.pick_one_per_year(items, seed=f'{day:%m-%d}', aspect=make.FRAME_ASPECT[make.LIVE_STYLE], day=day)
    make.tag_festivals(photos)
    story = make.tg_story(tg_evs, photos)
    make.compose(photos, day, seed=f'{day:%m-%d}', style=make.LIVE_STYLE, history=story).convert('RGB') \
        .resize((2400, round(2400 * make.H / make.W)), Image.LANCZOS).save(os.path.join(out, 'real.jpg'), quality=85)

    years = []
    for w in make.WORKINGS:
        if w['pick'] is None:
            continue
        rows = [w['pick']] + [x for _, x, _ in w['rows'] if x is not w['pick']]
        cands = []
        for k, x in enumerate(rows[:6]):
            im = x['im'].copy(); s = min(1, LONG / max(im.size)); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            name = f'{w["year"]}-{k}.jpg'
            im.save(os.path.join(out, name), quality=82)
            d = str(x.get('d') or '')[:10]
            fs = make.festivals(make.cal_day(d)) if len(d) == 10 else []
            cands.append(dict(img=name, w=im.width, h=im.height,
                              face=[round(v * s, 1) for v in x['face']] if x['face'] else None,
                              crop=x.get('crop', 'frame'), caption=make.caption(x), original=x.get('c') or '',
                              place=make.place(x), date=d, special=bool(x.get('special')), nice=bool(x.get('nice')),
                              festival=fs[0] if fs else ''))
        years.append(dict(year=w['year'], mode=w['mode'], cands=cands))
    cal = make.cal_footer(day)
    pack = dict(date=str(day), title=make.cal_title(day) or f'{day.day} {day:%B}', subtitle='in Bapa’s Diary',
                footer=make.FOOTER, cal_line=cal[0] if cal else '', tomorrow=cal[1] if cal else '',
                story=dict(year=story['date'][:4], line=story.get('line', '')) if story else None,
                years=years, made=datetime.datetime.utcnow().isoformat(timespec='minutes') + 'Z')
    json.dump(pack, open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{day}: {len(years)} years, {sum(len(y["cands"]) for y in years)} photos -> {out}')


if __name__ == '__main__':
    main()
