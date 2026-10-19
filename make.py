#!/usr/bin/env python3
"""Bapa's Diary: one darshan of Bapa from every year on today's date, hung like ivory polaroids on cords.

    python make.py                     today's date in London
    python make.py --date 2026-10-12   any date (only the day and month matter)

Writes out/bapas-diary.png and .jpg (2796 x 1290, iPhone landscape), out/date.txt and out/summary.txt.
"""
import argparse, collections, concurrent.futures, datetime, hashlib, json, os, random, re, threading, time, urllib.request
from zoneinfo import ZoneInfo

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_URL = 'https://darshan-screensaver.pages.dev/memories/{mmdd}.json'
W, H = 2796, 1290
MAROON_OUT = (18, 4, 8)
GOLD, GOLD_SOFT = (255, 207, 107), (217, 164, 65)
FOOTER = 'Darpan’s Smruti Project'
GLOW = .5           # soft lamp light behind the title (0 = none)
JALI = .13          # faint carved lattice at the edges (0 = none)


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.woff2'), max(8, round(size)))



# ---------------------------------------------------------------- photos

def fetch(url, tries=3, timeout=25):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bapas-diary)'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            err = e
            time.sleep(2 * (i + 1))
    raise err


def vicharan_items(path, mmdd, place, per_caption=2):
    """archive/vicharan/MM-DD.txt: '#year album prefix|place|date' lines (date only for a nearby day of the same trip),
    then 'ids|caption' lines (lower case caption = 'Swamishri ...')."""
    out, y, when = [], None, None
    lines = [l.rstrip('\n') for l in open(path, encoding='utf-8')]
    for k, line in enumerate(lines):
        if line.startswith('# ') or not line.strip():
            continue
        if line.startswith('#'):
            head, _, rest = line[1:].partition('|')
            where, _, when = rest.partition('|')
            parts = head.split(' ')
            y, album, prefix = int(parts[0]), parts[1], (parts[2] if len(parts) > 2 else '')
            place.setdefault(y, where)
            continue
        ids, c = line.split('|', 1)
        if c.endswith('...') and k + 1 < len(lines) and '|' in lines[k + 1] and not lines[k + 1].startswith('#'):
            nxt = lines[k + 1].split('|', 1)[1]                           # 'sanctifies water...' + 'Swamishri with the holy relics' carry on as one sentence
            c = c[:-3].rstrip() + ' ' + re.sub(rf'^{NAME}\s+', '', nxt)
        if c[:1].islower():
            c = 'Swamishri ' + c
        for i in ids.split(',')[:per_caption]:
            out.append({'y': y, 'd': when or f'{y}-{mmdd}', 'p': where or place.get(y, ''), 'c': c,   # the album's own place (2017 has Paris and London albums)
                        'i': f'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{prefix}{i}.jpg'})
    return out


def download_all(items, cache):
    os.makedirs(cache, exist_ok=True)

    def one(x, timeout=25, quiet=True):
        path = os.path.join(cache, hashlib.sha1(x['i'].encode()).hexdigest() + '.jpg')
        if not os.path.exists(path):
            try:
                data = fetch(x['i'], tries=2, timeout=timeout)
            except Exception as e:
                if not quiet:
                    print('  could not download', x['i'], e)
                return
            if len(data) < 2000:
                return
            open(path, 'wb').write(data)
        x['path'] = path

    with concurrent.futures.ThreadPoolExecutor(4) as pool:   # baps.org gets slow when asked for too much at once
        list(pool.map(one, items))
    have_years = {x['y'] for x in items if 'path' in x}
    missed = sorted((x for x in items if 'path' not in x), key=lambda x: x['y'] in have_years)   # empty years first
    if missed:   # give the slow ones a second, gentler go (unless baps.org is plainly down)
        print(f'  {len(missed)} photos were slow, trying {min(len(missed), 40)} of them again', flush=True)
        time.sleep(20)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda x: one(x, timeout=60, quiet=False), missed[:40]))


MODELS = os.path.join(HERE, 'models')
DETECT = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .6, .3, 5000)
RECOGNISE = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'face_recognition_sface_2021dec.onnx'), '')
BAPA = {k: np.array(v) for k, v in json.load(open(os.path.join(MODELS, 'bapa-faces.json'))).items()}
PSM_UNTIL = '2016-08-13'   # Pramukh Swami Maharaj before this date, Mahant Swami Maharaj after
SAME_PERSON = .5           # cosine similarity; strangers and murtis score below .35
FACE_LOCK = threading.Lock()   # the face models can only look at one photo at a time


def bapa_face(im, when, need=SAME_PERSON):
    """Bapa's face in the photo as ((x, y, w, h), similarity), or (None, 0) when he can't be recognised."""
    small = im.copy(); small.thumbnail((1280, 1280))
    k = im.width / small.width
    bgr = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2BGR)
    ref = BAPA['psm' if when < PSM_UNTIL else 'msm']
    best, best_sim = None, 0
    with FACE_LOCK:
        DETECT.setInputSize((bgr.shape[1], bgr.shape[0]))
        faces = DETECT.detect(bgr)[1]
        for f in faces if faces is not None else []:
            e = RECOGNISE.feature(RECOGNISE.alignCrop(bgr, f))[0]
            sim = float(ref @ (e / np.linalg.norm(e)))
            if sim > best_sim:
                best, best_sim = tuple(float(v) * k for v in f[:4]), sim
                LAST_FRONT[0] = front_view(f)
    return (best, best_sim) if best_sim >= need else (None, best_sim)


LAST_FRONT = [1.0]   # how face-on the face bapa_face last recognised was (1 looking at the camera, 0 a profile)


def front_view(f):
    """0 to 1 from the detector's landmarks: the eyes are far apart on a face seen from the front and
    close together on a profile, and the nose sits between them when he looks at the camera."""
    x, y, w, h, rx, ry, lx, ly, nx, ny = [float(v) for v in f[:10]]
    eyes = abs(lx - rx) / max(w, 1)                                 # about .45 face on, under .2 side on
    centred = 1 - min(1, abs(nx - (lx + rx) / 2) / max(abs(lx - rx) / 2, 1))
    return max(0, min(1, (eyes - .18) / .25)) * (.5 + .5 * centred)


DOING = re.compile(r'arti|puja|pujan|bless|greet|shower|lights?\b|sanctif|plays?|walk|pradakshina|parikrama|reads?|offer|appl|'
                   r'address|discourse|mala|meets?|inaugurat|pratishtha|ritual|perform|bows|thal|sprinkl|writ|garland|honou?r|'
                   r'welcom|darshan|meditat|pray|arriv|visit|abhishek|lamp|tilak', re.I)
JUST_A_FACE = re.compile(r'divine|jovial|\bmood\b|^\s*(HH|Param Pujya)?\s*(Pramukh|Mahant) Swami( Maharaj)?\s*$', re.I)
# a one-off moment worth keeping as a wide shot even if Bapa comes out small in it (Darpan, 18 Oct 2026: "if it's special keep it")
SPECIAL = re.compile(r'pratishtha|inaugurat|annakut|diwali|new year|janm|jayanti|diksha|abhishek|bhumi|foundation|shilanyas|'
                     r'mahotsav|celebrat|festival|procession|rath|yagna|mahapuja|chopda|rangoli|dandiya|\braas\b|\bras\b|'
                     r'instrument|surando|drum|president|prime minister|governor|congress|minister|mayor|ambassador|'
                     r'pilgrim|on foot|airport|farewell|departs|flag|cake|balloon|boat|horse|elephant|tractor|'
                     r'cricket|football|plant|tree|cow|children|balaks?\b|kids?\b', re.I)
ACTION_KEEP = .72     # an action shot must keep at least this much of the photo inside the frame, or what Bapa does gets cut off
NICE_MIN = 2.0        # the action score a photo needs before it beats a close darshan
CLOSE_SHARE = .6      # about this share of the years are close darshans of Bapa's face (Darpan, 18 Oct 2026: 16 of 27)
RECENT_DAYS = 7       # a photo shown in the last week is not shown again: the old albums cover several days, so
                      # neighbouring dates list the same photos (18 and 19 October share 2003, 2005, 2006 and 2007)
SHOWN_FILE = os.path.join(HERE, 'archive', 'shown.json')   # which photo each year showed on each day (written after every run)
CLOSE_MIN_FACE = 64   # pixels: a face smaller than this can't be blown up into a close darshan


BAPA_WORDS = re.compile(r"\b(HH|H\.H\.|Param Pujya|P\.P\.|Pramukh|Mahant|Swami|Swamishri|Maharaj|Bapa|his|the|a|an|of|to|and|in|on|at|with|by|for|all)\b", re.I)
STANDARD = re.compile(r"divine|jovial|\bmood\b|morning puja|\bpuja\b|bless\w* (all|the assembly|everyone|devotees)\s*$|"
                      r"^\W*bless\w*\W*$|greet\w* (all|everyone|devotees)|folded hands|shikshapatri|satsang diksha|"
                      r"darshan of (the )?(shrine|murtis?|thakorji)|tapni mala|\bmala\b|\bdarshan\s*$|engaged in|"
                      r"listens|seated|in thought|smil|^\W*\w+ (performs|performing|does) (the )?(arti|aarti)\W*$", re.I)


def unique_caption(c):
    """True when the caption tells of something that happened that day (a visitor, a ceremony, balaks
    dressed as sadhus, playing the drum) rather than an everyday line (divine mood, morning puja,
    blesses all, greets all with folded hands, reads the Shikshapatri)."""
    c = re.sub(r"\s+", " ", c or "").strip()
    if not c or STANDARD.search(c):
        return False
    rest = re.findall(r"[A-Za-z][A-Za-z.]+", BAPA_WORDS.sub(" ", c))
    return len(rest) >= 2


STOP = {'the', 'a', 'an', 'of', 'to', 'and', 'in', 'on', 'at', 'with', 'by', 'for', 'his', 'all', 'bapa', 'during'}


def caption_key(c):
    """Rough word stems of a caption, so 'Greets all with folded hands' and 'Greeting all with folded hands' match."""
    words = re.findall(r"[a-z]+", c.lower())
    return {w[:5] for w in words if w not in STOP}


COMMON_VERBS = {'bless', 'perfo', 'readi', 'reads', 'greet', 'engag', 'engro', 'has', 'visit', 'arriv', 'disco',
                'medit', 'turns', 'plays', 'appli', 'offer', 'durin', 'start', 'daily', 'morni', 'eveni'}


def same_caption(a, b):
    """Near repeats count too: 'Reads the Shikshapatri' inside 'Reads the Shikshapatri and Satsang Diksha',
    'In a divine mood' inside 'In a divine, jovial mood', 'Blesses all' beside 'Blesses the assembly'."""
    if not (a and b):
        return False
    j = len(a & b) / len(a | b)
    small, big = sorted((a, b), key=len)
    shared_things = (a & b) - COMMON_VERBS     # 'tilak' in 'applies a tilak at start of daily puja' and '... on his forehead'
    return (j >= .7 or (small <= big and (len(small) >= 2 or j >= .5))
            or (len(a & b) >= 2 and shared_things and j >= .3))


PICKS = json.load(open(os.path.join(HERE, 'archive', 'picks.json'))) if os.path.exists(os.path.join(HERE, 'archive', 'picks.json')) else {}
ALL = []        # every photo the last pick looked at: (year, face match, recognised, caption, url)
WORKINGS = []   # what the last pick looked at: per year its best few photos, scores and the one chosen


def second_choices():
    """Each year's next best photo after the chosen one, still never repeating a caption."""
    out, used = [], []
    for w in WORKINGS:
        if w['pick'] is None:
            continue
        pk = caption_key(caption(w['pick']))
        rest = [x for _, x, st in w['rows'] if x is not w['pick'] and st != 'repeats an earlier caption']
        good = [x for x in rest if not same_caption(caption_key(caption(x)), pk)
                and not any(same_caption(caption_key(caption(x)), u) for u in used)]
        x = (good or rest or [w['pick']])[0]
        out.append(x); used.append(caption_key(caption(x)))
        w['second'] = x
    return out


def workings_sheet(day):
    """A tall sheet: one row per year, its top photos left to right with their scores and captions."""
    tw, th, pad, lab = 330, 250, 24, 260
    rows = [w for w in WORKINGS if w['rows']]
    cols = max(len(w['rows']) for w in rows)
    Wd, Hd = lab + cols * (tw + pad) + pad, 150 + len(rows) * (th + 144)
    img = Image.new('RGB', (Wd, Hd), (40, 10, 18)); d = ImageDraw.Draw(img)
    d.text((Wd / 2, 70), f'{day.day} {day:%B}: how each year was chosen', font=garamond(64), fill=GOLD, anchor='mm')
    cf, sf, yf = garamond(22, 500), arimo_bold(18), garamond(54, 600)
    for r, w in enumerate(rows):
        y0 = 150 + r * (th + 144)
        d.text((pad, y0 + 20), str(w['year']), font=yf, fill=GOLD, anchor='la')
        d.text((pad, y0 + 92), w['mode'].upper(), font=sf, fill=(226, 184, 104), anchor='la')
        for c, (score, x, status) in enumerate(w['rows']):
            x0 = lab + c * (tw + pad)
            img.paste(crop_to(x['im'], x['face'], tw, th, x.get('crop', 'frame')), (x0, y0))
            tag = 'CHOSEN' if status == 'chosen' else ('2ND CHOICE' if x is w.get('second') else status.upper())
            colour = GOLD if status == 'chosen' else (CAPTION_IVORY if tag == '2ND CHOICE' else (190, 150, 140))
            if status == 'chosen' or tag == '2ND CHOICE':
                d.rectangle((x0 - 4, y0 - 4, x0 + tw + 3, y0 + th + 3), outline=colour, width=4)
            face = f'Bapa {x["sim"]:.2f} front {x.get("front", 0):.1f}' if x['face'] else 'Bapa not found'
            how = f'shown {x.get("crop", "")}, frame keeps {round(100 * x.get("keep", 1))}%' + ('  SPECIAL' if x.get('special') else '') + ('  nice action' if x.get('nice') else '')
            d.text((x0, y0 + th + 10), f'{tag}  score {score:.2f}  {face}'.strip(), font=sf, fill=colour, anchor='la')
            d.text((x0, y0 + th + 34), how, font=sf, fill=colour, anchor='la')
            for i, line in enumerate(wrap(d, caption(x) or '(no caption)', cf, tw, 2)):
                d.text((x0, y0 + th + 60 + i * 26), line, font=cf, fill=CAPTION_GOLD, anchor='la')
    return img


def frame_keep(im, face, fa):
    """How much of the photo (0 to 1) a frame of aspect fa (width / height) keeps when it fills the frame
    around Bapa: a 3:2 photo in a tall 0.69 frame keeps 0.46, so whatever Bapa is doing beside him gets cut off."""
    iw, ih = im.size
    return min(1, (ih * fa) / iw) if iw / ih > fa else min(1, (iw / fa) / ih)


def shown():
    """archive/shown.json: {'YYYY-MM-DD': {'2003': photo url, ...}} for the pictures already made."""
    try:
        return {d: v for d, v in json.load(open(SHOWN_FILE)).items() if isinstance(v, dict)}
    except (OSError, ValueError):
        return {}


def remember(day, photos):
    """Record today's picks in archive/shown.json (the last two months), so the next days pick other photos."""
    s = shown()
    s[str(day)] = {str(x['y']): x['i'] for x in photos}
    s = {d: v for d, v in sorted(s.items()) if abs((day - datetime.date.fromisoformat(d)).days) <= 60}
    s['_how'] = 'The photo each year showed on each day. A photo shown in the last RECENT_DAYS days is not picked again (make.py).'
    json.dump(s, open(SHOWN_FILE, 'w'), indent=1)


def pick_one_per_year(items, seed, unique=False, aspect=.69, day=None):
    """Per year, a photo where Bapa is recognised, chosen by Darpan's rule (18 Oct 2026): a photo is either a
    really nice action shot or a close up of Bapa. An action shot only counts when what he is doing stays in
    the frame (the frame keeps >= ACTION_KEEP of the photo), he is not tiny, and the caption says he is doing
    something; a special one-off moment (pratishtha, festival, visitor) is kept even if the frame would cut
    it, and is then shown whole. Otherwise the year is a close darshan: a tight crop on his head and
    shoulders, which needs the face to be big enough to enlarge. His head is never cut. Years with a really
    nice action shot take it (close ups still get a turn every third year when the year has a good one),
    the rest are close ups, so a plain day gives darshan rather than a half-cut action.
    No two years share the same caption: when a year's best photo repeats an earlier year's caption its next
    best photo with a different caption is used. Years where he can't be recognised in any photo are left out,
    unless that would leave fewer than five; then they're kept and shown whole so he isn't cropped out.
    aspect is the frame's width / height (0.69 for the tall live cards, 1.33 for wide ones)."""
    rnd = random.Random(seed)
    cands = {}
    for x in items:
        if 'path' not in x:
            continue
        try:
            im = Image.open(x['path']).convert('RGB')
        except Exception:
            continue
        face, sim = bapa_face(im, x.get('d', str(x['y'])), TG_SAME_PERSON if x.get('tg') else SAME_PERSON)
        front = LAST_FRONT[0] if face else 0
        x = dict(x, im=im, face=face, sim=sim, front=round(front, 2))
        r = face[3] / im.height if face else 0
        c = x.get('c') or ''
        keep = frame_keep(im, face, aspect)
        special = bool(SPECIAL.search(c))
        subject = bapa_is_subject(c)
        doing = bool(DOING.search(c)) and not JUST_A_FACE.search(c)
        close_ok = bool(face) and face[3] >= CLOSE_MIN_FACE and front >= .35
        jitter = rnd.uniform(0, .04) + (1.2 if unique and face and unique_caption(c) else 0) + x.get('boost', 0)
        # a close darshan wants his face turned to the camera: a profile or a bowed head loses most of a point
        s_close = (1 + min(r, .35) + sim + (.2 if JUST_A_FACE.search(c) else 0) + .9 * (front - .6) if face else -5) + jitter
        s_close -= (.6 if face and not subject else 0) + (1.5 if face and not close_ok else 0)
        s_doing = (1 + sim + .6 * max(0, 1 - abs(r - .18) / .15) + (.4 if doing else 0) + (.3 if special else 0)
                   - (.5 if r < .1 else 0) - (.6 if not subject else 0)             # Bapa small in the frame, or not the subject
                   - (0 if keep >= ACTION_KEEP else (.3 if special else 1.5))       # what he is doing would be cut off
                   if face else -5) + jitter
        # a really nice action shot: he is doing something, he is the subject, not small, nothing cut off (or a special
        # moment), and it scores well; anything less and the year is better served by a close darshan
        nice = bool(face) and doing and subject and r >= .13 and (keep >= ACTION_KEEP or special) and s_doing - jitter >= NICE_MIN
        x.update(keep=round(keep, 2), special=special, nice=nice, close_ok=close_ok)
        ALL.append((x['y'], round(sim, 2), bool(face), caption(x), x['i']))
        lst = cands.setdefault(x['y'], [])
        lst.append((s_close, s_doing, x))
        if len(lst) > 16:   # keep memory down: only the best few of each kind stay
            keep_ids = {id(v) for v in sorted(lst, key=lambda v: -v[0])[:8] + sorted(lst, key=lambda v: -v[1])[:8]}
            lst[:] = [v for v in lst if id(v) in keep_ids]
    years = sorted(cands)
    if sum(1 for y in years if any(v[2]['face'] for v in cands[y])) >= 5:
        years = [y for y in years if any(v[2]['face'] or v[2].get('tg') for v in cands[y])]   # a channel year stays even unrecognised (flagged)
    # a caption that turns up in other years too ('reads the Shikshapatri' most mornings) loses a little,
    # so a year's one-off moment ('reads the Sahajanand Sudha') wins when the photos are otherwise close
    keys = {y: [caption_key(caption(v[2])) for v in cands[y]] for y in cands}
    for y in cands:
        for j, v in enumerate(cands[y]):
            k = keys[y][j]
            others = sum(1 for oy in cands if oy != y and any(same_caption(k, ok) for ok in keys[oy]))
            if others:   # capped: with 25 years on a day 'blesses the assembly' would otherwise lose several points
                cands[y][j] = (v[0] - min(.5, .25 * others), v[1] - min(.5, .25 * others), v[2])
    if day:   # a photo shown in the last week loses heavily and stops counting as a nice action shot, its caption loses a
        # little, so neighbouring dates that list the same album show different photos of Bapa
        recent, recent_keys = {}, {}   # url -> how many days ago it was shown (yesterday's loses most, last week's least)
        for d, ys in shown().items():
            ago = (day - datetime.date.fromisoformat(d)).days
            if 0 < ago <= RECENT_DAYS:
                for y, u in ys.items():
                    recent[u] = min(ago, recent.get(u, ago))
                    recent_keys.setdefault(int(y), []).append(u)
        for y in cands:
            seen = [keys[y][j] for j, v in enumerate(cands[y]) if v[2]['i'] in recent_keys.get(y, [])]
            for j, v in enumerate(cands[y]):
                if v[2]['i'] in recent:
                    v[2]['nice'] = False
                    loss = 3 * (RECENT_DAYS + 1 - recent[v[2]['i']]) / RECENT_DAYS
                    cands[y][j] = (v[0] - loss, v[1] - loss, v[2])
                elif any(same_caption(keys[y][j], k) for k in seen):
                    cands[y][j] = (v[0] - .5, v[1] - .5, v[2])
    for y, want in PICKS.get(seed, {}).items():   # Darpan's own choice for a year wins outright
        for j, v in enumerate(cands.get(int(y), [])):
            if want.lower() in (v[2].get('c') or '').lower():
                cands[int(y)][j] = (v[0] + 100, v[1] + 100, v[2])

    def with_crop(v, k):
        """The photo as it would be shown in that mode: 'close' tight on the head, 'frame' filling the frame,
        'whole' the entire photo (a special wide moment, or no face found)."""
        x = v[2]
        if not x['face']:
            return dict(x, crop='whole')
        if k == 0:
            return dict(x, crop='close' if x['close_ok'] else 'frame')
        return dict(x, crop='frame' if x['keep'] >= ACTION_KEEP else 'whole')

    # which years are close darshans: every third year when it has a good close up, then more until about a third
    # of the years are close ups (Darpan, 18 Oct 2026: he wanted 4 or 5 more faces on a 27 year day), spread out
    has_nice = {y: any(v[2]['nice'] for v in cands[y]) for y in years}
    has_close = {y: any(v[2]['close_ok'] for v in cands[y]) for y in years}
    modes = {y: 1 if has_nice[y] and not (i % 3 == 1 and has_close[y]) else (0 if has_close[y] else 1) for i, y in enumerate(years)}
    target = round(len(years) * CLOSE_SHARE)
    best_close = {y: max(v[0] for v in cands[y]) for y in years}
    while sum(1 for y in years if modes[y] == 0) < target:
        spare = [y for y in years if modes[y] == 1 and has_close[y]]
        if not spare:
            break
        def lonely(y):   # prefer a year whose neighbours are action shots, so the faces are spread out
            i = years.index(y)
            return sum(1 for j in (i - 1, i + 1) if 0 <= j < len(years) and modes[years[j]] == 0)
        modes[min(spare, key=lambda y: (lonely(y), -best_close[y]))] = 0
    picked, used = [], []
    WORKINGS.clear()
    for i, y in enumerate(years):
        k = modes[y]
        ranked = sorted(cands[y], key=lambda v: -v[k])
        if any(v[2]['face'] for v in ranked):   # photos where Bapa is recognised always come before ones where he isn't
            ranked = [v for v in ranked if v[2]['face']]
            if k == 1:   # only really nice action shots count as action; the rest of the year's photos follow as close ups
                ranked = [v for v in ranked if v[2]['nice']] + [v for v in sorted(ranked, key=lambda v: -v[0]) if not v[2]['nice']]
        w = dict(year=y, mode='close darshan' if k == 0 else 'doing something', rows=[], pick=None)
        for v in ranked:
            mode = 0 if (k == 0 or not v[2]['nice']) else 1
            x = with_crop(v, mode)
            key = caption_key(caption(x))
            if w['pick'] is None and not any(same_caption(key, u) for u in used):
                picked.append(x); used.append(key); w['pick'] = x
                w['rows'].append((v[mode], x, 'chosen'))
            elif len(w['rows']) < 5:
                w['rows'].append((v[mode], x, 'repeats an earlier caption' if w['pick'] is None else ''))
        WORKINGS.append(w)
    if len(picked) < 5:   # too few left once repeats are skipped: fall back to the plain best per year
        picked = [with_crop(sorted(cands[y], key=lambda v: -v[1])[0], 1) for y in years]
    return picked


def crop_to(im, face, w, h, mode='frame', at=.38):
    """A w:h window on the photo. 'frame': fills the frame around Bapa (face `at` of the way down).
    'close': a tight darshan, his head and shoulders filling the frame. 'whole', or no recognised face:
    the entire photo, softened into its own colours at the edges. His whole head stays in view in every mode."""
    iw, ih = im.size
    if not face or mode == 'whole':
        fill = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(14))
        fill = Image.blend(fill, Image.new('RGB', (w, h), MAROON_OUT), .3)
        whole = im.copy(); whole.thumbnail((w, h), Image.LANCZOS)
        fill.paste(whole, ((w - whole.width) // 2, (h - whole.height) // 2))
        return fill
    fx, fy, fw, fh = face
    cw, ch = (ih * w / h, ih) if iw / ih > w / h else (iw, iw * h / w)
    if mode == 'close':   # the face about 30% of the window's height, never bigger than the photo allows
        ch = min(ch, fh / (.38 if w > h else .30)); cw = min(cw, ch * w / h); ch = cw * h / w   # a wide frame is cropped tighter
    head = (fx - .35 * fw, fy - .5 * fh, fx + 1.35 * fw, fy + 1.4 * fh)    # top of the head (the detector's box starts at the brow) down to the chin and neck
    if head[3] - head[1] > ch * .98 or head[2] - head[0] > cw * .98:   # a wide window on a close portrait: show the whole photo
        return crop_to(im, None, w, h)
    x0, y0 = fx + fw / 2 - cw / 2, fy + fh / 2 - ch * ((.42 if h >= w else .36) if mode == 'close' else at)   # less dead space above his head in a wide frame
    y0 = max(y0, head[3] - ch); y0 = min(y0, head[1])                        # never slice through the head
    y0 = max(y0, head[1] - ch * (.07 if mode == 'close' else .14))            # and not much dead space above it (Darpan, 18 Oct 2026)
    x0 = min(max(0, x0), iw - cw); y0 = min(max(0, y0), ih - ch)
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- drawing

def diamond(dr, cx, cy, r, fill):
    dr.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


IVORY_TOP, IVORY_BOTTOM, IVORY_EDGE = (248, 242, 228), (234, 223, 200), (196, 178, 146)
YEAR_C2, PLACE_C2 = (96, 20, 32), (88, 34, 34)
garamond = lambda s, w=700: font(f'eb-garamond-latin-{w}-normal', s)
arimo_bold = lambda s: font('arimo-latin-700-normal', s)


def gold_text(img, xy, text, f, shadow=True, top=(255, 226, 150), bottom=(206, 152, 64)):
    """Text filled with a soft top to bottom gold gradient, over a faint dark shadow."""
    x, y = round(xy[0]), round(xy[1])
    box = [round(v) for v in ImageDraw.Draw(img).textbbox((x, y), text, font=f)]
    w, h = box[2] - box[0] + 40, box[3] - box[1] + 40
    mask = Image.new('L', (w, h), 0); ImageDraw.Draw(mask).text((x - box[0] + 20, y - box[1] + 20), text, font=f, fill=255)
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh.putalpha(mask.point(lambda v: v * 170 // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(7)); img.paste(sh, (box[0] - 20, box[1] - 20 + 4), sh)
    grad = Image.new('RGB', (w, h)); gd = ImageDraw.Draw(grad)
    for j in range(h):
        t = min(1, max(0, (j - 20) / max(1, h - 40)))
        gd.line((0, j, w, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    img.paste(grad, (box[0] - 20, box[1] - 20), mask)


def spaced(dr, text, f, track):
    return sum(dr.textlength(ch, font=f) for ch in text) + track * (len(text) - 1)


def draw_spaced(dr, x, y, text, f, track, fill):
    for ch in text:
        dr.text((x, y), ch, font=f, fill=fill); x += dr.textlength(ch, font=f) + track


def thin_rule(dr, y, x0, x1, fade_to_left):
    for xp in range(int(x0), int(x1)):
        t = (xp - x0) / (x1 - x0); a = t if fade_to_left else 1 - t
        dr.line((xp, y, xp, y + 1), fill=tuple(round(m + (g - m) * a) for m, g in zip(MAROON_OUT, GOLD_SOFT)))


def header(img, title, subtitle, compact=False):
    """Big bold gold title, then a smaller spaced capital line between two thin gold rules.
    compact: the same, a little smaller, fitting above cards that start at y=156."""
    dr = ImageDraw.Draw(img)
    tf = garamond(98 if compact else 118)
    tw = dr.textlength(title, font=tf)
    gold_text(img, ((W - tw) / 2, -2 if compact else 4), title, tf)
    sf, track = garamond(32 if compact else 40, 600), 9
    sub = subtitle.upper()
    sw = spaced(dr, sub, sf, track)
    sy = 114 if compact else 142
    draw_spaced(dr, (W - sw) / 2, sy, sub, sf, track, (240, 214, 160))
    mid = sy + 24
    thin_rule(dr, mid, (W - sw) / 2 - 50 - 330, (W - sw) / 2 - 50, True)
    thin_rule(dr, mid, (W + sw) / 2 + 50, (W + sw) / 2 + 50 + 330, False)


def header_one(img, title, subtitle):
    """'18 October in Bapa\u2019s Diary' as one gold title, a thin gold rule either side running through the middle of the letters."""
    dr = ImageDraw.Draw(img)
    tf = garamond(84)
    text = f'{title} {subtitle}'
    tw = dr.textlength(text, font=tf)
    top = 30
    gold_text(img, ((W - tw) / 2, top), text, tf)
    box = dr.textbbox(((W - tw) / 2, top), 'OB', font=tf)                   # capitals: the rule sits at their middle
    mid = (box[1] + box[3]) / 2
    pad, rule = 44, 300
    thin_rule(dr, mid, (W - tw) / 2 - pad - rule, (W - tw) / 2 - pad, True)
    thin_rule(dr, mid, (W + tw) / 2 + pad, (W + tw) / 2 + pad + rule, False)


def header_line(img, title, subtitle):
    """One line across the top: the title in the middle, 'IN BAPA'S DIARY' to its left and the footer line to its
    right, each between the title and a short gold rule, so the photos get the height instead of a footer."""
    dr = ImageDraw.Draw(img)
    tf, sf, ff = garamond(92), garamond(34, 600), garamond(34, 500)
    track, rule, pad = 7, 120, 48
    sub = subtitle.upper()
    tw, sw, fw = dr.textlength(title, font=tf), spaced(dr, sub, sf, track), dr.textlength(FOOTER, font=ff)
    base = 120
    gold_text(img, ((W - tw) / 2, base - 92 * .95 + 8), title, tf)
    mid = base - 12
    sx = (W - tw) / 2 - pad - sw                                           # subtitle ends a pad before the title
    draw_spaced(dr, sx, base - sf.getmetrics()[0] - 1, sub, sf, track, (240, 214, 160))
    thin_rule(dr, mid, sx - pad - rule, sx - pad, True)
    diamond(dr, sx - pad - rule - 14, mid + 1, 5, GOLD)
    fx = (W + tw) / 2 + pad                                                # footer starts a pad after the title
    dr.text((fx, base), FOOTER, font=ff, fill=(226, 184, 104), anchor='ls')
    thin_rule(dr, mid, fx + fw + pad, fx + fw + pad + rule, False)
    diamond(dr, fx + fw + pad + rule + 14, mid + 1, 5, GOLD)


def footer(img, small=False, history=None):
    if history:   # 'On this day in 1959  Yogiji Maharaj sets off ...' along the bottom, the project's name small at the right
        return history_footer(img, history)
    dr = ImageDraw.Draw(img)
    f = garamond(26 if small else 40, 500)
    w = dr.textlength(FOOTER, font=f)
    y = H - 42 if small else H - 88
    dr.text(((W - w) / 2, y), FOOTER, font=f, fill=(226, 184, 104))
    box = dr.textbbox(((W - w) / 2, y), 'Dp', font=f)                      # the rules run through the middle of the letters
    mid = (box[1] + box[3]) / 2 - f.size * .06
    thin_rule(dr, mid, (W - w) / 2 - 40 - 220, (W - w) / 2 - 40, True)
    thin_rule(dr, mid, (W + w) / 2 + 40, (W + w) / 2 + 40 + 220, False)
    diamond(dr, (W - w) / 2 - 28, mid + 1, 5, GOLD); diamond(dr, (W + w) / 2 + 28, mid + 1, 5, GOLD)


def history_footer(img, ev):
    """One gold line along the bottom from the Today in BAPS History channel (Darpan, 19 Oct 2026, idea 1)."""
    dr = ImageDraw.Draw(img)
    lead, text = f'On this day in {ev["date"][:4]}', ev['line']
    lf, tf, ff = garamond(30, 700), garamond(30, 500), garamond(24, 500)
    fw = dr.textlength(FOOTER, font=ff)
    room = W - 2 * (fw + 90)                                               # the line stays clear of the name at the right
    while dr.textlength(lead + '   ' + text, font=tf) > room and tf.size > 22:
        lf, tf = garamond(lf.size - 1, 700), garamond(tf.size - 1, 500)
    lw, tw = dr.textlength(lead + '   ', font=lf), dr.textlength(text, font=tf)
    x, y = (W - lw - tw) / 2, H - 15
    dr.text((x, y), lead, font=lf, fill=GOLD, anchor='ls')
    dr.text((x + lw, y), text, font=tf, fill=CAPTION_GOLD, anchor='ls')
    mid = y - tf.size * .33
    diamond(dr, x - 26, mid, 5, GOLD); diamond(dr, x + lw + tw + 26, mid, 5, GOLD)
    dr.text((W - 30, y), FOOTER, font=ff, fill=(226, 184, 104), anchor='rs')


def background():
    small = Image.new('RGB', (64, 64)); px = small.load()
    inner, outer = (66, 16, 28), (22, 5, 10)
    for j in range(64):
        for i in range(64):
            d = min(1, (((i - 32) / 32 / .85) ** 2 + ((j - 64 * .45) / 32 / .95) ** 2) ** .5)
            px[i, j] = tuple(round(a + (b - a) * d) for a, b in zip(inner, outer))
    img = small.resize((W, H), Image.BICUBIC)
    noise = Image.effect_noise((W // 2, H // 2), 10).resize((W, H)).convert('L')     # faint paper grain, stops banding
    img = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), img, noise.point(lambda v: max(0, v - 118) // 3))
    m = Image.new('L', (78, 36), 0); p = m.load()
    for j in range(36):
        for i in range(78):
            dd = (((i - 38.5) / 39) ** 2 + ((j - 17.5) / 18) ** 2) ** .5
            p[i, j] = int(140 * max(0, dd - .7) / .6)
    img.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 0), m.resize((W, H), Image.BICUBIC))
    return jali_edge(warm_glow(img))


def warm_glow(img):
    """Soft lamp light from above the title, and a fainter warmth along the bottom."""
    sw, sh = W // 8, H // 8
    yy, xx = np.mgrid[0:sh, 0:sw]
    top = np.clip(1 - np.hypot((xx - sw / 2) / (sw * .42), (yy - sh * .06) / (sh * .42)), 0, 1) ** 1.6
    bottom = np.clip(1 - np.hypot((xx - sw / 2) / (sw * .55), (yy - sh * 1.02) / (sh * .30)), 0, 1) ** 1.6 * .45
    light = np.array([132, 74, 34]) * np.clip(top + bottom, 0, 1)[..., None] * GLOW
    return ImageChops.add(img, Image.fromarray(light.astype('uint8')).resize((W, H), Image.BICUBIC))


def jali_edge(img, R=54):
    """The four petal lattice of a carved mandir jali (overlapping circles), faint and only near the edges."""
    k = 2
    m = Image.new('L', (W * k, H * k), 0); d = ImageDraw.Draw(m)
    for cy in range(-R, H + R, R):
        for cx in range(-R, W + R, R):
            d.ellipse(((cx - R) * k, (cy - R) * k, (cx + R) * k, (cy + R) * k), outline=255, width=3)
    xs = np.minimum(np.arange(W), W - 1 - np.arange(W)); ys = np.minimum(np.arange(H), H - 1 - np.arange(H))
    fade = np.clip(1 - np.minimum(xs[None, :], ys[:, None]) / 190, 0, 1) ** 1.3          # gone before the photos
    mask = ImageChops.multiply(m.resize((W, H), Image.LANCZOS), Image.fromarray((fade * 255 * JALI).astype('uint8')))
    img.paste(Image.new('RGB', (W, H), (160, 84, 74)), (0, 0), mask)
    return img


NAME = r"(?:(?:H\.?\s?H\.?|Param Pujya|P\.?\s?P\.?)\s+)?(?:Pramukh Swami(?: Maharaj)?|Mahant Swami(?: Maharaj)?|Swamishri|Bapa)"


OTHERS = r"(?:(?:Pujya|Sadguru|Shri|Param Pujya)\s+)*[A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)*(?:\s+Swami)?|(?i:(?:Senior\s+)?(?:swamis|sadhus|devotees|bhaktas|children|youths|kishores|students|volunteers|karyakars|sadhaks)(?:,? (?:and|parshads|sadhaks|swamis|devotees|bhaktas)+)*)(?:\s+from\s+[\w ,]+?)?|An?\s+\w+(?:\s+from\s+[\w ,]+?)?"
ABOUT_BAPA = [   # captions about someone else and Bapa, turned round so they say what Bapa does
    (rf"^({OTHERS}) (?:honou?rs?|garlands?) Swamishri(?: with (?:a|an) ([\w ,\-]+))?$", lambda m: f"Receives {('a ' + m.group(2)) if m.group(2) else 'a garland'} from {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:greets?|welcomes?) Swamishri.*$", lambda m: f"Greets {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:presents?|offers?) (?:a |an )?[\w ,\-]*?(?:and|to) hono?u?rs? Swamishri.*$", lambda m: f"Honoured by {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) hono?u?rs? Swamishri.*$", lambda m: f"Honoured by {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) sings? (thal|kirtans?|dhun|bhajans?)$", lambda m: f"Listens to {lower_group(m.group(1))} sing {m.group(2)}"),
    (rf"^({OTHERS}) (?:offers?|presents?) (?:a |an )?prayers? (?:to|before) Swamishri$", lambda m: f"Listens to a prayer from {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:prays?) before Swamishri$", lambda m: f"Listens to a prayer from {m.group(1)}"),
    (rf"^({OTHERS}) (?:doing|engrossed in|in) (?:the )?(?:unique )?(?:darshan of Swamishri|Swamishri's (?:puja )?darshan|Swamishri's puja)$", lambda m: f"Gives darshan to {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) recites? (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Listens to {lower_group(m.group(1))} recite {m.group(2)}"),
    (rf"^({OTHERS}) sings? (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Listens to {lower_group(m.group(1))} sing {m.group(2)}"),
    (rf"^({OTHERS}) (plays?|sings?|swings?) (.+?) with Swamishri$", lambda m: f"{re.sub('s$', '', m.group(2)).capitalize()}s {m.group(3)} with {m.group(1)}"),
    (rf"^({OTHERS}) (?:performs?|presents?|recites?|sings?) (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Watches {lower_group(m.group(1))} perform {m.group(2)}"),
]


def lower_group(g):
    """'Swamis' or 'A devotee' read in lower case mid sentence; names ('Pujya Kothari Swami') stay as they are."""
    return g[0].lower() + g[1:] if re.match(r'(?i)(senior |an? )?(swamis|sadhus|devotees|bhaktas|children|youths|kishores|students|volunteers|karyakars|sadhaks|devotee|bhakta|youth|child|swami|sadhak)\b', g) else g


def about_bapa(c):
    """'Pujya Kothari Swami plays dandiya with Swamishri' becomes 'Plays dandiya with Pujya Kothari Swami'."""
    for pat, fix in ABOUT_BAPA:
        m = re.match(pat, c)
        if m:
            return fix(m)
    return c


def bapa_is_subject(c):
    """False when the caption is about someone else ('Swamis sing kirtans in Swamishri's puja')."""
    c = about_bapa(re.sub(r'\s+', ' ', c or '').strip())
    return not re.search(r"\bSwamishri\b|Bapa\b", c) or bool(re.match(rf'^{NAME}', c)) or c[:1].islower()


def shorter_versions(text):
    """Ever shorter readings of a caption, cut at a natural break: 'Inaugurates DVD of Mystic India movie including ...'
    gives 'Inaugurates DVD of Mystic India movie', then 'Inaugurates DVD'."""
    t = re.sub(r'\s*\([^)]*\)', '', text)
    cuts = sorted({m.start() for m in re.finditer(
        r",| - | in the | in | at | during | for | including | titled | about | to be | after | before | on his | as | while | from | by | of the | of | "
        r"with | on the | on | to the | to | and | that | who | which | where | via | through | along | near | under | inside | outside | towards | into | '", t)}, reverse=True)
    out = [t] if t != text else []
    for i in cuts:
        cand = t[:i].rstrip(" ,;:-")
        quotes = len(re.findall(r"(?<![A-Za-z])'|'(?![A-Za-z])", cand))
        if len(cand.split()) >= 2 and quotes % 2 == 0 and cand.split()[-1].lower() not in SHORT_END and cand not in out:
            out.append(cand)
    return out


SHORT_END = {'the', 'a', 'an', 'of', 'and', 'to', 'with', 'his', 'her', 'their', 'on', 'in', 'at', 'for', 'by', 'from', 'that', 'two', 'new',
             'who', 'which', 'where', 'via', 'as', 'while', 'during', 'before', 'after', 'is', 'are', 'was', 'other', 'various', 'some'}
MONTH = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?'
SHORT_WORDS = [   # a few long phrases said shorter in the website's own words, so a caption fits without trailing off
    (r'\bvideo conference\b', 'video'), (r'\bBAPS Shri Swaminarayan Mandir(s?)\b', r'mandir\1'), (r'\bShri Swaminarayan Mandir\b', 'mandir'),
    (r'\bmurti-pratishtha (?:ceremony|rituals?)\b', 'murti-pratishtha'),
]


def tidy(c):
    """Small clean ups of the website's caption: the date (it is always this day), 'the the', Mr and Mrs."""
    c = re.sub(rf'[\s,]*(?:on |dated )?\b\d{{1,2}}(?:st|nd|rd|th)? {MONTH}(?: \d{{4}})?\s*$', '', c)   # 'Doing mala, 18 Oct 2016'
    c = re.sub(rf'[\s,]*(?:on |dated )?\b{MONTH} \d{{1,2}}(?:st|nd|rd|th)?(?:,? \d{{4}})?\s*$', '', c)   # 'on October 18, 2016'
    c = re.sub(r'\b(the|a|an|of|to|in|on|and) \1\b', r'\1', c, flags=re.I)
    c = re.sub(r'\b(?:Mr|Mrs|Ms|Dr)\.? (?=[A-Z])', '', c)
    c = re.sub(r'\b([Dd])evotee(s?)\b', lambda m: ('B' if m.group(1) == 'D' else 'b') + 'hakta' + m.group(2), c)   # satsang word (Darpan, 18 Oct 2026)
    return re.sub(r'\s+', ' ', c).strip(' ,;:')


def summarise(c):
    """The same caption in fewer words: 'Discourses with sadhus via video conference' becomes 'Discourses with sadhus via video'."""
    for pat, rep in SHORT_WORDS:
        c = re.sub(pat, rep, c)
    return c


def caption(x):
    """The caption without the name repeated on every card: 'Swamishri blesses all' becomes 'Blesses all'.
    Where dropping the name wouldn't read well ('Swamishri's divine gestures', 'Sadhus honour Swamishri'),
    the name becomes 'Bapa'."""
    c = tidy(re.sub(r'\s+', ' ', x.get('c') or '').strip())
    c = about_bapa(c)
    m = re.match(rf'^{NAME}[\s,]+(.+)$', c)
    if m and not re.match(r"(and|with|along|together|'s|’s)\b", m.group(1), re.I):
        c = m.group(1)[0].upper() + m.group(1)[1:]
    c = re.sub(NAME, 'Bapa', c)
    return c


def place(x):
    return re.sub(r'\s*\(.*?\)', '', (x.get('p') or '').split(',')[0]).strip()


def wrap(d, text, f, maxw, lines, shorten=True, min_words=0):
    """Up to `lines` lines no wider than maxw; whatever doesn't fit ends in an ellipsis.
    min_words: a natural cut that leaves fewer words than this is not used (so 'Sanctifies water' never stands for a sentence)."""
    words, out = text.split(), []
    while words and len(out) < lines:
        line = words.pop(0)
        if '-' in line[1:-1] and d.textlength(line, font=f) > maxw:   # 'mantra-pushpanjali' breaks after its hyphen
            head, _, tail = line.rpartition('-')
            while '-' in head[1:] and d.textlength(head + '-', font=f) > maxw:
                head, _, more = head.rpartition('-'); tail = more + '-' + tail
            line = head + '-'; words.insert(0, tail)
        while words and d.textlength(line + ' ' + words[0], font=f) <= maxw:
            line += ' ' + words.pop(0)
        out.append(line)
    cut = bool(words) or any(d.textlength(l, font=f) > maxw for l in out)
    if cut and shorten:   # say less rather than trail off: say it shorter, or cut the caption at a natural break so it fits
        short = summarise(text)
        for t in ([short] if short != text else []) + shorter_versions(short):
            if len(t.split()) < min_words:
                continue
            fits = wrap(d, t, f, maxw, lines, shorten=False)
            if not fits[-1].endswith('…'):
                return fits
    if cut and out:
        last = out[-1]
        while last and d.textlength(last + '…', font=f) > maxw:
            last = last[:-1]
        out[-1] = last.rstrip(' ,;:') + '…'
    return out


CAPTION_IVORY, CAPTION_GOLD = (250, 241, 222), (240, 214, 160)


class Card:
    """Ivory polaroid: thin border, nearly square photo, year and place in the bottom band.
    style: None (live look), 'B' caption on a soft band over the photo, 'C' year and caption in the band,
    'D' a small number on the photo for the caption list underneath ('A' draws its caption outside the card)."""
    def __init__(self, pw, aspect=1.08, band=.32, style=None):
        self.PW, self.PH = round(pw), round(pw * aspect)
        self.B, self.BB = max(6, round(pw * .045)), round(pw * band)
        self.CW, self.CH = self.PW + 2 * self.B, self.PH + self.B + self.BB
        self.style = style

    def make(self, x, num=None):
        PW, PH, B, BB, CW, CH = self.PW, self.PH, self.B, self.BB, self.CW, self.CH
        card = Image.new('RGBA', (CW, CH)); d = ImageDraw.Draw(card)
        for j in range(CH):
            t = j / CH
            d.line((0, j, CW, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)) + (255,))
        d.rectangle((0, 0, CW - 1, CH - 1), outline=IVORY_EDGE, width=1)
        card.paste(crop_to(x['im'], x['face'], PW, PH, x.get('crop', 'frame')), (B, B))
        if self.style == 'B' and caption(x):
            self.soft_band(card, caption(x))
        if self.style == 'D' and num is not None:
            r = PW * .085; cx, cy = B + r + PW * .035, B + r + PW * .035
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(96, 20, 32), outline=(226, 184, 104), width=max(1, round(PW * .008)))
            nf = garamond(r * 1.25, 700)
            d.text((cx, cy + r * .06), str(num), font=nf, fill=GOLD, anchor='mm')
        d.rectangle((B - 1, B - 1, B + PW, B + PH), outline=(150, 130, 100), width=1)
        if self.style == 'C':
            return self.year_and_caption(card, d, x)
        if self.style == 'E':
            return self.year_caption_place(card, d, x)
        if self.style == 'G':
            return self.quote_then_year(card, d, x)
        yf, yt = garamond(PW * .16, 600), str(x['y'])
        pl = place(x).upper()
        size, track = PW * .08, PW * .014
        while size > PW * .04 and spaced(d, pl, arimo_bold(size), track) > CW - 2 * B - 4:
            size -= 1
        pf = arimo_bold(size)
        yb = d.textbbox((0, 0), yt, font=yf, anchor='ls'); ab = d.textbbox((0, 0), 'A', font=pf, anchor='ls')
        yh, ph, gap = -yb[1], (-ab[1]) if pl else 0, PW * .055 if pl else 0
        top = B + PH + (BB - (yh + gap + ph)) / 2 - B * .2
        d.text(((CW - d.textlength(yt, font=yf)) / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ls')
        draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, top + yh + gap + ph - pf.getmetrics()[0], pl, pf, track, PLACE_C2)
        return card

    def soft_band(self, card, text):
        """Caption in ivory over a soft dark fade across the bottom of the photo."""
        PW, PH, B = self.PW, self.PH, self.B
        d = ImageDraw.Draw(card); f = garamond(PW * .085, 500)
        lines = wrap(d, text, f, PW * .92, 2)
        lh = PW * .098
        h = round(len(lines) * lh + PW * .16)
        fade = Image.new('RGBA', (PW, h)); fd = ImageDraw.Draw(fade)
        for j in range(h):
            t = j / h
            fd.line((0, j, PW, j), fill=(30, 8, 12, round(205 * min(1, t / .55) ** 1.4)))
        card.alpha_composite(fade, (B, B + PH - h))
        y = B + PH - PW * .045 - (len(lines) - 1) * lh
        for i, line in enumerate(lines):
            d.text((B + PW / 2, y + i * lh), line, font=f, fill=CAPTION_IVORY, anchor='ms')

    def year_and_caption(self, card, d, x):
        """Year, then the caption in the polaroid band (the place when there's no caption)."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        yf, yt = garamond(PW * .14, 600), str(x['y'])
        cf = garamond(PW * .08, 500); lh = PW * .093
        lines = wrap(d, caption(x) or place(x), cf, CW - 2 * B - PW * .04, 3)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        block = yh + PW * .05 + len(lines) * lh
        top = B + PH + (BB - block) / 2
        d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
        for i, line in enumerate(lines):
            d.text((CW / 2, top + yh + PW * .05 + (i + .8) * lh), line, font=cf, fill=PLACE_C2, anchor='ms')
        return card

    def year_caption_place(self, card, d, x):
        """Style E: year, caption, then the place in small spaced capitals, all in the polaroid band."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        yf, yt = garamond(PW * .13, 600), str(x['y'])
        cf = garamond(PW * .078, 500); lh = PW * .09
        pf, track = arimo_bold(PW * .05), PW * .012
        pl = place(x).upper()
        lines = wrap(d, caption(x), cf, CW - 2 * B - PW * .04, 2)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1] if pl else 0
        block = yh + PW * .04 + len(lines) * lh + (PW * .04 + ph if pl else 0)
        top = B + PH + (BB - block) / 2
        d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
        y = top + yh + PW * .04
        for i, line in enumerate(lines):
            d.text((CW / 2, y + (i + .8) * lh), line, font=cf, fill=PLACE_C2, anchor='ms')
        y += len(lines) * lh + PW * .04 + ph
        if pl:
            draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, y - pf.getmetrics()[0], pl, pf, track, (150, 96, 80))
        return card

    def quote_then_year(self, card, d, x):
        """Style G: the caption leads, in quotes, with the year and place underneath in small capitals."""
        PW, PH, B, BB, CW = self.PW, self.PH, self.B, self.BB, self.CW
        cf = garamond(PW * .084, 500); lh = PW * .097
        pf, track = arimo_bold(PW * .056), PW * .012
        c = caption(x)
        lines = wrap(d, f'“{c}”' if c else '', cf, CW - 2 * B - PW * .04, 3)
        tag = f'{x["y"]}  ·  {place(x).upper()}' if place(x) else str(x['y'])
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1]
        block = len(lines) * lh + (PW * .05 if lines else 0) + ph
        top = B + PH + (BB - block) / 2
        for i, line in enumerate(lines):
            d.text((CW / 2, top + (i + .8) * lh), line, font=cf, fill=YEAR_C2, anchor='ms')
        y = top + len(lines) * lh + (PW * .05 if lines else 0) + ph
        draw_spaced(d, (CW - spaced(d, tag, pf, track)) / 2, y - pf.getmetrics()[0], tag, pf, track, PLACE_C2)
        return card

    def hang(self, card):
        sh = Image.new('RGBA', (self.CW + 80, self.CH + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((40, 48, self.CW + 40, self.CH + 46), fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(13)); sh.alpha_composite(card, (40, 40))
        return sh


PEG = 'gloss'   # how the pegs on the cord are drawn: round varnished wood (Darpan's choice, 17 Oct 2026); 'flat' and 'bevel' are the others


def peg(img, cx, cy, s, look=None, short=1.0):
    look = look or PEG                                      # short < 1 makes a stubbier peg (the wide cards, Darpan 18 Oct 2026)
    if look == 'flat':
        dr = ImageDraw.Draw(img)
        w, h = 9 * s, 30 * s
        dr.rounded_rectangle((cx - w, cy - h * .45, cx + w, cy + h * .55), radius=3 * s, fill=(138, 94, 58), outline=(84, 52, 30), width=max(1, round(2 * s)))
        dr.line((cx - w + 3 * s, cy - h * .45 + 3 * s, cx - w + 3 * s, cy + h * .55 - 3 * s), fill=(176, 128, 84), width=max(1, round(2 * s)))
        dr.line((cx, cy - h * .4, cx, cy + h * .5), fill=(84, 52, 30), width=1)
        return
    # a round wooden clothes peg: soft rounded top, lit from the top left like the cards, a small dark spring and a soft shadow
    K = 4                                                   # drawn four times bigger, then shrunk, for smooth edges
    w, h = 10 * s * K * (.6 + .4 * short), 35 * s * K * short
    pw_, ph_ = int(2 * w + 16 * s * K), int(h + 16 * s * K)
    ox, oy = 6 * s * K, 4 * s * K                           # where the peg sits inside its little canvas
    yy, xx = np.mgrid[0:ph_, 0:pw_].astype(np.float32)
    v = (yy - oy) / h                                       # 0 at the top of the peg, 1 at the bottom
    # half width down the peg: the handle, a little waist where the spring sits, then the jaws taper slightly
    half = w * np.interp(v, (0, .38, .43, .5, .55, 1), (1, 1, .9, .9, .96, .86))
    dx = np.abs(xx - ox - w)
    rt, rb = w * .55, w * .25                               # softly rounded top corners, small ones at the jaws
    ty, by_ = yy - oy, oy + h - yy
    lim = np.where(ty < rt, half - rt + np.sqrt(np.clip(rt ** 2 - (rt - ty) ** 2, 0, None)), half)
    lim = np.where(by_ < rb, half - rb + np.sqrt(np.clip(rb ** 2 - (rb - by_) ** 2, 0, None)), lim)
    inside = (dx <= lim) & (v >= 0) & (v <= 1)
    mask = Image.fromarray((inside * 255).astype(np.uint8))
    # cylinder shading across the peg, a little lighter on the left
    n = np.clip((xx - ox - w) / half, -1, 1)
    light = np.sqrt(1 - n ** 2) * .5 + (-n) * .18 + .62
    base = np.array((150, 104, 64) if look == 'bevel' else (140, 90, 52), np.float32)
    grain = 1 + .035 * np.sin(xx / (K * s) * 1.7 + 3 * np.sin(yy / (K * s * 9)))
    col = base[None, None] * (light * grain)[..., None]
    if look == 'gloss':                                     # varnished: a soft bright streak and a little more colour
        streak = np.exp(-((n + .45) / .13) ** 2) * (.45 + .55 * (1 - v))
        col += (streak * 95)[..., None]
    else:                                                   # carved: a bright bevel along the left and top, dark along the right
        edge = np.clip(1 - (lim - dx) / (w * .16), 0, 1)
        top = np.clip(1 - ty / (w * .3), 0, 1)
        col += (np.maximum(edge * np.where(n < 0, 1, -.8), top) * 50)[..., None]
    sp = inside & (v > .42) & (v < .51)                                # the spring
    col[sp] = (col[sp] * .35 + np.array((60, 50, 44)) * .65) * (1 + .25 * np.sin((yy[sp] - oy) / (K * s) * 2.2))[..., None]
    split = inside & (v > .56) & (np.abs(xx - ox - w) < K * s * .5)   # the gap between the two jaws
    col[split] *= .55
    rgb = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8))
    outline = mask.filter(ImageFilter.MaxFilter(3)); edge_ring = ImageChops.subtract(outline, mask)
    piece = Image.new('RGBA', (pw_, ph_), (0, 0, 0, 0))
    shadow = Image.new('RGBA', (pw_, ph_), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 120), (int(3 * s * K), int(4 * s * K)), mask)
    piece.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(4 * s * K)))
    piece.paste((70, 42, 24, 255), (0, 0), outline)
    piece.paste(rgb, (0, 0), mask)
    piece = piece.resize((pw_ // K, ph_ // K), Image.LANCZOS)
    img.paste(piece, (int(cx - (ox + w) / K), int(cy - h * .45 / K - oy / K)), piece)


def caption_list(img, photos, y0, y1):
    """Style D: the numbered captions in three columns between the photos and the footer."""
    dr = ImageDraw.Draw(img)
    cols = 3; per = -(-len(photos) // cols)
    nf, cf = garamond(25, 700), garamond(25, 500)
    lh = min(36, (y1 - y0) / per)
    colw = (W - 2 * 120) / cols
    for i, x in enumerate(photos):
        c, r = divmod(i, per)
        xl, yb = 120 + c * colw, y0 + (r + .8) * lh
        lead = f'{i + 1}.'
        dr.text((xl + 30, yb), lead, font=nf, fill=GOLD, anchor='rs')
        yt = f'{x["y"]}'
        dr.text((xl + 42, yb), yt, font=nf, fill=(226, 184, 104), anchor='ls')
        tx = xl + 42 + dr.textlength(yt, font=nf) + 16
        text = wrap(dr, caption(x) or place(x), cf, xl + colw - 30 - tx, 1)
        dr.text((tx, yb), text[0] if text else '', font=cf, fill=CAPTION_GOLD, anchor='ls')


# style H with bigger frames: H2 narrower margins and two line captions, H3 one line captions and polaroids may overlap a little
LAYOUT = {'H2': dict(M=70, min_gap=14, row_gap=40, lines=2, cap=360, top=212, bottom=H - 100),
          'H3': dict(M=60, min_gap=-14, row_gap=34, lines=1, cap=360, top=210),
          'P': dict(M=40, min_gap=6, row_gap=26, lines=0, cap=400, top=212, bottom=H - 100),   # photos only, no captions, biggest frames
          'W': dict(M=60, min_gap=12, row_gap=30, lines=1, cap=400, top=205, bottom=H - 90, rows=3, aspect=.75, band=.26)}   # wide photos, three cords
FRAME_ASPECT = {'W': 1 / .75, 'W1': 1 / .74, 'W2': 1 / .9, 'W3': 1.5}   # photo width / height per style; the tall live cards work out at about .69 on a full day


def under_card(x, card, gap, f, lh, style, rnd):
    cf_size = f.size
    """Style F: a small ivory paper tag on a short thread under the polaroid.
    Style H: ivory caption on a soft dark plate under the polaroid."""
    probe = ImageDraw.Draw(Image.new('L', (1, 1)))
    if style == 'F':
        lines = wrap(probe, caption(x), f, card.CW * .86 - 20, 3)
        tw = max(probe.textlength(l, font=f) for l in lines) + 30
        th = len(lines) * lh + 18
        im = Image.new('RGBA', (int(tw) + 40, int(th) + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cx = im.width / 2
        d.line((cx, 0, cx, 26), fill=(170, 132, 78), width=2)                          # the thread
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((20, 30, 20 + tw, 30 + th), radius=6, fill=(0, 0, 0, 120))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
        d.rounded_rectangle((20, 24, 20 + tw, 24 + th), radius=6, fill=IVORY_TOP + (255,), outline=IVORY_EDGE)
        d.ellipse((cx - 4, 30, cx + 4, 38), fill=(150, 120, 90))                         # the hole
        for i, line in enumerate(lines):
            d.text((cx, 24 + 14 + (i + .8) * lh), line, font=f, fill=YEAR_C2, anchor='ms')
        return im.rotate(rnd.uniform(-2.5, 2.5), resample=Image.BICUBIC, expand=True), 2
    n = WIDE.get(style, LAYOUT.get(style, {})).get('lines', 3)
    text, maxw = caption(x), card.CW + min(gap, 30) - 40
    half = max(3, len(text.split()) * 2 // 3)
    # the whole caption first, then a touch smaller; only then a natural cut, keeping at least two thirds of it; a shorter cut last
    for shrink, extra, cut, keep in ((1, 0, False, 0), (.9, 0, False, 0), (.82, 0, False, 0), (.82, 0, True, half), (.82, 0, True, 0)):
        f2 = garamond(f.size * shrink, 500) if shrink < 1 else f
        lines = wrap(probe, text, f2, maxw, n + extra, shorten=cut, min_words=keep)
        if not lines[-1].endswith('…'):
            f = f2
            break
    else:
        lines = wrap(probe, text, f, maxw, n)
    lh = lh * f.size / cf_size
    # drawn four times bigger and shrunk: small text then keeps the font's true letter spacing (no 'Perform s') and smooth edges
    K = 4; fk = garamond(f.size * K, 500)
    tw = max(probe.textlength(l, font=fk) for l in lines) / K + 34
    th = len(lines) * lh + 16
    W4, H4 = round(tw) * K, round(th) * K
    im = Image.new('RGBA', (W4, H4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W4 - 1, H4 - 1), radius=int(H4 / 2) if len(lines) == 1 else 14 * K, fill=(30, 8, 12, 150))
    for i, line in enumerate(lines):
        d.text((W4 / 2, (8 + (i + .5) * lh) * K), line, font=fk, fill=CAPTION_IVORY, anchor='mm')
    return im.resize((round(tw), round(th)), Image.LANCZOS), 14


# wide polaroids (photos wider than tall) on three or four cords, so the width of the picture is used and little hangs below the cards
WIDE = {'W1': dict(rows=3, M=60, gap=16, ratio=.74, band='caption', row_gap=28, tilt=1.6),   # year, place and caption all in the ivory band
        'W2': dict(rows=3, M=44, gap=10, ratio=.9, band='yearline', pill=2, lines=2, row_gap=8, tilt=2.2, compact=True, one_title=True, lift=162, fill=True, straight=True),   # year and place in the band, caption on a pill below
        'W3': dict(rows=4, M=60, gap=18, ratio=2 / 3, band='none', row_gap=22, tilt=1.2)}    # thin ivory frames, year and caption over the photo


class WideCard(Card):
    """Ivory frame round a photo wider than it is tall. band: 'caption' (year, caption and place in the ivory band),
    'year' (year and place, as the live card) or 'none' (a thin frame, year and caption over the photo's foot)."""
    def __init__(self, pw, ratio, band):
        self.PW, self.PH, self.band = round(pw), round(pw * ratio), band
        self.B = max(6, round(pw * .035)) if band != 'none' else max(6, round(pw * .028))
        self.BB = {'caption': round(pw * .46), 'year': round(pw * .3), 'yearline': round(pw * .17), 'none': 0}[band]
        self.CW, self.CH = self.PW + 2 * self.B, self.PH + self.B + self.BB
        self.style = None

    def make(self, x, num=None):
        PW, PH, B, BB, CW, CH = self.PW, self.PH, self.B, self.BB, self.CW, self.CH
        card = Image.new('RGBA', (CW, CH)); d = ImageDraw.Draw(card)
        for j in range(CH):
            t = j / CH
            d.line((0, j, CW, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)) + (255,))
        d.rectangle((0, 0, CW - 1, CH - 1), outline=IVORY_EDGE, width=1)
        photo = crop_to(x['im'], x['face'], PW, PH, x.get('crop', 'frame'), at=.3)   # Bapa high in the frame, no dead space over his head
        card.paste(polish(photo), (B, B))
        d.rectangle((B - 1, B - 1, B + PW, B + PH), outline=(150, 130, 100), width=1)
        if self.band == 'none':
            self.foot_band(card, x)
            return card
        yf, yt = garamond(PW * .12 if self.band == 'caption' else PW * .15, 700 if self.band == 'yearline' else 600), str(x['y'])
        pl = place(x).upper()
        pf, track = arimo_bold(PW * .048 if self.band == 'caption' else PW * .06), PW * .012
        room = CW - 2 * B - 4 - (d.textlength(yt, font=yf) + PW * .035 if self.band == 'yearline' else 0)
        while pf.size > PW * .035 and spaced(d, pl, pf, track) > room:
            pf = arimo_bold(pf.size - 1)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1] if pl else 0
        if self.band == 'yearline':   # '2016  JUNAGADH' on one line, the year bigger, both sitting on the same baseline
            yw, pw_ = d.textlength(yt, font=yf), spaced(d, pl, pf, track)
            sp = PW * .035 if pl else 0
            x0 = (CW - (yw + sp + pw_)) / 2
            base = B + PH + BB / 2 + yh / 2                                   # the year's digits centred in the band
            d.text((x0, base), yt, font=yf, fill=YEAR_C2, anchor='ls')
            draw_spaced(d, x0 + yw + sp, base - (yh - ph) / 2 - pf.getmetrics()[0], pl, pf, track, PLACE_C2)   # the place centred on the year
            return card
        if self.band == 'year':
            gap = PW * .05 if pl else 0
            top = B + PH + (BB - (yh + gap + ph)) / 2 - B * .2
            d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
            draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, top + yh + gap + ph - pf.getmetrics()[0], pl, pf, track, PLACE_C2)
            return card
        cf = garamond(PW * .082, 500); lh = PW * .092
        lines = wrap(d, caption(x), cf, CW - 2 * B - PW * .03, 2)
        block = yh + PW * .035 + len(lines) * lh + (PW * .035 + ph if pl else 0)
        top = B + PH + (BB - block) / 2
        d.text((CW / 2, top + yh), yt, font=yf, fill=YEAR_C2, anchor='ms')
        y = top + yh + PW * .035
        for i, line in enumerate(lines):
            d.text((CW / 2, y + (i + .8) * lh), line, font=cf, fill=(70, 40, 40), anchor='ms')
        y += len(lines) * lh + PW * .035 + ph
        if pl:
            draw_spaced(d, (CW - spaced(d, pl, pf, track)) / 2, y - pf.getmetrics()[0], pl, pf, track, (150, 96, 80))
        return card

    def foot_band(self, card, x):
        """W3: one line over a soft dark fade at the foot of the photo: the year in gold, then the caption in ivory."""
        PW, PH, B = self.PW, self.PH, self.B
        d = ImageDraw.Draw(card)
        yf, cf = garamond(PW * .075, 700), garamond(PW * .062, 500)
        yt = str(x['y']); yw = d.textlength(yt, font=yf); sp = PW * .03
        lines = wrap(d, caption(x), cf, PW * .92 - yw - sp, 1)
        text = lines[0] if lines else ''
        h = round(PW * .17)
        fade = Image.new('RGBA', (PW, h)); fd = ImageDraw.Draw(fade)
        for j in range(h):
            fd.line((0, j, PW, j), fill=(30, 8, 12, round(205 * min(1, (j / h) / .55) ** 1.3)))
        card.alpha_composite(fade, (B, B + PH - h))
        tw = yw + (sp + d.textlength(text, font=cf) if text else 0)
        x0, y = B + (PW - tw) / 2, B + PH - PW * .04
        d.text((x0, y), yt, font=yf, fill=GOLD, anchor='ls')
        if text:
            d.text((x0 + yw + sp, y), text, font=cf, fill=CAPTION_IVORY, anchor='ls')


def compose_wide(photos, day, seed, style, history=None):
    """Three (W1, W2) or four (W3) cords of wide cards, every year on the day, sized to fill the picture."""
    lay = WIDE[style]
    rnd = random.Random(seed)
    img = background(); dr = ImageDraw.Draw(img)
    if lay.get('oneline'):
        header_line(img, f'{day.day} {day:%B}', 'in Bapa’s Diary')
    elif lay.get('one_title'):
        header_one(img, f'{day.day} {day:%B}', 'in Bapa’s Diary')
    else:
        header(img, f'{day.day} {day:%B}', 'in Bapa’s Diary', compact=lay.get('compact', False))
    n = len(photos)
    nrows = max(1, min(lay['rows'], -(-n // (5 if lay['rows'] == 3 else 6))))
    per = [n // nrows + (1 if i < n % nrows else 0) for i in range(nrows)]
    rows, k = [], 0
    for c in per:
        rows.append(photos[k:k + c]); k += c
    cols, M, gap, row_gap = per[0], lay['M'], lay['gap'], lay['row_gap']
    top_space, bottom_space = (156, H - 44 - SAG) if lay.get('oneline') or lay.get('compact') else (200, H - 96)
    if lay.get('lift'):   # the cord's lowest point (the middle) sits at the top line and its ends rise into the free corners beside the title
        top_space, bottom_space = lay['lift'], H - 46
    cf_a, lh_a = garamond(CAPTION_SIZE, 500), round(CAPTION_SIZE * 1.2)
    below = (lay.get('pill', 0) * lh_a + 22) if lay.get('pill') else 0
    probe = WideCard(100, lay['ratio'], lay['band'])
    pw_w = min(440, ((W - 2 * M - gap * (cols - 1)) / cols) / (probe.CW / 100))   # as wide as the row allows
    row_h = (bottom_space - top_space - (nrows - 1) * row_gap - nrows * below) / nrows
    ph = min(pw_w * lay['ratio'], row_h - (probe.CH - probe.PH) / 100 * pw_w)     # as tall as the rows allow
    pw = min(pw_w, ph / lay.get('min_ratio', .6))            # a photo is never wider than 16:9 ish, so shrink the card if it would be
    card = WideCard(pw, ph / pw, lay['band'])
    gap = min(60, (W - 2 * M - cols * card.CW) / max(1, cols - 1))
    pitch = card.CH + below + row_gap
    block = (nrows - 1) * pitch + card.CH + below
    if lay.get('fill') and nrows > 1:   # spare height goes between the rows rather than above and below them
        pitch += max(0, bottom_space - top_space - block) / (nrows - 1); block = (nrows - 1) * pitch + card.CH + below
    first = top_space + max(0, (bottom_space - top_space - block) / 2)
    s = card.PW / 220
    for r, row in enumerate(rows):
        y_top = first + r * pitch
        if lay.get('lift'):
            sag = lambda xp: y_top - 4 - SAG * (1 - 4 * (xp / W) * (1 - xp / W))              # lowest in the middle, ends higher
        else:
            sag = lambda xp: y_top - 4 + SAG * 4 * (xp / W) * (1 - xp / W)                    # the cord dips a little in the middle
        dr.line([(xp, sag(xp)) for xp in range(0, W + 1, 6)], fill=(170, 132, 78), width=2)
        later = []   # pegs and captions go on after the whole row, so a card swinging over its neighbour never hides them
        x0 = (W - (len(row) * card.CW + (len(row) - 1) * gap)) / 2
        for c, x in enumerate(row):
            cx = x0 + c * (card.CW + gap) + card.CW / 2
            if lay.get('straight'):   # every card hangs straight down from its peg on the curved cord (Darpan 18 Oct 2026: any swing looked messy)
                a, drop = 0, 0
            elif lay.get('playful'):   # a real line of photos: a few nearly straight, most swung a little, a couple swung well, some touching
                a = rnd.choice((-1, 1)) * lay['tilt'] * rnd.choice((.3, .7, 1, 1, 1.4)) * rnd.uniform(.85, 1.05)   # halfway between v9 and v10 (Darpan: v10 a bit too messy)
                cx += rnd.uniform(-11, 11); drop = rnd.uniform(-3.5, 8)
            else:
                a = rnd.uniform(-lay['tilt'], lay['tilt']) * rnd.choice((.4, 1, 1))              # some hang nearly straight, some swing more
                cx += rnd.uniform(-6, 6); drop = rnd.uniform(-3, 4)                               # pegged a little left or right, higher or lower
            t = np.radians(a)
            hung = card.hang(card.make(x)).rotate(a, resample=Image.BICUBIC, expand=True)
            px, py = cx, sag(cx) + 4 + drop
            mx, my = px + card.CH / 2 * np.sin(t), py + card.CH / 2 * np.cos(t)
            img.paste(hung, (int(mx - hung.width / 2), int(my - hung.height / 2)), hung)
            later.append(lambda cx=cx: peg(img, cx, sag(cx) + 4, s, short=.72))
            if lay.get('pill') and caption(x):
                tag, pos = under_card(x, card, gap, cf_a, lh_a, 'W2', rnd)
                bx, by = px + card.CH * np.sin(t), py + card.CH * np.cos(t)
                later.append(lambda tag=tag, bx=bx, by=by: img.paste(tag, (int(bx - tag.width / 2), int(by + 6)), tag))
        for f in later:
            f()
    if not lay.get('oneline'):
        footer(img, small=lay.get('compact', False), history=history)
    return img


CAPTION_SIZE = 21   # caption text under each frame (was 24; smaller since 18 Oct 2026 so whole captions fit, people zoom in)
SAG = 60            # how far the cords dip in the middle, in pixels (Darpan 18 Oct 2026: 20 then 34 looked too straight, he wanted more)
LIVE_STYLE = 'W2'   # the daily picture: design B, wide cards hanging straight on three curved cords, PNG (Darpan locked it in, 18 Oct 2026)


def polish(photo):
    """Final touch on each resized photo (Darpan 19 Oct 2026 chose look 2 'Natural' with a touch of warmth, then 'D
    richer skin'): a light levels stretch, one gentle sharpening pass whose threshold keeps skin and smooth walls clean,
    a little more red and a little less blue so the photos sit warmly with the maroon and gold, then robe and skin tones
    drawn together (rich_skin)."""
    photo = ImageOps.autocontrast(photo, cutoff=(.2, .1), preserve_tone=True)
    photo = photo.filter(ImageFilter.UnsharpMask(radius=1, percent=45, threshold=4))
    a = np.asarray(photo).astype(np.float32)
    a[..., 0] *= 1.025
    a[..., 2] *= .965
    return rich_skin(Image.fromarray(a.clip(0, 255).astype(np.uint8)))


def rich_skin(photo, hue_k=.3, sat_up=.22):
    """Bring the orange robes and skin closer in colour without fading anything (Darpan disliked desaturated robes):
    in orange and skin hues only, the hues drift toward each other and paler warm areas (skin) gain a little richness.
    Reds, blues, gold, greys, white cloth and deep shadows are left alone."""
    hsv = cv2.cvtColor(np.asarray(photo), cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    w = np.clip((h - 6) / 6, 0, 1) * np.clip((44 - h) / 8, 0, 1)
    w *= np.clip((v - 40) / 40, 0, 1) * np.clip((s - 60) / 50, 0, 1)
    hsv[..., 0] = h + hue_k * w * (19 - h)
    hsv[..., 1] = s + sat_up * w * np.clip(200 - s, 0, None)
    return Image.fromarray(cv2.cvtColor(hsv.clip(0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB_FULL))


def dump_photos(photos, folder):
    """Save the chosen photos and what make.py knows about them, so a layout can be redrawn offline (relayout.py)."""
    os.makedirs(folder, exist_ok=True)
    meta = []
    for i, x in enumerate(photos):
        x['im'].convert('RGB').save(os.path.join(folder, f'{i:02d}.jpg'), quality=95)
        meta.append({k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in x.items()
                     if k != 'im' and isinstance(v, (str, int, float, bool, list, tuple, dict, type(None), np.ndarray, np.generic))})
    json.dump(meta, open(os.path.join(folder, 'photos.json'), 'w'), default=float)


def compose(photos, day, seed, style=None, look=None, history=None):
    if style in WIDE:
        return compose_wide(photos, day, seed, style, history)
    rnd = random.Random(seed)
    img = background(); dr = ImageDraw.Draw(img)
    header(img, f'{day.day} {day:%B}', 'in Bapa’s Diary')

    n = len(photos)
    lay = LAYOUT.get(style, {})
    nr = lay.get('rows', 1 if n <= 5 else 2)
    rows = [photos[round(i * n / nr):round((i + 1) * n / nr)] for i in range(nr)]
    cols, M, min_gap = max(len(r) for r in rows), lay.get('M', 100), lay.get('min_gap', 30)
    list_h = (-(-n // 3) * 36 + 30) if style == 'D' else 0     # room for the numbered caption list
    top_space, bottom_space = lay.get('top', 222), lay.get('bottom', H - 128) - list_h
    row_gap = lay.get('row_gap', 58)
    band = lay.get('band') or {'C': .52, 'E': .6, 'G': .56}.get(style, .32)
    cf_a = garamond(CAPTION_SIZE, 500); lh_a = round(CAPTION_SIZE * 1.2)
    below = {'A': 3 * lh_a + 16, 'F': 3 * lh_a + 52, 'H': 3 * lh_a + 34}.get(style, 0)   # room under each card
    if style in LAYOUT:
        below = lay['lines'] * lh_a + 30
    pw_w = ((W - 2 * M - min_gap * (cols - 1)) / cols) / 1.09
    row_h = (bottom_space - top_space - row_gap * (len(rows) - 1)) / len(rows) - below
    pw = min(lay.get('cap', 300), pw_w, row_h / (lay.get('aspect', 1.08) + .045 + band))
    # on busy days the cards are narrower, so let the photos grow taller to fill the height instead
    card = Card(pw, lay.get('aspect') or max(1.08, min(1.45, row_h / pw - .045 - band)), band, style)
    gap = min(70, (W - 2 * M - cols * card.CW) / max(1, cols - 1))
    pitch = card.CH + below + row_gap
    block = (len(rows) - 1) * pitch + card.CH + below
    first = top_space + max(0, (bottom_space - top_space - block) / 2)
    s = card.PW / 220

    num = 0
    for r, row in enumerate(rows):
        y_top = first + r * pitch
        sag = lambda xp: y_top - 4 + 12 * 4 * (xp / W) * (1 - xp / W)
        dr.line([(xp, sag(xp)) for xp in range(0, W + 1, 6)], fill=(170, 132, 78), width=2)
        x0 = (W - (len(row) * card.CW + (len(row) - 1) * gap)) / 2
        for c, x in enumerate(row):
            cx = x0 + c * (card.CW + gap) + card.CW / 2
            # each polaroid swings a little on its peg, like a real one would
            a = rnd.uniform(-2.2, 2.2); t = np.radians(a)
            num += 1
            hung = card.hang(card.make(x, num)).rotate(a, resample=Image.BICUBIC, expand=True)
            px, py = cx, y_top                                  # the peg holds the middle of the top edge
            mx, my = px + card.CH / 2 * np.sin(t), py + card.CH / 2 * np.cos(t)
            img.paste(hung, (int(mx - hung.width / 2), int(my - hung.height / 2)), hung)
            peg(img, cx, sag(cx) + 4, s, look)
            if style == 'A' and caption(x):
                lines = wrap(dr, caption(x), cf_a, card.CW + gap - 14, 3)
                ty = y_top + card.CH + 18
                for i, line in enumerate(lines):
                    dr.text((cx, ty + (i + .8) * lh_a), line, font=cf_a, fill=CAPTION_GOLD, anchor='ms')
            if style and (style[0] in 'FH' or lay.get('lines')) and caption(x):
                tag, pos = under_card(x, card, gap, cf_a, lh_a, style, rnd)
                bx, by = px + card.CH * np.sin(t), py + card.CH * np.cos(t)   # middle of the tilted card's bottom edge
                img.paste(tag, (int(bx - tag.width / 2), int(by + pos)), tag)

    if style == 'D':
        caption_list(img, photos, bottom_space + 18, H - 112)
    footer(img)
    return img


# ---------------------------------------------------------------- the Today in BAPS History channel

TG_FILE = os.path.join(HERE, 'telegram', 'events.json')   # every dated story on t.me/TodayinBAPShistory, with our short lines (tools/telegram.py)
TG_PAGE = 'https://t.me/s/TodayinBAPShistory?before={n}'
TG_SAME_PERSON = .38   # the channel's photos are often old video stills of a younger Bapa, and its story already says he is there
TG_GAP_BOOST = 1.0   # a channel photo from the very day beats a baps.org photo borrowed from a nearby day of the trip


def tg_events(mmdd):
    if not os.path.exists(TG_FILE):
        return []
    return [e for e in json.load(open(TG_FILE, encoding='utf-8')) if e['date'][5:] == mmdd]


def tg_photos(posts):
    """The channel's photo addresses for these posts, read fresh from its public web page (the addresses expire)."""
    urls = []
    for n in posts:
        try:
            html = fetch(TG_PAGE.format(n=n + 1), tries=2).decode('utf-8', 'replace')
        except Exception as e:
            print('  could not read the channel page for post', n, e)
            continue
        for part in html.split('class="tgme_widget_message_wrap')[1:]:
            if f'data-post="TodayinBAPShistory/{n}"' in part:
                urls += re.findall(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", part)
    return list(dict.fromkeys(urls))


def tg_day(day, items):
    """Idea 2 and 5 (Darpan, 19 Oct 2026): the channel's photos of Bapa join the day as extra cards for years before
    baps.org's photos start, and stand in for a year whose baps.org photos come from a nearby day of the trip.
    Returns (extra items, the day's stories, the special story or None)."""
    mmdd = f'{day:%m-%d}'
    evs = [e for e in tg_events(mmdd) if int(e['date'][:4]) < day.year]
    if not evs:
        return [], None, None
    exact = {x['y'] for x in items if x.get('d', '')[:10] == f'{x["y"]}-{mmdd}'}
    have = {x['y'] for x in items}
    extra = []
    for e in evs:
        y = int(e['date'][:4])
        if not e.get('card') or y < 1950 or y in exact:
            continue
        gap = y in have
        town = lambda p: re.split(r'[,(]', p or '')[0].strip().lower()
        if gap and town(e.get('place')) not in {town(x.get('p')) for x in items if x['y'] == y}:
            print(f'  channel story {e["date"]} is in {e.get("place")}, baps.org has that year elsewhere: left as it is')
            continue   # Darpan, 19 Oct 2026: only fill a gap when both say the same place (not Mahelav on one, Nairobi on the other)
        urls = tg_photos(e['posts'])
        print(f'  + {len(urls)} photos from the channel for {e["date"]} ({"stands in for a nearby day" if gap else "a year before baps.org"})')
        extra += [{'y': y, 'd': e['date'], 'p': e.get('place') or '', 'c': e['card'], 'i': u, 'tg': True, 'post': e.get('url'),
                   'boost': (TG_GAP_BOOST if gap else 0) - .01 * k} for k, u in enumerate(urls)]   # the channel's lead photo first
    special = max((e for e in evs if e.get('special')), key=tg_rank, default=None)
    return extra, evs, special


tg_rank = lambda e: (bool(e.get('special')), e.get('reposts', 1), -int(e['date'][:4]))


def tg_story(evs, photos):
    """The story for the history line: never one a card already tells (Darpan, 19 Oct 2026: the older darshan card
    comes first, the line must say something different), so not a story from the same day and town as a card."""
    town = lambda p: re.split(r'[,(]', p or '')[0].strip().lower()
    shown = {(x.get('d', '')[:10], town(x.get('p'))) for x in photos}
    left = [e for e in evs if (e['date'], town(e.get('place'))) not in shown]
    return max(left, key=tg_rank, default=None)


def tg_caption(ev):
    """Idea 4: the story for the 2pm WhatsApp message, added under Darpan's own caption by his script."""
    text = ev.get('whatsapp') or f'On this day in {ev["date"][:4]}, {ev["line"]}.'
    if ev.get('video'):
        text += f'\n\U0001F3A5 {ev["video"]}'
    return text + '\n'


def compose_special(ev, day):
    """Idea 3: on a big day in BAPS history, a second picture of that day's story: the channel's lead photo large,
    four more beside it under the story, in the daily picture's colours."""
    urls = tg_photos(ev['posts'])[:5]
    cache = os.path.join(HERE, '.cache')
    ims = []
    for u in urls:
        x = {'i': u, 'y': 0}
        download_all([x], cache)
        if 'path' in x:
            ims.append(Image.open(x['path']).convert('RGB'))
    if not ims:
        return None
    img = background(); dr = ImageDraw.Draw(img)
    header(img, f'{day.day} {day:%B} in Bapa’s Diary', 'A special day in BAPS history', compact=True)
    yr, pl = ev['date'][:4], (ev.get('place') or '').upper()

    def card(im, w, h):
        c = Image.new('RGBA', (w + 24, h + 24 + round(w * .1))); d = ImageDraw.Draw(c)
        for j in range(c.height):
            t = j / c.height
            d.line((0, j, c.width, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(IVORY_TOP, IVORY_BOTTOM)) + (255,))
        d.rectangle((0, 0, c.width - 1, c.height - 1), outline=IVORY_EDGE)
        r = max(w / im.width, h / im.height)
        p = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
        p = p.crop(((p.width - w) // 2, round((p.height - h) * .3), (p.width - w) // 2 + w, round((p.height - h) * .3) + h))
        c.paste(polish(p), (12, 12))
        yf, pf = garamond(w * .07, 700), arimo_bold(w * .03)
        yw = d.textlength(yr, font=yf); sp = w * .03 if pl else 0
        x0 = (c.width - yw - sp - spaced(d, pl, pf, w * .006)) / 2; base = h + 12 + (c.height - h - 12) * .72
        d.text((x0, base), yr, font=yf, fill=YEAR_C2, anchor='ls')
        draw_spaced(d, x0 + yw + sp, base - pf.getmetrics()[0] - w * .008, pl, pf, w * .006, PLACE_C2)
        sh = Image.new('RGBA', (c.width + 60, c.height + 60))
        ImageDraw.Draw(sh).rectangle((30, 36, c.width + 30, c.height + 36), fill=(0, 0, 0, 150))
        sh = sh.filter(ImageFilter.GaussianBlur(12)); sh.alpha_composite(c, (30, 30))
        return sh
    hero = card(ims[0], 1180, 800)
    img.paste(hero, (70, 200), hero)
    peg(img, 70 + hero.width / 2, 228, 1.5)
    x0, tw = 1360, W - 1360 - 90
    hf, bf = garamond(60, 700), garamond(36, 500)
    y = 300
    for line in wrap(dr, ev.get('headline') or ev['line'], hf, tw, 2):
        gold_text(img, (x0, y - 60), line, hf); y += 72
    y += 20
    for line in wrap(dr, ev.get('story') or ev.get('whatsapp') or ev['line'], bf, tw, 7):
        dr.text((x0, y), line, font=bf, fill=CAPTION_IVORY, anchor='ls'); y += 50
    small = ims[1:5]
    top = max(620, y + 40)
    if small:
        sw = min(330, (tw - 30 * (len(small) - 1)) / len(small) - 24)
        for k, im in enumerate(small):
            c = card(im, round(sw), round(sw * .74))
            cx = x0 - 30 + k * (sw + 54)
            img.paste(c, (round(cx), top), c); peg(img, cx + c.width / 2, top + 28, 1)
    footer(img, small=True)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='YYYY-MM-DD (default: today in London)')
    ap.add_argument('--data', help='use this JSON file instead of downloading the day list')
    ap.add_argument('--cache', default=os.path.join(HERE, '.cache'))
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--workings', action='store_true', help='also make second-choice.jpg (H2) and workings.jpg')
    ap.add_argument('--compare', action='store_true', help='also make original.jpg and unique.jpg (captions shown) and captions.txt')
    ap.add_argument('--styles', default='', help='also make caption mockups, e.g. A,B,C,D (out/caption-A.jpg ...)')
    a = ap.parse_args()

    day = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(ZoneInfo('Europe/London')).date()
    mmdd = f'{day:%m-%d}'
    items = json.load(open(a.data)) if a.data else json.loads(fetch(DATA_URL.format(mmdd=mmdd)))
    collected = os.path.join(HERE, 'archive', mmdd + '.json')      # newer years found by collect.py
    if os.path.exists(collected):
        have = {x['i'] for x in items}
        items += [x for x in json.load(open(collected)) if x['i'] not in have]
    combed = os.path.join(HERE, 'archive', 'vicharan', mmdd + '.txt')   # every captioned photo of Bapa from that day's vicharan pages
    if os.path.exists(combed):
        have = {x['i'] for x in items}
        place = {x['y']: x.get('p', '') for x in items}
        extra = [x for x in vicharan_items(combed, f'{day:%m-%d}', place) if x['y'] < day.year]   # past years only
        full = {x['i']: x['c'] for x in extra}
        for x in items:                                                   # the day list's 'sanctifies water...' gets the carried on caption
            if (x.get('c') or '').endswith('...') and x['i'] in full:
                x['c'] = full[x['i']]
        items += [x for x in extra if x['i'] not in have]
        print(f'  + {len(items) - len(have)} more captioned photos from the vicharan pages')
    print(f'{day}: {len(items)} photos across {len({x["y"] for x in items})} years')

    tg_extra, tg_evs, special = tg_day(day, items)
    items += tg_extra
    download_all(items, a.cache)
    tall = 1 / 1.45 if len({x['y'] for x in items}) > 10 else 1 / 1.08
    photos = pick_one_per_year(items, seed=mmdd, aspect=FRAME_ASPECT.get(LIVE_STYLE, tall), day=day)
    if not photos:
        raise SystemExit('No photos could be downloaded for ' + mmdd)
    remember(day, photos)
    story = tg_story(tg_evs, photos)
    unsure = [x for x in photos if x.get('tg') and (not x['face'] or x['sim'] < SAME_PERSON)]   # Darpan: carry on, but flag it and keep a backup
    for x in photos:
        print(f'  {x["y"]}  {x.get("p", "")[:28]:28}  Bapa {"%.2f" % x["sim"] if x["face"] else "not found, shown whole"}  {x["crop"]:5}  {caption(x)}')

    os.makedirs(a.out, exist_ok=True)
    live = compose(photos, day, seed=mmdd, style=LIVE_STYLE, history=story)
    live.save(os.path.join(a.out, 'bapas-diary.jpg'), quality=95, optimize=True)
    live.save(os.path.join(a.out, 'bapas-diary.png'), optimize=True)   # the PNG is the final file (Darpan, 18 Oct 2026): crisp text
    workings_live = list(WORKINGS)
    for st in filter(None, a.styles.split(',')):
        if st.startswith('peg-'):   # peg mockups on the live layout, e.g. peg-bevel
            compose(photos, day, seed=mmdd, style=LIVE_STYLE, look=st[4:]).save(os.path.join(a.out, f'caption-{st}.jpg'), quality=95, optimize=True)
            continue
        ps = photos
        if st in FRAME_ASPECT:   # a wide frame keeps more of each photo, so more action shots qualify: pick again for it
            ps = pick_one_per_year(items, seed=mmdd, aspect=FRAME_ASPECT[st], day=day)
            print(f'  {st}: ' + ', '.join(f'{x["y"]} {x["crop"]}' for x in ps))
            workings_sheet(day).save(os.path.join(a.out, f'caption-workings-{st}.jpg'), quality=88, optimize=True)
        im = compose(ps, day, seed=mmdd, style=st)
        im.save(os.path.join(a.out, f'caption-{st}.jpg'), quality=95, optimize=True)
        if st in WIDE:
            im.save(os.path.join(a.out, f'caption-{st}.png'), optimize=True)   # lossless copy, text stays crisp
            dump_photos(ps, os.path.join(a.out, f'photos-{st}'))
    WORKINGS[:] = workings_live
    if a.workings:
        seconds = second_choices()
        compose(seconds, day, seed=mmdd, style='H2').save(os.path.join(a.out, 'caption-second-choice.jpg'), quality=95, optimize=True)
        for st in filter(lambda st: st and st != 'H2', a.styles.split(',')):
            compose(seconds, day, seed=mmdd, style=st).save(os.path.join(a.out, f'caption-second-choice-{st}.jpg'), quality=95, optimize=True)
        workings_sheet(day).save(os.path.join(a.out, 'caption-workings.jpg'), quality=88, optimize=True)
        chosen = {id(w['pick']) for w in WORKINGS}
        with open(os.path.join(a.out, 'all-photos.txt'), 'w') as f:
            listed = collections.Counter(x['y'] for x in items)
            got = collections.Counter(x['y'] for x in items if 'path' in x)
            for y in sorted(listed):
                rows = sorted((r for r in ALL if r[0] == y), key=lambda r: -r[1])
                f.write(f'\n{y}: {listed[y]} photos listed, {got[y]} downloaded, {sum(r[2] for r in rows)} with Bapa recognised\n')
                for r in rows:
                    f.write(f'  {"Bapa %.2f" % r[1] if r[2] else "not recognised"}  {r[3] or "(no caption)"}  {r[4]}\n')
    if a.compare:
        photos_u = pick_one_per_year(items, seed=mmdd, unique=True)
        compose(photos, day, seed=mmdd, style='A').save(os.path.join(a.out, 'original.jpg'), quality=95, optimize=True)
        compose(photos_u, day, seed=mmdd, style='A').save(os.path.join(a.out, 'unique.jpg'), quality=95, optimize=True)
        with open(os.path.join(a.out, 'captions.txt'), 'w') as f:
            for name, ps in (('original', photos), ('unique', photos_u)):
                f.write(f'{name}:\n')
                for x in ps:
                    f.write(f'  {x["y"]}  {"UNIQUE  " if unique_caption(caption(x)) else "standard"}  {caption(x)}\n')
    for f in ('caption.txt', 'bapas-diary-special.png', 'bapas-diary-special.jpg', 'flags.txt', 'bapas-diary-backup.png'):   # nothing left over from another day
        if os.path.exists(os.path.join(a.out, f)):
            os.remove(os.path.join(a.out, f))
    told = story or max(tg_evs, key=tg_rank, default=None)   # the 2pm message may tell the card's story when there is no other
    if told:
        open(os.path.join(a.out, 'caption.txt'), 'w', encoding='utf-8').write(tg_caption(told))
        print('  story:', told['date'], told['line'], '' if story else '(caption only, a card tells it)')
    if unsure:   # a channel card where Bapa's face isn't surely recognised: say so, and keep the picture without it too
        with open(os.path.join(a.out, 'flags.txt'), 'w', encoding='utf-8') as f:
            for x in unsure:
                f.write(f"{x['y']} {place(x)}: {caption(x)}. Bapa {'not recognised' if not x['face'] else 'only a weak match (%.2f)' % x['sim']} "
                        f"in the channel's photo ({x.get('post')})\n")
        rest = [x for x in photos if x not in unsure]
        if rest:
            compose(rest, day, seed=mmdd, style=LIVE_STYLE, history=tg_story(tg_evs, rest)).save(
                os.path.join(a.out, 'bapas-diary-backup.png'), optimize=True)
        print('  flagged:', ', '.join(str(x['y']) for x in unsure))
    if special:
        sp = compose_special(special, day)
        if sp:
            sp.save(os.path.join(a.out, 'bapas-diary-special.png'), optimize=True)
            sp.save(os.path.join(a.out, 'bapas-diary-special.jpg'), quality=95, optimize=True)
            print('  special picture:', special['date'], special.get('headline'))
    open(os.path.join(a.out, 'date.txt'), 'w').write(f'{day}\n')
    open(os.path.join(a.out, 'summary.txt'), 'w').write(f'{len(photos)} years: ' + ', '.join(str(x['y']) for x in photos) + '\n')
    print('saved', os.path.join(a.out, 'bapas-diary.jpg'))


if __name__ == '__main__':
    main()
