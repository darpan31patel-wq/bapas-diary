"""A copy of a BAPS website that builds itself in the browser (na.baps.org: a plain reader only gets an empty first
page). Darpan, 13 Nov 2026: "Yes to all"; "Everything from the other websites need to have full detail".

One real browser tab (Playwright Chromium) opens each page of the site, waits for it to finish drawing, scrolls down
so every photo loads, and keeps:
  work/files/<path on the site>       the page as the browser drew it (so tools/sites_index.py can read its photos,
                                      captions, dates and places), and every photo the page showed, exactly as served
                                      (photos from the site's picture server are kept at their own path)
  state/files.jsonl                   one line per file: address, type, size, Last-Modified, when fetched
  state/seen.txt, state/todo.txt      where it got to, so the next round carries on from there
Gentle: one tab, a pause between pages, only the site's own pages are opened. It stops at once on any protection
check page and never tries to get past one. Never touches the 2pm picture, the website, R2 or bapas.db.

  python3 tools/browser_copy.py --site na.baps.org --base https://na.baps.org/ --seeds seeds.txt --stop-at 13:00
"""
import argparse, datetime as dt, json, os, re, sys, time, urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swaminarayan_org import local, sane   # the same file names and the same made up address filter

SKIP = re.compile(r'/(?:search|login|signin|account|cart|checkout|wp-admin|wp-json|feed|api)(?:/|$)|\.(?:xml|json|js|css)$', re.I)
FILE = re.compile(r'\.(?:pdf|mp3|zip|docx?|jpe?g|png|gif|webp)$', re.I)
CHECK = re.compile(r'(?i)just a moment|attention required|checking your browser|verify you are human|cf-chl|captcha')


def now():
    return dt.datetime.now(dt.timezone.utc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--seeds', default='')
    ap.add_argument('--work', default='work')
    ap.add_argument('--state', default='state')
    ap.add_argument('--stop-at', default='', help='UTC HH:MM to stop by')
    ap.add_argument('--gap', type=float, default=3.0)
    ap.add_argument('--have', default='', help='paths already in Drive (rclone lsf -R)')
    ap.add_argument('--again', action='store_true', help='open the pages seen before once more (to find links missed)')
    ap.add_argument('--no-routes', action='store_true')
    a = ap.parse_args()
    base = a.base.rstrip('/') + '/'
    hosts = {a.site, 'www.' + a.site}
    files = os.path.join(a.work, 'files')
    os.makedirs(files, exist_ok=True)
    os.makedirs(a.state, exist_ok=True)
    stop = None
    if a.stop_at:
        h, m = map(int, a.stop_at.split(':'))
        stop = now().replace(hour=h, minute=m, second=0, microsecond=0)
        if stop <= now():
            stop += dt.timedelta(days=1)

    def rd(name):
        p = os.path.join(a.state, name)
        return [x for x in open(p, encoding='utf-8').read().split('\n') if x] if os.path.exists(p) else []

    have = set()
    if a.have and os.path.exists(a.have):
        have = set(x for x in open(a.have, encoding='utf-8').read().split('\n') if x)
    seen = set(rd('seen.txt'))
    todo = rd('todo.txt')
    if a.again and seen:
        todo = [base] + sorted(seen - {base}) + todo
        seen = set()
    if not seen:
        todo = todo or [base] + (rd(os.path.abspath(a.seeds)) if a.seeds and os.path.exists(a.seeds) else [])
    got = set()      # photo addresses kept this round or before
    for line in rd('files.jsonl'):
        try:
            got.add(json.loads(line)['url'])
        except Exception:
            pass
    flog = open(os.path.join(a.state, 'files.jsonl'), 'a', encoding='utf-8')
    queued = set(todo) | seen

    def norm(u):
        u = urllib.parse.urldefrag(u)[0]
        s = urllib.parse.urlsplit(u)
        if s.scheme not in ('http', 'https') or s.netloc.lower() not in hosts:
            return None
        path = sane(s.path or '/')
        if path is None or SKIP.search(path):
            return None
        q = '' if re.search(r'(?i)utm_|fbclid|sort=|share=', s.query) else s.query
        return urllib.parse.urlunsplit((s.scheme, s.netloc.lower(), path, q, ''))

    def add(u):
        n = norm(u)
        if n and n not in queued:
            queued.add(n)
            todo.append(n)

    for u in list(todo):
        if not norm(u):
            todo.remove(u)

    def name(url, page=False):
        """where a file is kept: a page always as .../index.htm (a folder address), a photo at its own path"""
        s = urllib.parse.urlsplit(url)
        if page:
            rel = local(url)
            if not re.search(r'(?i)\.html?$', rel):
                rel += '/index.htm'
            return rel
        rel = re.sub(r'[<>:"\\|?*]', '_', urllib.parse.unquote(s.path).lstrip('/')) or 'image'
        if s.query:   # a resized copy from the picture server: never "__" (that is how the lists spot a page)
            rel += '~' + re.sub(r'[^\w=.-]+', '_', s.query)[:80]
        return rel

    def keep(url, kind, body, headers, page=False):
        """one file saved at its own path, with its details noted"""
        rel = name(url, page)
        fn = os.path.join(files, rel)
        os.makedirs(os.path.dirname(fn) or files, exist_ok=True)
        with open(fn, 'wb') as f:
            f.write(body)
        row = dict(url=url, file=rel, type=kind, bytes=len(body), last_modified=headers.get('last-modified'),
                   etag=headers.get('etag'), fetched_at=now().isoformat(timespec='seconds'), source=a.site)
        flog.write(json.dumps(row) + '\n')

    counts = dict(pages=0, photos=0, missing=0, failed=0, checked=False)

    def save():
        with open(os.path.join(a.state, 'seen.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(seen)))
        with open(os.path.join(a.state, 'todo.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(todo))
        flog.flush()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROME_PATH') or None)
        ctx = browser.new_context(user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                             'Chrome/126.0 Safari/537.36 (bapas-diary archive; gentle)',
                                  viewport={'width': 1366, 'height': 900})
        tab = ctx.new_page()
        pics = []

        def on_response(r):
            try:
                if r.request.resource_type == 'image' and r.status == 200:
                    pics.append(r)
            except Exception:
                pass
        tab.on('response', on_response)
        print(json.dumps(dict(site=a.site, to_do=len(todo), seen=len(seen))), flush=True)
        routes_read = bool(a.no_routes)
        while todo:
            if stop and now() >= stop:
                break
            url = todo.pop(0)
            if url in seen:
                continue
            seen.add(url)
            pics.clear()
            if FILE.search(urllib.parse.urlsplit(url).path):
                if name(url) in have or url in got:
                    continue
                try:
                    r = ctx.request.get(url, timeout=60000)
                    if r.status == 200:
                        keep(url, r.headers.get('content-type', ''), r.body(), r.headers)
                        got.add(url)
                    else:
                        counts['missing'] += 1
                except Exception:
                    counts['failed'] += 1
                time.sleep(a.gap)
                continue
            try:
                resp = tab.goto(url, wait_until='domcontentloaded', timeout=60000)
                try:
                    tab.wait_for_load_state('networkidle', timeout=20000)
                except Exception:
                    pass
            except Exception as e:
                counts['failed'] += 1
                print('could not open', url, str(e)[:100], flush=True)
                time.sleep(a.gap * 3)
                continue
            status = resp.status if resp else 0
            title = tab.title() or ''
            head = tab.content()[:20000]
            if status in (403, 429, 503) or CHECK.search(title) or 'challenge-platform' in head:
                counts['checked'] = True
                print(f'A protection check page ({status}, "{title[:60]}") at {url}: stopping at once, '
                      'never trying to get past it', flush=True)
                todo.insert(0, url)
                seen.discard(url)
                break
            if status >= 400:
                counts['missing'] += 1
                time.sleep(a.gap)
                continue
            for _ in range(12):   # down the page, so photos that wait to be seen load too
                done = tab.evaluate('() => { window.scrollBy(0, window.innerHeight); '
                                    'return window.scrollY + window.innerHeight >= document.body.scrollHeight - 5; }')
                tab.wait_for_timeout(500)
                if done:
                    break
            try:
                tab.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            final = norm(tab.url) or url
            body = tab.content().encode('utf-8')
            keep(final, 'text/html; charset=utf-8 (as the browser drew it)', body, resp.headers if resp else {}, page=True)
            counts['pages'] += 1
            for href in tab.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)'):
                add(href)
            if not routes_read:   # a Next.js site lists every page it has in its build manifest
                routes_read = True
                try:
                    bid = tab.evaluate('() => (window.__NEXT_DATA__ || {}).buildId || ""')
                    if bid:
                        r = ctx.request.get(urllib.parse.urljoin(base, f'/_next/static/{bid}/_buildManifest.js'), timeout=60000)
                        txt = r.text() if r.status == 200 else ''
                        open(os.path.join(a.state, 'routes.js'), 'w', encoding='utf-8').write(txt)
                        found = sorted(set(re.findall(r'"(/[A-Za-z0-9_\-/\[\]]*)"\s*:', txt)))
                        fixed = [x for x in found if '[' not in x and not x.startswith(('/_', '/api', '/404', '/500'))]
                        print(json.dumps(dict(routes=len(found), pages=fixed, by_name=[x for x in found if '[' in x])), flush=True)
                        for x in fixed:
                            add(urllib.parse.urljoin(base, x.lstrip('/')))
                except Exception as e:
                    print('build manifest not read:', str(e)[:100], flush=True)
            for r in list(pics):
                pu = urllib.parse.urldefrag(r.url)[0]
                if pu.startswith('data:') or pu in got or name(pu) in have:
                    continue
                try:
                    b = r.body()
                except Exception:
                    continue
                if len(b) < 3000:
                    continue   # icons and little buttons
                keep(pu, r.headers.get('content-type', ''), b, r.headers)
                got.add(pu)
                counts['photos'] += 1
            if counts['pages'] % 25 == 0:
                save()
                print(json.dumps(dict(counts, left=len(todo), at=now().strftime('%H:%M'))), flush=True)
            time.sleep(a.gap)
        browser.close()
    save()
    flog.close()
    out = dict(counts, left=len(todo), finished=not todo and not counts['checked'],
               at=now().isoformat(timespec='seconds'))
    with open(os.path.join(a.state, 'last-run.json'), 'w') as f:
        json.dump(out, f)
    print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
