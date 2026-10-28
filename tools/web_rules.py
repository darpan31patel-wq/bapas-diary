"""The On this day picture's rules, brought to the website's Bapa pages (Darpan, 25 Oct 2026: "want all of them apart
from 8", from the list comparing his picture rules with the website). Website only: nothing here touches the daily 2pm
picture chain. Like web_bapa_rules.py, the parts of make.py used here are copies, so neither side can break the other.

    python3 tools/web_rules.py captions --db bapa.db --db bapa-top.db      1  tidy captions in the Bapa pages' databases
    python3 tools/web_rules.py tg --db bapas.db --drive tgsrc --out tg      5  darshan before 1999 from the channel photos
    python3 tools/web_rules.py day --day out/data/day --db bapa.db --faces faces --tg tg-cards.json
                                                                          3 4 5 6 7  the Today page's data
    python3 tools/web_rules.py calfaces --site cal --faces faces          3  the Calendar tab's photos keep his head too
    python3 tools/web_rules.py look --out out                             2  the gentle finish on every photo of Bapa
    python3 tools/web_rules.py calendar --db bapas.db --db bapa.db ...    the BAPS calendar days the picture shows (25 Oct 2026)

1  A caption says what Bapa does, without his name, dates or link text; "devotee" is "bhakta"; an album's own date
   heading is "Darshan". On a card it is summarised to fit two lines, never cut with "...".
2  Look D, the picture's "Natural" finish with a touch of warmth and richer skin: drawn by the browser on the photos.
3  Each Today and Calendar photo frames Bapa's whole head (pagh included); the pages do the framing from where his face
   is, which this adds to their data.
4  A year's card only borrows photos from other days when that date has none: the same trip's range, or the nearest
   day up to 3 days away.
5  Years before 1999 get a darshan card from the two On this day channels' photos when Bapa (Pramukh Swami Maharaj)
   is recognised in them. Earlier gurus are left out (the Bapa pages show only photos of Bapa).
6, 7  A story is not told again when a card of that year already shows that day in that town (the UK and Europe diary
   included); its 2008 to 2016 years are already left out where the stories are read in (tools/satpurush.py).
"""
import argparse, datetime, glob, gzip, hashlib, io, json, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_bapa_rules as R

HERE = R.HERE
CARD_CHARS = 40   # a Today card's caption fits two lines in about this many letters (cards are 150 to 200 px wide)
NEAR_DAYS = 7     # a day up to 7 days away may fill a year that has no photos on the date (make.py: 3; Darpan, 26 Oct 2026: "yes nearest day")
TG_SAME_PERSON = .38   # make.py: the channel's photos are often old video stills of a younger Bapa
TG_FACE_MIN = .1     # from 1999 on: a channel photo's face of Bapa is at least this part of the photo's height
TG_FROM = 1950    # make.py: channel darshans of Bapa from this year (earlier ones are of the gurus before him)
EARLY = 'early'    # R2 folder of the darshan photos before 1999 (public name: never the source's)
BAPS_FROM = 1999  # baps.org's own photos start here


# ---------------------------------------------------------------- 1 captions (copied from make.py)

SHORT_END = {'the', 'a', 'an', 'of', 'and', 'to', 'with', 'his', 'her', 'their', 'on', 'in', 'at', 'for', 'by', 'from', 'that', 'two', 'new',
             'who', 'which', 'where', 'via', 'as', 'while', 'during', 'before', 'after', 'is', 'are', 'was', 'other', 'various', 'some'}
SHORT_WORDS = [   # a few long phrases said shorter in the website's own words, so a caption fits without trailing off
    (r'\bvideo conference\b', 'video'), (r'\bBAPS Shri Swaminarayan Mandir(s?)\b', r'mandir\1'), (r'\bShri Swaminarayan Mandir\b', 'mandir'),
    (r'\bmurti-pratishtha (?:ceremony|rituals?)\b', 'murti-pratishtha'),
]


def summarise(c):
    """The same caption in fewer words: 'Discourses with sadhus via video conference' becomes 'Discourses with sadhus via video'."""
    for pat, rep in SHORT_WORDS:
        c = re.sub(pat, rep, c)
    return c


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


def website_caption(c):
    """The caption the Bapa pages show: what Bapa does (make.caption), said shorter where the website's words are long."""
    return summarise(R.caption({'c': c})) if c else ''


def card_caption(c):
    """A caption for under a Today card: the whole caption when it fits two lines, else its longest natural shortening
    that does (Darpan, 18 Oct 2026: summarise rather than cut, never end with '...')."""
    c = re.sub(r'\.$', '', c or '')
    if len(c) <= CARD_CHARS:
        return c
    fits = [v for v in shorter_versions(c) if len(v) <= CARD_CHARS and len(v.split()) >= 3]
    return fits[0] if fits else c


def captions(a):
    """1: the Bapa pages' databases get the website caption in place of baps.org's own words (Search keeps those)."""
    for path in a.db:
        db = sqlite3.connect(path)
        rows = db.execute('SELECT album, file, caption FROM photos').fetchall()
        new = [(website_caption(c), al, fi) for al, fi, c in rows]
        db.executemany('UPDATE photos SET caption = ? WHERE album = ? AND file = ?', [n for n, r in zip(new, rows) if n[0] != (r[2] or '')])
        db.commit()
        changed = sum(1 for n, r in zip(new, rows) if n[0] != (r[2] or ''))
        print(f'{path}: {changed} of {len(rows)} captions tidied', flush=True)
        for (n, _, _), r in list(zip(new, rows))[:: max(1, len(rows) // 12)][:12]:
            print(f'   {r[2]!r} -> {n!r}')


# ---------------------------------------------------------------- the BAPS calendar, as the picture says it

# Copied from make.py (live 25 Oct 2026, 9e668e8): only the days Darpan kept, festivals on the Indian date, birthdays
# and anniversaries on their English date, an Ekadashi without its name. National days stay (he said no to 8).
DAYS = [(r'^diwali$', 'Diwali'), (r'annakut', 'Annakut'), (r'\bbestu', 'New Year'), (r'janmashtami', 'Janmashtami'),
        (r'guru purnima', 'Guru Purnima'), (r'vasant panch', 'Vasant Panchami'), (r'^holi', 'Holi'),
        (r'pushpadol|dhuleti', 'Pushpadolotsav'), (r'ram ?navm', 'Ram Navami'), (r'hari.?nom|swaminarayan jayanti', 'Swaminarayan Jayanti'),
        (r'rathyatra', 'Rathyatra'), (r'jal jhilani', 'Jal Jhilani Ekadashi'), (r'^prabodhini ekadashi$', 'Prabodhini Ekadashi'),
        (r'^dev diwali$', 'Dev Diwali'), (r'akshar purnima', 'Akshar Purnima'), (r'shri hari navmi', 'Shri Hari Navmi'),
        (r'hindola prarambh', 'Hindola begins'), (r'hindola samapt', 'Hindola ends'), (r'devpodhi|devshayani', 'Devpodhi Ekadashi'),
        (r'vagh baras$', 'Vagh Baras'), (r'dhan te|dhan tray', 'Dhan Teras'), (r'kali ch?audas', 'Kali Chaudas'), (r'^bhai b', 'Bhai Beej'),
        (r'la+bh pancham', 'Labh Pancham'), (r'makar sankranti', 'Makar Sankranti'), (r'shivratri', 'Shivratri'),
        (r'raksha bandhan', 'Raksha Bandhan'), (r'republic day', 'Republic Day'), (r'independence day', 'Independence Day'),
        (r'jagaswami', 'Jagaswami Jayanti'), (r'grahan', 'Eclipse'), (r'shra+d+h', 'Shraddh'), (r'dhanurmas prarambh', 'Dhanurmas begins'),
        (r'dhanurmas (samapt|purn|end)', 'Dhanurmas ends'), (r'holashtak', 'Holashtak begins')]
ONCE = {'Shri Hari Navmi': 'Kartak', 'Akshar Purnima': 'Magshar'}   # on the calendar every month, shown once a year
FIXED = {'01-20': 'Gunatitanand Swami Diksha Day', '01-23': 'Yogiji Maharaj Smrutiparva', '01-31': 'Shastriji Maharaj Jayanti',
         '03-20': 'Bhagatji Maharaj Jayanti', '05-10': 'Shastriji Maharaj Smrutiparva', '05-21': 'Pramukh Varni Din',
         '05-23': 'Yogiji Maharaj Jayanti', '06-01': 'Bhagwan Swaminarayan Smrutiparva', '08-13': 'Pramukh Swami Maharaj Smrutiparva',
         '09-13': 'Mahant Swami Maharaj Jayanti', '10-11': 'Gunatitanand Swami Smrutiparva', '10-17': 'Gunatitanand Swami Jayanti',
         '11-07': 'Bhagatji Maharaj Smrutiparva', '12-07': 'Pramukh Swami Maharaj Jayanti'}


def kept_days(date, month, names, ekadashi, punam, amas, indian_date):
    """make.festivals and cal_parts: the kept days on this date, an Ekadashi first (by its own name only when the
    calendar gives it one of the kept names), then the English date ones."""
    out = []
    for n in names:
        for part in re.split(r'\s*[,;]\s*', n):
            for k, v in DAYS:
                if re.search(k, part.strip(), re.I) and v not in out and ONCE.get(v, month) == month:
                    out.append(v)
    for flag, word in ((punam, 'Punam'), (amas, 'Amas')):   # the website shows the whole Indian date ('Aso Sud Chaudas/Punam')
        if flag and word not in (indian_date or '') and word not in out:
            out.append(word)
    if date[5:10] in FIXED:
        out.append(FIXED[date[5:10]])
    ek = [f for f in out if 'Ekadashi' in f][:1] or (['Ekadashi'] if ekadashi else [])
    return ek + [f for f in out if f not in ek]


def calendar(a):
    """The calendar table of each database says what the picture says: festivals = the kept days, notes left empty."""
    for path in a.db:
        db = sqlite3.connect(path)
        rows = db.execute('SELECT date, month, festivals, notes, ekadashi, punam, amas, indian_date FROM calendar').fetchall()
        new = [('; '.join(kept_days(d, m, [f or '', n or ''], ek, pu, am, ind)), '', d) for d, m, f, n, ek, pu, am, ind in rows]
        db.executemany('UPDATE calendar SET festivals = ?, notes = ? WHERE date = ?', new)
        db.commit()
        print(f'{path}: {len(rows)} calendar days, {sum(1 for x in new if x[0])} with a kept day')


# ---------------------------------------------------------------- 5 channel darshans before 1999

def trim_bars(im):
    """The photo without the flat black bars a video still or a channel's frame leaves round it (make.trim_bars)."""
    import numpy as np
    g = np.asarray(im.convert('L').resize((max(1, im.width // 4), max(1, im.height // 4))), dtype=float)

    def bar(rows):
        n = 0
        for r in rows:
            if r.mean() > 30 or r.std() > 14:
                break
            n += 1
        return n * 4
    t, b, l, r = bar(g), bar(g[::-1]), bar(g.T), bar(g.T[::-1])
    if t + b > im.height * .5 or l + r > im.width * .5 or not (t or b or l or r):
        return im
    return im.crop((l, t, im.width - r, im.height - b))


UNFRAME_CAPTION = 124   # make.py: the UK diary's caption written along the bottom of the darshan


def unframe(im):
    """The Satpurush in UK & Europe photos come in the channel's frame (its title above, the date below, a caption
    written along the bottom): only the darshan, above its written caption (make.unframe). None when it isn't framed."""
    import numpy as np
    g = np.asarray(im.convert('L'), dtype=float)
    h = g.shape[0]
    if im.width / h > .8 or h < 600:
        return None
    d = np.abs(np.diff(g, axis=0)).mean(axis=1)
    top = int(np.argmax(d[int(.15 * h):int(.32 * h)])) + int(.15 * h) + 1
    bottom = int(np.argmax(d[int(.6 * h):int(.85 * h)])) + int(.6 * h) + 1
    if d[top - 1] < 20 or d[bottom - 1] < 20 or bottom - top < .4 * h:
        return None
    im = im.crop((0, top, im.width, bottom - UNFRAME_CAPTION))
    return im.resize((im.width * 2, im.height * 2))


def tg(a):
    """5: every channel story before 1999 with a darshan card, its photos (copied from the Drive archive into --drive by
    the workflow), Bapa's face checked. Writes --out/s/early/KEY and m/early/KEY for R2, and --out/tg-cards.json:
    {"MM-DD": [[year, place, "early", KEY, caption, [cx, cy, x, y, w, h, aspect, close], card caption], ...]}."""
    from PIL import Image, ImageOps
    db = sqlite3.connect(a.db)
    folder = {(ch, i): f for ch, i, f in db.execute('SELECT channel, id, local_folder FROM tg_posts')}
    cards, seen, tried = {}, 0, 0
    known = known_places(db)
    for os_dir in ('s/' + EARLY, 'm/' + EARLY):
        os.makedirs(os.path.join(a.out, os_dir), exist_ok=True)
    for ch, date, place, posts, data, guru in db.execute(
            'SELECT channel, date, place, posts, data, guru FROM tg_events ORDER BY date'):
        e = json.loads(data)
        y = int(date[:4])
        # every year, not only before 1999: the 2pm picture also takes the channel's photo of the very day when baps.org
        # has none that day (Darpan, 26 Oct 2026: 26 October 2006 showed in the picture but not on the website)
        if guru or not e.get('card') or y < TG_FROM:
            continue
        sat = ch == 'satpurush'
        for n in json.loads(posts or '[]'):
            f = folder.get((ch, n))
            own = (e.get('cards') or {}).get(str(n)) or {}
            for path in sorted(glob.glob(os.path.join(a.drive, glob.escape(f or '-'), 'photo *.jpg'))):
                tried += 1
                try:
                    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
                except Exception as err:
                    print('  could not open', path, err)
                    continue
                if sat:
                    im = unframe(im)
                    if im is None:
                        continue
                im = trim_bars(im)
                face, sim, front, _, other = R.bapa_face(im, date)
                if not face or sim < TG_SAME_PERSON:
                    continue
                # a plain number for the public photo name: no channel or source name anywhere on the site
                src = f'{ch}-{n}-{re.sub(r"[^0-9]", "", os.path.basename(path)) or 1}'
                key = hashlib.sha1(src.encode()).hexdigest()[:12] + '.jpg'
                for tier, size in (('m', 1200), ('s', 480)):
                    c = im.copy()
                    c.thumbnail((size, size * 2), Image.LANCZOS)
                    c.save(os.path.join(a.out, tier, EARLY, key), 'JPEG', quality=86, optimize=True, progressive=True)
                x, yy, w, h = face
                W, H = im.size
                sharp, bright = R.face_quality(im, face)
                close = h >= R.CLOSE_MIN_FACE and front >= .35 and sharp >= R.SHARP_MIN and bright >= R.BRIGHT_MIN
                cap = website_caption(own.get('card') or e['card'])
                cards.setdefault(date[5:], []).append(
                    [y, card_place(own.get('place'), e.get('place') or place, known), EARLY, key, cap,
                     [round((x + w / 2) / W, 3), round((yy + h / 2) / H, 3), round(x / W, 4), round(yy / H, 4), round(w / W, 4),
                      round(h / H, 4), round(W / H, 4), int(close)], round(sim, 3), card_caption(cap)])
                seen += 1
    with open(os.path.join(a.out, 'tg-cards.json'), 'w', encoding='utf-8') as fh:
        json.dump(cards, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'{seen} of {tried} channel photos show Bapa, on {len(cards)} days')


# ---------------------------------------------------------------- 3 4 5 6 7 the Today page's data

town = lambda p: re.split(r'[,(]', p or '')[0].strip().lower()

# Darpan, 28 Oct 2026 ("Look at 1990, why is the location like this?"): the UK diary's place is read off the words written
# on each photo, so it can come with the rest of that line and specks read as letters ('Morning puja —.London',
# 'London oN', 'Evening sabha =London'). A card shows a town only: a place Bapa's photos know, else a tidy name.
NOT_A_PLACE = re.compile(r'\b(morning|evening|afternoon|puja|sabha|arti|aarti|viday|arrival|arrive|departure|flight|swagat|'
                         r'yatra|pratishtha|muhurat|rangotsav|mahotsav|shibir|sammelan|din|day|opening|visit|meets|festival|crematorium|'
                         r'tournament|counter|vad|sud|ashirwad|meeting|project|national|kishore|shishu|balika|mandal|cultural)\b', re.I)


def known_places(db):
    """Every town Bapa's photos name, and the places file's towns, longest first."""
    names = {(p or '').split(',')[0].strip() for (p,) in db.execute('SELECT DISTINCT place FROM photos')}
    try:
        names |= set(json.load(open(os.path.join(HERE, 'places.json'), encoding='utf-8')))
    except (OSError, ValueError):
        pass
    return sorted((n for n in names if len(n) > 2 and not NOT_A_PLACE.search(n)), key=len, reverse=True)


def tidy_place(text, known):
    """('Morning puja —.London', ...) -> 'London': the first known town in it, else a tidy name, else ''."""
    text = text or ''
    found = [(m.start(), n) for n in known for m in [re.search(r'(?<![\w-])' + re.escape(n) + r'(?![\w-])', text, re.I)] if m]
    if found:
        return min(found, key=lambda f: (f[0], -len(f[1])))[1]
    m = re.search(r"\b(?:in|to|from|meets)\s+([A-Z][\w'’.-]*(?:\s+(?:[A-Z][\w'’.-]*|on|upon|under))*)", text)
    if m and NOT_A_PLACE.search(text):   # 'Murti Pratishtha in Ashton-under-Lyne', 'Visit to town of Unhost'
        return m.group(1)
    t = re.split(r'\s*[—–=~:;|@*«»"“”©®<>]+\s*|\s+-+\s*|\s*-+\s+', text.split(',')[0])
    t = max((x for x in t if x), key=len, default='')
    if NOT_A_PLACE.search(t):   # 'Aso vad 4', 'Evening sabha'
        return ''
    words = t.strip(' .\'’-').split()
    while words and (len(re.sub(r'\W', '', words[-1])) <= 2 or not words[-1][0].isupper()):   # 'Leeds So', 'Islington aN'
        words.pop()
    while words and len(re.sub(r'\W', '', words[0])) <= 1:   # 'V Wellingborough'
        words.pop(0)
    t = ' '.join(words)
    ok = (len(t) > 2 and re.fullmatch(r"[A-Z][\w'’.-]*(?: (?:[A-Z][\w'’.-]*|of|on|upon|under|the|de|la))*", t)
          and not re.search(r'\d', t) and not NOT_A_PLACE.search(t) and not re.match(r'(At|In|To|From) ', t))
    return t if ok else ''


def card_place(card, event, known):
    """A channel card's town: the one read off the photo when it is clean, else the post's own place."""
    own = tidy_place(card, known)
    ev = tidy_place(event, known)
    if own and ev and own != ev and own.lower().startswith(ev.lower()) and own not in known:
        return ev   # 'Parish' read off the photo, the post says Paris
    return own or ev


def face_box(rec, close=None):
    """[centre x, centre y, x, y, w, h, photo width / height, close] from a face scan record, or None."""
    if not rec or rec[0] < TG_SAME_PERSON:   # no face of Bapa found in it
        return None
    sim, x, y, w, h = rec[:5]
    W, H = rec[8], rec[9]
    return [round(x + w / 2, 3), round(y + h / 2, 3), x, y, w, h, round(W / H, 4) if H else 0, int(bool(close))]


def day(a):
    faces = R_faces(a.faces)
    db = sqlite3.connect(a.db)
    pick = {(al, fi): (r, c) for al, fi, r, c in db.execute('SELECT album, file, rank, close FROM bapa_pick')}
    rank = lambda p: pick.get((p[0], p[1]), (9999, 0))[0]
    # every dated photo kept for the Bapa pages, by year and date, for 4 (the nearest day up to 3 days away)
    dated = {}
    for y, date, place, al, fi, cap, bapa in db.execute(
            'SELECT year, date, place, album, file, caption, is_bapa FROM photos WHERE date IS NOT NULL'):
        dated.setdefault((y, date), []).append([al, fi, cap or '', bapa, place])
    tgc = json.load(open(a.tg, encoding='utf-8')) if a.tg and os.path.exists(a.tg) else {}
    known = known_places(db)
    stats = dict(trip_dropped=0, near_added=0, stories_dropped=0, tg_years=0, framed=0)

    def finish(p):
        """p = [album, file, caption, bapa, face, card caption]"""
        del p[4:]
        rec = faces.get(f'{p[0]}/{p[1]}')
        box = face_box(rec, pick.get((p[0], p[1]), (0, 0))[1])
        stats['framed'] += bool(box)
        p += [box, card_caption(p[2])]
        return p

    for f in sorted(glob.glob(os.path.join(a.day, '*.json'))):
        D = json.load(open(f, encoding='utf-8'))
        mmdd = D['date']
        years = {Y['y']: Y for Y in D['years']}
        for Y in D['years']:
            if Y['p'] and Y.get('t'):   # 4: the date has photos of its own, so nothing is borrowed from other days
                stats['trip_dropped'] += 1
                Y.pop('t'); Y.pop('trip', None)
        # 4: a year with no photos on the date or its trip: the nearest day up to NEAR_DAYS away
        have = set(years)
        for k in range(1, NEAR_DAYS + 1):
            for s in (-1, 1):
                for y in {yy for (yy, _) in dated} - have:
                    try:
                        d = datetime.date(y, *map(int, mmdd.split('-'))) + datetime.timedelta(days=s * k)
                    except ValueError:
                        continue
                    rows = dated.get((y, d.isoformat()))
                    if rows:
                        # each day that borrows from this day takes its own share, so no photo shows on two days
                        i = s * k + NEAR_DAYS - (s > 0)   # 0 to 2 * NEAR_DAYS - 1
                        rows = sorted(rows, key=rank)
                        n = 2 * NEAR_DAYS
                        rows = rows[i * len(rows) // n:(i + 1) * len(rows) // n] or rows[i % len(rows):i % len(rows) + 1]
                        years[y] = {'y': y, 'place': (rows[0][4] or '').split(',')[0].strip(), 'p': [],
                                    'trip': [d.isoformat(), d.isoformat()], 't': [r[:4] for r in rows]}
                        have.add(y)
                        stats['near_added'] += 1
        shown_tg = set()
        # the post's own place for each year, tidied, for a card whose photo gave none worth showing
        for s in D['stories']:
            s[1] = tidy_place(s[1], known)
        said = {s[0]: s[1] for s in D['stories'] if s[1]}
        # 5: the channels' darshan of Bapa on this very day (every year since 26 Oct 2026, as the 2pm picture)
        for y, place, al, key, cap, box, sim, short in tgc.get(mmdd, []):
            place = tidy_place(place, known) or said.get(y, '')   # 'Morning puja —.London' is London (Darpan, 28 Oct 2026)
            # from 1999 on, as sure of Bapa's face as for baps.org's photos, and his face big enough to see (a tenth of
            # the photo's height at least), never a tiny far figure (Darpan, 26 Oct 2026: "i only want bapa")
            if y >= BAPS_FROM and (sim < R.SAME_PERSON or box[5] < TG_FACE_MIN):
                continue
            # a 3:4 channel post is the channel's own frame (its name above, the date below) that unframe() didn't take
            # off: never shown, the site never names its sources (Darpan, 23 Oct 2026)
            if abs(box[6] - .75) < .01:
                continue
            # the two channels often post the same photo: show it once (Darpan, 26 Oct 2026: never repeat a picture)
            same = (y, tuple(round(v, 2) for v in box[:7]))
            if same in shown_tg:
                continue
            shown_tg.add(same)
            if y in years and not years[y].get('tg'):   # baps.org has this year already
                B = years[y]
                # make.py: baps.org's own photos of the very day stay; when it only has a nearby day or a trip, the
                # channel's photo of the very day wins, but only when both put Bapa in the same town
                if B['p'] or town(B['place']) != town(place):
                    continue
                B.pop('t', None); B.pop('trip', None); B['tg'] = 1
            if y not in years:
                stats['tg_years'] += 1
            Y = years.setdefault(y, {'y': y, 'place': (place or '').split(',')[0].strip(), 'p': [], 'tg': 1})
            Y['p'].append([al, key, cap, 1, box, card_caption(cap)])
        for Y in years.values():
            if not Y.get('tg'):
                for part in ('p', 't'):
                    Y.get(part, []).sort(key=rank)
                    for p in Y.get(part, []):
                        finish(p)
            Y.pop('tg', None)
        # 6, 7: a story is not told again where a card already shows that day in that town
        shown = {(Y['y'], town(Y['place'])) for Y in years.values() if Y['p'] or Y.get('t')}
        keep = []
        for s in D['stories']:
            if (s[0], town(s[1])) in shown:
                stats['stories_dropped'] += 1
                continue
            keep.append(s)
        D['stories'] = keep
        D['years'] = [years[y] for y in sorted(years)]
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(D, fh, ensure_ascii=False, separators=(',', ':'))
    print(json.dumps(stats))


def R_faces(folder):
    out = {}
    for f in sorted(glob.glob(os.path.join(folder or '-', 'face2-*.json.gz'))):
        out.update(json.load(gzip.open(f, 'rt')))
    return out


# ---------------------------------------------------------------- 3 on the Calendar tab

# Darpan, 25 Oct 2026 (13 October 2026 cut through Bapa's head): the Calendar's photos are framed the same way, his
# whole head in view. The Calendar page belongs to its own thread, so this only adds where his face is to its data
# ("f") and a small script that moves each photo to keep the head in its window (make.fill's head box).
CAL_SCRIPT = r"""<script id="cal-faces">
(() => {
  let F = null;
  const key = im => im.dataset.k || ((m => m && m[1] + '/' + decodeURIComponent(m[2]))(im.src.match(/\/s\/(.+?)\/([^\/?]+)$/)));
  function place(im) {
    const f = F && F[key(im)];
    if (!f) return;
    if (!im.complete || !im.naturalWidth) { im.addEventListener('load', () => place(im), {once: true}); return; }
    const w = im.clientWidth, h = im.clientHeight, iw = im.naturalWidth, ih = im.naturalHeight;
    if (!w || !h) return;
    const k = Math.max(w / iw, h / ih), cw = w / k, ch = h / k;
    const fx = f[0] * iw, fy = f[1] * ih, fw = f[2] * iw, fh = f[3] * ih, top = fy - .9 * fh, bottom = fy + 1.4 * fh;
    let x0 = fx + fw / 2 - cw / 2, y0 = Math.min(top, Math.max(bottom - ch, top - ch * .1));
    x0 = Math.min(Math.max(0, x0), iw - cw); y0 = Math.min(Math.max(0, y0), ih - ch);
    im.style.objectPosition = `${iw - cw > 1 ? x0 / (iw - cw) * 100 : 50}% ${ih - ch > 1 ? y0 / (ih - ch) * 100 : 50}%`;
  }
  const all = () => document.querySelectorAll('.win img').forEach(place);
  fetch('/data/calendar.json').then(r => r.json()).then(d => { F = d.f || {}; all(); }).catch(() => {});
  new MutationObserver(l => l.forEach(r => r.addedNodes.forEach(n => n.nodeType === 1 &&
    (n.matches('.win img') ? [n] : n.querySelectorAll('.win img')).forEach(place)))).observe(document.documentElement, {childList: true, subtree: true});
  addEventListener('resize', all);
})();
</script>"""


def calfaces(a):
    faces = R_faces(a.faces)
    path = os.path.join(a.site, 'data', 'calendar.json')
    c = json.load(open(path, encoding='utf-8'))
    c['f'] = {}
    for days in c['m'].values():
        for d in days:
            if len(d) > 5:
                rec = faces.get(f'{d[4]}/{d[5]}')
                if rec and rec[0] >= TG_SAME_PERSON:
                    c['f'][f'{d[4]}/{d[5]}'] = [round(v, 4) for v in rec[1:5]]
    json.dump(c, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    page = os.path.join(a.site, 'calendar', 'index.html')
    body = open(page, encoding='utf-8').read()
    if 'id="cal-faces"' not in body:
        open(page, 'w', encoding='utf-8').write(body.replace('</body>', CAL_SCRIPT + '\n</body>', 1))
    print(f"calendar: {len(c['f'])} photos framed by Bapa's face")


# ---------------------------------------------------------------- 2 the gentle finish

# make.polish: a light levels stretch, a little more red and a little less blue, then robes and skin drawn together.
# The browser can't run make.py on each photo, so the same finish is drawn with its filters, matched to make.polish
# on 28 photos of Bapa (one a year, least squares: half the difference left of none). The share pictures, made here
# in Python, get make.polish itself.
LOOK_D = 'brightness(.98) contrast(1.1) saturate(1.13) sepia(.07)'
LOOK_CSS = ('<style id="look-d">/* the On this day picture\'s finish, look D (Darpan, 19 Oct 2026) */'
            'img[src*="photos.bapas-diary.com/"],img[src^="p/"],img[src*="/p/"],.photo img,.thumb img,.vframe img'
            '{filter:%s}</style>' % LOOK_D)


def look(a):
    n = 0
    for path in glob.glob(os.path.join(a.out, '**', '*.html'), recursive=True):
        body = open(path, encoding='utf-8').read()
        if 'id="look-d"' in body or '</head>' not in body:
            continue
        open(path, 'w', encoding='utf-8').write(body.replace('</head>', LOOK_CSS + '\n</head>', 1))
        n += 1
    print(f'look D on {n} pages')


def polish(photo, radius=1):
    """make.polish, for pictures this website makes in Python (the share a day pictures)."""
    import numpy as np
    from PIL import Image, ImageFilter, ImageOps
    photo = ImageOps.autocontrast(photo.convert('RGB'), cutoff=(.2, .1), preserve_tone=True)
    photo = photo.filter(ImageFilter.UnsharpMask(radius=radius, percent=45, threshold=4))
    arr = np.asarray(photo).astype(np.float32)
    arr[..., 0] *= 1.025
    arr[..., 2] *= .965
    return rich_skin(Image.fromarray(arr.clip(0, 255).astype(np.uint8)))


def rich_skin(photo, hue_k=.3, sat_up=.22):
    """make.rich_skin: in orange and skin hues only, robes and skin drift toward each other and paler warm areas gain a
    little richness. Reds, blues, gold, greys, white cloth and deep shadows are left alone."""
    import cv2, numpy as np
    from PIL import Image
    hsv = cv2.cvtColor(np.asarray(photo), cv2.COLOR_RGB2HSV_FULL).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    w = np.clip((h - 6) / 6, 0, 1) * np.clip((44 - h) / 8, 0, 1)
    w *= np.clip((v - 40) / 40, 0, 1) * np.clip((s - 60) / 50, 0, 1)
    hsv[..., 0] = h + hue_k * w * (19 - h)
    hsv[..., 1] = s + sat_up * w * np.clip(200 - s, 0, None)
    return Image.fromarray(cv2.cvtColor(hsv.clip(0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB_FULL))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('captions'); s.add_argument('--db', action='append', required=True); s.set_defaults(fn=captions)
    s = sub.add_parser('tg'); s.add_argument('--db', required=True); s.add_argument('--drive', required=True); s.add_argument('--out', required=True); s.set_defaults(fn=tg)
    s = sub.add_parser('day'); s.add_argument('--day', required=True); s.add_argument('--db', required=True)
    s.add_argument('--faces'); s.add_argument('--tg'); s.set_defaults(fn=day)
    s = sub.add_parser('calendar'); s.add_argument('--db', action='append', required=True); s.set_defaults(fn=calendar)
    s = sub.add_parser('calfaces'); s.add_argument('--site', required=True); s.add_argument('--faces', required=True); s.set_defaults(fn=calfaces)
    s = sub.add_parser('look'); s.add_argument('--out', required=True); s.set_defaults(fn=look)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
