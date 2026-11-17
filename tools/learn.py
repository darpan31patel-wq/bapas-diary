"""Learn from Darpan's Studio changes (Darpan, 17 Nov 2026, idea 4): which photos he swaps, removes or adds, how big he
makes the words and the big photo, and which look he picks, so each morning's first draft looks more like his finished
one. Run once a week (learn.yml):

    python tools/learn.py            writes archive/learned.json (what the builder uses) and archive/learned/<date>.txt
                                     (the week's lessons in plain words)

Where it reads from: his special pictures as he left them in the Studio (bapas-diary.com/special-days.json, every
layout he arranged, Final or not), the first drafts the morning run made (archive/drafts/<date>.json), and, when the
repository's STUDIO_READ_KEY secret is set, the Studio's own log of every Final (bapas-diary.com/api/studio-log)."""
import datetime, json, os, re, statistics, sys, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import make   # noqa: E402

DRAFTS = make.DRAFTS
OUT = os.path.join(HERE, 'archive', 'learned.json')
WEEKLY = os.path.join(HERE, 'archive', 'learned')


def key(u):   # a photo's own file name, the same whichever address it was given by (baps.org, the archive, the website)
    return re.sub(r'\.(jpe?g|png|webp)$', '', str(u or '').split('?')[0].rstrip('/').split('/')[-1].lower())


def on(c):
    d = str(c.get('day') or '')
    return d if re.match(r'^\d{4}-\d\d-\d\d$', d) else None


LOG_URL = os.environ.get('STUDIO_LOG_URL') or 'https://bapas-diary.com/api/studio-log'


def studio_log(since=None):
    """The Studio's log of his Final pictures (website project, 17 Nov 2026): each entry has how (Final...), changes (his
    changes in plain words: swaps, crops, sizes, moves, text style), layout (what he sent) and first (the first draft,
    layout version 2). Read with the repository's secret STUDIO_READ_KEY; [] without it or when the site doesn't answer."""
    k = os.environ.get('STUDIO_READ_KEY')
    if not k:
        print('studio log not read: no STUDIO_READ_KEY')
        return []
    try:
        url = LOG_URL + (f'?since={since}' if since else '')
        req = urllib.request.Request(url, headers={'X-Studio-Read-Key': k, 'User-Agent': 'bapas-diary-learn'})
        got = json.loads(urllib.request.urlopen(req, timeout=30).read().decode('utf-8'))
        got = got if isinstance(got, list) else got.get('log') or got.get('entries') or got.get('items') or []
        return [e for e in got if isinstance(e, dict)]
    except Exception as e:
        print('studio log not read:', e)
        return []


def entry_day(e):
    for k in ('day', 'date', 'special', 'for'):
        v = str(e.get(k) or '')
        if re.match(r'^\d{4}-\d\d-\d\d', v):
            return v[:10]
    v = str(e.get('at') or e.get('time') or e.get('when') or '')
    return v[:10] if re.match(r'^\d{4}-\d\d-\d\d', v) else ''


def change_words(e):
    c = e.get('changes')
    if isinstance(c, str):
        return [p.strip() for p in re.split(r'[\n;]+', c) if p.strip()]
    if isinstance(c, list):
        return [str(p.get('text') or p.get('what') or p) if isinstance(p, dict) else str(p) for p in c]
    return []


def learn(today=None):
    today = today or datetime.date.today()
    week = str(today - datetime.timedelta(days=7))
    choices = [c for c in make.special_choices()['add'] if isinstance(c, dict)]
    drafts = {}
    for f in sorted(os.listdir(DRAFTS)) if os.path.isdir(DRAFTS) else []:
        try:
            d = json.load(open(os.path.join(DRAFTS, f), encoding='utf-8')); drafts[d['day']] = d
        except (OSError, ValueError, KeyError):
            pass
    heads, stories, counts, shares, zooms, looks = [], [], [], [], [], {}
    swapped_big = kept = removed = added = compared = 0
    week_notes = []
    for c in choices:
        if c.get('look'):
            looks[c['look']] = looks.get(c['look'], 0) + 1
        lay = c.get('layout')
        if not isinstance(lay, dict) or not lay.get('items'):
            continue
        items = [i for i in lay['items'] if isinstance(i, dict)]
        ph = [i for i in items if i.get('type') == 'photo' and i.get('photo')]
        for i in items:
            if i.get('type') == 'text' and isinstance(i.get('size'), (int, float)):
                (heads if i.get('role') == 'headline' else stories if i.get('role') == 'story' else []).append(float(i['size']))
        if ph:
            counts.append(len(ph))
            big = max(ph, key=lambda i: float(i.get('w') or 0) * float(i.get('h') or 0))
            shares.append(float(big.get('w') or 0) / 2796)
            z = big.get('zoom')
            if isinstance(z, (int, float)):
                zooms.append(z / 100 if z > 5 else z)
        d = drafts.get(on(c) or '')
        if d and ph:
            compared += 1
            mine, his = [key(u) for u in d.get('photos') or []], [key(i['photo']) for i in ph]
            top = mine[:5]
            k = len(set(top) & set(his)); kept += k; removed += len(set(top) - set(his)); added += len(set(his) - set(mine))
            if mine and key(big['photo']) != mine[0]:
                swapped_big += 1
            if on(c) >= week:
                week_notes.append(f"{on(c)}: kept {k} of my first {len(top)} photos, added {len(set(his) - set(mine))} of his own"
                                  + (', and chose a different big photo' if mine and key(big['photo']) != mine[0] else ''))
    log = studio_log()
    kinds = {}
    for e in log:
        lay, first = e.get('layout'), e.get('first')
        his = [i for i in (lay or {}).get('items') or [] if isinstance(i, dict)] if isinstance(lay, dict) else []
        mine = [i for i in (first or {}).get('items') if isinstance(i, dict)] if isinstance(first, dict) and isinstance(first.get('items'), list) else []
        for i in his:
            if i.get('type') == 'text' and isinstance(i.get('size'), (int, float)):
                (heads if i.get('role') == 'headline' else stories if i.get('role') == 'story' else []).append(float(i['size']))
        hp = [i for i in his if i.get('type') == 'photo' and i.get('photo')]
        mp = [i for i in mine if i.get('type') == 'photo' and i.get('photo')]
        if hp and mp:
            compared += 1
            hk, mk = [key(i['photo']) for i in hp], [key(i['photo']) for i in mp]
            kept += len(set(hk) & set(mk)); removed += len(set(mk) - set(hk)); added += len(set(hk) - set(mk))
            big = lambda ps: key(max(ps, key=lambda i: float(i.get('w') or 0) * float(i.get('h') or 0))['photo'])
            if big(hp) != big(mp):
                swapped_big += 1
            counts.append(len(hp))
        if (lay or {}).get('look') if isinstance(lay, dict) else None:
            looks[lay['look']] = looks.get(lay['look'], 0) + 1
        words = change_words(e)
        for w in words:
            for k, rx in (('photo swaps', r'swap|replac|chang\w* (the )?photo'), ('photos removed', r'remov|took out|delet'),
                          ('photos added', r'add'), ('crops', r'crop|zoom|focus'), ('text sizes', r'size|bigger|smaller'),
                          ('moves', r'mov|position'), ('text style', r'font|colou?r|bold|weight|align|style')):
                if re.search(rx, w, re.I):
                    kinds[k] = kinds.get(k, 0) + 1
        d = entry_day(e)
        if d >= week and words:
            week_notes.append(f"{d}: " + '; '.join(words[:6]))
    med = lambda v: round(statistics.median(v), 2) if v else None
    got = dict(updated=str(today), layouts=len(counts), compared=compared, headline_size=med(heads), story_size=med(stories),
               photos=med(counts), big_share=med(shares), zoom=med(zooms), looks=looks,
               look=max(looks, key=looks.get) if looks and max(looks.values()) >= 3 else None,
               big_swapped=swapped_big, kept=kept, removed=removed, added=added, studio_log_entries=len(log),
               change_kinds=kinds)
    return got, week_notes


def plain(got, notes):
    """The lessons in plain words, as he would read them."""
    out = [f"What I learned from your Studio changes (week to {got['updated']})", '']
    if not got['layouts']:
        return '\n'.join(out + ['You did not arrange any special pictures in the Studio yet, so nothing new to learn this week.'])
    out.append(f"I looked at {got['layouts']} special pictures you arranged" + (f", {got['compared']} of them next to my first draft." if got['compared'] else '.'))
    if got['compared']:
        out.append(f"You kept {got['kept']} of my photos, took out {got['removed']} and put in {got['added']} of your own.")
        if got['big_swapped']:
            out.append(f"You chose a different big photo {got['big_swapped']} times, so I now lean even more to close ups of Bapa doing the action.")
    if got['story_size']:
        out.append(f"You like the story words at about size {got['story_size']:g}" + (f" and the headline at {got['headline_size']:g}" if got['headline_size'] else '') + '; the first drafts now start there.')
    if got['photos']:
        out.append(f"You usually use {got['photos']:g} photos" + (f", with the big photo about {round(got['big_share'] * 100)} percent of the width" if got['big_share'] else '') + '.')
    if got.get('change_kinds'):
        top = sorted(got['change_kinds'].items(), key=lambda kv: -kv[1])[:4]
        out.append('What you change most: ' + ', '.join(f'{k} ({n})' for k, n in top) + '.')
    if got['look']:
        out.append(f"You picked the look '{got['look']}' most often, so the first draft now comes in that look.")
    if notes:
        out += ['', 'This week:'] + [f'  {n}' for n in notes]
    return '\n'.join(out)


def main():
    got, notes = learn()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    json.dump({**old, **{k: v for k, v in got.items() if v is not None}}, open(OUT, 'w'), indent=1, ensure_ascii=False)
    os.makedirs(WEEKLY, exist_ok=True)
    text = plain(got, notes)
    open(os.path.join(WEEKLY, f"{got['updated']}.txt"), 'w', encoding='utf-8').write(text + '\n')
    print(text)


if __name__ == '__main__':
    main()
