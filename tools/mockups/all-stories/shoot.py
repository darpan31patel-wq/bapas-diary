"""Mockup pictures of Today and Search with every collected story (Darpan, 16 Nov 2026), taken on the live pages on a
GitHub runner with the change put in. Mockup only: nothing here is part of the website build.

    python3 tools/mockups/all-stories/shoot.py --reads reads.json --out shots
"""
import argparse, base64, json, os, signal, urllib.request
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
CH = json.load(open(os.path.join(HERE, 'changes.json'), encoding='utf-8'))


def patched(url, key):
    html = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 mockup'}), timeout=60).read().decode('utf-8')
    for a, b in CH[key]:
        a, b = a.replace('{{DATA}}', '/data/day/'), b.replace('{{DATA}}', '/data/day/')
        assert html.count(a) == 1, f'{key}: not found once ({html.count(a)}): {a[:160]!r}'
        html = html.replace(a, b, 1)
    print(key, 'changes put in:', len(CH[key]), flush=True)
    return html


def alarm(*a): raise TimeoutError('step took too long')
signal.signal(signal.SIGALRM, alarm)


def snap(pg, path, clip, most=2600):
    signal.alarm(90); print('snap', path, flush=True)
    clip = dict(clip, height=min(clip['height'], most))
    cdp = pg.context.new_cdp_session(pg)
    if clip['height'] > pg.viewport_size['height']:
        pg.set_viewport_size({'width': pg.viewport_size['width'], 'height': int(clip['height']) + 40}); pg.wait_for_timeout(1500)
    pg.evaluate("y => window.scrollTo(0, y)", max(0, clip['y'] - 10)); pg.wait_for_timeout(2500)
    data = cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 84, 'clip': dict(clip, scale=1)})['data']
    open(path, 'wb').write(base64.b64decode(data)); signal.alarm(0)


def box(pg, sel, pad=18, wide=0):
    b = pg.evaluate("s=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {x:r.left+scrollX,y:r.top+scrollY,width:r.width,height:r.height}}", sel)
    if not b: return None
    vw = pg.viewport_size['width']
    x = max(0, b['x'] - pad - wide)
    return {'x': x, 'y': max(0, b['y'] - pad), 'width': min(vw - x, b['width'] + 2 * pad + 2 * wide), 'height': b['height'] + 2 * pad}


def context(br, w, h, dpr, day, routes):
    ctx = br.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dpr, service_workers='block', reduced_motion='reduce',
                         is_mobile=w < 500, has_touch=w < 500)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: print('page error', e, flush=True))
    pg.clock.set_fixed_time(day + 'T09:00:00')
    def answer(body, kind):
        return lambda route, request=None: route.fulfill(status=200, content_type=kind, body=body)
    for match, body, kind in routes:
        pg.route(match, answer(body, kind))
    return ctx, pg


def today(br, html, day, w, h, dpr, tag, out):
    is_page = lambda u: u.split('#')[0].split('?')[0].rstrip('/') == 'https://bapas-diary.com'
    ctx, pg = context(br, w, h, dpr, day, [(is_page, html, 'text/html; charset=utf-8')])
    try:
        signal.alarm(70)
        try: pg.goto('https://bapas-diary.com/', wait_until='domcontentloaded', timeout=50000)
        except Exception as e: print('goto', e, flush=True)
        pg.wait_for_timeout(12000); signal.alarm(0)
        info = pg.evaluate("""() => ({count: (document.getElementById('count')||{}).innerText,
          cards: document.querySelectorAll('#cards .slot').length, text: document.querySelectorAll('#cards .photo.story').length,
          first: (()=>{const s=[...document.querySelectorAll('#cards .slot')].find(x=>x.querySelector('.photo.story'));return s?s.querySelector('.yr').textContent:''})()})""")
        print(day, tag, info, flush=True)
        snap(pg, f'{out}/{day}-{tag}-1-top.jpg', {'x': 0, 'y': 0, 'width': w, 'height': h})
        b = box(pg, '#board', 10)
        if b: snap(pg, f'{out}/{day}-{tag}-2-board.jpg', b, 3000 if tag == 'computer' else 2400)
        if info['first']:
            pg.evaluate("y => { const s=[...document.querySelectorAll('#cards .slot')].find(x=>x.querySelector('.yr').textContent===y); s.id='mockslot'; s.scrollIntoView({block:'center',inline:'center'}); }", info['first'])
            pg.wait_for_timeout(2500)
            if tag == 'phone':
                pg.screenshot(path=f'{out}/{day}-{tag}-3-card.jpg', type='jpeg', quality=84)
            else:
                b = box(pg, '#mockslot', 30, 260)
                if b: snap(pg, f'{out}/{day}-{tag}-3-card.jpg', b)
            b = box(pg, '#y' + info['first'], 18)
            if b: snap(pg, f'{out}/{day}-{tag}-4-year.jpg', b, 1800)
    except Exception as e: print(day, tag, 'stopped:', e, flush=True)
    finally:
        signal.alarm(0)
        try: ctx.close()
        except Exception: pass


def search(br, html, reads, hashes, w, h, dpr, tag, out):
    is_page = lambda u: u.split('#')[0].split('?')[0].rstrip('/') == 'https://bapas-diary.com/search'
    is_reads = lambda u: u.split('?')[0] == 'https://bapas-diary.com/search/data/reads.json'
    for n, (name, hs, click) in enumerate(hashes):
        ctx, pg = context(br, w, h, dpr, '2026-11-16', [(is_page, html, 'text/html; charset=utf-8'), (is_reads, reads, 'application/json')])
        try:
            signal.alarm(80)
            try: pg.goto('https://bapas-diary.com/search/' + hs, wait_until='domcontentloaded', timeout=50000)
            except Exception as e: print('goto', e, flush=True)
            pg.wait_for_timeout(20000); signal.alarm(0)
            print('search', name, tag, pg.evaluate("(document.getElementById('count')||{}).innerText"), flush=True)
            snap(pg, f'{out}/search-{name}-{tag}-1.jpg', {'x': 0, 'y': 0, 'width': w, 'height': h if tag == 'phone' else 1300})
            if click and pg.evaluate("s => { const c = document.querySelector(s); if (!c) return false; c.closest('section.day').id = 'mockday'; return true; }", click):
                b = box(pg, '#mockday', 10)
                if b: snap(pg, f'{out}/search-{name}-{tag}-2-day.jpg', b, 1600)
                pg.evaluate("s => document.querySelector(s).click()", click); pg.wait_for_timeout(3000)
                pg.screenshot(path=f'{out}/search-{name}-{tag}-3-open.jpg', type='jpeg', quality=84)
        except Exception as e: print('search', name, tag, 'stopped:', e, flush=True)
        finally:
            signal.alarm(0)
            try: ctx.close()
            except Exception: pass


def pick_days(folder):
    """Two dates where the old website wrote about years with no photo of Bapa, so the new boxes show (40 small reads)."""
    n = {f[:5]: json.load(open(os.path.join(folder, f), encoding='utf-8')) for f in os.listdir(folder) if f.endswith('.json')}
    best = []
    for md in sorted(n, key=lambda k: -len(n[k]))[:40]:
        try:
            D = json.load(urllib.request.urlopen(urllib.request.Request(f'https://bapas-diary.com/data/day/{md}.json', headers={'User-Agent': 'Mozilla/5.0 mockup'}), timeout=30))
        except Exception as e:
            print(md, e); continue
        have = {str(Y['y']) for Y in D.get('years', []) if Y.get('p') or Y.get('t')}
        best.append((len([y for y in n[md] if y not in have]), md))
    best.sort(reverse=True)
    print('days with written years and no photo:', best[:6], flush=True)
    return ['2026-' + md if md < '11-16' else '2025-' + md for _, md in best[:2]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--reads', required=True)
    ap.add_argument('--out', default='shots')
    ap.add_argument('--reports', default='reports')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    day_html = patched('https://bapas-diary.com/', 'site/day.html')
    search_html = patched('https://bapas-diary.com/search/', 'site/search.html')
    reads = open(a.reads, encoding='utf-8').read()
    with sync_playwright() as p:
        br = p.chromium.launch()
        for day in ['2026-07-19', '2026-11-07'] + pick_days(a.reports)[:1]:
            today(br, day_html, day, 1600, 1000, 1, 'computer', a.out)
            today(br, day_html, day, 390, 844, 2, 'phone', a.out)
        looks = [('day', '#date=2001-11-16', '.card.read'), ('word', '#q=Finland', '.card.read'), ('report', '#q=Cincinnati', '.card.read')]
        for w, h, dpr, tag in ((1600, 1000, 1, 'computer'), (390, 844, 2, 'phone')):
            search(br, search_html, reads, looks, w, h, dpr, tag, a.out)
        br.close()
    print(sorted(os.listdir(a.out)))


if __name__ == '__main__':
    main()
