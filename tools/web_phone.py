"""bapas-diary.com on phones (Darpan typed yes to the phone design, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site, last of all:

    python3 tools/web_phone.py --out out

  out/phone.css, out/phone.js   from site/phone/: the tab bar at the bottom, the About button, the Today switch
                                (One year / All years together, with zoom) and the Calendar months scrolling up and down
and adds the two files to every page. Both only change anything on screens 760px wide or less.
"""
import argparse, os, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'site', 'phone')
TAGS = '<link rel="stylesheet" href="/phone.css">\n<script src="/phone.js" defer></script>\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    for f in ('phone.css', 'phone.js'):
        shutil.copy(os.path.join(SRC, f), os.path.join(a.out, f))
    n = 0
    for d, _, files in os.walk(a.out):
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding='utf-8').read()
            if '/phone.js' in s or 'site-menu' not in s:   # only pages with the shared menu
                continue
            if '</head>' in s:
                s = s.replace('</head>', TAGS + '</head>', 1)
            elif '</title>' in s:
                s = s.replace('</title>', '</title>\n' + TAGS, 1)
            else:
                s = TAGS + s
            open(p, 'w', encoding='utf-8').write(s)
            n += 1
    print('phone: added to', n, 'pages')


if __name__ == '__main__':
    main()
