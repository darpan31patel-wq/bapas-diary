"""Every tab linked together on bapas-diary.com (Darpan, 28 Oct 2026: "I want all the websites, all the tabs to be
linked together somehow"). Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built
site, after site_menu.py:

    python3 tools/web_links.py --out out

  out/links.js   from site/links/links.js, with the Travels map's places and the Then and now places filled in
                 (read from out/travels/places/index.html, so the lists are always the live ones)
and adds it to the pages that show photos, days or stays, which draw the gold "Photos, On this day, Calendar,
Travels, Places, Then and now" buttons with it (window.BDLinks).
"""
import argparse, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['index.html', 'search/index.html', 'calendar/index.html', 'then-and-now/index.html', 'about/index.html',
         'through-the-years/index.html', 'travels/index.html', 'travels/places/index.html']
TAG = '<script src="/links.js"></script>\n'


def places(out):
    s = open(os.path.join(out, 'travels', 'places', 'index.html'), encoding='utf-8').read()
    data = json.loads(re.search(r'<script[^>]*id="trips"[^>]*>(.*?)</script>', s, re.S).group(1))
    names = {p['name'].lower(): p['name'] for p in data['places'].values()}
    tn = {}
    m = re.search(r'const TN = \{(.*?)\};', s, re.S)
    if m:
        tn = dict(re.findall(r"'([^']+)':\s*'([^']+)'", m.group(1)))
    return names, tn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    names, tn = places(a.out)
    js = open(os.path.join(HERE, 'site', 'links', 'links.js'), encoding='utf-8').read()
    js = js.replace('{{PLACES}}', json.dumps(names, ensure_ascii=False)).replace('{{TN}}', json.dumps(tn, ensure_ascii=False))
    open(os.path.join(a.out, 'links.js'), 'w', encoding='utf-8').write(js)
    n = 0
    for page in PAGES:
        p = os.path.join(a.out, page)
        if not os.path.exists(p):
            print('links: no', page)
            continue
        s = open(p, encoding='utf-8').read()
        if TAG in s:
            continue
        s = s.replace('</head>', TAG + '</head>', 1) if '</head>' in s else TAG + s
        open(p, 'w', encoding='utf-8').write(s)
        n += 1
    print(f'links: {len(names)} places, {len(tn)} Then and now places, added to {n} pages')


if __name__ == '__main__':
    main()
