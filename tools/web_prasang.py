#!/usr/bin/env python3
"""Prasang from today (Darpan, 30 Oct 2026): "a little button under that day's picture" on Today that opens the
prasangs of Mahant Swami Maharaj that happened on this date in the years gone by. They come from the private channel
Moments with Mahant Swami, saved by hand from Darpan's own Telegram into telegram/prasang/mms-prasangs.json
([{id, title, place, date 'YYYY-MM-DD', text}], the date being the day the prasang happened, not the day it was posted).

A deploy step:
    python3 tools/web_prasang.py --posts telegram/prasang/mms-prasangs.json --out out/data/prasang
writes data/prasang/MM-DD.json = [[year, title, [paragraphs], place], ...], oldest year first, for every date that has
one. Like every page of the site it never names where the words come from: no links, no channel names, no hashtags.
Website only: touches nothing in the daily picture.
"""
import argparse, json, os, re

NOT_SAID = re.compile(r'https?://|www\.|t\.me|telegram|whatsapp|instagram|youtube|\bchannel\b|subscribe', re.I)


def paragraphs(text):
    """The story in paragraphs, without links, hashtags or a line that sends people somewhere else."""
    out = []
    for b in re.split(r'\n\s*\n', (text or '').replace('\r', '')):
        b = ' '.join(l.strip() for l in b.split('\n') if l.strip() and not l.strip().startswith('#'))
        b = re.sub(r'#(\w)', r'\1', b).strip()   # '#Agna' in a sentence reads 'Agna'
        if b and not NOT_SAID.search(b):
            out.append(b)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--posts', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    days = {}
    for p in json.load(open(a.posts, encoding='utf-8')) if os.path.exists(a.posts) else []:
        d, said = p.get('date') or '', paragraphs(p.get('text'))
        if not re.fullmatch(r'\d{4}-\d\d-\d\d', d) or not said or not p.get('title'):
            continue
        day = days.setdefault(d[5:], [])
        if any(o[0] == int(d[:4]) and o[1].lower() == p['title'].lower() for o in day):   # the same prasang posted twice
            continue
        day.append([int(d[:4]), p['title'].strip(), said, (p.get('place') or '').strip()])
    os.makedirs(a.out, exist_ok=True)
    for mmdd, day in days.items():
        day.sort(key=lambda s: s[0])
        json.dump(day, open(os.path.join(a.out, mmdd + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'prasang: {sum(map(len, days.values()))} prasangs on {len(days)} days')


if __name__ == '__main__':
    main()
