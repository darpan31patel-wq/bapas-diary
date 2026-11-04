# Mockup only, never deploys: pictures of "Did you mean" on the live Search page and the new part of /interaction/,
# (second run: Did you mean kept on one line)
# with this branch's search.html and search-ask.js changes swapped into the live page on the runner (Darpan, 4 Nov 2026).
import json
import os
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

PAIRS = json.load(open('tools/mockups/did-you-mean-pairs.json', encoding='utf-8'))
INTER = open('live/interaction/index.html', encoding='utf-8').read()
TRIES = ['Sarangpr', 'Saranpru', 'Londn', 'Gurupurnma', 'janmastmi', 'Akshardam Delli', 'Neasdn', 'Gondl', 'smilling', 'Bocasan', 'Atlant', 'Chicgo mandir', 'xyzzyq']
SHOOT = {'Saranpru', 'Gurupurnma', 'Akshardam Delli'}
LEARNED = {'saranpru': 'sarangpur'}
os.makedirs('shots', exist_ok=True)
log = open('shots/log.txt', 'w')


def patch(route):
    r = route.fetch()
    body = r.text()
    for old, new in PAIRS:
        n = body.count(old)
        log.write(f'patch found {n}x: {old[:70]!r}\n')
        body = body.replace(old, new, 1)
    route.fulfill(response=r, body=body)


def spellings(learned):
    return lambda route: route.fulfill(status=200, content_type='application/json', body=json.dumps({'learned': learned}))


with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h, dpr, tag in [(1600, 1000, 1, 'computer'), (390, 844, 2, 'phone')]:
        for learned in [{}, LEARNED]:
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dpr, is_mobile=tag == 'phone', has_touch=tag == 'phone')
            ctx.route(lambda u: urlparse(u).path in ('/search/', '/search/index.html'), patch)
            ctx.route(lambda u: urlparse(u).path == '/api/spellings', spellings(learned))
            ctx.route(lambda u: urlparse(u).path == '/api/missed', lambda r: r.fulfill(status=204, body=''))
            pg = ctx.new_page()
            pg.on('pageerror', lambda e, t=tag: log.write(f'{t} pageerror: {e}\n'))
            pg.goto('https://bapas-diary.com/search/', wait_until='networkidle', timeout=60000)
            pg.wait_for_function('() => total > 0 && loaded >= total', timeout=120000)
            pg.wait_for_timeout(1500)
            for q in (TRIES if not learned else ['Saranpru']):
                pg.fill('#q', q)
                pg.wait_for_timeout(1200)
                pg.evaluate("() => { document.getElementById('q').blur(); document.getElementById('suggest').hidden = true; }")
                pg.wait_for_timeout(400)
                line = pg.inner_text('#count')
                log.write(f'{tag} learned={bool(learned)} {q!r}: {line!r}\n')
                if learned or q in SHOOT:
                    name = f"{tag}-{'learned-' if learned else ''}{q.replace(' ', '-').lower()}"
                    pg.evaluate("() => document.getElementById('count').scrollIntoView({block: 'center'})")
                    pg.wait_for_timeout(300)
                    pg.screenshot(path=f'shots/{name}.jpg', type='jpeg', quality=86)
                    if not learned and q == 'Saranpru':   # tap the word: it searches it
                        pg.click('#count .dym a')
                        pg.wait_for_timeout(2500)
                        pg.evaluate("() => document.getElementById('count').scrollIntoView({block: 'start'})")
                        log.write(f'   after tap: {pg.input_value("#q")!r} {pg.inner_text("#count")!r}\n')
                        pg.screenshot(path=f'shots/{name}-tapped.jpg', type='jpeg', quality=86)
            ctx.close()
    # the new part of /interaction/, with example rows (no real data is read)
    ctx = b.new_context(viewport={'width': 1300, 'height': 900}, device_scale_factor=1)
    ctx.route(lambda u: urlparse(u).path in ('/interaction/', '/interaction/index.html'),
              lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=INTER))
    fake = {
        '/api/missed': {'days': [['2026-11-04', [['saranpru', 2], ['gurupurnma', 1]]]]},
        '/api/feedback': {'items': []},
        '/api/visitors': {'error': 'example'},
        '/api/spellings': {'learnAt': 2, 'all': [['saranpru', 'sarangpur', 2, '2026-11-04'], ['gurupurnma', 'guru purnima', 1, '2026-11-04']]},
    }
    ctx.route(lambda u: urlparse(u).path in fake,
              lambda r: r.fulfill(status=503 if urlparse(r.request.url).path == '/api/visitors' else 200, content_type='application/json',
                                  body=json.dumps(fake[urlparse(r.request.url).path])))
    pg = ctx.new_page()
    pg.add_init_script("try { localStorage.setItem('bapas-diary-missed', 'example') } catch (e) {}")
    pg.goto('https://bapas-diary.com/interaction/', wait_until='networkidle', timeout=60000)
    pg.wait_for_timeout(2500)
    pg.locator('#spellings').screenshot(path='shots/interaction-spellings.jpg', type='jpeg', quality=88)
    ctx.close()
    b.close()
log.close()
