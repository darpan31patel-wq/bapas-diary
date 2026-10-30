"""Places that are a year or a date, made right for the website (Darpan's Today, 19 June: the 2004 card said "2004" where
the town goes). baps.org named the 2004 tour's albums '2004, Los Angeles', '2004, Houston' ... and two murti albums only
by their date ('15 June 2012', '13 to 19 March 2011'), so every page that shows the first part of a place showed a year.

Website only: run by .github/workflows/website-deploy.yml right after the database is downloaded, so Today, Calendar,
Search, Year in review and the Darshan tab all read the right town; nothing here touches the daily 2pm picture.

    python3 tools/web_places.py --db bapas.db                             the photos' places, in the database (and places-fixed.json)
    python3 tools/web_places.py --page out/through-the-years/index.html   the same places on a built page, from places-fixed.json

'2004, Los Angeles' -> 'Los Angeles, CA' (the town's usual full name in the photos), '2004, Orlando' -> 'Orlando';
a date with no town -> the town of the next photos dated after it ('15 June 2012' -> 'Ahmedabad, India').
"""
import argparse, collections, json, re, sqlite3

YEAR = re.compile(r'\s*(?:1[89]|20)\d\d\s*')
MONTH = r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*'
DATE = re.compile(r'[\d\s,.\-/]*(?:\d{1,2}\s+(?:to\s+\d{1,2}\s+)?' + MONTH + r'|' + MONTH + r'\s+\d{1,2})[\w\s,.\-/]*\d{4}\s*', re.I)


def not_a_town(text):
    """'2004', '15 June 2012', '13 to 19 March 2011': a year or a date, never a town."""
    t = (text or '').strip()
    return bool(t) and bool(YEAR.fullmatch(t) or DATE.fullmatch(t) or re.fullmatch(r'[\d\s,.\-/]+', t))


def town_of(place):
    """The town a place names, never a year: '2004, Houston' -> 'Houston', '15 June 2012' -> ''."""
    for part in (place or '').split(','):
        if part.strip() and not not_a_town(part):
            return part.strip()
    return ''


def fixes(db):
    """{wrong place: right place} for every photo place that starts with a year or is a date."""
    count = collections.Counter(p for (p,) in db.execute('SELECT place FROM photos WHERE place IS NOT NULL'))
    towns = {p.split(',')[0].strip() for p in count}
    full = {}   # 'Houston' -> 'Houston, TX': the town's most used place whose second part is a state or country, not a town
    for p, n in count.most_common():
        parts = [x.strip() for x in p.split(',')]
        if len(parts) == 2 and not not_a_town(parts[0]) and parts[1] not in towns and not not_a_town(parts[1]):
            full.setdefault(parts[0], p)
    out = {}
    for p in count:
        if not not_a_town(p.split(',')[0]):
            continue
        t = town_of(p)
        if t:
            out[p] = full.get(t, t)
            continue
        # only a date: where the next photos dated after it are (or the ones before, at the end of the archive)
        start = db.execute('SELECT MIN(COALESCE(date, date_from)) FROM photos WHERE place = ?', (p,)).fetchone()[0] or ''
        for sql in ('SELECT place FROM photos WHERE COALESCE(date, date_from) > ? ORDER BY COALESCE(date, date_from)',
                    'SELECT place FROM photos WHERE COALESCE(date, date_from) < ? ORDER BY COALESCE(date, date_from) DESC'):
            near = next((q for (q,) in db.execute(sql, (start,)) if q and not not_a_town(q.split(',')[0])), '')
            if near:
                out[p] = near
                break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', action='append', default=[], help='a database whose photos get their towns')
    ap.add_argument('--page', action='append', default=[], help='a built page whose places are put right as well')
    ap.add_argument('--map', default='places-fixed.json', help='the places put right, kept for --page (default %(default)s)')
    a = ap.parse_args()
    fix = {}
    for path in a.db:
        db = sqlite3.connect(path)
        fix.update(fixes(db))
        n = sum(db.execute('UPDATE photos SET place = ? WHERE place = ?', (new, old)).rowcount for old, new in fix.items())
        db.commit()
        print(f'{path}: {n} photos given their town')
    if a.db:
        json.dump(fix, open(a.map, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    elif a.page:
        fix = json.load(open(a.map, encoding='utf-8'))
    for path in a.page:
        html = open(path, encoding='utf-8').read()
        n = 0
        for old, new in fix.items():
            q = json.dumps(old, ensure_ascii=False)
            n += html.count(q)
            html = html.replace(q, json.dumps(new, ensure_ascii=False))
        open(path, 'w', encoding='utf-8').write(html)
        print(f'{path}: {n} places given their town')
    for old, new in sorted(fix.items()):
        print(f'  {old!r} -> {new!r}')


if __name__ == '__main__':
    main()
