#!/usr/bin/env python3
"""From the darshan screensaver kit. Copies ONE Sarangpur mandir darshan photo into the site: the central shrine (the three golden
murtis), which darshansmruti.com posts SECOND in each day's bundle. Mixed in with the Neasden daily
darshan (14 Oct 2026), one photo of each day's bundle, with a Sarangpur tag and the date. If the second
photo isn't a wide group photo (the order changed), nothing is shown that day: the owner would rather
see no Sarangpur photo than a different one.

Writes <site>/sarangpur/YYYYMMDD.jpg (shrunk to Mac size) and <site>/sarangpur/today.json
{"iso": "2026-10-13", "img": "sarangpur/20261013.jpg"}. If the page can't be read, the photo
already on the live site is kept, so a bad morning never takes Sarangpur off the screen.
"""
import io, json, os, re, sys, urllib.request
from datetime import datetime

PAGE = 'https://www.darshansmruti.com/Sarangpur-mandir-17.html'
IMAGES = 'https://www.darshansmruti.com/images/'
LIVE = 'https://photos.bapas-diary.com/darshan/'   # Bapa's Diary's own copy (tools/screensaver/darshan_copy.sh puts it there)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'
LONGEST = 2000   # pixels on the longest side: sharp on a Retina MacBook, light for the screensaver


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def newest():
    """(iso date, photo file names of the newest day's bundle, in page order)."""
    html = get(PAGE).decode('utf-8', 'replace')
    names = []
    for n in re.findall(r'images/(?:thumb/)?(Sarangpur-swami-narayan-mandir-[A-Za-z0-9]+\.jpg)', html):
        if n not in names: names.append(n)
    dates = [datetime.strptime(d, '%d %b, %Y') for d in re.findall(r'\b(\d{1,2} [A-Z][a-z]{2}, 20\d\d)\b', html)]
    if not names or not dates: raise ValueError('no photos or dates on the page')
    if len(dates) != len(names):   # each photo should have its own date; if not, trust only the top one
        names, dates = names[:1], dates[:1]
    top = max(dates)
    return top.strftime('%Y-%m-%d'), [n for n, d in zip(names, dates) if d == top]


def central_shrine(bundle):
    """(file name, photo bytes) of the bundle's second photo, the central shrine, or None when there
    is no second photo or it is a tall single murti (so not the shrine)."""
    from PIL import Image
    if len(bundle) < 2: return None
    data = get(IMAGES + bundle[1])
    w, h = Image.open(io.BytesIO(data)).size
    return (bundle[1], data) if w >= .95 * h else None


def shrink(data):
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert('RGB')
    im.thumbnail((LONGEST, LONGEST), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, 'JPEG', quality=86, optimize=True, progressive=True)
    return out.getvalue()


def main(site):
    folder = os.path.join(site, 'sarangpur')
    os.makedirs(folder, exist_ok=True)
    try:
        iso, bundle = newest()
        shrine = central_shrine(bundle)
        if not shrine:   # show nothing rather than a different photo
            print(f'::warning::no central shrine photo for Sarangpur {iso}; showing none')
            return
        name, data = shrine
        photo = shrink(data)
        source = name
    except Exception as e:   # keep what the live site already shows
        print(f'::warning::Sarangpur page not read ({e}); keeping the live photo')
        try:
            info = json.loads(get(LIVE + 'sarangpur/today.json'))
            iso, photo, source = info['iso'], get(LIVE + info['img']), 'live site'
        except Exception as e2:
            print(f'::warning::no Sarangpur photo this time ({e2})')
            return
    img = f"sarangpur/{iso.replace('-', '')}.jpg"
    with open(os.path.join(site, img), 'wb') as f: f.write(photo)
    with open(os.path.join(folder, 'today.json'), 'w') as f: json.dump({'iso': iso, 'img': img}, f)
    print(f'::notice::Sarangpur darshan {iso} from {source} ({len(photo) // 1024} KB)')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'site')
