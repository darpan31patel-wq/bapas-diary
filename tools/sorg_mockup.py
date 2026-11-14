"""Pictures of the real pages with the old BAPS website's photos, reports and towns in them, for Darpan's mockup
(nothing is published: the site is built exactly like a deploy, served on this machine and photographed).

    python3 tools/sorg_mockup.py --site out --rows sorg-rows.json --days sorg-days.json --reports out/data/reports --shots shots

Picks the days to show by itself: a day that had no photo before and now has one of Bapa, a day with a long report,
a run of days Travels did not have. Writes shots/*.jpg (computer 1440 wide and phone) and shots/list.json.
"""
import argparse, functools, glob, http.server, json, os, random, sqlite3, threading


def serve(site):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=site)
    h.log_message = lambda *a, **k: None
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 8765), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:8765'


def choose(a):
    picks = []
    bapa = sqlite3.connect(a.bapa) if a.bapa and os.path.exists(a.bapa) else None
    old = sqlite3.connect(a.old) if a.old and os.path.exists(a.old) else None
    if bapa:
        new_days = [d for (d,) in bapa.execute("SELECT DISTINCT date FROM photos WHERE source = 'swaminarayan.org' AND date IS NOT NULL ORDER BY date")]
        if old:
            had = {d for (d,) in old.execute('SELECT DISTINCT date FROM photos WHERE date IS NOT NULL')}
            fresh = [d for d in new_days if d not in had]
        else:
            fresh = new_days
        random.Random(14).shuffle(fresh)
        for d in sorted(fresh[:2]) + [d for d in new_days if d[:4] < '1999'][:1]:
            picks.append(('today', d))
            picks.append(('box', d))
    reps = {}
    for f in glob.glob(os.path.join(a.reports, '*.json')):
        for y, items in json.load(open(f, encoding='utf-8')).items():
            for it in items:
                if it.get('k') != 'p':
                    reps[f'{y}-{os.path.basename(f)[:5]}'] = sum(len(p) for p in it['w'])
    for d in sorted(reps, key=lambda d: -reps[d])[:2] + ['2004-04-24']:
        if d in reps:
            picks.append(('box', d))
    days = json.load(open(a.days, encoding='utf-8'))
    if days:
        d = sorted(days)[len(days) // 3]
        picks.append(('calendar', d))
    picks.append(('travels', ''))
    seen, out = set(), []
    for p in picks:
        if p not in seen:
            seen.add(p); out.append(p)
    return out


def shoot(a):
    from playwright.sync_api import sync_playwright
    base = serve(a.site)
    os.makedirs(a.shots, exist_ok=True)
    made = []
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        for kind, d in choose(a):
            for dev, view in (('computer', dict(width=1440, height=900)), ('phone', dict(width=390, height=844))):
                ctx = br.new_context(viewport=view, device_scale_factor=2 if dev == 'phone' else 1,
                                     is_mobile=dev == 'phone', has_touch=dev == 'phone')
                if kind == 'today':   # Today opens on that day of the year
                    ctx.add_init_script(f"""(() => {{ const T = new Date('2026-{d[5:]}T09:00:00').getTime();
                      const D = Date; class F extends D {{ constructor(...x) {{ super(...(x.length ? x : [T])); }} static now() {{ return T; }} }}
                      window.Date = F; }})();""")
                page = ctx.new_page()
                url = {'today': '/', 'box': f'/photos/#date={d}', 'calendar': f'/calendar/#{d}', 'travels': '/travels/'}[kind]
                try:
                    page.goto(base + url, wait_until='networkidle', timeout=90000)
                except Exception as e:
                    print(kind, d, dev, 'slow:', e)
                page.wait_for_timeout(4000)
                name = f'{kind}-{d or "now"}-{dev}'
                full = kind in ('box',)
                if kind == 'box':   # the report sits under the photos
                    page.evaluate("document.querySelector('.vr') && document.querySelector('.vr').scrollIntoView({block: 'start'})")
                    page.wait_for_timeout(1500)
                    page.screenshot(path=os.path.join(a.shots, name + '-report.jpg'), quality=82, type='jpeg')
                    made.append(dict(kind=kind, date=d, device=dev, file=name + '-report.jpg'))
                    page.evaluate('scrollTo(0, 0)'); page.wait_for_timeout(800)
                page.screenshot(path=os.path.join(a.shots, name + '.jpg'), quality=82, type='jpeg', full_page=False)
                made.append(dict(kind=kind, date=d, device=dev, file=name + '.jpg'))
                ctx.close()
        br.close()
    json.dump(made, open(os.path.join(a.shots, 'list.json'), 'w'), indent=1)
    print(f'{len(made)} pictures in {a.shots}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True); ap.add_argument('--days', required=True); ap.add_argument('--reports', required=True)
    ap.add_argument('--bapa', default='bapa.db'); ap.add_argument('--old', default='old.db'); ap.add_argument('--shots', default='shots')
    shoot(ap.parse_args())


if __name__ == '__main__':
    main()
