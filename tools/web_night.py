"""Gentle night mode on every page (Darpan, 29 Oct 2026: "a darker, softer look for the evenings. YES"). Website only;
run by .github/workflows/website-deploy.yml on the built site, after web_type.py and before web_offline.py.

From 7pm to 6am by the visitor's own clock the page turns softer by itself (no button): a tiny script first thing in
each page's <head> sets class "night" on <html> (and checks again every minute, so an open page turns at 7pm), and says
which page it is (data-pg="today", "search", ...) for site/night/night.css, which comes last in the <head>.
The screensaver page is left alone: it keeps the kit's own look.

    python3 tools/web_night.py --out out
"""
import argparse, hashlib, os, re, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = ('<script id="site-night">(function(){var d=document.documentElement;'
         'd.setAttribute("data-pg",location.pathname.split("/")[1]||"today");'
         'function t(){var h=new Date().getHours();d.classList.toggle("night",h>=19||h<6)}t();setInterval(t,60000)})()</script>')
OLD = re.compile(r'<script id="site-night">.*?</script>|<link rel="stylesheet" href="/night\.css(\?v=[0-9a-f]+)?" id="site-night-css">', re.S)
FIRST = re.compile(r'<meta charset[^>]*>|<head[^>]*>|<html[^>]*>', re.I)


def dress(s, link):
    """One page with the clock check first and night.css last in its head (unchanged if it has neither place)."""
    t = OLD.sub('', s)
    if '</head>' in t:
        t = t.replace('</head>', link + '</head>', 1)
    elif '<nav class="site-menu' in t:   # Through the years leaves out </head>: just before the menu, the body's start
        t = t.replace('<nav class="site-menu', link + '<nav class="site-menu', 1)
    else:
        return s
    m = FIRST.search(t)   # the check before anything is drawn, so a page never flashes bright at night
    at = m.end() if m else 0
    return t[:at] + CHECK + t[at:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    out = ap.parse_args().out
    css = os.path.join(out, 'night.css')
    shutil.copyfile(os.path.join(HERE, 'site', 'night', 'night.css'), css)
    v = hashlib.sha1(open(css, 'rb').read()).hexdigest()[:10]   # a browser never keeps an old copy after a change
    link = f'<link rel="stylesheet" href="/night.css?v={v}" id="site-night-css">'
    n = 0
    for d, _, files in os.walk(out):
        if os.path.relpath(d, out).split(os.sep)[0] == 'screensaver':
            continue
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding='utf-8').read()
            t = dress(s, link)
            if t != s:
                open(p, 'w', encoding='utf-8').write(t)
                n += 1
    print('night: gentle evening look on', n, 'pages')


if __name__ == '__main__':
    main()
