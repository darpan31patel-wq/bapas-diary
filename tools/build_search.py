"""Build the searchable photo database page from bapas.db (Darpan, 23 Oct 2026: search the captions for words, by year and month).

    python tools/build_search.py --db bapas.db --out search

Writes a folder that works as it is on any web host (Cloudflare Pages, or opened from a small local server):
  index.html          the search page (site/search.html wrapped as a full page)
  data/YYYY.json      one file per year of baps.org photos:
                        {"g": [[date, date_to, place, album], ...],      a group = one album on one day (or date range)
                         "p": [[group, file, caption, is_bapa], ...]}    every photo, nothing cut out
  data/stories.json   every On this day story (the Telegram channel posts, shown without any Telegram links): [[date, place, text], ...]
  data/calendar.json  every BAPS calendar day, when the database has the calendar table:
                        [[date, weekday, vikram_samvat, indian_date, festivals, festival_about, notes, source], ...]
  data/about.json     years, counts and when it was built
"""
import argparse, json, os, sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(HERE, 'site', 'search.html')


# The BAPS calendar spells some festivals differently from year to year. Each spelling maps to one name, so the
# festival list on the search page has every festival once (Darpan, 23 Oct 2026: "be smart with the festivals").
SAME_FESTIVAL = {
    'bhai bij': 'Bhai Beej',
    'devpodhi ekadashi': 'Devshayani Ekadashi', 'devshayani ekadashi': 'Devshayani Ekadashi',
    "mahant swami maharaj's jayanti": "Mahant Swami Maharaj's Jayanti",
    'mahant swami maharaj janma jayanti': "Mahant Swami Maharaj's Jayanti",
    'mahant swami maharaj janma jayanti celebration': "Mahant Swami Maharaj's Jayanti",
    'vasant panchami': 'Vasant Panchmi',
    'annakut and bestu varash': 'Annakut and Bestu Varash (New Year)', 'annakut': 'Annakut and Bestu Varash (New Year)',
    'bestu varash': 'Annakut and Bestu Varash (New Year)',
    'akha trij': 'Akhatrij',
    'pramukh varani din': 'Pramukh Varni Din',
    'pushpadolotsav': 'Pushpadolotsav (Dhuleti)', 'dhuleti/pushpadolotsav': 'Pushpadolotsav (Dhuleti)', 'dhuleti': 'Pushpadolotsav (Dhuleti)',
    'sam-shravani': 'Sam Shravani', 'sam shravni': 'Sam Shravani',
    "aksharbrahma gunatitanand swami's birthday": "Gunatitanand Swami's Birthday (Sharad Punam)",
    'aksharbrahman gunatitanand swami janma jayanti': "Gunatitanand Swami's Birthday (Sharad Punam)",
    'aksharbrahma gunatitanand swami pragatyotsav': "Gunatitanand Swami's Birthday (Sharad Punam)",
    'sharad punam': "Gunatitanand Swami's Birthday (Sharad Punam)",
    'aksharbrahma gunatitanand swami diksha day': 'Gunatitanand Swami Diksha Day (Poshi Punam)',
    'aksharbrahma swami diksha day': 'Gunatitanand Swami Diksha Day (Poshi Punam)',
    'poshi punam': 'Gunatitanand Swami Diksha Day (Poshi Punam)',
    'vijaya dashami': 'Vijaya Dashmi',
    'dhan teras/lakshmi pujan': 'Dhan Teras (Lakshmi Pujan)', 'dhan teras': 'Dhan Teras (Lakshmi Pujan)',
    'lakshmi pujan': 'Dhan Teras (Lakshmi Pujan)', 'dhan trayodashi': 'Dhan Teras (Lakshmi Pujan)',
    'dhan teras-lakshmi pujan': 'Dhan Teras (Lakshmi Pujan)',
    'kali caudash': 'Kali Chaudash',
    'ramnavami': 'Ramnavmi',
    "hari-nom (bhagwan swaminarayan's birthday)": 'Swaminarayan Jayanti (Hari Navmi)',
    'swaminarayan jayanti': 'Swaminarayan Jayanti (Hari Navmi)',
    'jal jhilni ekadashi': 'Jal Jhilani Ekadashi',
    "bhagatji maharaj's birthday q": "Bhagatji Maharaj's Birthday",
    "swaminarayan jayanti (bhagwan swaminarayan's birthday)": 'Swaminarayan Jayanti (Hari Navmi)',
    "hari-nom - bhagwan swaminarayan's birthday": 'Swaminarayan Jayanti (Hari Navmi)',
    'makar sankranti - uttarayan': 'Makar Sankranti (Uttarayan)',
    'buddha purnima': 'Buddha Jayanti',
    'samshravani': 'Sam Shravani',
}


def festivals(text):
    """'Holi, Bhagatji Maharaj's Birthday; Diwali' -> ['Holi', "Bhagatji Maharaj's Birthday", 'Diwali'], one name each."""
    out = []
    for part in (text or '').split('; '):
        for f in part.split(', '):
            f = f.strip()
            if f:
                f = SAME_FESTIVAL.get(f.lower(), f)
                if f not in out:
                    out.append(f)
    return out


def write(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='search')
    ap.add_argument('--photos', default='https://photos.bapas-diary.com/', help='where the s/ and m/ photos are (R2)')
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'data'), exist_ok=True)
    db = sqlite3.connect(a.db)

    years, counts = {}, {}
    rows = db.execute("SELECT year, date, date_from, date_to, place, album, file, caption, is_bapa FROM photos "
                      "ORDER BY coalesce(date, date_from), album, file")
    for y, date, d0, d1, place, album, file, cap, bapa in rows:
        yr = years.setdefault(y, {'g': [], 'p': [], 'at': {}})
        key = (date or d0, '' if date else (d1 or ''), place or '', album)
        if key not in yr['at']:
            yr['at'][key] = len(yr['g'])
            yr['g'].append(list(key))
        yr['p'].append([yr['at'][key], file, cap or '', 1 if bapa else 0])
    for y, yr in years.items():
        write(os.path.join(a.out, 'data', f'{y}.json'), {'g': yr['g'], 'p': yr['p']})
        counts[y] = len(yr['p'])

    tg = [[date or (posted or '')[:10], place or '', text.strip()]
          for posted, date, place, text in db.execute(
              "SELECT posted, date, place, text FROM tg_posts "
              "WHERE trim(coalesce(text, '')) != '' ORDER BY coalesce(date, posted)")]
    write(os.path.join(a.out, 'data', 'stories.json'), tg)

    # BAPS calendar days (table `calendar`, when the database has it): one row per date, nothing cut out
    cal = []
    if db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'calendar'").fetchone():
        cal = [list(r) for r in db.execute(
            "SELECT date, weekday, vikram_samvat, indian_date, festivals, festival_about, notes, source, ekadashi, punam, amas FROM calendar ORDER BY date")]
        cal = [[c if c is not None else '' for c in r] for r in cal]
        for r in cal:
            # festivals, one name each; Ekadashi, Punam and Amas join them so the festival list can find every one
            ek, pu, am = r[8:11]
            r[4] = '; '.join(festivals(r[4]) + [n for n, on in (('Ekadashi', ek), ('Punam', pu), ('Amas', am)) if on])
            del r[8:]
        write(os.path.join(a.out, 'data', 'calendar.json'), cal)

    built = dict(db.execute("SELECT key, value FROM about"))
    write(os.path.join(a.out, 'data', 'about.json'),
          {'built': built.get('built'), 'years': sorted(counts), 'photos': counts, 'stories': len(tg), 'calendar': len(cal)})

    body = open(PAGE, encoding='utf-8').read().replace('{{PHOTOS}}', a.photos)
    with open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    print(sum(counts.values()), 'photos in', len(counts), 'years,', len(tg), 'Telegram posts ->', a.out)


if __name__ == '__main__':
    main()
