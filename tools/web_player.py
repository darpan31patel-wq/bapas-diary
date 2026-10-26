"""The full screen player on the Today page of bapas-diary.com, for a TV in a mandir room or at home (Darpan, 26 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site, after web_extras.py:

    python3 tools/web_player.py --out out

  out/player/player.js, player.css   from site/player/: the player (see player.js)
  out/player/psm.jpg, msm.jpg        Pramukh Swami Maharaj and Mahant Swami Maharaj, together in its corner
and adds the two files to the Today page, where the Slideshow button becomes Full screen and /?play opens the player.
"""
import argparse, os, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'site', 'player')
TAGS = '<link rel="stylesheet" href="/player/player.css">\n<script src="/player/player.js" defer></script>\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'player'), exist_ok=True)
    for f in ('player.js', 'player.css', 'psm.jpg', 'msm.jpg'):
        shutil.copy(os.path.join(SRC, f), os.path.join(a.out, 'player', f))
    p = os.path.join(a.out, 'index.html')
    s = open(p, encoding='utf-8').read()
    if '/player/player.js' not in s:
        s = s.replace('</head>', TAGS + '</head>', 1) if '</head>' in s else s.replace('</title>', '</title>\n' + TAGS, 1)
        open(p, 'w', encoding='utf-8').write(s)
    print('player: added to index.html')


if __name__ == '__main__':
    main()
