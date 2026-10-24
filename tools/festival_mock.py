"""Mockup only (Darpan, 24 Oct 2026): one photo per year from that year's festival day, using the BAPS calendar.
python tools/festival_mock.py Diwali out/diwali-photos"""
import datetime, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make

name, folder = sys.argv[1], sys.argv[2]
cal = json.load(open(os.path.join(make.HERE, 'calendar', 'baps-calendar.json'), encoding='utf-8'))['days']
days = {}
for x in cal:
    y = int(x['date'][:4])
    if y < 2026 and y not in days and any(re.fullmatch(name, f['name'], re.I) for f in x['festivals']):
        days[y] = datetime.date.fromisoformat(x['date'])
items = []
for y, d in sorted(days.items()):
    mmdd, have = f'{d:%m-%d}', {x['i'] for x in items}
    got = [x for x in make.day_list(mmdd) if x['y'] == y]
    path = os.path.join(make.HERE, 'archive', 'vicharan', mmdd + '.txt')
    if os.path.exists(path):
        got += [x for x in make.vicharan_items(path, mmdd, {}) if x['y'] == y]
    for x in got:
        if x['i'] not in have:
            have.add(x['i']); items.append(dict(x, fest=str(d)))
    print(y, d, len(got), 'photos')
make.album_towns(items)
make.download_all(items, os.path.join(make.HERE, '.cache'))
photos = make.pick_one_per_year(items, seed=name, aspect=make.FRAME_ASPECT[make.LIVE_STYLE])
for x in photos:
    print(x['y'], x.get('fest'), x['crop'], make.caption(x))
make.dump_photos(photos, folder)
