"""bapas-diary.com with no internet, for travelling (Darpan, 25 Oct 2026: "save the phone version so it opens even
with no internet").

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site, after web_phone.py:

    python3 tools/web_offline.py --out out --photo-years photo-years.txt

  out/sw.js                     from site/offline/sw.js: the helper that keeps every page opened on the phone
  out/offline.js, offline.css   the "No internet" note and, on phones, the Save for travelling button and sheet
  out/offline/index.html        shown with no internet for a page that was never opened (site/offline/offline.html)
  out/offline/files.json        what Save for travelling keeps: all of Search, Travels, Bapa through the years
and adds offline.js and offline.css to every page with the shared menu. The photos at photos.bapas-diary.com are
only kept as real copies when the photo bucket allows bapas-diary.com to read them (its CORS rule, see README).
"""
import argparse, hashlib, json, os, re, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'site', 'offline')
PHOTOS = 'https://photos.bapas-diary.com/'
TAGS = '<link rel="stylesheet" href="/offline.css">\n<script src="/offline.js" defer></script>\n'
PHONE = '<link rel="stylesheet" href="/phone.css">\n<script src="/phone.js" defer></script>\n'
# the pages saved the first time anyone opens the site, and the lists they need straight away
PAGES = ['/', '/calendar/', '/search/', '/travels/', '/through-the-years/', '/about/', '/favourites/', '/offline/']
DATA = ['/data/calendar.json', '/search/data/about.json', '/search/data/calendar.json', '/manifest.webmanifest',
        '/icon-192.png', '/apple-touch-icon.png', '/favicon-32.png']
# kept only when someone taps Save for travelling
PACK = ['search/data', 'travels/photos', 'through-the-years/p', 'through-the-years/f']
BIG = 3 << 20   # anything bigger than this waits for Save for travelling


def local(out, url):
    path = url.split('?')[0].split('#')[0]
    f = os.path.join(out, path.lstrip('/'))
    if path.endswith('/'):
        f = os.path.join(f, 'index.html')
    return f if os.path.isfile(f) else None


def page_file(out, page):
    return os.path.join(out, page.lstrip('/'), 'index.html')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--photo-years', help='years with photos in R2, one a line')
    a = ap.parse_args()
    out = a.out

    os.makedirs(os.path.join(out, 'offline'), exist_ok=True)
    s = open(os.path.join(SRC, 'offline.html'), encoding='utf-8').read()
    if os.path.exists(os.path.join(out, 'phone.js')):
        s = s.replace('</head>', PHONE + '</head>', 1)
    open(os.path.join(out, 'offline', 'index.html'), 'w', encoding='utf-8').write(s)
    for f in ('offline.js', 'offline.css'):
        shutil.copy(os.path.join(SRC, f), os.path.join(out, f))

    n = 0
    for d, _, files in os.walk(out):
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding='utf-8').read()
            if '/offline.js' in s or 'site-menu' not in s:   # only pages with the shared menu
                continue
            s = s.replace('</head>', TAGS + '</head>', 1) if '</head>' in s else TAGS + s
            open(p, 'w', encoding='utf-8').write(s)
            n += 1
    print('offline: added to', n, 'pages')

    # every page's own files: what its src= and href= point at on this site, its Google fonts and the globe's d3
    shell = []
    for page in PAGES:
        if not os.path.isfile(page_file(out, page)):
            print('offline: no', page)
            continue
        shell.append(page)
        html = open(page_file(out, page), encoding='utf-8').read()
        for u in re.findall(r'''(?:src|href)=["']([^"'$]+)["']''', html):
            if u.startswith(('https://fonts.googleapis.com/css', 'https://cdnjs.cloudflare.com/')):
                shell.append(u.replace('&amp;', '&'))
            elif u.startswith('/') and not u.startswith('//') and not u.endswith('/'):
                f = local(out, u)
                if f and os.path.getsize(f) <= BIG:
                    shell.append(u.split('#')[0])
    for u in DATA:
        if local(out, u):
            shell.append(u)
    for f in os.listdir(os.path.join(out, 'fonts')) if os.path.isdir(os.path.join(out, 'fonts')) else []:
        shell.append('/fonts/' + f)
    shell = list(dict.fromkeys(shell))

    pack, size = [], 0
    for folder in PACK:
        top = os.path.join(out, folder)
        for d, _, files in os.walk(top):
            for f in sorted(files):
                p = os.path.join(d, f)
                pack.append('/' + os.path.relpath(p, out).replace(os.sep, '/'))
                size += os.path.getsize(p)

    years = []
    if a.photo_years and os.path.exists(a.photo_years):
        years = sorted({int(y) for y in open(a.photo_years).read().split() if re.fullmatch(r'\d{4}', y)})

    h = hashlib.sha256()
    for u in shell:
        f = local(out, u)
        h.update(u.encode())
        if f:
            h.update(open(f, 'rb').read())
    h.update(json.dumps([pack, years]).encode())
    version = h.hexdigest()[:12]

    sw = open(os.path.join(SRC, 'sw.js'), encoding='utf-8').read()
    sw = sw.replace("'__VERSION__'", json.dumps(version)).replace('__SHELL__', json.dumps(shell))
    open(os.path.join(out, 'sw.js'), 'w', encoding='utf-8').write(sw)
    json.dump({'version': version, 'photos': PHOTOS, 'photoYears': years, 'pack': pack, 'packMB': round(size / 1048576)},
              open(os.path.join(out, 'offline', 'files.json'), 'w'), separators=(',', ':'))
    print(f'offline: version {version}, {len(shell)} files saved at first visit, '
          f'{len(pack)} more ({size / 1048576:.0f} MB) with Save for travelling, photo years {years}')


if __name__ == '__main__':
    main()
