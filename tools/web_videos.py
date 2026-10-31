"""BAPS videos on the Today page (Darpan, 30 Oct 2026: "if you know that on the 30th of October, on a specific year, this
action happened, and there was a video that was on the channel already ... we can click a link that will take you to that
video of that day"). Website only: nothing here touches the daily 2pm picture.

The BAPS YouTube playlist of Guruhari Darshan videos (tools/youtube/match.py) gives each video the day(s) in its title,
data/youtube/days.json. This puts them on each year of the Today day files and the festival files, as "v":
[[YouTube id, title], ...], for the year's own date (a festival year's "d", otherwise that year on the page's date).
The page shows a gold "Video Darshan" under that year's card, opening the first one on YouTube.

A festival card (data/fest/KEY.json, Darpan 31 Oct 2026: "Diwali, Annakut and New Year cards each show that year's
festival video") opens the festival's own video first: of that day's videos, the ones whose title names the festival
(Chopda Pujan, Annakut, New Year ...) go before the day's ordinary Guruhari Darshan.

With --site it also writes the same links for the other pages (Darpan, 31 Oct 2026):
  data/videos/YYYY.json   {date: [YouTube id, title]} for every day of that year with a video: the Calendar's day
                          box (/photos/), the big photo in Search, each stay on Travels, and the morning and Sunday emails
  data/videos/latest.json {d, id, title}: the newest Video Darshan, for Search's Latest vicharan view

    python3 tools/web_videos.py --videos data/youtube/days.json --site out out/data/day out/data/fest
"""
import argparse, collections, glob, json, os, re

# the festival's own name in a video title, by the festival file's key (tools/web_festival.py FESTS)
FEST_WORDS = {
    'diwali': r'diwali|chopda|deepavali|sharda pujan',
    'annakut': r'annakut|new year|nava varsh|navu varsh|bestu',
    'janmashtami': r'janmashtami', 'holi': r'\bholi\b', 'fuldol': r'fuldol|pushpadol|dhuleti',
    'gurupurnima': r'guru ?purnima', 'harinom': r'hari ?n(o|av)m|swaminarayan jayanti|ram ?navmi',
    'vasant': r'vasant', 'rathyatra': r'rath ?yatra', 'raksha': r'raksha', 'sharad': r'sharad|punam',
    'psm': r'pramukh swami maharaj.{0,30}(birth|janma|jayanti)', 'msm': r'mahant swami maharaj.{0,30}(birth|janma|jayanti)',
}

ap = argparse.ArgumentParser()
ap.add_argument('--videos', required=True)
ap.add_argument('--site', help='the finished site folder: write data/videos/ there too')
ap.add_argument('dirs', nargs='+')
a = ap.parse_args()
videos = json.load(open(a.videos))
files = years = 0
for d in a.dirs:
    for f in sorted(glob.glob(os.path.join(d, '*.json'))):
        day = json.load(open(f))
        if not isinstance(day, dict) or 'years' not in day:
            continue
        key = os.path.splitext(os.path.basename(f))[0]
        own = re.compile(FEST_WORDS[key], re.I) if os.path.basename(d.rstrip('/')) == 'fest' and key in FEST_WORDS else None
        hit = False
        for Y in day['years']:
            date = Y.get('d') or f"{Y['y']}-{day['date']}"
            v = videos.get(date)
            if v:
                if own:   # the festival's own video first (sorted keeps the day's order otherwise)
                    v = sorted(v, key=lambda x: not own.search(x['title']))
                Y['v'] = [[x['id'], x['title']] for x in v]
                hit = True
                years += 1
        if hit:
            files += 1
            with open(f, 'w') as o:
                json.dump(day, o, ensure_ascii=False, separators=(',', ':'))
print(f'videos on {years} years in {files} day files')

if a.site:
    out = os.path.join(a.site, 'data', 'videos')
    os.makedirs(out, exist_ok=True)
    by_year = collections.defaultdict(dict)
    for date in sorted(videos):
        if videos[date]:
            by_year[date[:4]][date] = [videos[date][0]['id'], videos[date][0]['title']]
    for y, days in by_year.items():
        with open(os.path.join(out, y + '.json'), 'w') as o:
            json.dump(days, o, ensure_ascii=False, separators=(',', ':'))
    newest = max(d for d in videos if videos[d])
    with open(os.path.join(out, 'latest.json'), 'w') as o:
        json.dump({'d': newest, 'id': videos[newest][0]['id'], 'title': videos[newest][0]['title']}, o, ensure_ascii=False)
    print(f'data/videos: {len(by_year)} years, {sum(map(len, by_year.values()))} days, newest {newest}')
