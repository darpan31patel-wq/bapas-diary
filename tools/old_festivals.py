"""Festival days before the BAPS calendar in the diary begins (2010), for Ask the diary on the search page.

Darpan, 26 Oct 2026: "Ask the diary: more festivals before 2010". The diary's BAPS calendar (table `calendar` in
bapas.db) runs from 2010 to 2027. For the years before, each festival's day is worked out from the moon and the sun,
the way the Gujarati calendar is made: the tithi (lunar day) and the month (amant, starting at each new moon, named by
the sun's sidereal sign, with adhik months). The rule for each festival (its month, tithi and the time of day the tithi
must hold: sunrise for most, evening for Holi and Diwali) is learnt from the BAPS calendar itself, and checked on it:
the worked out days match the BAPS calendar on 9 in 10 festival days from 2010 to 2027, and the rest are one day off.
Then checked against the photo captions of 1999 to 2009 that name a festival (118 agree; the 13 that do not are
celebrations held on a nearby day, or albums dated a day early).

Run by hand (needs `pip install ephem`); it prints the OLD_FEST table that goes into site/search-ask.js:
    python3 tools/old_festivals.py --db bapas.db
"""
import argparse, collections, datetime as dt, functools, json, math, os, sqlite3, sys

import ephem

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_search import festivals

FIRST, LAST = 1940, 2009
MONTHS = ['Chaitra', 'Vaishakh', 'Jeth', 'Ashadh', 'Shravan', 'Bhadarvo', 'Aso', 'Kartak', 'Magshar', 'Posh', 'Maha', 'Fagan']
TITHI = ['Padvo', 'Bij', 'Trij', 'Choth', 'Pancham', 'Chhath', 'Satam', 'Atham', 'Nom', 'Dasham', 'Ekadashi', 'Baras', 'Teras', 'Chaudas']
LAT, LON = '23.03', '72.58'   # Ahmedabad
WHENS = ['sunrise', 'aparahna', 'pradosh', 'night']
# festivals whose day the sums could not find reliably (half or less right on the BAPS calendar), left out
SKIP = {'Nrusinh Jayanti', 'Sam Shravani', 'Vagh Baras', 'Shastriji Maharaj Smruti Parva', 'Rang Panchami', 'Bhim Ekadashi'}


def ayanamsa(d):   # Lahiri, in degrees
    return 23.853 + (float(d) - float(ephem.Date('2000/1/1 12:00'))) / 365.25 * 0.0139694


def longitudes(d):
    sun = math.degrees(ephem.Ecliptic(ephem.Sun(d), epoch=d).lon)
    moon = math.degrees(ephem.Ecliptic(ephem.Moon(d), epoch=d).lon)
    return sun, moon


def tithi_at(d):   # 0..29: 0 to 14 sud (14 = punam), 15 to 29 vad (29 = amas)
    sun, moon = longitudes(d)
    return int(((moon - sun) % 360) // 12)


def sign(d):
    return int(((longitudes(d)[0] - ayanamsa(d)) % 360) // 30)


@functools.lru_cache(None)
def month_from(nm):   # the month that starts at this new moon
    nm = ephem.Date(nm)
    s = sign(ephem.Date(nm + 0.01))
    nxt = ephem.next_new_moon(ephem.Date(nm + 1))
    return ('Adhik ' if s == sign(ephem.Date(nxt + 0.01)) else '') + MONTHS[(s + 1) % 12]


@functools.lru_cache(None)
def sun_times(day):
    o = ephem.Observer(); o.lat, o.lon = LAT, LON; o.pressure = 0; o.horizon = '-0:50'
    o.date = ephem.Date(dt.datetime(day.year, day.month, day.day) - dt.timedelta(hours=5.5))   # midnight in India
    return float(o.next_rising(ephem.Sun())), float(o.next_setting(ephem.Sun()))


def moment(day, when):
    rise, sets = sun_times(day)
    return {'sunrise': rise, 'aparahna': rise + (sets - rise) * 0.7, 'pradosh': sets + 0.0625, 'night': sets + 0.2}[when]


@functools.lru_cache(None)
def lunar(day, when):
    x = ephem.Date(moment(day, when))
    return float(ephem.previous_new_moon(x)), tithi_at(x)


def tithi_index(paksha, tithi):
    t = tithi.split('/')[0]
    return 14 if t == 'Punam' else 29 if t == 'Amas' else TITHI.index(t) + (0 if paksha == 'Sud' else 15)


def find(year, month, T, when, usual):
    """The first day of `year` near `usual` (MM-DD) on which tithi T of `month` holds at `when`, or has just passed."""
    mid = dt.date.fromisoformat(f'{year}-{usual}')
    start = ephem.Date(dt.datetime(mid.year, mid.month, mid.day)) - (T + 0.5) * 0.984
    moons, nm = [], ephem.previous_new_moon(start - 60)
    while nm < start + 60:
        if month_from(round(float(nm), 4)) == month:
            moons.append(float(nm))
        nm = ephem.next_new_moon(ephem.Date(nm + 1))
    if not moons:
        return None
    nm0 = min(moons, key=lambda n: abs(n - start))
    d0 = ephem.Date(nm0).datetime().date() - dt.timedelta(days=1)
    for k in range(40):
        d = d0 + dt.timedelta(days=k)
        n, t = lunar(d, when)
        if T <= round((n - nm0) / 29.530589) * 30 + t < T + 3:
            return d
    return None


def learn(db):
    """Each festival's rule, from the BAPS calendar: its usual month and tithi, and the time of day that fits best."""
    days, seen = collections.defaultdict(list), collections.defaultdict(collections.Counter)
    for d, m, p, t, f in db.execute('SELECT date, month, paksha, tithi, festivals FROM calendar'):
        for x in festivals(f):
            days[x].append(d)
            if t:
                seen[x][(m, p, t)] += 1
    rules = {}
    for x, ds in days.items():
        if x in SKIP or len(ds) < 3:
            continue
        usual = sorted(d[5:] for d in ds)[len(ds) // 2]
        if len({d[5:] for d in ds}) <= 2:   # a fixed date (Republic Day, Uttarayan)
            rules[x] = {'fixed': collections.Counter(d[5:] for d in ds).most_common(1)[0][0], 'right': len(ds), 'of': len(ds)}
            continue
        (m, p, t), _ = seen[x].most_common(1)[0]
        T = tithi_index(p, t)
        best = max(WHENS, key=lambda w: sum(str(find(int(d[:4]), m, T, w, usual)) == d for d in ds))
        right = sum(str(find(int(d[:4]), m, T, best, usual)) == d for d in ds)
        rules[x] = {'month': m, 'tithi': T, 'when': best, 'usual': usual, 'right': right, 'of': len(ds)}
    return rules


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    a = ap.parse_args()
    rules = learn(sqlite3.connect(a.db))
    out = {}
    for x, r in sorted(rules.items()):
        print(f"{x}: {r.get('fixed') or r['month'] + ' ' + str(r['tithi']) + ' at ' + r['when']}, {r['right']} of {r['of']} right", file=sys.stderr)
        dates = []
        for y in range(FIRST, LAST + 1):
            d = f"{y}-{r['fixed']}" if 'fixed' in r else str(find(y, r['month'], r['tithi'], r['when'], r['usual']) or '')
            dates.append(d[5:].replace('-', '') if d.startswith(str(y)) else '----')
        out[x] = ''.join(dates)
    print(f'  // worked out by tools/old_festivals.py: for each festival, MMDD for every year from {FIRST} to {LAST}')
    print(f'  const OLD_FEST_FROM = {FIRST}, OLD_FEST = {json.dumps(out, ensure_ascii=False, indent=0)};')


if __name__ == '__main__':
    main()
