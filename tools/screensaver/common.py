"""Shared bits from the darshan screensaver kit (place names, time zones, photo addresses), for tools/web_screensaver.py."""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLACES = json.loads((HERE / 'places.json').read_text())
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
DAYS = 10             # Latest Vicharan keeps the 10 newest days that have photos
MOST = 150            # photos a day in Latest Vicharan, so one huge day can't swamp the rest
URL = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{file}'
TZ = {'UK': 'Europe/London', 'India': 'Asia/Kolkata', 'France': 'Europe/Paris', 'Kenya': 'Africa/Nairobi',
      'Uganda': 'Africa/Kampala', 'Tanzania': 'Africa/Dar_es_Salaam', 'South Africa': 'Africa/Johannesburg',
      'UAE': 'Asia/Dubai', 'Singapore': 'Asia/Singapore', 'Thailand': 'Asia/Bangkok', 'Indonesia': 'Asia/Jakarta',
      'China': 'Asia/Shanghai', 'Australia': 'Australia/Sydney', 'New Zealand': 'Pacific/Auckland',
      'USA': 'America/New_York', 'Canada': 'America/Toronto'}


def stays_on(day, schedule):
    return [s for s in schedule.get('stays', []) if s['from'] <= str(day) <= s['to']]


def tz_of(place, day, schedule):
    """The time zone for a photo's place: from the schedule's stay there, else by country (India if unknown)."""
    for s in stays_on(day, schedule):
        if s['place'].split(',')[0].strip().lower() == place.split(',')[0].strip().lower():
            return s['tz']
    return TZ.get(place.split(', ')[-1].strip(), 'Asia/Kolkata')


def clean(c):
    c = re.sub(r'<[^>]+>', '', c or '').replace('�', "'")
    return re.sub(r'\s+', ' ', c).strip()


def photo_url(album, file):
    """baps.org refuses .JPG (403) but serves .jpg, and spaces must be %20."""
    file = re.sub(r'\.JPE?G$', lambda m: m.group(0).lower(), file)
    return URL.format(album=album, file=file).replace(' ', '%20')


def spread(xs, most):
    """At most `most` of xs, spread evenly through the day."""
    if len(xs) <= most:
        return xs
    return [xs[round(i * (len(xs) - 1) / (most - 1))] for i in range(most)]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
