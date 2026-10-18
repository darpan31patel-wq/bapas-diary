"""Write the whole photo database (archive/vicharan/MM-DD.txt, 366 files) as one JSON file that other projects,
such as the screensaver, can read without knowing the text format.

    python tools/export_db.py [--out bapas-diary-photos.json] [--urls] [--split folder]

The file has, for every day of the year, one group per year and place with the photos of that day:
    days["10-18"] -> [{"year": 1999, "date": "1999-10-18", "place": "Nairobi, Kenya", "album": "3228",
                       "photos": [{"id": "TP_1999_115_0a", "caption": "BAPS Shri Swaminarayan Mandir, Nairobi"}, ...]}, ...]
A photo's picture is at image_url with {album} and {id} filled in (--urls writes that address on every photo too).
"date" is the day the photos were really taken: it differs from the day only when a nearby day of the same trip stands in.
Captions are written out in full ("Swamishri ..." where the text file abbreviates). Every photo is kept, murtis and devotees too.
--split also writes one small MM-DD.json per day (the same groups list) for a site that loads one day at a time.
"""
import argparse, datetime, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{id}.jpg'


def read_day(path, mmdd):
    """[{year, date, place, album, photos: [{id, caption}]}] for one MM-DD.txt (same reading as make.py's vicharan_items)."""
    groups, g = [], None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('# ') or not line.strip():
            continue
        if line.startswith('#'):
            head, _, rest = line[1:].partition('|')
            place, _, when = rest.partition('|')
            parts = head.split(' ')
            year, album, prefix = int(parts[0]), parts[1], (parts[2] if len(parts) > 2 else '')
            g = {'year': year, 'date': when or f'{year}-{mmdd}', 'place': place, 'album': album, 'photos': []}
            if prefix:
                g['prefix'] = prefix
            groups.append(g)
            continue
        ids, caption = line.split('|', 1)
        if caption[:1].islower():
            caption = 'Swamishri ' + caption
        for i in ids.split(','):
            g['photos'].append({'id': g.get('prefix', '') + i, 'caption': caption})
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=os.path.join(os.path.dirname(HERE), 'archive', 'vicharan'), help='folder of MM-DD.txt files')
    ap.add_argument('--out', default='bapas-diary-photos.json')
    ap.add_argument('--urls', action='store_true', help='write the full picture address on every photo (a bigger file)')
    ap.add_argument('--split', help='also write one MM-DD.json per day into this folder')
    a = ap.parse_args()
    days = {}
    for path in sorted(glob.glob(os.path.join(a.db, '[01][0-9]-[0-3][0-9].txt'))):
        mmdd = os.path.basename(path)[:5]
        days[mmdd] = read_day(path, mmdd)
        if a.urls:
            for g in days[mmdd]:
                for p in g['photos']:
                    p['url'] = URL.format(album=g['album'], id=p['id'])
    photos = sum(len(g['photos']) for d in days.values() for g in d)
    unique = len({(g['album'], p['id']) for d in days.values() for g in d for p in g['photos']})
    years = sorted({g['year'] for d in days.values() for g in d})
    out = {
        'about': "Bapa's Diary photo database: every captioned photo on baps.org's vicharan pages, by day of the year and year. "
                 "Bapa is Pramukh Swami Maharaj before 13 August 2016 and Mahant Swami Maharaj from then on.",
        'built': datetime.date.today().isoformat(),
        'source': 'github.com/darpan31patel-wq/bapas-diary, archive/vicharan/MM-DD.txt (tools/build_db.py), exported by tools/export_db.py',
        'image_url': URL,
        'years': years,
        'days_with_photos': len(days),
        'photo_entries': photos,
        'unique_photos': unique,
        'days': days,
    }
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    if a.split:
        os.makedirs(a.split, exist_ok=True)
        for mmdd, groups in days.items():
            json.dump(groups, open(os.path.join(a.split, mmdd + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{a.out}: {len(days)} days, {years[0]} to {years[-1]}, {photos} photo entries ({unique} different photos), {os.path.getsize(a.out) / 1e6:.1f} MB')


if __name__ == '__main__':
    sys.exit(main())
