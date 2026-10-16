#!/usr/bin/env python3
"""Test runs only: for one date, how many photos each year's baps.org album really has compared with the
On This Day list. Uses only the photo files (the album pages sit behind Cloudflare and are never touched).

    python probe.py --date 2026-10-16 --out out
"""
import argparse, collections, json, re, urllib.error, urllib.request

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
PAT = re.compile(r'(.*/GalleryImages/(\d+)/WebImages/)(\d{4}_\d{2}_\d{2})_(\d{3})_(.+)\.jpg$', re.I)
errors = 0


def exists(url):
    global errors
    if errors >= 30:
        return None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA}), timeout=10):
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
    except Exception:
        pass
    errors += 1
    return None


ap = argparse.ArgumentParser(); ap.add_argument('--date'); ap.add_argument('--out', default='out')
a = ap.parse_args()
mmdd = a.date[5:]
items = json.loads(urllib.request.urlopen(urllib.request.Request(
    f'https://darshan-screensaver.pages.dev/memories/{mmdd}.json', headers={'User-Agent': UA}), timeout=30).read())
albums = collections.defaultdict(set)
other = collections.Counter()
for x in items:
    m = PAT.match(x['i'])
    if m:
        albums[(x['y'], m.group(1), m.group(3), m.group(5))].add(int(m.group(4)))
    else:
        other[x['y']] += 1
with open(f'{a.out}/album-check.txt', 'w') as f:
    for (y, base, d, name), nums in sorted(albums.items()):
        top = max(nums)
        extra = [n for n in range(1, top + 15) if n not in nums and exists(f'{base}{d}_{n:03d}_{name}.jpg')]
        f.write(f'{y}  {d}  {name}: {len(nums)} in the list (numbers up to {top}), {len(extra)} more on baps.org {extra[:40]}\n')
    for y, n in sorted(other.items()):
        f.write(f'{y}: {n} photos with an older style address (not checked)\n')
    f.write(f'\nbaps.org errors: {errors}\n')
print(open(f'{a.out}/album-check.txt').read())
