"""Test only (never ship): for every festival and every year of it, the photos whose captions show the festival itself
with Bapa (fireworks, diyas, chopda pujan, annakut, colours, rath, rakhi...), best first. Darpan, 30 Oct 2026: 'there
must be pictures with Bapa and fireworks... make all the festivals and the pictures relevant to that event'.

python tools/fest_find.py  -> preview/fest/cands.json + preview/fest/want.txt"""
import datetime, glob, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWL = '/mnt/project-files/bapas-diary-crawl/'

# tiers, best first: what makes a photo clearly from this festival
FEST = {
    'diwali': [r'firework|fireworks|fatak', r'\bdiyas?\b|\blamps?\b|deepmala|deep ?pr|lights? (a|the)', r'chopda|sharda|lakshmi|account books?|vahi|ledger', r'diwali|deepavali'],
    'annakut': [r'annakut|annakoot|\bthal\b', r'new year|nutan varsh|bestu', r'govardhan'],
    'janmashtami': [r'janmashtami|janmotsav|krishna janm|\bmatki|dahi.?handi|paranu|cradle|nand mahotsav|panjari', r'krishna|thakorji.{0,20}swing|jhule|hindol'],
    'holi': [r'\bholi\b|holika|bonfire|\bfire\b', r'colou?rs?'],
    'fuldol': [r'colou?rs?|\brang|pichkari|gulal|sprinkl|spray', r'fuldol|pushpadol|dhuleti|phuldol', r'flowers? petals|showers? flowers'],
    'gurupurnima': [r'guru.?purnima|guru.?pujan|gurupujan', r'garland|honou?r|pujan|offers? (a )?(pranam|vandan)'],
    'harinom': [r'janmotsav|jayanti|hari.?nom|ram.?nav|birth', r'paranu|cradle|abhishek|swing'],
    'vasant': [r'vasant|panchami|panchmi', r'shikshapatri|yellow|shastriji'],
    'rathyatra': [r'rath|chariot', r'yatra|procession|pulls?'],
    'raksha': [r'rakhi|raksha'],
    'sharad': [r'sharad|dudh.?pau|pauva|moon', r'gunatitanand|jayanti'],
    'psm': [r'cake|birthday|janma.?jayanti|jayanti|tula', r'garland|honou?r|celebrat|swamishri.{0,30}greets'],
    'msm': [r'cake|birthday|janma.?jayanti|jayanti|tula', r'garland|honou?r|celebrat'],
}
NAME = re.compile(r'swamishri|swami maharaj|\bbapa\b|pramukh swami|mahant swami|\bhdh\b|\bhh\b', re.I)
NOT_BAPA = re.compile(r'^(devotees|children|balaks|kishores|youths|sadhus|swamis|thousands|the |a |an )|murti|mandir,|shri harikrishna|thakorji|ghanshyam maharaj|\bonly\b', re.I)


def files():
    """(album, stem lower) -> file name, from the full crawl."""
    out = {}
    for f in glob.glob(CRAWL + 'bapas-diary-*.json'):
        d = json.load(open(f, encoding='utf-8'))
        for p in d.get('pages', []):
            for r in p['rows']:
                out[(str(r[0]), os.path.splitext(r[1])[0].lower())] = r[1]
    return out


def day_lines(when):
    path = os.path.join(HERE, 'archive', 'vicharan', when.strftime('%m-%d') + '.txt')
    if not os.path.exists(path):
        return
    y = album = None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('# ') or not line.strip():
            continue
        if line.startswith('#'):
            head, _, rest = line[1:].partition('|')
            parts = head.split(' ')
            y, album, prefix = int(parts[0]), parts[1], (parts[2] if len(parts) > 2 else '')
            continue
        if y != when.year:
            continue
        ids, c = line.split('|', 1)
        for i in ids.split(','):
            yield album, prefix + i, c


def bapa_in(c):
    return bool(c[:1].islower() or NAME.search(c)) and not NOT_BAPA.search(c if not c[:1].islower() else '')


def main():
    names = files()
    out, want = {}, []
    for f in sorted(glob.glob(os.path.join(HERE, 'preview', 'fest', 'json', '*.json'))):
        fest = json.load(open(f, encoding='utf-8'))
        k = fest['fest']; tiers = [re.compile(t, re.I) for t in FEST[k]]
        name_re = tiers[0]
        years = []
        for y in fest['years']:
            d = datetime.date.fromisoformat(y['d'])
            seen, cands = set(), []
            for off in (0, -1, 1):
                for album, stem, c in day_lines(d + datetime.timedelta(days=off)):
                    fn = names.get((album, stem.lower()))
                    if not fn or (album, fn) in seen:
                        continue
                    t = next((i for i, r in enumerate(tiers) if r.search(c)), None)
                    if t is None or (off and not any(r.search(c) for r in tiers[:2])):
                        continue
                    seen.add((album, fn))
                    cands.append(dict(a=album, f=fn, c=c, t=t, bapa=bapa_in(c), off=off))
            for p in y['p']:   # the website's own face checked photos, as a fallback
                if (p[0], p[1]) not in seen:
                    t = next((i for i, r in enumerate(tiers) if r.search(p[2] or '')), 9)
                    cands.append(dict(a=p[0], f=p[1], c=p[2], t=t, bapa=True, off=0, web=1, box=p[4] if len(p) > 4 else None))
                    seen.add((p[0], p[1]))
            cands.sort(key=lambda x: (x['t'], not x['bapa'], x['off'] != 0, 'web' not in x))
            keep, caps = [], {}
            for x in cands:   # at most 2 photos of one caption, at most 8 a year
                if caps.get(x['c'], 0) >= 2:
                    continue
                caps[x['c']] = caps.get(x['c'], 0) + 1
                keep.append(x)
                if len(keep) >= 8:
                    break
            years.append(dict(y=y['y'], d=y['d'], place=y.get('place', ''), c=keep))
            want += [f"{x['a']}\t{x['f']}" for x in keep]
        out[k] = dict(title=fest['title'], years=years)
        print(k, sum(1 for y in years if y['c'] and y['c'][0]['t'] < 9), 'of', len(years), 'years have a festival caption')
    json.dump(out, open(os.path.join(HERE, 'preview', 'fest', 'cands.json'), 'w'), indent=0)
    open(os.path.join(HERE, 'preview', 'fest', 'want.txt'), 'w').write('\n'.join(dict.fromkeys(want)) + '\n')
    print(len(set(want)), 'photos wanted')


if __name__ == '__main__':
    main()
