#!/usr/bin/env python3
"""bapas-diary.com in Gujarati (Darpan, 25 Oct 2026: "a button that shows the whole website in Gujarati").

A deploy step, run on the finished site after every other step:
    python3 tools/web_gujarati.py --out out
It puts the English / ગુજરાતી switch (site/gujarati/gu.js) at the top of every page, and the Gujarati words
(site/gujarati/words/*.tsv, English <tab> Gujarati) into /gu/words.json, with the two Gujarati fonts in /gu/fonts/.
The pages themselves are not changed beyond the one script line. Website only: touches nothing in the daily picture.
"""
import argparse, json, pathlib, re, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent.parent / 'site' / 'gujarati'
TAG = '<script src="/gu/gu.js"></script>'


def words():
    w = {}
    for f in sorted((HERE / 'words').glob('*.tsv')):
        for n, line in enumerate(f.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.startswith('#'):
                continue
            en, _, g = line.partition('\t')
            en, g = en.strip(), g.strip()
            if not en or not g:
                sys.exit(f'{f.name} line {n}: needs English, a tab, then Gujarati')
            w[en] = g
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='the finished site folder')
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    gu = out / 'gu'
    (gu / 'fonts').mkdir(parents=True, exist_ok=True)
    shutil.copy(HERE / 'gu.js', gu / 'gu.js')
    for f in (HERE / 'fonts').iterdir():
        shutil.copy(f, gu / 'fonts' / f.name)
    w = words()
    text = json.dumps(w, ensure_ascii=False, separators=(',', ':'))
    if re.search(r'telegram|t\.me/', text, re.I):
        sys.exit('Telegram found in the Gujarati words: never on the public site')
    (gu / 'words.json').write_text(text, encoding='utf-8')
    pages = 0
    for p in out.rglob('*.html'):
        s = p.read_text(encoding='utf-8')
        if TAG in s:
            continue
        # first thing in <head>, so the globe and Through the years draw their words in Gujarati too
        s2, n = re.subn(r'(<head[^>]*>)', lambda m: m.group(1) + TAG, s, count=1, flags=re.I)
        if not n:
            continue
        p.write_text(s2, encoding='utf-8')
        pages += 1
    print(f'gujarati: switch on {pages} pages, {len(w)} words and lines, {len(text) // 1024} KB')


if __name__ == '__main__':
    main()
