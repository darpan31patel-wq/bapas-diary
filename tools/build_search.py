"""Build the searchable photo database page from bapas.db (Darpan, 23 Oct 2026: search the captions for words, by year and month).

    python tools/build_search.py --db bapas.db --out search

Writes a folder that works as it is on any web host (Cloudflare Pages, or opened from a small local server):
  index.html          the search page (site/search.html wrapped as a full page)
  data/YYYY.json      one file per year of baps.org photos:
                        {"g": [[date, date_to, place, album, mandir], ...],  a group = one album on one day (or date range);
                                                                    mandir only on mandir days, e.g. "p" (see MANDIR)
                         "p": [[group, file, caption, tags], ...]}   tags: what is happening in it, e.g. "smiling, garland"    every photo, nothing cut out
  data/stories.json   every On this day story (the Telegram channel posts, shown without any Telegram links): [[date, place, text, mandir?], ...]
  data/calendar.json  every BAPS calendar day, when the database has the calendar table:
                        [[date, weekday, vikram_samvat, indian_date, festivals, festival_about, notes, source], ...]
  data/about.json     years, counts and when it was built
"""
import argparse, json, os, re, sqlite3

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


# What is happening in a photo (tools/photo_tags.py gives each photo a similarity to each tag's sentence). A single
# score says little, so a tag is kept only where the photo stands out from all the others: at least TAG_Z standard
# deviations above that tag's average (TAG_Z). Only tags checked by eye on contact sheets of the 1999 photos are
# used; the others (glasses, elephant, plane...) were wrong too often and wait for better sentences.
TAG_Z = {'smiling': 2.0, 'laughing': 2.0, 'garland': 2.1, 'blessing': 2.1, 'close up': 2.2, 'children': 2.3}


def tag_picker(data):
    names, photos = data.get('tags', []), data.get('photos', {})
    if not photos:
        return lambda key: ''
    bars = []
    for i, t in enumerate(names):
        v = [r[i] for r in photos.values()]
        m = sum(v) / len(v)
        sd = (sum((x - m) ** 2 for x in v) / len(v)) ** .5
        bars.append(m + TAG_Z[t] * sd if t in TAG_Z else None)
    return lambda key: ', '.join(t for t, b, x in zip(names, bars, photos.get(key, ())) if b is not None and x >= b)


def with_deep(tags, deep):
    """Add the deep photo tags (release deep-tags, deep-tags.json from tools/deep_tags.py on branch
    claude/project-thread-vcys74: {"ALBUM/FILE": "red flowers, smiling"}, each word checked by eye)."""
    def both(key):
        out = [t for t in tags(key).split(', ') if t]
        out += [t for t in deep.get(key, '').split(', ') if t and t not in out]
        return ', '.join(out)
    return both


# Mandir days (Darpan, 25 Oct 2026: mandir openings belong in the photo search, not on a page of their own). A day of
# an album is a mandir day when any caption of it says so, and then every photo of that day and album is too (the
# nagar yatra, the yagna and the assembly of an opening are part of it). p = murti pratishtha (a mandir opening, or
# murtis consecrated for a new mandir), s = shilanyas (foundation stone), t = patotsav (a mandir's anniversary).
# "Inaugurates a new publication" is not a mandir, so only the inaugurating of a mandir counts.
MANDIR = {
    'p': re.compile(r'prati?sh?th?a|consecration ceremony|newly consecrated|murtis? to be consecrated|consecrat\w* (?:the )?murti'
                    r'|opening ceremony of the (?:new )?mandir|inaugurat\w* (?:the )?(?:new )?'
                    r'(?:baps )?(?:shri )?(?:swaminarayan )?(?:hari )?mandir', re.I),
    's': re.compile(r'shilany|khat ?muhurt|foundation stone', re.I),
    't': re.compile(r'patotsav', re.I),
}


def mandir(text):
    return ''.join(k for k, rx in MANDIR.items() if rx.search(text or ''))


def write(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='search')
    ap.add_argument('--tags', help='tags.json from tools/photo_tags.py (what is happening in each photo)')
    ap.add_argument('--deep-tags', help='deep-tags.json from release deep-tags (red flowers, food, crowd...)')
    ap.add_argument('--photos', default='https://photos.bapas-diary.com/', help='where the s/ and m/ photos are (R2)')
    ap.add_argument('--start-year', default='', help='the year the page opens on, e.g. while only that year has photos')
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'data'), exist_ok=True)
    db = sqlite3.connect(a.db)

    tags = tag_picker(json.load(open(a.tags)) if a.tags and os.path.exists(a.tags) else {})
    if a.deep_tags and os.path.exists(a.deep_tags):
        tags = with_deep(tags, json.load(open(a.deep_tags)))
    years, counts = {}, {}
    rows = db.execute("SELECT year, date, date_from, date_to, place, album, file, caption, is_bapa FROM photos "
                      "ORDER BY coalesce(date, date_from), album, file")
    for y, date, d0, d1, place, album, file, cap, bapa in rows:
        yr = years.setdefault(y, {'g': [], 'p': [], 'at': {}})
        key = (date or d0, '' if date else (d1 or ''), place or '', album)
        if not date and mandir(cap):
            # an album with only a range of dates may be a whole tour, so there only the photos that say so are mandir photos
            key += (mandir(cap),)
        if key not in yr['at']:
            yr['at'][key] = len(yr['g'])
            yr['g'].append(list(key))
        yr['p'].append([yr['at'][key], file, cap or '', tags(f'{album}/{file}')])
        g = yr['g'][yr['at'][key]]
        for k in mandir(cap) if date else ():
            if len(g) < 5:
                g.append('')
            if k not in g[4]:
                g[4] = ''.join(sorted(g[4] + k))
    for y, yr in years.items():
        write(os.path.join(a.out, 'data', f'{y}.json'), {'g': yr['g'], 'p': yr['p']})
        counts[y] = len(yr['p'])

    tg = [[date or (posted or '')[:10], place or '', text.strip()] + ([mandir(text)] if mandir(text) else [])
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

    body = open(PAGE, encoding='utf-8').read().replace('{{PHOTOS}}', a.photos).replace('{{START_YEAR}}', a.start_year)
    with open(os.path.join(a.out, 'index.html'), 'w', encoding='utf-8') as f:
        f.write('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
    print(sum(counts.values()), 'photos in', len(counts), 'years,', len(tg), 'Telegram posts ->', a.out)


if __name__ == '__main__':
    main()
