"""The London Mandir Murti Darshan channel (t.me/LondonMandirMurtiDarshan) for the Darshan tab's older days
(Darpan, 30 Oct 2026: "save older darshan"). Website only: nothing here touches the daily 2pm picture.

The channel posts each morning's darshan as two posts ('London Mandir Murti Darshan / Friday 30 October 2026 / Aso vad 5'),
about 11 photos a day, from 10 Sep 2022. The mandir's own site (darshan_copy.sh) names each photo (ddm, gm, ...), the
channel does not, so each channel photo is given the name of the mandir photo it looks most like.

    python tools/murti_channel.py study posts.json out/      # checks the matching on days R2 has from the mandir; writes nothing to R2
    python tools/murti_channel.py save posts.json            # the older days into R2 (Darpan, 30 Oct 2026: "web copies okay")

The study (30 Oct 2026) found the channel's web copies are 450 x 800 and named right by look only 4 times in 10, so
'save' keeps the channel's own order and names its photos t01, t02, ... (no murti names: these days are left out of
By murti). For each day before 2026 that the Darshan tab does not have yet it writes
    darshan/tg/YYYYMMDD/NN.jpg       the channel's photo as it is
    darshan/s|m/YYYYMMDD/tNN.jpg     the Darshan page's small and big copies (the same file: already under 480 px wide)
and darshan/older.js, the list the page adds before archive.js's days:
    window.DARSHAN_OLDER = [{"d": "2022-09-10", "k": ["t01", ...], "c": ["Pink"]}, ...]
It never writes archive.js or list.json (the screensaver robot's), and never asks londonmandir.baps.org for anything.
"""
import collections, hashlib, importlib.util, io, shutil, json, os, re, subprocess, sys, time, urllib.request
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


def save(posts_file, before='20260101'):
    """See the top. Resumable: a day already in R2 (darshan/s/YYYYMMDD/) is left as it is."""
    spec = importlib.util.spec_from_file_location('da', os.environ.get('DARSHAN_ARCHIVE', 'darshan_archive.py'))
    da = importlib.util.module_from_spec(spec); spec.loader.exec_module(da)   # the Darshan tab's own colour reader
    bucket = os.environ['BUCKET']
    have = set()
    for l in r2('ls', f's3://{bucket}/darshan/s/').splitlines():
        if l.strip().startswith('PRE '):
            have.add(l.split()[-1].strip('/'))
    work = 'older'
    old = []
    try:
        r2('cp', f's3://{bucket}/darshan/older.js', 'older-was.js', '--only-show-errors')
        t = open('older-was.js', encoding='utf-8').read(); old = json.loads(t[t.index('['):t.rindex(']') + 1])
    except Exception:
        pass
    ch = days(json.load(open(posts_file, encoding='utf-8')))
    todo = [d for d in sorted(ch) if d < before and d not in have][:int(os.environ.get('LIMIT') or 10 ** 6)]
    print('channel days before', before, sum(d < before for d in ch), '| already in R2', sum(d in have for d in ch if d < before), '| to save', len(todo))
    out, n = list(old), 0

    def flush():
        if os.path.isdir(work):
            subprocess.run(['aws', 's3', 'cp', work, f's3://{bucket}/darshan/', '--recursive', '--endpoint-url', os.environ['R2'],
                            '--only-show-errors', '--content-type', 'image/jpeg', '--cache-control', 'public, max-age=31536000, immutable'], check=True)
            shutil.rmtree(work)
        js = 'window.DARSHAN_OLDER=' + json.dumps(sorted(out, key=lambda x: x['d']), separators=(',', ':')) + ';\n'
        open('older.js', 'w', encoding='utf-8').write(js)
        subprocess.run(['aws', 's3', 'cp', 'older.js', f's3://{bucket}/darshan/older.js', '--endpoint-url', os.environ['R2'], '--only-show-errors',
                        '--content-type', 'application/javascript', '--cache-control', 'public, max-age=300'], check=True)
        print('saved so far:', len(out), 'days,', n, 'photos', flush=True)

    for j, d in enumerate(todo):
        seen, keep, votes = set(), [], collections.Counter()
        for u in ch[d]:
            b = get(u)
            time.sleep(.2)
            if not b or hashlib.md5(b).hexdigest() in seen:
                continue
            seen.add(hashlib.md5(b).hexdigest())
            try:
                im = Image.open(io.BytesIO(b)).convert('RGB')
            except Exception:
                continue
            keep.append(b)
            for k, c in enumerate(da.colours(im)):
                votes[c] += 2 - k
        if not keep:
            continue
        codes = []
        for i, b in enumerate(keep, 1):
            for path in (f'tg/{d}/{i:02d}.jpg', f's/{d}/t{i:02d}.jpg', f'm/{d}/t{i:02d}.jpg'):
                os.makedirs(os.path.dirname(f'{work}/{path}'), exist_ok=True)
                open(f'{work}/{path}', 'wb').write(b)
            codes.append(f't{i:02d}')
        n += len(keep)
        top = votes.most_common(2)
        col = [top[0][0]] + ([top[1][0]] if len(top) > 1 and top[1][1] >= .5 * top[0][1] else []) if top else ['White']
        iso = f'{d[:4]}-{d[4:6]}-{d[6:]}'
        out = [x for x in out if x['d'] != iso] + [dict(d=iso, k=codes, c=col)]
        if (j + 1) % 50 == 0:
            flush()
    flush()
    print('done:', len(out), 'older days listed,', n, 'photos saved this run')


if __name__ == '__main__':
    {'study': study, 'save': save}[sys.argv[1]](*sys.argv[2:])
