"""Share preview, site icon and app feel for every page of bapas-diary.com (Darpan, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy after the pages are put together:

    python3 tools/web_share.py --out out      # share.jpg and the icons
    python3 tools/web_head.py --out out       # adds the tags below to every page, writes the app manifest

Each page gets its own title and short line (what WhatsApp shows under the picture), the share picture, the gold B
icon for the tab and the home screen, and a link to manifest.webmanifest so "Add to Home Screen" opens it full
screen like an app. A page that already has an og:image is left as it is.
"""
import argparse, json, os, re

SITE = 'https://bapas-diary.com'
NAME = "Bapa's Diary"
LINE = 'A smruti of Bapa for every day. Open His diary to see where He was.'   # Darpan's final words, 24 Oct 2026
PAGES = {
    '': (NAME, LINE),
    'search/': (NAME, LINE),
    'calendar/': ("Calendar · Bapa's Diary",
                  "A smruti for every day since 1999. Scroll through Bapa's calendar."),
    'travels/': ("Bapa's Travels · Bapa's Diary",
                 'A smruti of every journey. Follow Bapa across the world, year by year.'),
    'through-the-years/': ("Bapa Through the Years · Bapa's Diary",
                           "A smruti of every month. See Bapa's smile through the years."),
    'travels/places/': ("Bapa's Places · Bapa's Diary",
                        'A smruti of every place. See every place Bapa visited, on the globe.'),
    'about/': ("About Bapa's Diary",
               'Why Bapa\'s Diary was made, with love and thanks to BAPS.'),
}
DEFAULT = (NAME, LINE)
THEME = '#42101c'


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def tags(path):
    title, desc = PAGES.get(path, DEFAULT)
    t, d, u = esc(title), esc(desc), SITE + '/' + path
    return '\n'.join([
        f'<meta name="description" content="{d}">',
        f'<link rel="canonical" href="{u}">',
        f'<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{NAME}">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{u}">',
        f'<meta property="og:image" content="{SITE}/share.jpg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="Bapa smiling, beside the gold title {NAME}">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">',
        '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
        '<link rel="manifest" href="/manifest.webmanifest">',
        f'<meta name="theme-color" content="{THEME}">',
        '<meta name="apple-mobile-web-app-capable" content="yes">',
        '<meta name="mobile-web-app-capable" content="yes">',
        f'<meta name="apple-mobile-web-app-title" content="{NAME}">',
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">',
    ]), title


def fix(page, path):
    s = open(page, encoding='utf-8').read()
    if 'og:image' in s:
        return False
    head, title = tags(path)
    s = re.sub(r'<meta name="description"[^>]*>\n?', '', s, count=1)
    s, n = re.subn(r'<title>.*?</title>', lambda m: f'<title>{esc(title)}</title>\n{head}', s, count=1, flags=re.S)
    if not n:
        s = s.replace('</head>', head + '\n</head>', 1) if '</head>' in s else head + '\n' + s
    open(page, 'w', encoding='utf-8').write(s)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    for root, _, files in os.walk(a.out):
        if 'index.html' in files:
            rel = os.path.relpath(root, a.out).replace(os.sep, '/')
            path = '' if rel == '.' else rel + '/'
            if path.count('/') <= 1 or path in PAGES:   # top pages (and Places), not photo folders inside them
                print(path or '/', 'tagged' if fix(os.path.join(root, 'index.html'), path) else 'already has a preview')
    json.dump({
        'name': NAME, 'short_name': NAME, 'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#160509', 'theme_color': THEME,
        'description': DEFAULT[1],
        'icons': [{'src': '/icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                  {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
                  {'src': '/icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}],
    }, open(os.path.join(a.out, 'manifest.webmanifest'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
