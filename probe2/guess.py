"""Probe: can GitHub find new vicharan photos by guessing image addresses?"""
import urllib.request, urllib.error, concurrent.futures as cf, time, json

BASE = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages/'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
count = 0

def status(url, method='HEAD'):
    global count
    count += 1
    req = urllib.request.Request(url, method=method, headers={'User-Agent': UA, 'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8'})
    for _ in range(2):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.headers.get('Content-Type'), r.headers.get('Content-Length')
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Content-Type'), e.headers.get('cf-mitigated')
        except Exception as e:
            err = repr(e)[:80]
            time.sleep(1)
    return 0, err, None

out = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.append(s)

say('A. single images')
for u in ['37019/WebImages/2026_10_09_009_London.jpg', '37019/WebImages/2026_10_09_001_London.jpg', '37019/WebImages/2026_10_09_009_Londonx.jpg']:
    say(' HEAD', u, status(BASE + u))
    say(' GET ', u, status(BASE + u, 'GET'))

say('B. album folders')
for u in ['37019/', '37019/WebImages/', '37019/Thumbnails/', '37100/', '37100/WebImages/', '99999990/', '99999990/WebImages/']:
    say(' HEAD', u, status(BASE + u))

def scan(date, place, ids, nums=range(1, 31)):
    y, m, d = date.split('-')
    jobs = {(i, n): f'{BASE}{i}/WebImages/{y}_{m}_{d}_{n:03d}_{place}.jpg' for i in ids for n in nums}
    hits = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for k, r in zip(jobs, ex.map(status, jobs.values())):
            if r[0] == 200:
                hits.setdefault(k[0], []).append(k[1])
            elif r[0] not in (404,):
                hits.setdefault('other', []).append((k, r[0]))
    return hits

t = time.time()
say('C. rediscover 3 Oct 2026 (known album 37012) scanning 37002..37013')
say(' ', json.dumps(scan('2026-10-03', 'London', range(37002, 37014)))[:600], f'{time.time()-t:.0f}s')

t = time.time()
say('D. new days 10..13 Oct 2026, London, albums 37020..37050')
for date in ['2026-10-10', '2026-10-11', '2026-10-12', '2026-10-13']:
    say(' ', date, json.dumps(scan(date, 'London', range(37020, 37051)))[:600], f'{time.time()-t:.0f}s')

say('E. full count in album 37019 (9 Oct), numbers 1..400')
h = scan('2026-10-09', 'London', [37019], range(1, 401))
say(' ', len(h.get(37019, [])), 'photos', h.get(37019, [])[:60])
say('total requests', count)
open('results/guess.txt', 'w').write('\n'.join(out) + '\n')
