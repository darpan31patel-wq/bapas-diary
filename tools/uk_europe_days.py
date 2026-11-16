#!/usr/bin/env python3
"""Every calendar day Bapa was in the UK or Europe, as one file the Collage builder can read (live/uk-europe-days.json,
served at bapas-diary.com/uk-europe-days.json).

Darpan, 14 Nov 2026: "When there's 2 or more days that Bapa has been in the UK, Europe, I would like a special card
made. Keep it ready as a backup for anything else ... as many nice pictures as possible ... captions ... the text is
secondary ... so we can see exactly on that day what Bapa was doing."

We only KEEP and SHOW: the Collage builder chooses the photos and builds the picture. This file gives it, for each
day (MM-DD), every year Bapa was there, the guru, the places, the day's dated stories and every photo of Bapa we hold:
  - database photos (Bapa clearly in them), large and small copies on photos.bapas-diary.com, caption, close up or
    activity, and the face picker's rank (0 = best darshan of that album);
  - older photos (1970 to 1998 have no others) by their folder in his archive, "<date> <place> (post N)", with the
    story line as caption. No links and no channel names (the public site never names where words come from).
"backup": true marks the days with 2 or more years: a UK and Europe special should always be ready for those.

Visits are worked out from the dated stories (places in the UK and Europe, a visit = stories no more than 10 days
apart, plus the arrival and departure days) and the Travels page. Rerun after a new visit:
  python3 tools/uk_europe_days.py --db "Bapas Diary everything.db" --travels live/travels/index.html --out live/uk-europe-days.json
(the db is the master database export, tools/export_everything.py; its tables photos, everything_photos, bapa_pick,
on_this_day and tg_posts are used).
"""
import argparse, collections, datetime as dt, json, re, sqlite3

EUROPE = set('''Antwerp|Ashton under Lyne|Ashton-under-Lyne|Audenshaw|Barcelona|Beaulieu|Birmingham|Bochum|Boras|
Bradford|Cardiff|Colchester|Crawley|Flawil|Leeds|Leicester|Lisbon|London|Luton|Manchester|Mariestad|Melton Mowbray|
Middlesbrough|Milton Keynes|Netherlands|Nottingham|Nuneaton|Oldham|Oslo|Paris|Peterborough|Prague|Preston|Rome|
Rushden|Sarpsborg|Southampton|Southend-on-Sea|St. Helens|Stalybridge|Vatican City|Vienna|Wellingborough|
Welwyn Garden City|Wickford|Wigan|Wolverhampton'''.replace('\n', '').split('|'))
TRAVELS_COUNTRIES = {'UK', 'France', 'Portugal'}
# stories in UK or Europe towns that are not a visit by the day's guru
NOT_A_VISIT = {'2011-10-09', '2022-07-31', '2025-10-29',   # mandir opened by senior swamis, a festival, the King's visit
               '2002-06-06', '2002-06-08', '2002-06-09',   # Mahant Swami before he was guru
               '2014-08-18'}                               # refuelling stop in Paris on the plane home
# Travels albums whose date range runs on into the next country: the stories give the real first and last days
TRAVELS_FIX = {('London', '2000-06-03'): ('2000-06-09', None), ('London', '2000-07-01'): (None, '2000-07-17'),
               ('London', '2000-11-01'): (None, '2000-11-06'), ('Lisbon', '2000-06-16'): (None, '2000-06-18')}
MSM_FROM = '2016-08-13'
# a photo's place must be in the UK or Europe (Collage builder, 14 Nov 2026: travel days carried Ahmedabad, New York,
# New Delhi, Toronto and Sarangpur photos)
IN_EUROPE = re.compile(r'\bUK\b|U\.K\.|Europe|England|Scotland|Wales|Ireland|France|Portugal|Italy|Vatican|Belgium|'
                       r'Netherlands|Spain|Switzerland|Austria|Germany|Sweden|Norway|Czech|Russia|Greece|Poland|'
                       + '|'.join(re.escape(t) for t in sorted(EUROPE)))
# an album's heading written as each photo's caption ("Pramukh Swami Maharaj's Satsang Vicharan in London, UK & Europe",
# "Swami Bapa, My Best Friend | Shishu Din, UK & Europe"): not a caption, so it is replaced or left out
HEADING = re.compile(r'\||Satsang Vicharan|\bVisit \d{4}|^Moods of|(, (UK|London, UK|UK & Europe|France|Portugal))( \d{4})?$|'
                     r'^(Pramukh|Mahant) Swami Maharaj\'s .*(Vicharan|Visit|Tour)\b', re.I)
NOT_SAID = re.compile(r'https?://\S+|t\.me\S*|telegram', re.I)


def guru(day):
    if day.year == 1970:
        return 'Yogiji Maharaj, with Pramukh Swami and Mahant Swami'
    return 'Mahant Swami Maharaj' if day.isoformat() >= MSM_FROM else 'Pramukh Swami Maharaj'


def is_heading(cap, same):
    return bool(cap) and (bool(HEADING.search(cap)) or same >= 25)


def clean(t):
    return re.sub(r'\s+', ' ', NOT_SAID.sub('', t or '')).strip()


def visits(db, travels):
    seen = collections.defaultdict(set)
    for d, p in db.execute('SELECT date, place FROM on_this_day'):
        if d and d >= '1970' and p in EUROPE and d not in NOT_A_VISIT:
            seen[dt.date.fromisoformat(d[:10])].add(p)
    T = json.loads(re.search(r'<script[^>]*id="trips"[^>]*>(.*?)</script>', open(travels).read(), re.S).group(1))
    for stops in T['years'].values():
        for s in stops:
            if T['places'][s['p']]['country'] not in TRAVELS_COUNTRIES:
                continue
            a, b = TRAVELS_FIX.get((s['p'], s['a']), (None, None))
            a, b = dt.date.fromisoformat(a or s['a']), dt.date.fromisoformat(b or s['b'])
            while a <= b:
                seen[a].add(s['p'])
                a += dt.timedelta(1)
    days = sorted(seen)
    groups = [[days[0]]]
    for x in days[1:]:
        if (x - groups[-1][-1]).days <= 10:
            groups[-1].append(x)
        else:
            groups.append([x])

    def said(d):
        return ' '.join(s or '' for (s,) in db.execute('SELECT story FROM on_this_day WHERE date = ?', (d.isoformat(),)))
    out = []
    for g in groups:
        a, b = g[0], g[-1]
        if re.search(r'Heathrow|Gatwick', said(a - dt.timedelta(1))):
            a -= dt.timedelta(1)
        if re.search(r'Heathrow|Gatwick|Luton|Neasden|London|UK|Viday|Departure from (Prague|Paris|Lisbon)', said(b + dt.timedelta(1))):
            b += dt.timedelta(1)
        out.append((a, b))
    return out, seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--travels', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sorg-rows', help='swaminarayan-org-web release sorg-rows.json: the old BAPS website photos')
    ap.add_argument('--sorg-have', help='sorg-have.txt: the photos already in the photo store')
    ap.add_argument('--sorg-captions', help='sorg-captions.json: the old site\'s own caption of a baps.org photo')
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    tours, places = visits(db, a.travels)
    inside = lambda d: next(((x, y) for x, y in tours if x <= d <= y), None)

    rank = {(al, f): (r, c) for al, f, r, c in db.execute('SELECT album, file, rank, close FROM bapa_pick')}
    better = {}
    if a.sorg_captions:
        for k, v in json.load(open(a.sorg_captions)).items():
            if v.get('swaminarayan_org'):
                better[tuple(k.split('/', 1))] = clean(v['swaminarayan_org'])
    same = collections.Counter((al, c) for al, c in db.execute('SELECT album, caption FROM photos WHERE is_bapa = 1'))
    left_out = collections.Counter()
    photos = collections.defaultdict(list)
    for d, f, t, place, al, fi, cap, kind, big, small in db.execute(
            '''SELECT p.date, p.date_from, p.date_to, p.place, p.album, p.file, p.caption, e.close_up_or_activity,
                      e.high_quality_photo, e.small_photo
               FROM photos p JOIN everything_photos e ON e.album = p.album AND e.file = p.file WHERE p.is_bapa = 1'''):
        if d:
            span = [dt.date.fromisoformat(d[:10])]
        elif f:
            x, y = dt.date.fromisoformat(f[:10]), dt.date.fromisoformat((t or f)[:10])
            tour = inside(x)
            if not tour or y > tour[1]:   # an album that runs on past the visit could be from the next country
                continue
            span = [x + dt.timedelta(i) for i in range((y - x).days + 1)]
        else:
            continue
        if not place or not IN_EUROPE.search(place):
            left_out['photo outside the UK and Europe'] += 1
            continue
        c2 = clean(cap)
        if is_heading(c2, same[(al, cap)]):
            c2 = better.get((al, fi), '')
            left_out['album heading as caption: ' + ('the old site\'s caption used' if c2 else 'no caption')] += 1
        if '|' in place or HEADING.search(place) and ',' not in place[:25]:
            place = ''   # a heading in the place too: the day's own place is in "places"
        for day in span:
            if inside(day):
                r, c = rank.get((al, fi), (None, None))
                photos[day].append({k: v for k, v in (('large', big), ('small', small), ('caption', c2),
                                    ('place', place), ('look', kind), ('rank', r), ('exact_day', bool(d))) if v not in (None, '')})
    # the old BAPS website's own photos of these visits (1999 to 2007), only those in the photo store whose caption names Bapa
    if a.sorg_rows and a.sorg_have:
        have = set(open(a.sorg_have).read().split())
        known = {(p['large']) for v in photos.values() for p in v}
        for r in json.load(open(a.sorg_rows)):
            d = r.get('date') or (r.get('date_from') if r.get('date_from') == r.get('date_to') else None)
            if not d or not r.get('is_bapa') or f"s/{r['album']}/{r['file']}" not in have:
                continue
            try:
                day = dt.date.fromisoformat(d[:10])
            except ValueError:
                continue
            words = ' '.join(filter(None, (r.get('caption'), r.get('place'), r.get('page_url'))))
            if r.get('place') and not IN_EUROPE.search(r['place']):
                continue
            if not inside(day) or not IN_EUROPE.search(words) or re.search(r'New York|USA|Canada|India|Africa|Kenya', r.get('caption') or ''):
                continue
            big = f"https://photos.bapas-diary.com/{'o' if 'o/' + r['album'] + '/' + r['file'] in have else 's'}/{r['album']}/{r['file']}"
            if big in known:
                continue
            c2 = clean(r.get('caption'))
            photos[day].append({k: v for k, v in (('large', big), ('small', f"https://photos.bapas-diary.com/s/{r['album']}/{r['file']}"),
                                ('caption', '' if is_heading(c2, 0) else c2), ('place', r.get('place') or ''),
                                ('from', 'old BAPS website'), ('exact_day', True)) if v not in (None, '')})

    stories = collections.defaultdict(list)
    older = collections.defaultdict(list)
    for d, p, line, story, src, link, posts in db.execute(
            'SELECT date, place, line, story, source, source_link, posts FROM on_this_day WHERE date >= "1970"'):
        day = dt.date.fromisoformat(d[:10])
        if not inside(day) or d in NOT_A_VISIT:
            continue
        if p and p not in EUROPE and not re.search(r'Heathrow|Gatwick|Luton|Neasden|London', story or ''):
            continue   # the day he flew on: only what happened before he left
        s = {k: v for k, v in (('place', p), ('line', clean(line)), ('story', clean(story))) if v}
        if s.get('line') and not any(o.get('line') == s['line'] for o in stories[day]):
            stories[day].append(s)
        ch = 'history' if 'TodayinBAPShistory' in (link or '') else 'satpurush'
        ids = json.loads(posts or '[]') or ([int(link.rstrip('/').rsplit('/', 1)[-1])] if link else [])
        for n in ids:
            row = db.execute('SELECT local_folder, photos FROM tg_posts WHERE channel = ? AND id = ?', (ch, n)).fetchone()
            if row and row[0] and row[1]:
                folder = row[0].rsplit('/', 1)[-1]
                if not folder.startswith(day.isoformat()):   # a post about another year (31 March 1982 listed a 1984 post)
                    left_out['older folder of another date'] += 1
                    continue
                if not any(o['folder'] == folder for o in older[day]):
                    older[day].append({k: v for k, v in (('folder', folder), ('photos', row[1]), ('caption', clean(line or story)),
                                       ('words', clean(story))) if v})

    days = {}
    for m in range(1, 13):
        for n in range(1, 32):
            try:
                k = dt.date(2024, m, n)
            except ValueError:
                continue
            years = []
            for x, y in tours:
                for yr in range(x.year, y.year + 1):
                    try:
                        day = dt.date(yr, m, n)
                    except ValueError:
                        continue
                    if x <= day <= y:
                        ph = sorted(photos[day], key=lambda p: (p.get('rank') is None, p.get('rank') or 0, p.get('look') != 'close up'))
                        years.append({'year': yr, 'date': day.isoformat(), 'guru': guru(day),
                                      'places': sorted(places.get(day, [])),
                                      'visit': f'{x:%-d %B %Y} to {y:%-d %B %Y}',
                                      'stories': stories[day], 'photos': ph, 'older_photos': older[day],
                                      'photo_count': len(ph) + sum(o['photos'] for o in older[day])})
            if years:
                days[k.strftime('%m-%d')] = {'title': f'{k:%-d %B}', 'backup': len(years) >= 2,
                                             'both_gurus': len({y['guru'] for y in years if y['year'] > 1970}) == 2,
                                             'years': years}
    file = {'about': "Every year Bapa was in the UK or Europe on each calendar day. Days with backup true (2 or more "
                     "years) should always have a UK and Europe special picture ready. Photos: large and small copies, "
                     "best first (rank 0 = the best darshan of its album), only photos taken in the UK or Europe; a photo whose caption was only the album's heading has the old BAPS website's own caption, or none. Captions are whole. older_photos = folders in Bapa's Archive, not yet checked for Bapa: use only those where Bapa is clearly seen.",
            'made': dt.date.today().isoformat(),
            'visits': [{'from': x.isoformat(), 'to': y.isoformat(), 'guru': guru(x)} for x, y in tours],
            'no_visit': [f'{dt.date(2024, m, n):%m-%d}' for m in range(1, 13) for n in range(1, 32)
                         if _ok(m, n) and f'{dt.date(2024, m, n):%m-%d}' not in days],
            'days': days}
    json.dump(file, open(a.out, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(dict(left_out))
    print(len(tours), 'visits,', len(days), 'days,', sum(d['backup'] for d in days.values()), 'backup days')


def _ok(m, n):
    try:
        dt.date(2024, m, n)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    main()
