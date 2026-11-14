"""A full copy of swaminarayan.org, the old BAPS website from before baps.org (Darpan, 13 Nov 2026: "Yes to all,
prioritise swaminarayan.org, ASAP"): every page and every photo, as real files, for Darpan's Drive archive.
Nothing here touches the 2pm picture's chain, the website or bapas.db; the database step comes later, with his yes.

    python3 tools/swaminarayan_org.py --work work --state state --stop-at 03:50 --workers 3 --gap 0.7

What it keeps
  work/files/<path on the site>    each page and photo exactly as the site serves it (pages are old Windows text)
  state/pages.jsonl                 one line per page: url, title, the page words, its date and place read from the
                                    address (vicharan/2000/05/02/photo/bharuch/...), every photo on it with its
                                    caption (the full size file from the javascript:fullimage('caption','84-0f.jpg')
                                    links and each thumbnail), and the links to audio, zips and video it names but
                                    which this copy does not fetch (download.baps.org is baps.org's own server)
  state/seen.txt, state/todo.txt    where it got to, so the next run carries on from there
Only swaminarayan.org itself is read (its robots.txt allows every reader), a few pages at a time with a pause between
each; search, guest book and e-card pages are left out. It stops by itself at --stop-at (UTC), so the 2pm picture's
morning (04:00 to 07:30 UTC) is always kept free.
"""
import argparse, datetime as dt, html, json, os, queue, re, sys, threading, time, urllib.error, urllib.parse
import urllib.request

HOSTS = {'swaminarayan.org', 'www.swaminarayan.org'}
BASE = 'https://www.swaminarayan.org/'
KEEP = re.compile(r'\.(?:html?|php|jpe?g|gif|png|bmp|pdf|txt|css|js)$', re.I)
PAGE = re.compile(r'(?:\.(?:html?|php)|/)$', re.I)
SKIP = re.compile(r'/(?:search|guestbook|ecard|cgi-bin)/|\.(?:asp|aspx)$', re.I)
OTHER = re.compile(r'\.(?:mp3|wav|wma|ram?|rm|zip|wmv|avi|mpe?g|mp4|mov|flv|swf|exe)$', re.I)
QUOTED = re.compile(r"""(?:href|src|background|action)\s*=\s*["']?([^"'\s>]+)|["']([^"'<>\s]+?\.(?:jpe?g|gif|png|"""
                    r"""html?|pdf|mp3|zip|wmv|ram?|rm))["']""", re.I)
FULLIMG = re.compile(r"""\w*image\w*\(\s*'((?:[^'\\]|\\.)*)'\s*,\s*'([^']+)'""", re.I)
IMGTAG = re.compile(r'<img\b[^>]*>', re.I)
MONTHS = 'january february march april may june july august september october november december'.split()


def seeds():
    s = ['index.htm', 'sitemap/index.htm', 'vicharan/index.htm', 'vicharan/pastvicharan/index.htm',
         'news/index.htm', 'news/pastnews/index.htm', 'whatsnew/index.htm', 'festivals/index.htm',
         'pramukhswami/index.htm', 'publications/magazine/index.htm', 'download/index.htm']
    for y in range(1996, 2013):    # pages the indexes may have dropped: the address pattern finds them anyway
        s += [f'pastvicharan/{y}.htm', f'vicharan/pastvicharan/{y}.htm', f'news/pastnews/{y}.htm']
        for m in range(1, 13):
            s.append(f'news/{y}/{m:02d}/index.htm')
            s += [f'vicharan/{y}/{m:02d}/{n:02d}/index.htm' for n in range(1, 5)]
    return [BASE + p for p in s]


def norm(url):
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ('http', 'https') or u.hostname not in HOSTS:
        return None
    path = urllib.parse.quote(urllib.parse.unquote(re.sub(r'/+', '/', u.path or '/')), safe="/%-_.~()!'$&+,;=:@")
    if path.endswith('/'):
        path += 'index.htm'    # a folder address is its index page (the copy needs a file name)
    q = '' if not u.query or not path.lower().endswith('.php') else '?' + u.query
    return 'https://www.swaminarayan.org' + path + q


def local(url):
    p = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip('/')
    q = urllib.parse.urlsplit(url).query
    if q:
        p += '__' + re.sub(r'[^\w=.-]+', '_', q)[:80] + '.html'
    return p


def when_where(path):
    """vicharan/2000/05/02/photo/bharuch/index.htm -> ('2000-05', 'Bharuch'); news/2000/05/x/ -> ('2000-05', '')"""
    m = re.match(r'(vicharan|news|festivals)/(\d{4})(?:/(\d{2}))?', path)
    if not m:
        m2 = re.match(r'festivals/(\d{4})', path)
        return ('', '') if not m2 else (m2[1], '')
    ym = m[2] + (f'-{m[3]}' if m[3] else '')
    place = ''
    pm = re.search(r'/photo/([a-z][a-z0-9_-]*)/', path)
    if pm:
        place = re.sub(r'\d+$', '', pm[1]).replace('_', ' ').replace('-', ' ').title()
    else:
        fm = re.search(r'/\d{2}/([a-z][a-z_-]*?)\d*\.html?$', path)
        if fm and fm[1] not in ('index', 'photo', 'photos'):
            place = fm[1].replace('_', ' ').title()
    return ym, place


def words(body):
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', body)
    t = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|td|h\d|li)>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t).strip()


def dates_in(text):
    """English dates the page itself names, e.g. '18 to 23 May 2000', '21 May 2000' (kept for the database step)"""
    out = []
    for m in re.finditer(r'\b(\d{1,2})(?:\s*(?:to|-|&|and)\s*(\d{1,2}))?\s+(' + '|'.join(MONTHS) + r'),?\s+(\d{4})',
                         text, re.I):
        out.append(m.group(0))
    return out[:20]


def attr(tag, name):
    m = re.search(name + r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", tag, re.I)
    return html.unescape(next((g for g in m.groups() if g is not None), '')) if m else ''


class Copier:
    def __init__(self, a):
        self.a = a
        self.files = os.path.join(a.work, 'files')
        os.makedirs(self.files, exist_ok=True)
        os.makedirs(a.state, exist_ok=True)
        self.lock = threading.Lock()
        self.tl = threading.local()
        self.seen = set()
        sp = os.path.join(a.state, 'seen.txt')
        if os.path.exists(sp):
            self.seen = set(x for x in open(sp, encoding='utf-8').read().split('\n') if x)
        self.q = queue.Queue()
        tp = os.path.join(a.state, 'todo.txt')
        todo = [x for x in open(tp, encoding='utf-8').read().split('\n') if x] if os.path.exists(tp) else []
        for u in todo + seeds():
            self.add(u, force=u in todo)
        self.pages = open(os.path.join(a.state, 'pages.jsonl'), 'a', encoding='utf-8')
        self.files_log = open(os.path.join(a.state, 'files.jsonl'), 'a', encoding='utf-8')
        self.counts = dict(pages=0, photos=0, other=0, missing=0, failed=0, bytes=0)
        self.stop_at = None
        if a.stop_at:
            h, m = map(int, a.stop_at.split(':'))
            now = dt.datetime.now(dt.timezone.utc)
            t = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if t <= now:
                t += dt.timedelta(days=1)
            self.stop_at = t
        self.done = threading.Event()
        # what earlier rounds already put in Drive: photos are not fetched again, and pages are read from the copy
        # of them made at the start of this round (so a round that ended without saving where it got to costs
        # nothing but a quick re-read)
        self.have = set()
        if a.have and os.path.exists(a.have):
            self.have = set(x for x in open(a.have, encoding='utf-8').read().split('\n') if x)
        self.since_save = 0

    def add(self, url, force=False):
        u = norm(url)
        if not u or SKIP.search(u):
            return
        if OTHER.search(u):
            return
        if not (KEEP.search(urllib.parse.urlsplit(u).path) or PAGE.search(urllib.parse.urlsplit(u).path)):
            return
        with self.lock:
            if u in self.seen and not force:
                return
            self.seen.add(u)
        self.q.put(u)

    def get(self, url):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bapas-diary archive; gentle)'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    self.tl.h = {k.lower(): v for k, v in r.headers.items()}
                    return r.status, r.headers.get('Content-Type', ''), r.read(), r.geturl()
            except urllib.error.HTTPError as e:
                if e.code in (404, 410, 403):
                    return e.code, '', b'', url
                time.sleep(5 * (attempt + 1))
            except Exception:
                time.sleep(5 * (attempt + 1))
        return None, '', b'', url

    def note(self, url, kind, size, h):
        row = dict(url=url, file=local(url), type=kind, bytes=size, last_modified=h.get('last-modified'),
                   etag=h.get('etag'), fetched_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
                   source='swaminarayan.org')
        with self.lock:
            self.files_log.write(json.dumps(row) + '\n')

    def heads(self, urls):
        """the file details (type, size, Last-Modified) for files an earlier round saved before these were kept"""
        for url in urls:
            if self.stop_at and dt.datetime.now(dt.timezone.utc) >= self.stop_at:
                return
            req = urllib.request.Request(url, method='HEAD',
                                         headers={'User-Agent': 'Mozilla/5.0 (bapas-diary archive; gentle)'})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    h = {k.lower(): v for k, v in r.headers.items()}
                    self.note(url, h.get('content-type', ''), int(h.get('content-length') or 0), h)
            except Exception:
                pass
            time.sleep(self.a.gap / max(1, self.a.workers))

    def page(self, url, body_bytes):
        body = body_bytes.decode('cp1252', errors='replace')
        path = urllib.parse.urlsplit(url).path.lstrip('/')
        photos, other = [], []
        caps = {}
        for cap, f in FULLIMG.findall(body):
            full = urllib.parse.urljoin(url, f)
            caps[norm(full) or full] = cap.replace("\\'", "'")
            photos.append(dict(file=norm(full) or full, caption=cap.replace("\\'", "'"), size='full'))
        for tag in IMGTAG.findall(body):
            src = attr(tag, 'src')
            if not src:
                continue
            full = norm(urllib.parse.urljoin(url, src))
            if not full or re.search(r'/images/|\.gif$', full, re.I):
                continue   # the site's own buttons and lines
            photos.append(dict(file=full, caption=attr(tag, 'alt') or attr(tag, 'title'), size='small'))
        for m in QUOTED.finditer(body):
            link = (m[1] or m[2] or '').strip()
            if not link or link.startswith(('javascript:', 'mailto:', '#')):
                continue
            full = urllib.parse.urljoin(url, html.unescape(link).split('#')[0])
            if OTHER.search(urllib.parse.urlsplit(full).path):
                other.append(full)
            self.add(full)
        for p in photos:
            self.add(p['file'])
        text = words(body)
        tm = re.search(r'(?is)<title>(.*?)</title>', body)
        ym, place = when_where(path)
        row = dict(url=url, file=local(url), title=html.unescape(re.sub(r'\s+', ' ', tm[1])).strip() if tm else '',
                   month=ym, place=place, dates=dates_in(text), photos=photos, media=sorted(set(other)),
                   words=text[:20000])
        with self.lock:
            self.pages.write(json.dumps(row, ensure_ascii=False) + '\n')

    def work(self):
        while not self.done.is_set():
            if self.stop_at and dt.datetime.now(dt.timezone.utc) >= self.stop_at:
                self.done.set()
                break
            try:
                url = self.q.get(timeout=20)
            except queue.Empty:
                with self.lock:
                    if self.active == 0 and self.q.empty():
                        self.done.set()
                continue
            with self.lock:
                self.active += 1
            try:
                self.one(url)
            finally:
                with self.lock:
                    self.active -= 1

    def save(self):
        """where it got to, written now and then, so a round cut short still carries on from there"""
        with self.lock:
            left = list(self.q.queue) + list(self.retry)
            seen = sorted(self.seen)
            self.pages.flush()
            self.files_log.flush()
            counts = dict(self.counts)
        for name, text in (('todo.txt', '\n'.join(left)), ('seen.txt', '\n'.join(seen))):
            tmp = os.path.join(self.a.state, name + '.tmp')
            with open(tmp, 'w', encoding='utf-8') as f:
                f.write(text)
            os.replace(tmp, os.path.join(self.a.state, name))
        with open(os.path.join(self.a.state, 'last-run.json'), 'w') as f:
            json.dump(dict(counts, left=len(left), finished=False, partial=True,
                           at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')), f)

    def one(self, url):
        rel = local(url)
        if rel in self.have:
            copy = os.path.join(self.a.pages_dir, rel) if self.a.pages_dir else ''
            if copy and os.path.exists(copy):
                try:
                    self.page(url, open(copy, 'rb').read())
                except Exception as e:
                    print('could not read', url, e, flush=True)
                with self.lock:
                    self.counts['pages_again'] = self.counts.get('pages_again', 0) + 1
                return
            if not PAGE.search(urllib.parse.urlsplit(url).path):
                with self.lock:
                    self.counts['already'] = self.counts.get('already', 0) + 1
                return
        if True:
            status, kind, body, final = self.get(url)
            time.sleep(self.a.gap)
            if status is None:
                with self.lock:
                    self.counts['failed'] += 1
                    self.retry.append(url)
                return
            if status != 200:
                with self.lock:
                    self.counts['missing'] += 1
                return
            if re.search(rb'(?i)<title>\s*(file|page) not found', body[:3000]):
                with self.lock:
                    self.counts['missing'] += 1   # the site answers a missing page with a 'File Not Found' page
                return
            if b'Just a moment' in body[:5000] and b'challenge' in body[:20000]:
                print('A protection check page: stopping at once, never trying to get past it', flush=True)
                self.done.set()
                with self.lock:
                    self.retry.append(url)
                return
            self.note(url, kind, len(body), getattr(self.tl, 'h', {}))
            fn = os.path.join(self.files, local(url))
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            with open(fn, 'wb') as f:
                f.write(body)
            ispage = 'html' in kind or PAGE.search(urllib.parse.urlsplit(url).path)
            with self.lock:
                self.counts['bytes'] += len(body)
                self.counts['pages' if ispage else 'photos'] += 1
                n = self.counts['pages'] + self.counts['photos']
            if ispage:
                try:
                    self.page(url, body)
                except Exception as e:
                    print('could not read', url, e, flush=True)
            if n % 500 == 0:
                print(json.dumps(self.counts), 'waiting', self.q.qsize(), flush=True)
            if n % 2000 == 0:
                self.save()

    def run(self):
        self.retry = []
        self.active = 0
        ts = [threading.Thread(target=self.work, daemon=True) for _ in range(self.a.workers)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        left = []
        while not self.q.empty():
            left.append(self.q.get())
        left += self.retry
        if not left and self.a.heads and os.path.exists(self.a.heads):
            self.heads([x for x in open(self.a.heads, encoding='utf-8').read().split('\n') if x])
        self.pages.close()
        self.files_log.close()
        with open(os.path.join(self.a.state, 'todo.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(left))
        with open(os.path.join(self.a.state, 'seen.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(self.seen)))
        self.counts['left'] = len(left)
        self.counts['finished'] = not left
        print(json.dumps(self.counts), flush=True)
        with open(os.path.join(self.a.state, 'last-run.json'), 'w') as f:
            json.dump(dict(self.counts, at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')), f)
        return self.counts


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', default='work')
    ap.add_argument('--state', default='state')
    ap.add_argument('--stop-at', default='03:50', help='UTC time to stop by (the 2pm picture morning stays free)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--gap', type=float, default=0.7, help='seconds each reader waits between files')
    ap.add_argument('--heads', default='', help='addresses of saved files whose details are missing (asked once)')
    ap.add_argument('--have', default='', help='paths already in Drive (rclone lsf -R)')
    ap.add_argument('--pages-dir', default='', help='a copy of the pages already in Drive, read instead of fetched')
    ap.add_argument('--most', type=int, default=0, help='stop after this many files (a test)')
    a = ap.parse_args()
    c = Copier(a)
    if a.most:
        def watch():
            while not c.done.is_set():
                if c.counts['pages'] + c.counts['photos'] >= a.most:
                    c.done.set()
                time.sleep(0.5)
        threading.Thread(target=watch, daemon=True).start()
    c.run()
