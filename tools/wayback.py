"""Old BAPS websites that are gone now, copied from the Internet Archive's Wayback Machine (Darpan, 13 Nov 2026:
"Yes to all"). For one old host (mandir.org, kids.swaminarayan.org, ...) it asks the Archive's list (CDX) for every
address it ever kept, takes the last good copy of each (pages, photos, PDFs, sounds) and saves the file exactly as
it was (the raw "id_" copy, without the Archive's own bar). Gentle: one reader, four seconds between files (the Archive's own pace), a long wait
whenever the Archive says slow down. Never touches the 2pm picture, the website, R2 or bapas.db.

Saved as <work>/files/<path on the old site>; files.jsonl notes for each file the old address, the Archive copy it
came from and the day the Archive took it (last_modified), so tools/sites_index.py lists it with full detail.

  python3 tools/wayback.py --host mandir.org --work work --state state --stop-at 13:00
"""
import argparse
import datetime as dt
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (bapas-diary archive; gentle)'
KEEP = re.compile(r'(?i)\.(html?|php|asp|aspx|shtml|jpe?g|gif|png|bmp|tiff?|pdf|mp3|wav|ram?|rm|wma|mpe?g|mp4|avi|wmv|'
                  r'flv|swf|doc|txt|zip)$|/$|^[^.]*$')


def get(url, tries=4):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410):
                return e.code, '', b''
            time.sleep(90 * (i + 1) if e.code in (429, 503) else 5 * (i + 1))   # the Archive asks to slow down: wait well
        except Exception:
            time.sleep(10 * (i + 1))
    return None, '', b''


def local(original):
    u = urllib.parse.urlsplit(original)
    p = urllib.parse.unquote(u.path).lstrip('/')
    if p == '' or p.endswith('/'):
        p += 'index.htm'
    if u.query:
        p += '__' + re.sub(r'[^\w=.-]+', '_', u.query)[:80] + '.html'
    return re.sub(r'[<>:"\\|?*]', '_', p)


def listing(host, state):
    """every address the Archive kept for this host, newest good copy of each (cached in state/cdx.json)"""
    cache = os.path.join(state, 'cdx.json')
    if os.path.exists(cache):
        return json.load(open(cache, encoding='utf-8'))
    best = {}
    for pattern in (f'{host}/*', f'www.{host}/*'):
        resume = ''
        while True:
            q = urllib.parse.urlencode({'url': pattern, 'output': 'json', 'fl': 'urlkey,timestamp,original,mimetype,statuscode',
                                        'filter': 'statuscode:200', 'limit': '50000', 'showResumeKey': 'true',
                                        **({'resumeKey': resume} if resume else {})})
            st, _, body = get('https://web.archive.org/cdx/search/cdx?' + q)
            if st != 200 or not body.strip():
                break
            rows = json.loads(body)
            resume = ''
            if len(rows) >= 2 and rows[-2] == []:
                resume = rows[-1][0]
                rows = rows[:-2]
            for r in rows[1:]:
                if len(r) < 5:
                    continue
                key, ts, orig, mime, _ = r
                path = urllib.parse.urlsplit(orig).path or '/'
                if not KEEP.search(path):
                    continue
                if key not in best or ts > best[key]['ts']:
                    best[key] = dict(ts=ts, original=orig, mime=mime)
            time.sleep(3)
            if not resume:
                break
    out = sorted(best.values(), key=lambda r: r['original'])
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True)
    ap.add_argument('--work', default='work')
    ap.add_argument('--state', default='state')
    ap.add_argument('--stop-at', default='', help='UTC HH:MM to stop by')
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--gap', type=float, default=4.0)
    ap.add_argument('--have', default='', help='paths already in Drive (rclone lsf -R)')
    a = ap.parse_args()
    os.makedirs(a.state, exist_ok=True)
    files = os.path.join(a.work, 'files')
    os.makedirs(files, exist_ok=True)
    stop = None
    if a.stop_at:
        h, m = map(int, a.stop_at.split(':'))
        now = dt.datetime.now(dt.timezone.utc)
        stop = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if stop <= now:
            stop += dt.timedelta(days=1)
    have = set(x for x in open(a.have, encoding='utf-8').read().split('\n') if x) if a.have and os.path.exists(a.have) else set()
    donep = os.path.join(a.state, 'done.txt')
    done = set(x for x in open(donep, encoding='utf-8').read().split('\n') if x) if os.path.exists(donep) else set()
    rows = listing(a.host, a.state)
    todo = [r for r in rows if r['original'] not in done and local(r['original']) not in have]
    print(json.dumps(dict(host=a.host, archive_addresses=len(rows), to_fetch=len(todo))), flush=True)
    lock = threading.Lock()
    counts = dict(saved=0, missing=0, failed=0, bytes=0)
    log = open(os.path.join(a.state, 'files.jsonl'), 'a', encoding='utf-8')
    dlog = open(donep, 'a', encoding='utf-8')
    fp = os.path.join(a.state, 'failed.txt')
    failed_before = set(x for x in open(fp, encoding='utf-8').read().split('\n') if x) if os.path.exists(fp) else set()
    failed_now = []
    it = iter(todo)
    halt = threading.Event()

    def work():
        while not halt.is_set():
            if stop and dt.datetime.now(dt.timezone.utc) >= stop:
                halt.set()
                break
            with lock:
                r = next(it, None)
            if r is None:
                break
            snap = f"https://web.archive.org/web/{r['ts']}id_/{r['original']}"
            st, kind, body = get(snap)
            time.sleep(a.gap)
            with lock:
                if st is None:
                    counts['failed'] += 1
                    if r['original'] in failed_before:
                        dlog.write(r['original'] + '\n')    # failed in two rounds: given up, so the site can finish
                        counts['gave_up'] = counts.get('gave_up', 0) + 1
                    else:
                        failed_now.append(r['original'])
                    continue
                dlog.write(r['original'] + '\n')
                if st != 200:
                    counts['missing'] += 1
                    continue
            fn = os.path.join(files, local(r['original']))
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            with open(fn, 'wb') as f:
                f.write(body)
            ts = r['ts']
            when = f'{ts[0:4]}-{ts[4:6]}-{ts[6:8]}T{ts[8:10]}:{ts[10:12]}:{ts[12:14]}+00:00'
            row = dict(url=f'http://{a.host}/' + urllib.parse.quote(local(r['original'])), original_url=r['original'],
                       file=local(r['original']), type=kind or r['mime'], bytes=len(body),
                       last_modified=when, archived_at=when, archive_copy=snap,
                       fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                       source=f'web.archive.org copy of {a.host}')
            with lock:
                log.write(json.dumps(row, ensure_ascii=False) + '\n')
                counts['saved'] += 1
                counts['bytes'] += len(body)
                if counts['saved'] % 500 == 0:
                    log.flush()
                    dlog.flush()
                    print(json.dumps(counts), flush=True)

    ts_ = [threading.Thread(target=work, daemon=True) for _ in range(a.workers)]
    for t in ts_:
        t.start()
    for t in ts_:
        t.join()
    log.close()
    dlog.close()
    with open(fp, 'w', encoding='utf-8') as f:
        f.write('\n'.join(failed_now))
    left = len([r for r in todo if r['original'] not in set(open(donep, encoding='utf-8').read().split('\n'))])
    out = dict(counts, left=left, finished=left == 0, at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
    with open(os.path.join(a.state, 'last-run.json'), 'w') as f:
        json.dump(out, f)
    print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
