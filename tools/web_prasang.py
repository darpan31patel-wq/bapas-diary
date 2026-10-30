#!/usr/bin/env python3
"""Prasang from today (Darpan, 30 Oct 2026): "a little button under that day's picture" on Today that opens the stories
posted on this same date in the recent years. They come from a public channel of daily prasangs (each a passage of the
Vachanamrut with its title and reference), saved in telegram/prasang/posts.json by tools/tg_fetch.py.

A deploy step:
    python3 tools/web_prasang.py --posts telegram/prasang/posts.json --fresh --out out/data/prasang
writes data/prasang/MM-DD.json = [[year, title, [paragraphs], reference], ...], oldest year first, for all 366 days.
--fresh first reads the channel's newest posts from its open web page, so the days since the saved copy are there too
(a failure keeps the saved copy). Like every page of the site it never names where the words come from: no links, no
channel names. Website only: touches nothing in the daily picture.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CHANNEL = 'bapsprasangs'
REF = re.compile(r'^\[\s*([^\]]*?)\s*\]?\s*$')   # '[Gadhadã II-47]', '[Loyã-18.11]', '[Gadhadã II-2' (cut off)
TAIL = re.compile(r'\s*\[\s*([^\[\]]*\d[^\[\]]*?)\s*\]\s*$')
NOT_SAID = re.compile(r'https?://|www\.|t\.me|telegram|whatsapp|instagram|youtube|channel|subscribe|\bjoin\b', re.I)


def fresh(posts):
    """The channel's newest posts, page by page back to the ones already saved."""
    import time
    import tg_fetch
    have, before, new = {p['id'] for p in posts}, None, {}
    for _ in range(40):
        pg = tg_fetch.Page()
        pg.feed(tg_fetch.get(f'https://t.me/s/{CHANNEL}' + (f'?before={before}' if before else '')))
        if not pg.posts:
            break
        for p in pg.posts:
            new[p['id']] = p
        low = min(p['id'] for p in pg.posts)
        if low in have or (before and low >= before):
            break
        before = low
        time.sleep(0.5)
    print(f'prasang: {len(set(new) - have)} new posts from the channel')
    return sorted({**{p['id']: p for p in posts}, **new}.values(), key=lambda p: p['id'])


def prasang(text):
    """(title, [paragraphs], reference) of one post, or None for a photo, a link or anything that is not a prasang."""
    lines = [l.replace('\xa0', ' ').strip() for l in (text or '').replace('\r', '').split('\n')]
    lines = [l for l in lines if l]
    if len(lines) < 2 or NOT_SAID.search(text):
        return None
    title, ref = lines[0], ''
    m = REF.match(lines[-1]) or TAIL.search(lines[-1])   # its own line, or at the end of the last one
    if m and re.search(r'\d', m[1]):
        ref, lines[-1] = m[1].rstrip(' .'), lines[-1][:m.start()].strip()
        lines = [l for l in lines if l]
    body = lines[1:]
    if not body or len(title) > 120 or sum(map(len, body)) < 60:
        return None
    return title, body, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posts', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--fresh', action='store_true', help='add the newest posts from the channel first')
    a = ap.parse_args()
    posts = json.load(open(a.posts, encoding='utf-8'))
    if a.fresh:
        try:
            posts = fresh(posts)
        except BaseException as e:   # the saved copy is still good
            print('prasang: could not read the newest posts:', e)
    days = {}
    for p in posts:
        got = p.get('posted') and prasang(p.get('text'))
        if not got:
            continue
        y, mmdd = int(p['posted'][:4]), p['posted'][5:10]
        day = days.setdefault(mmdd, [])
        if any(o[1].lower() == got[0].lower() for o in day):   # the same prasang again on this date a year later: once
            continue
        day.append([y, *got])
    os.makedirs(a.out, exist_ok=True)
    for mmdd, day in days.items():
        day.sort(key=lambda s: s[0])
        json.dump(day, open(os.path.join(a.out, mmdd + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'prasang: {sum(map(len, days.values()))} prasangs on {len(days)} days')


if __name__ == '__main__':
    main()
