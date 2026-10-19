"""Builds telegram/events.json, the dated stories of the Today in BAPS History channel (t.me/TodayinBAPShistory)
that make.py adds to Bapa's Diary: the history line, extra and stand in cards, the 2pm story and special pictures.

telegram/posts.json: every post of the channel, read from its public web page t.me/s/TodayinBAPShistory in
Darpan's Chrome on 19 Oct 2026 (id, posted, photos, videos, files, forwarded_from, text, links).
telegram/lines.json: per story (key 'YYYY-MM-DD#n') the short words written for it: line, place, card, whatsapp,
special, headline.

    python tools/telegram.py            # rebuilds telegram/events.json
"""
import collections, json, os, re
from datetime import datetime

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'telegram')
M = 'january february march april may june july august september october november december'.split()
DATE = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(M) + r')\s*,?\s+(\d{4})', re.I)


def stories(posts):
    """A story is a post whose first lines carry a date ('14 October 1970'), plus the untitled photo and video posts
    sent within six hours of it."""
    last = None
    for p in posts:
        last = p['posted'] or last
        p['when'] = datetime.fromisoformat(last).timestamp() if last else None
        p['date'] = None
        for line in [l.strip() for l in p['text'].split('\n') if l.strip()][:3]:
            m = DATE.search(line)
            if m and 1700 < int(m[3]) <= 2100:
                p['date'] = f'{m[3]}-{M.index(m[2].lower()) + 1:02d}-{int(m[1]):02d}'
                break
    dated = [p for p in posts if p['date']]
    out = {p['id']: dict(date=p['date'], text=p['text'].strip(), posts=[p['id']], photos=p['photos'], links=list(p['links']),
                         posted=(p['posted'] or '')[:10]) for p in dated}
    for p in posts:
        if p['date'] or p['when'] is None:
            continue
        best = min(dated, key=lambda d: (abs(d['when'] - p['when']), d['id'] < p['id']))
        if abs(best['when'] - p['when']) < 6 * 3600:
            s = out[best['id']]; s['posts'].append(p['id']); s['photos'] += p['photos']; s['links'] += p['links']
    return list(out.values()), {p['id']: p['photos'] for p in posts}


def body(text):
    """The story's own words: the lines after the date and place, up to about three sentences."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    keep = [l for l in lines[2:] if len(l) > 60 and not re.match(r'^(\W|Video|Watch|Photo)', l)]
    out = ''
    for sent in re.split(r'(?<=[.!?])\s+', ' '.join(keep)):
        if len(out) + len(sent) > 330:
            break
        out = (out + ' ' + sent).strip()
    return out or None


def main():
    posts = json.load(open(os.path.join(HERE, 'posts.json'), encoding='utf-8'))
    lines = json.load(open(os.path.join(HERE, 'lines.json'), encoding='utf-8'))
    cards = json.load(open(os.path.join(HERE, 'cards.json'), encoding='utf-8'))   # cards for stories lines.json gave none
    media = {p['id']: p['photos'] + p['videos'] for p in posts}   # a video's still can be a card too
    S, photos = stories(posts)
    by = collections.defaultdict(list)
    for s in S:
        by[s['date']].append(s)
    events = []
    for d, v in sorted(by.items(), key=lambda kv: kv[0][5:] + kv[0][:4]):
        groups = {}
        for s in v:   # the same story reposted each year, grouped by its opening words (as lines.json was written)
            b = re.sub(r'https?://\S+', '', s['text'])
            groups.setdefault(re.sub(r'\W+', '', ' '.join(b.split('\n')[2:6]).lower())[:60], []).append(s)
        for n, g in enumerate(groups.values()):
            w = lines.get(f'{d}#{n}')
            if not w:
                continue
            video = next((l for s in g for l in s['links'] if 'youtu' in l), None)
            longest = max(g, key=lambda s: len(s['text']))
            extra = {} if w.get('card') else cards.get(d, {})
            pick = max(g, key=lambda s: (s['photos'], sum(media[p] for p in s['posts']), s['posted']))   # the fullest, newest repost
            events.append(dict(date=d, reposts=len(g), posts=[p for p in pick['posts'] if media.get(p)],
                               photos=pick['photos'], place=w.get('place'), line=w['line'], card=w.get('card') or extra.get('card'),
                               guru=bool(extra.get('guru')),
                               whatsapp=w.get('whatsapp'), special=bool(w.get('special')), headline=w.get('headline'),
                               story=body(longest['text']), video=re.sub(r'[?&](?!v=)[^&]*', '', video).replace('&', '?') if video else None,
                               url=f'https://t.me/TodayinBAPShistory/{pick["posts"][0]}'))
    json.dump(events, open(os.path.join(HERE, 'events.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(events), 'stories on', len({e['date'][5:] for e in events}), 'days;',
          sum(e['special'] for e in events), 'special,', sum(bool(e['card']) and not e['guru'] for e in events), 'with Bapa,',
          sum(e['guru'] for e in events), 'earlier gurus')


if __name__ == '__main__':
    main()
