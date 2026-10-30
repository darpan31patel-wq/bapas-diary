"""The London Mandir Murti Darshan channel (t.me/LondonMandirMurtiDarshan) for the Darshan tab's older days
(Darpan, 30 Oct 2026: "save older darshan"). Website only: nothing here touches the daily 2pm picture.

The channel posts each morning's darshan as two posts ('London Mandir Murti Darshan / Friday 30 October 2026 / Aso vad 5'),
about 11 photos a day, from 10 Sep 2022. The mandir's own site (darshan_copy.sh) names each photo (ddm, gm, ...), the
channel does not, so each channel photo is given the name of the mandir photo it looks most like.

    python tools/murti_channel.py study posts.json out/      # checks the matching on days R2 has from the mandir; writes nothing to R2
"""
import collections, io, json, os, re, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta
from PIL import Image, ImageOps

CODES = ['ddm', 'ddm_c', 'gm', 'gm_c', 'hkm_c', 'varni', 'bm', 'sm', 'ym', 'psm']
M = 'january february march april may june july august september october november december'.split()
DATE = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(M) + r')\s*,?\s+(\d{4})', re.I)


def days(posts):
    """{YYYYMMDD: [image url, ...]} in the channel's own order. A post's day is the date written on it, else the
    London morning it was posted (the 2022 posts carry their date in a Gujarati post of their own)."""
    out = collections.defaultdict(list)
    for p in sorted(posts, key=lambda p: p['id']):
        if not p.get('images'):
            continue
        m = DATE.search(p.get('text') or '')
        if m:
            d = f'{m[3]}{M.index(m[2].lower()) + 1:02d}{int(m[1]):02d}'
        else:
            t = datetime.fromisoformat(p['posted']) + timedelta(hours=1)
            d = t.strftime('%Y%m%d')
        out[d] += p['images']
    return dict(out)


def get(url):
    for n in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
        except Exception as e:
            print('retry', e); time.sleep(3 * (n + 1))
    return None


def sig(im):
    """What a shrine looks like whatever the day's clothes: the shape of light and dark, small and evened out."""
    g = ImageOps.equalize(ImageOps.grayscale(im)).resize((24, 32), Image.BILINEAR)
    v = list(g.getdata()); mu = sum(v) / len(v)
    sd = (sum((x - mu) ** 2 for x in v) / len(v)) ** .5 or 1
    return [(x - mu) / sd for x in v] + [im.size[0] / im.size[1] * 8]


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def r2(*a):
    return subprocess.run(['aws', 's3', *a, '--endpoint-url', os.environ['R2']], check=True, capture_output=True, text=True).stdout


def study(posts_file, out):
    os.makedirs(out, exist_ok=True)
    ch = days(json.load(open(posts_file, encoding='utf-8')))
    print('channel days', len(ch), 'first', min(ch), 'last', max(ch))
    per = collections.Counter(len(v) for v in ch.values())
    print('photos per day', sorted(per.items()))
    bucket = os.environ['BUCKET']
    keys = [l.split()[-1] for l in r2('ls', f's3://{bucket}/darshan/', '--recursive').splitlines() if l.split()]
    have = collections.defaultdict(dict)
    for k in keys:
        m = re.match(r'^darshan/(\d{8})/([a-z_]+)_(\d\d)\.jpg$', k)
        if m and m[2] in CODES:
            have[m[1]][m[2]] = k
    both = sorted(d for d in have if d in ch and len(have[d]) == 10)
    print('days in both with all ten', len(both))
    pick = both[::max(1, len(both) // 24)][:24]
    ref = []   # (day, code, sig)
    chan = []  # (day, index, sig, size)
    for d in pick:
        for c, k in have[d].items():
            r2('cp', f's3://{bucket}/{k}', f'{out}/r.jpg', '--only-show-errors')
            im = Image.open(f'{out}/r.jpg').convert('RGB')
            ref.append((d, c, sig(im), im.size))
        for i, u in enumerate(ch[d]):
            b = get(u)
            if not b:
                continue
            im = Image.open(io.BytesIO(b)).convert('RGB')
            chan.append((d, i, sig(im), im.size))
            if d == pick[-1]:
                im.save(f'{out}/{d}-{i:02d}.jpg')
            time.sleep(.3)
    print('mandir sizes', collections.Counter(s for *_, s in ref).most_common(4))
    print('channel sizes', collections.Counter(s for *_, s in chan).most_common(4))
    # same day: which mandir photo is each channel photo (the truth for that day)
    truth, order = {}, collections.Counter()
    for d, i, s, _ in chan:
        best = min((dist(s, rs), c) for rd, c, rs, _ in ref if rd == d)
        truth[(d, i)] = best[1]
        order[(i, best[1])] += 1
    print('channel place -> mandir photo, same day:', sorted(order.items()))
    # other days only: how often the look alone finds the right name (what the older days will rely on)
    ok = n = 0
    for d, i, s, _ in chan:
        guess = min((dist(s, rs), c) for rd, c, rs, _ in ref if rd != d)[1]
        n += 1; ok += guess == truth[(d, i)]
    print(f'named right from other days: {ok} of {n}')
    old = [d for d in sorted(ch) if d < '20260101']
    for d in old[::max(1, len(old) // 6)][:6]:
        print('older day', d, len(ch[d]), 'photos')


if __name__ == '__main__':
    {'study': study}[sys.argv[1]](*sys.argv[2:])
