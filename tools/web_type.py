"""Lora for headings and Poppins for subtitles, labels, menu and buttons on every page (Darpan, 28 Oct 2026: "Lora can
be your heading font, Poppins for subtitle things, leave the other bits as they are"). Website only; run by
.github/workflows/website-deploy.yml on the built site, after every step that adds pages.

Adds <link rel="stylesheet" href="/type.css?v=..."> as the last thing in each page's <head> (live/type.css, fonts in
live/fonts/), so it comes after the page's own fonts. Rerunning it moves the link back to the end.

    python3 tools/web_type.py --out out
"""
import argparse, hashlib, os, re

LINK = re.compile(r'<link rel="stylesheet" href="/type\.css(\?v=[0-9a-f]+)?" id="site-type">')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    out = ap.parse_args().out
    css = os.path.join(out, 'type.css')
    v = hashlib.sha1(open(css, 'rb').read()).hexdigest()[:10]   # a browser never keeps an old copy after a change
    tag = f'<link rel="stylesheet" href="/type.css?v={v}" id="site-type">'
    n = 0
    for d, _, files in os.walk(out):
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding='utf-8').read()
            t = LINK.sub('', s)
            if '</head>' in t:
                t = t.replace('</head>', tag + '</head>', 1)
            elif '<nav class="site-menu' in t:   # Through the years leaves out </head>: just before the menu, the body's start
                t = t.replace('<nav class="site-menu', tag + '<nav class="site-menu', 1)
            else:
                continue
            if t != s:
                open(p, 'w', encoding='utf-8').write(t)
                n += 1
    print('type: Lora and Poppins on', n, 'pages')


if __name__ == '__main__':
    main()
