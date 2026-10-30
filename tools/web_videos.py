"""BAPS videos on the Today page (Darpan, 30 Oct 2026: "if you know that on the 30th of October, on a specific year, this
action happened, and there was a video that was on the channel already ... we can click a link that will take you to that
video of that day"). Website only: nothing here touches the daily 2pm picture.

The BAPS YouTube playlist of Guruhari Darshan videos (tools/youtube/match.py) gives each video the day(s) in its title,
data/youtube/days.json. This puts them on each year of the Today day files and the festival files, as "v":
[[YouTube id, title], ...], for the year's own date (a festival year's "d", otherwise that year on the page's date).
The page shows a gold "Watch the video" under that year's card, opening the first one on YouTube.

    python3 tools/web_videos.py --videos data/youtube/days.json out/data/day out/data/fest
"""
import argparse, glob, json, os

ap = argparse.ArgumentParser()
ap.add_argument('--videos', required=True)
ap.add_argument('dirs', nargs='+')
a = ap.parse_args()
videos = json.load(open(a.videos))
files = years = 0
for d in a.dirs:
    for f in sorted(glob.glob(os.path.join(d, '*.json'))):
        day = json.load(open(f))
        if not isinstance(day, dict) or 'years' not in day:
            continue
        hit = False
        for Y in day['years']:
            date = Y.get('d') or f"{Y['y']}-{day['date']}"
            v = videos.get(date)
            if v:
                Y['v'] = [[x['id'], x['title']] for x in v]
                hit = True
                years += 1
        if hit:
            files += 1
            with open(f, 'w') as o:
                json.dump(day, o, ensure_ascii=False, separators=(',', ':'))
print(f'videos on {years} years in {files} day files')
