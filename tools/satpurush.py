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


def place_lines(text, rest=None):
    """The one to three place lines after the date and an optional tithi ('Mumbai, India' then 'London, UK' on a
    travel day); rest gets the lines after them."""
    lines = [l.strip() for l in text.split('\n') if l.strip()][1:]
    if lines and TITHI.search(lines[0]) and len(lines[0]) < 30:
        lines = lines[1:]
    places = []
    while lines and len(lines[0]) < 40 and not re.search(r'[.!:]$|https?://', lines[0]) and len(places) < 3:
        places.append(lines.pop(0))
    if rest is not None:
        rest += lines
    return places


def parts(text):
    """(place, the day's sentences) from the post's lines after the date: an optional tithi, one to three place lines
    ('Mumbai, India' then 'London, UK' on a travel day), then what happened."""
    lines = []
    places = place_lines(text, lines)
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
    end = lambda s: re.sub(r'(\s+(and|with|of|at|to|the|a|for|Mr|Mrs|Dr|in|on|from|by|his))+$', '', s, flags=re.I)
    return end(re.sub(r'\s+to [a-z]+$', '', end(s)))   # not 'Utsav to celebrate' (Darpan, 28 Oct 2026: never a cut off sentence)


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


NOT_TOWN = re.compile(r'\b(sabha|puja|darshan|arrival|arrives|departure|flight|transit|visit|viday|mandir|mahotsav|'
                      r'pratishtha|ekadashi|jayanti|tithi|parva|din|bandhan|rangotsav|amas|yatra|programme|meeting|'
                      r'promise|chhavani|crematorium|park|forest|parcs|maharaj|swami|uk|usa|nj|india|kenya|uganda|'
                      r'tanzania|zambia|canada|france|germany|italy|spain|portugal|belgium|netherlands|norway|sweden|'
                      r'switzerland|austria|czech|republic|south africa|monday|tuesday|wednesday|thursday|friday|'
                      r'saturday|sunday|surrey|kent|essex|hertfordshire|janmashtami|chaudash|pancham)\b|\d|;', re.I)


def towns(posts):
    """Every town the channel names on a day's place lines ('London', 'Ashton-under-Lyne', 'Dar es Salaam'), longest
    first, so a town can be found inside a caption misread off a photo ('Morning puja —.London')."""
    found = set()
    for s in stories(posts):
        for line in place_lines(s['text']):
            for part in re.split(r',|/|\bto\b|\bfrom\b|\bin\b', line):
                part = part.strip(' .')
                if re.fullmatch(r"[A-Z][\w.'’-]*(?: (?:es|on|upon|under)?[A-Z]?[\w.'’-]*)*", part) and len(part) > 2 and not NOT_TOWN.search(part):
                    found.add(re.sub(r'^(?:North|South|East|West|Central)(?:[- ](?:East|West))?\s+', '', part))   # 'South London' is London
    return sorted(found, key=len, reverse=True)


def town_in(text, known):
    """The last known town named in text ('Arrival in London from Mumbai' -> 'London': where he went, not where
    from), or None. Darpan, 28 Oct 2026: a card's place is only ever a clean town ('Morning puja —.London' showed)."""
    for t in (re.sub(r"\bfrom\s+[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)*", '', text or ''), text or ''):   # not where he came from, unless that is all it names
        hits = [(m.end(), len(k), k) for k in known for m in re.finditer(rf'(?<!\w){re.escape(k)}(?!\w)', t, re.I)]
        if hits:
            return max(hits)[2]
    return None


def card_words(t, words):
    """A photo's own caption, tidied ('7 Evening sabha' -> 'Evening sabha', 'Epping Forest — East' -> 'Epping Forest'),
    or None when it is cut short or misread ('Lord Mayor at', 'Morning of', 'Even', 'Any a Pn')."""
    t = re.sub(r'[‘’“”"]', ' ', t or '')
    t = re.sub(r'^(?:[\W\d_]+|[B-Zb-z]\s)+', '', t)
    t = re.sub(r'(?:[\s,:;.—–\-]+(?:North|South|East|West)(?:-?(?:east|west|East|West))?)+[\s,:;.]*$', '', t)   # 'Stanley Hall, South' (London)
    t = re.sub(r'\s+', ' ', re.sub(r'[\s—–\-«»~:=|@*.,;]+$', '', t)).strip()
    t = read(t, words) if t else None
    if not t or re.search(r"[^\w\s:'’,-]|\d", t):
        return None
    w = t.split()
    if (len(w) == 1 and len(t) < 5) or w[-1].lower() in {'at', 'of', 'in', 'on', 'to', 'from', 'the', 'a', 'and', 'with', 'meets', 'maharaj', 'swami', 'by'} \
            or any(len(x) <= 2 and x.lower() not in {'a', 'of', 'at', 'in', 'on', 'to', 'by'} for x in w) or w[0].lower() == 'maharaj' \
            or t.lower() in {'morning', 'evening', 'afternoon', 'north', 'south', 'east', 'west', 'central', 'north-west',
                             'a day', 'friday', 'fourways'}:
        return None
    return t.capitalize() if re.search(r'[a-z][A-Z]|[A-Z]{2,}[a-z]', t) else t   # 'MOrning puja', 'POST PUJa'


def main():
    posts = json.load(open(os.path.join(HERE, 'posts.json'), encoding='utf-8'))
    caps = json.load(open(os.path.join(HERE, 'captions.json'), encoding='utf-8')) if os.path.exists(os.path.join(HERE, 'captions.json')) else {}
    words = {w.lower() for p in posts for w in re.findall(r"[\w'’]+", p['text'])}   # every word the channel has written
    known = towns(posts)
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
        where = town_in(place, known) or (None if NOT_TOWN.search(place) else re.split(r',', place)[0].strip() or None)
        line = short(first, 110) if narrative else f'{bapa(y)} in {where or "the UK"}: {short(first, 90)}'
        cards = {}
        for p in pick['media']:
            c = caps.get(str(p['id']))
            if p['photos'] and c:
                what, rest = re.split(r'\s+[—–\-«»~:]\s+', c, maxsplit=1) if re.search(r'\s[—–\-«»~:]\s', c) else ('', c)   # 'Evening sabha – London', or just 'London'
                town = town_in(c, known)   # Darpan, 28 Oct 2026: 'Morning puja —.London' showed as the 1990 card's place
                if not town and not what and NOT_TOWN.search(c):   # no town, all caption ('Evening sabha: Shishu Din')
                    what = c
                if town:   # the words before the town are the caption ('Morning puja London', 'Viday —- London')
                    what = re.split(r'\s*[—–«»~=|@*]|\s-|-\s|,', c[:max(m.start() for m in re.finditer(re.escape(town), c, re.I))])[0]
                what = card_words(what, words)
                if what and town_in(what, known):
                    what = None   # the caption is only the town again
                if what or town:
                    cards[str(p['id'])] = dict(card=what, place=town)
        video = next((l for s in g for l in s['links'] if 'youtu' in l), None)
        events.append(dict(date=d, reposts=len(g), posts=[p['id'] for p in pick['media'] if p['photos']],
                           photos=sum(p['photos'] for p in pick['media']), place=where,
                           line=line, card=short(first, 48), cards=cards, guru=y < 1971,
                           whatsapp=f'On this day in {y}, {bapa(y)} was in {place if where and place.startswith(where) else where or "the UK"}. ' + ' '.join(said[:3]),
                           special=False, headline=None, story=' '.join(said[:3]), video=video,
                           url=f'https://t.me/{CHANNEL}/{pick["id"]}', channel=CHANNEL))
    json.dump(events, open(os.path.join(HERE, 'events.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(events), 'days,', sum(1 for e in events if e['date'] < '1999'), 'before 1999,',
          sum(len(e['cards']) for e in events), 'photos with their own caption')


if __name__ == '__main__':
    ocr() if sys.argv[1:] == ['ocr'] else main()
