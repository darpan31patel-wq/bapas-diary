"""Favourites, Share a day and the TV slideshow on bapas-diary.com (Darpan typed yes to all three, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site, after web_head.py:

    python3 tools/web_extras.py --out out

  out/extras.js, out/extras.css   from site/extras/: hearts, the share choices and the slideshow (see extras.js)
  out/favourites/index.html       My favourite darshans (site/extras/favourites.html)
and adds the two files to Today, Search, About and My favourites: hearts and share buttons on Today and
Search, and on every one of them the Aa text size button (Darpan typed yes to large text, 24 Oct 2026).
The day pictures and day links come from tools/web_dayshare.py.
"""
import argparse, os, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'site', 'extras')
# not Calendar: it fits the screen and already has its own zoom buttons
PAGES = ['index.html', os.path.join('search', 'index.html'),
         os.path.join('about', 'index.html'), os.path.join('favourites', 'index.html')]
# the chosen text size is set before the page is drawn, so the page never jumps
SIZE = ("<script>try{var z=+localStorage.getItem('bapas-diary-text');"
        "if(z>1)document.documentElement.style.zoom=z}catch(e){}</script>\n")
TAGS = '<link rel="stylesheet" href="/extras.css">\n<script src="/extras.js" defer></script>\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    for f in ('extras.js', 'extras.css'):
        shutil.copy(os.path.join(SRC, f), os.path.join(a.out, f))
    os.makedirs(os.path.join(a.out, 'favourites'), exist_ok=True)
    shutil.copy(os.path.join(SRC, 'favourites.html'), os.path.join(a.out, 'favourites', 'index.html'))
    for page in PAGES:
        p = os.path.join(a.out, page)
        if not os.path.exists(p):
            print('extras: no', page)
            continue
        s = open(p, encoding='utf-8').read()
        if 'bapas-diary-text' in s:
            continue
        tags = SIZE + ('' if '/extras.js' in s else TAGS)
        s = s.replace('</head>', tags + '</head>', 1) if '</head>' in s else s.replace('</title>', '</title>\n' + tags, 1)
        open(p, 'w', encoding='utf-8').write(s)
        print('extras: added to', page)


if __name__ == '__main__':
    main()
