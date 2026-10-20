"""Builds telegram/satpurush/events.json, the day by day diary of Bapa in the UK and Europe from the Satpurush in UK &
Europe channel (t.me/SatpurushInUKEurope), in the same shape as telegram/events.json so make.py adds it the same way:
older cards (1970 to 1998), a stand in where baps.org only has a nearby day, and lines for the 2pm 'Also on this day'.

telegram/satpurush/posts.json: every post of the channel (tools/tg_fetch.py, 20 Oct 2026). A dated post
('Saturday 20 October 1990 / Kartik sud 2 / London / Evening Swayamsevak sabha at Neasden Mandir.') is followed by
untitled photo and video posts of that day. Each photo is a framed picture: the channel's title on top, the darshan
with its caption written on it ('Evening sabha – London'), the date below. make.py cuts the darshan out (unframe).
telegram/satpurush/captions.json: the caption written on each photo, read once with tesseract (ocr below).

    python tools/satpurush.py           # rebuilds telegram/satpurush/events.json
    python tools/satpurush.py ocr       # reads the captions off the photos (GitHub Actions: needs t.me and tesseract)
"""
import collections, concurrent.futures, json, os, re, subprocess, sys, tempfile, urllib.request

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'telegram', 'satpurush')
CHANNEL = 'SatpurushInUKEurope'
M = 'january february march april may june july august september october november december'.split()
DATE = re.compile(r'^\s*(?:\w+day,?\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(M) + r'),?\s+(\d{4})', re.I)
TITHI = re.compile(r'\b(sud|vad|sudi|vadi|purnima|amas)\b', re.I)
SKIP = range(2008, 2017)   # 2012 to 2015 are Mahant Swami before he was guru, while Bapa (Pramukh Swami) was in India


def bapa(year):
    return 'Yogiji Maharaj' if year < 1971 else 'Pramukh Swami Maharaj' if year < 2017 else 'Mahant Swami Maharaj'


def stories(posts):
    """A dated post and the untitled photo and video posts that follow it."""
    out, cur = [], None
    for p in posts:
        m = DATE.match(p['text'])
        if m:
            cur = dict(date=f'{m[3]}-{M.index(m[2].lower()) + 1:02d}-{int(m[1]):02d}', id=p['id'], text=p['text'],
                       links=list(p['links']), media=[], posted=(p['posted'] or '')[:10])
            out.append(cur)
        elif cur and (p['photos'] or p['videos']) and not p['text'].strip():
            cur['media'].append(p)
        elif p['text'].strip():
            cur = None
    return out


def parts(text):
    """(place, the day's sentences) from the post's lines after the date: an optional tithi, one to three place lines
    ('Mumbai, India' then 'London, UK' on a travel day), then what happened."""
    lines = [l.strip() for l in text.split('\n') if l.strip()][1:]
    if lines and TITHI.search(lines[0]) and len(lines[0]) < 30:
        lines = lines[1:]
    places = []
    while lines and len(lines[0]) < 40 and not re.search(r'[.!:]$|https?://', lines[0]) and len(places) < 3:
        places.append(lines.pop(0))
    said = [l for l in lines if not re.search(r'https?://|^\W*(Full programme|Highlights|Video|Watch|📹)', l)]
    sentences = [s.strip() for l in said for s in re.split(r'(?<=[.!?])\s+', l) if s.strip()]
    return (places[-1] if places else ''), sentences


def short(s, n=60):
    """A card's few words: the first clause of a sentence."""
    s = re.sub(r'\s+', ' ', s).strip().rstrip('.')
    for cut in (r'\.\s', r';', r' – ', r' - ', r','):
        if len(s) > n:
            s = re.split(cut, s)[0]
    if len(s) > n:
        s = ' '.join(s[:n].split()[:-1])
    return re.sub(r'(\s+(and|with|of|at|to|the|a|for|Mr|Mrs|Dr|in|on))+$', '', s)


def ocr():
    """The caption written on each photo of a kept story ('Evening sabha – London'), into captions.json."""
    import numpy as np
    from PIL import Image
    posts = json.load(open(os.path.join(HERE, 'posts.json'), encoding='utf-8'))
    path = os.path.join(HERE, 'captions.json')
    done = json.load(open(path)) if os.path.exists(path) else {}
    todo = [p for s in stories(posts) if int(s['date'][:4]) not in SKIP for p in s['media'] if p['images'] and str(p['id']) not in done]
    print(len(todo), 'photos to read')

    def one(p):
        try:
            data = urllib.request.urlopen(urllib.request.Request(p['images'][0], headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read()
            with tempfile.NamedTemporaryFile(suffix='.jpg') as f:
                f.write(data); f.flush()
                im = Image.open(f.name).convert('RGB')
            top, bottom = band(im)
            if not top:
                done[str(p['id'])] = None; return
            strip = np.asarray(im.crop((0, bottom - 85, im.width, bottom - 8)).convert('L'))
            ink = Image.fromarray(np.where(strip > 200, 0, 255).astype('uint8')).resize((im.width * 2, 154))   # the white letters, black on white
            with tempfile.NamedTemporaryFile(suffix='.png') as f:
                ink.save(f.name)
                text = subprocess.run(['tesseract', f.name, '-', '--psm', '7'], capture_output=True, text=True).stdout
            done[str(p['id'])] = re.sub(r'\s+', ' ', text).strip(' .|_-—–') or None
        except Exception as e:
            print('  could not read', p['id'], e)

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for k, _ in enumerate(pool.map(one, todo)):
            if k % 200 == 0:
                print(k, flush=True)
                json.dump(done, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    json.dump(done, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


def band(im):
    """Top and bottom of the darshan inside the channel's frame: the two sharpest lines across the picture, one in
    the upper and one in the lower part (174 to 626 for a video still, 204 to 596 for a photo, on a 600x800 frame)."""
    import numpy as np
    g = np.asarray(im.convert('L'), dtype=float)
    h = g.shape[0]
    if im.width / h > .8 or h < 600:   # not the channel's tall frame (a video still, or another design)
        return None, None
    d = np.abs(np.diff(g, axis=0)).mean(axis=1)
    lo, hi = int(.15 * h), int(.60 * h)
    top = int(np.argmax(d[lo:int(.32 * h)])) + lo + 1
    bottom = int(np.argmax(d[hi:int(.85 * h)])) + hi + 1
    if d[top - 1] < 20 or d[bottom - 1] < 20 or bottom - top < .4 * h:
        return None, None
    return top, bottom


def read(t, words):
    """Words read off a photo, only when every word is one the channel has written ('Lonaon' and 'suja' are not)."""
    t = re.sub(r'(\s+\w)+$', '', re.sub(r'^\W+|[\W\d]+$', '', t.strip()))   # 'London a': a speck read as a letter
    if len(re.sub(r'\W', '', t)) < 4 or not all(w.lower() in words for w in re.findall(r"[\w'’]+", t)):
        return None
    return t[0].upper() + t[1:]


def main():
    posts = json.load(open(os.path.join(HERE, 'posts.json'), encoding='utf-8'))
    caps = json.load(open(os.path.join(HERE, 'captions.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'captions.json')) else {}
    words = {w.lower() for p in posts for w in re.findall(r"[\w'’]+", p['text'])}   # every word the channel has written
    by = collections.defaultdict(list)
    for s in stories(posts):
        if int(s['date'][:4]) not in SKIP:
            by[s['date']].append(s)
    events = []
    for d, g in sorted(by.items(), key=lambda kv: kv[0][5:] + kv[0][:4]):
        pick = max(g, key=lambda s: (sum(p['photos'] for p in s['media']), s['posted']))   # the fullest, newest repost
        longest = max(g, key=lambda s: len(s['text']))
        place, said = parts(longest['text'])
        y = int(d[:4])
        if not said:
            continue
        first = said[0]
        narrative = len(first) > 80 or re.search(r'\b(Swamishri|Swami|Maharaj)\b', first)
        line = short(first, 110) if narrative else f'{bapa(y)} in {re.split(r",", place)[0] or "the UK"}: {short(first, 90)}'
        cards = {}
        for p in pick['media']:
            c = caps.get(str(p['id']))
            if p['photos'] and c:
                what, town = re.split(r'\s+[—–\-«»~:]\s+', c, maxsplit=1) if re.search(r'\s[—–\-«»~:]\s', c) else ('', c)   # 'Evening sabha – London', or just 'London'
                what, town = read(what, words), read(town, words)   # a word misread off the photo ('Lonaon') is not used
                if what or town:
                    cards[str(p['id'])] = dict(card=what, place=town)
        video = next((l for s in g for l in s['links'] if 'youtu' in l), None)
        events.append(dict(date=d, reposts=len(g), posts=[p['id'] for p in pick['media'] if p['photos']],
                           photos=sum(p['photos'] for p in pick['media']), place=re.split(r',', place)[0].strip() or None,
                           line=line, card=short(first, 48), cards=cards, guru=y < 1971,
                           whatsapp=f'On this day in {y}, {bapa(y)} was in {place or "the UK"}. ' + ' '.join(said[:3]),
                           special=False, headline=None, story=' '.join(said[:3]), video=video,
                           url=f'https://t.me/{CHANNEL}/{pick["id"]}', channel=CHANNEL))
    json.dump(events, open(os.path.join(HERE, 'events.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(events), 'days,', sum(1 for e in events if e['date'] < '1999'), 'before 1999,',
          sum(len(e['cards']) for e in events), 'photos with their own caption')


if __name__ == '__main__':
    ocr() if sys.argv[1:] == ['ocr'] else main()
