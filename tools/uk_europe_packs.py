"""Tell the Studio's special picture page about the day's UK and Europe backup (Darpan, 14 Nov 2026: 'so they would
automatically come up in the special picture dashboard?').

    python tools/uk_europe_packs.py site
For every special pack site/packs/special/<YYYY-MM-DD>/pack.json whose day has a backup ready in
site/packs/uk-europe/index.json, the pack gains one field, "uk_europe": {name, title, picture, pack, drive, years,
years_shown, cards, both_gurus, made, add}. Nothing else in the pack changes; a day without a backup loses the field.
The backup is only shown there as a choice: it is never sent unless he adds it ("add" says how)."""
import glob, json, os, sys

site = sys.argv[1]
try:
    days = json.load(open(os.path.join(site, 'packs', 'uk-europe', 'index.json'))).get('days', {})
except (OSError, ValueError):
    days = {}
for f in glob.glob(os.path.join(site, 'packs', 'special', '*', 'pack.json')):
    date = os.path.basename(os.path.dirname(f))
    try:
        p = json.load(open(f, encoding='utf-8'))
    except ValueError:
        continue
    b = days.get(date[5:])
    new = dict(b, day=date[5:], add="Start the run 'Studio photo packs' (studio.yml) with uk_europe_add = today, before 1:50pm on the day") if b else None
    if p.get('uk_europe') != new:
        if new:
            p['uk_europe'] = new
        else:
            p.pop('uk_europe', None)
        json.dump(p, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(date, 'UK and Europe backup', 'added to the pack' if new else 'taken off the pack')
