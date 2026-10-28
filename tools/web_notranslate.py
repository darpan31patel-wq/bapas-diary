"""Website only (bapas-diary.com): browsers must never translate our pages by themselves (Darpan, 28 Oct 2026).

On his Android phone Chrome guessed the About page was in another language (it is full of Gujarati words such as
Vachanamrut, Swamishri and vicharan) and translated it: "Bapa's Diary" became "Dad's diary" and Travels became
"Wandering". Every page gets translate="no" on <html> plus Google's notranslate meta, so Chrome, Safari and
Google Translate leave the words alone. Our own ગુજરાતી switch (site/gujarati/gu.js) ignores the <html> level mark.
Run it last, after every step that adds pages.

    python3 tools/web_notranslate.py --out out
"""
import argparse
import pathlib
import re

META = '<meta name="google" content="notranslate">'


def fix(html):
    m = re.search(r'<html\b[^>]*>', html, re.I)
    if not m:
        return html
    tag = m.group(0)
    if 'translate=' not in tag:
        tag = tag[:-1].rstrip() + ' translate="no">'
    if 'notranslate' not in tag:
        if 'class="' in tag:
            tag = tag.replace('class="', 'class="notranslate ', 1)
        else:
            tag = tag[:-1] + ' class="notranslate">'
    html = html[:m.start()] + tag + html[m.end():]
    if META not in html:
        html = re.sub(r'<head\b[^>]*>', lambda h: h.group(0) + META, html, count=1, flags=re.I)
    return html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    n = 0
    for page in pathlib.Path(ap.parse_args().out).rglob('*.html'):
        html = page.read_text(encoding='utf-8')
        new = fix(html)
        if new != html:
            page.write_text(new, encoding='utf-8')
            n += 1
    print(f'{n} pages marked: browsers will not translate them')


if __name__ == '__main__':
    main()
