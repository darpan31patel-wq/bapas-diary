#!/usr/bin/env python3
"""Collects each day's new vicharan photos of Bapa from baps.org, without Claude and without reading baps.org pages.

baps.org pages sit behind a Cloudflare check that GitHub can't pass, but the photos themselves load fine,
and vicharan photos are named in one pattern:

    https://www.baps.org/Data/Sites/1/Media/GalleryImages/<album>/WebImages/<YYYY>_<MM>_<DD>_<NNN>_<Place>.jpg

Album numbers only ever go up. So each run tries the next album numbers with the recent dates and the place
Bapa is likely to be (the vicharan schedule, then where he was last), lists the whole album once it finds it,
keeps the photos where Bapa's face is recognised and adds them to archive/MM-DD.json.
make.py adds those to the On This Day list, so next year's picture for that date includes them.

    python collect.py                  look for albums up to today (London)
    python collect.py --today 2026-10-12
"""
import argparse, concurrent.futures, datetime, io, json, os, urllib.error, urllib.request
from zoneinfo import ZoneInfo

from PIL import Image

import make

HERE = os.path.dirname(os.path.abspath(__file__))
ARCHIVE = os.path.join(HERE, 'archive')
STATE = os.path.join(ARCHIVE, 'state.json')
SCHEDULE_URL = 'https://darshan-screensaver.pages.dev/memories/schedule.json'
PHOTO = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{d:%Y_%m_%d}_{n:03d}_{name}.jpg'
LOOKBACK = 6          # albums usually appear within a day or two; look back this many days
KEEP = 30             # photos of Bapa kept per day
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
PLACES = json.load(open(os.path.join(HERE, 'places.json')))
errors = 0


def exists(url):
    """True when the photo is there, False when baps.org says it isn't."""
    global errors
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA, 'Accept': 'image/*'})
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20):
                return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
        except Exception:
            pass
    errors += 1
    return False


def names_for(city):
    p = PLACES.get(city)
    return p['names'] if p else [city.replace(' ', '_')]


def schedule_names(day, schedule):
    out = []
    for s in schedule.get('stays', []):
        if s['from'] <= str(day) <= s['to']:
            city = s['place'].split(',')[0].strip()
            out += [(n, s['place']) for n in names_for(city)]
    return out


def display_place(name, schedule_pairs):
    for n, place in schedule_pairs:
        if n == name:
            return place
    for city, p in PLACES.items():
        if name in p['names']:
            return p['place']
    return name.replace('_', ' ')


def find_albums(state, today, schedule):
    """[(album, date, name)] for new vicharan albums, newest album numbers first tried in order."""
    known = {int(a) for a in state['albums']}
    found_dates = {v['date'] for v in state['albums'].values() if v['kept']}
    last_date = datetime.date.fromisoformat(state['last_date'])
    start = max(datetime.date.fromisoformat(state['since']), today - datetime.timedelta(LOOKBACK))
    days = [start + datetime.timedelta(k) for k in range((today - start).days + 1)]
    days = [d for d in days if str(d) not in found_dates]
    if not days:
        return []
    quiet = (today - last_date).days
    window = min(200, 40 + 20 * quiet)          # more albums get uploaded while we wait
    combos = []
    for d in days:
        names = [n for n, _ in schedule_names(d, schedule)] + state['names']
        combos += [(d, n) for n in dict.fromkeys(names)]
    if quiet > 3:                                # nothing found for a while: also try his usual places
        usual = sorted(PLACES.values(), key=lambda p: -p['since_2017'])[:12]
        combos += [(d, p['names'][0]) for d in days[-2:] for p in usual if (d, p['names'][0]) not in combos]
    print(f'Looking for {len(days)} day(s) {days[0]} to {days[-1]} in albums {state["last_album"] + 1} to '
          f'{state["last_album"] + window}, names {sorted({n for _, n in combos})}')

    def album(a):
        for d, name in combos:
            for n in (1, 2, 3):
                if exists(PHOTO.format(album=a, d=d, n=n, name=name)):
                    return a, d, name
        return None

    ids = [a for a in range(state['last_album'] + 1, state['last_album'] + window + 1) if a not in known]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        return [r for r in pool.map(album, ids) if r]


def list_album(a, d, name, gap=45, most=600):
    """Every photo number in the album (numbers have gaps where photos were left out)."""
    nums, n, last_hit = [], 1, 0
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        while n <= most and n - last_hit <= gap:
            batch = list(range(n, n + 16))
            for k, ok in zip(batch, pool.map(lambda k: exists(PHOTO.format(album=a, d=d, n=k, name=name)), batch)):
                if ok:
                    nums.append(k); last_hit = k
            n += 16
    return [PHOTO.format(album=a, d=d, n=k, name=name) for k in nums]


def bapa_photos(urls, when):
    """(score, url) for photos where Bapa is recognised, best first."""
    def one(url):
        try:
            im = Image.open(io.BytesIO(make.fetch(url))).convert('RGB')
        except Exception:
            return None
        face, sim = make.bapa_face(im, when)
        return (min(face[3] / im.height, .35) + sim, url) if face else None
    with concurrent.futures.ThreadPoolExecutor(6) as pool:
        return sorted((r for r in pool.map(one, urls) if r), reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', help='YYYY-MM-DD (default: today in London)')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(ZoneInfo('Europe/London')).date()
    state = json.load(open(STATE))
    try:
        schedule = json.loads(make.fetch(SCHEDULE_URL))
    except Exception as e:
        print('No vicharan schedule this time:', e)
        schedule = {}

    found = find_albums(state, today, schedule)
    if errors > 50:
        raise SystemExit(f'baps.org refused {errors} requests; trying again next time')
    if not found:
        print('No new vicharan albums yet')
        return

    for album, d, name in sorted(found):
        urls = list_album(album, d, name)
        place = display_place(name, schedule_names(d, schedule))
        keep = bapa_photos(urls, str(d))[:KEEP]
        print(f'Album {album}: {d} {place}, {len(urls)} photos, Bapa recognised in {len(keep)} kept')
        path = os.path.join(ARCHIVE, f'{d:%m-%d}.json')
        items = json.load(open(path)) if os.path.exists(path) else []
        have = {x['i'] for x in items}
        items += [{'y': d.year, 'd': str(d), 'p': place, 'i': url, 'c': ''} for _, url in keep if url not in have]
        json.dump(items, open(path, 'w'), indent=1, ensure_ascii=False)
        state['albums'][str(album)] = {'date': str(d), 'name': name, 'photos': len(urls), 'kept': len(keep)}

    state['last_album'] = max(state['last_album'], max(f[0] for f in found))
    with_bapa = [(d, name) for album, d, name in found if state['albums'][str(album)]['kept']]
    if with_bapa:
        d, name = max(with_bapa)
        state['last_date'] = max(state['last_date'], str(d))
        state['names'] = [name]
    json.dump(state, open(STATE, 'w'), indent=1)


if __name__ == '__main__':
    main()
