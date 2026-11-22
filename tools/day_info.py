"""Everything else we know about each day of Bapa's life, gathered into one small file per date for the 2pm picture
(Darpan, 16 Nov 2026: 'always try to use all the new information we have collected about Bapa's days').

    python3 tools/day_info.py FOLDER            writes archive/days/MM-DD.json and archive/days/captions.json

FOLDER holds the files the website project keeps (nothing here is read from baps.org or any other site):
  release swaminarayan-org-web:  sorg-reports.jsonl  sorg.db  sorg-same.json  sorg-days.json  sorg-captions.json
                                 face2-YEAR-sorg.json.gz
  release database:              akshardham-com-pages.jsonl  akshardham-com-photos.jsonl
  the website branch:            prasang.json  (data/baps/prasang.json)  bio.json  (data/bio/bio.json)
                                 youtube-days.json  (data/youtube/days.json)
  release database (21 Nov 2026): SITE-pages.jsonl  SITE-photos.jsonl  for each site in MORE_SITES (the whole files, or
                                 only the pages that give one exact date and name Bapa, with those pages' photos)

archive/days/MM-DD.json, one entry per year that has anything:
  {"YYYY": {"pl": [towns Bapa was in, in order],
            "o":  "the occasion the old BAPS website gave the day",
            "w":  [the day report's paragraphs, as written at the time],
            "pr": [{"t": title, "pl": [towns], "w": [paragraphs]}],             prasangs of that day
            "ds": [{"t": title, "p": place, "who": "psm" or "msm", "w": [...]}],  Daily Satsang prasangs, in English
            "st": [{"t": title, "p": place, "w": [...], "ph": [Drive paths]}],   other sites' stories of that day (akshardham.com,
                                                                                 the old swaminarayan.org News, mandir.org, the kids sites...)
            "jc": [{"t": heading, "p": place, "w": [...]}],                      the Jivan Charitra life story (1921 to 1975)
            "yt": [occasion],                                                    what BAPS's own videos of that exact day call it
            "ph": [[album, file, caption, Drive path]]}}                         old website photos that show Bapa clearly

Where each thing came from stays in these files and is never drawn on a picture. make.py reads them (day_info) and never
needs any website to be up.
"""
import collections, glob, gzip, html, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, 'archive', 'days')
SAME_PERSON = .5      # make.py's own face check: Bapa recognised
MIN_SIDE = 400        # a smaller file is a thumbnail and can't make a card
MONTHS = 'January February March April May June July August September October November December'.split()
HEADING = re.compile(rf"\s*\d{{1,2}}(?:st|nd|rd|th)? (?:{'|'.join(MONTHS)}) \d{{4}}\s*\(V\.?\s?S\.?")   # another day's heading run into the words


def clean(p):
    """A paragraph as the old website wrote it, without another day's heading run into it or the broken half sentence
    such a join leaves behind."""
    p = re.sub(r'<br\s*/?>', ' ', p or '')
    p = ' '.join(p.split())
    m = HEADING.search(p)
    if m:
        p = p[:m.start()]
    sents = re.split(r'(?<=[.!?”"])\s+(?=[A-Z“"‘\'(0-9])', p)
    sents = [s for k, s in enumerate(sents) if k == 0 or not re.match(r'[a-z]', s)]
    out = []
    for s in sents:   # 'six BAPS hari mandirs; ... and Sathvav. accounts books by showering ...': the part after the join goes
        m = re.search(r'\.\s+(?=[a-z])', s)
        out.append(s[:m.start() + 1] if m else s)
    return ' '.join(out).strip()


def reports(folder, days):
    for line in open(os.path.join(folder, 'sorg-reports.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        d = r.get('date') or ''
        if not re.fullmatch(r'\d{4}-\d\d-\d\d', d):
            continue
        y = days[d[5:]].setdefault(d[:4], {})
        paras = [p for p in (clean(p) for p in r.get('paragraphs') or []) if p]
        towns = [t for t in r.get('places') or [] if t]
        if r.get('kind') == 'prasang':
            if paras:
                y.setdefault('pr', []).append({'t': (r.get('title') or '').strip(), 'pl': towns, 'w': paras})
            continue
        for t in towns:
            if t not in y.setdefault('pl', []):
                y['pl'].append(t)
        occ = (r.get('occasion') or '').strip()
        if occ and occ not in y.get('o', ''):
            y['o'] = (y['o'] + ' and ' + occ) if y.get('o') else occ
        y.setdefault('w', []).extend(p for p in paras if p not in y.get('w', []))


def towns_of_days(folder, days):
    """The towns of every day the old website's travel pages give, for a year with no report of its own."""
    path = os.path.join(folder, 'sorg-days.json')
    if not os.path.exists(path):
        return
    for d, v in json.load(open(path, encoding='utf-8')).items():
        if re.fullmatch(r'\d{4}-\d\d-\d\d', d) and v.get('pl'):
            y = days[d[5:]].setdefault(d[:4], {})
            if not y.get('pl'):
                y['pl'] = [t for t in v['pl'] if t]


def satsang(folder, days):
    path = os.path.join(folder, 'prasang.json')
    if not os.path.exists(path):
        return
    for v in json.load(open(path, encoding='utf-8')).values():
        d = v.get('d') or ''
        if re.fullmatch(r'\d{4}-\d\d-\d\d', d) and v.get('en'):
            days[d[5:]].setdefault(d[:4], {}).setdefault('ds', []).append(
                {'t': (v.get('title') or '').strip(), 'p': v.get('place') or '', 'who': v.get('who') or '', 'w': [' '.join(p.split()) for p in v['en'] if p.strip()]})


def life_story(folder, days):
    """The Jivan Charitra study (Pramukh Swami Maharaj's life, 1921 to 1975, data/bio/bio.json on the website branch):
    each day it gives, with its place, heading and story. Only days it is sure of (not 'Unsure (day)', not worked out);
    the dates Darpan has not checked yet are not in the file at all."""
    path = os.path.join(folder, 'bio.json')
    if not os.path.exists(path):
        return 0
    n = 0
    for years in json.load(open(path, encoding='utf-8')).get('days', {}).values():
        for es in years.values():
            for e in es:
                d = e.get('d') or ''
                if not re.fullmatch(r'\d{4}-\d\d-\d\d', d) or e.get('prec') != 'Day' or 'day' in (e.get('conf') or '').lower():
                    continue
                days[d[5:]].setdefault(d[:4], {}).setdefault('jc', []).append(
                    {'t': (e.get('h') or '').strip(), 'p': e.get('pl') or '', 'w': [' '.join(p.split()) for p in e.get('w') or [] if p.strip()]})
                n += 1
    return n


def photos(folder, days):
    faces = {}
    for f in glob.glob(os.path.join(folder, 'face2-*-sorg.json.gz')):
        faces.update(json.loads(gzip.open(f).read()))
    same = {(s['album'], s['file']) for s in json.load(open(os.path.join(folder, 'sorg-same.json'), encoding='utf-8'))}   # a photo baps.org has too: already in the picture's lists
    db = sqlite3.connect(os.path.join(folder, 'sorg.db'))
    n = 0
    for date, place, album, file, cap, rel in db.execute(
            'SELECT date, place, album, file, caption, local_path FROM photos WHERE date IS NOT NULL AND local_path IS NOT NULL ORDER BY album, rowid'):
        f = faces.get(f'{album}/{file}')
        if not f or (album, file) in same or not re.fullmatch(r'\d{4}-\d\d-\d\d', date or ''):
            continue
        sim, other, w, h = f[0], f[11] if len(f) > 11 else 0, f[8], f[9]
        if sim < SAME_PERSON or other >= sim or max(w, h) < MIN_SIDE:   # Bapa clearly seen, and big enough to show
            continue
        cap = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', cap or '')).split())
        y = days[date[5:]].setdefault(date[:4], {})
        y.setdefault('ph', []).append([album, file, cap, rel] + ([place] if place else []))
        n += 1
    db.close()
    return n


def site_stories(folder, days):
    """akshardham.com's own news stories (a president, a prime minister, a delegation visiting): the story as written,
    under the day it says it happened. A story whose words name another full date than the one under its title is left
    out (the exact day told in the story is the day, never a listing date alone)."""
    path = os.path.join(folder, 'akshardham-com-pages.jsonl')
    if not os.path.exists(path):
        return 0
    shots = collections.defaultdict(list)
    for line in open(os.path.join(folder, 'akshardham-com-photos.jsonl'), encoding='utf-8'):
        p = json.loads(line)
        u = p.get('photo_url') or ''
        if '/wp-content/uploads/' in u and re.search(r'\.jpe?g$', u, re.I) and not re.search(r'-\d+x\d+\.jpe?g$', u, re.I) and int(p.get('bytes') or 0) > 30000:
            if p['drive_path'] not in shots[p['page_url']]:
                shots[p['page_url']].append(p['drive_path'])
    month = {m.lower(): k + 1 for k, m in enumerate(MONTHS)}
    full = rf"(?:(\d{{1,2}})(?:st|nd|rd|th)? ({'|'.join(MONTHS)}),? (\d{{4}})|({'|'.join(MONTHS)}) (\d{{1,2}})(?:st|nd|rd|th)?,? (\d{{4}}))"
    def dates(text):
        out = []
        for m in re.finditer(full, text):
            d, mo, y = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(5), m.group(4), m.group(6))
            out.append(f'{int(y):04}-{month[mo.lower()]:02}-{int(d):02}')
        return out
    n = 0
    for line in open(path, encoding='utf-8'):
        r = json.loads(line)
        url = r.get('page_url') or ''
        if '/testimonial/' in url or not shots.get(url):
            continue
        body = r.get('words') or ''
        body = body[body.rfind('CONTACT US') + 10:] if 'CONTACT US' in body else body
        body = re.split(r'\n\s*BAPS News\s*\n', body)[0]
        paras = [' '.join(p.split()) for p in body.split('\n\n') if p.strip()]
        if len(paras) < 3 or not dates(paras[1]) or len(paras[1]) > 30:
            continue
        title, when, words = paras[0], dates(paras[1])[0], paras[2:]
        if len(words) > 1 and len(re.findall(r'[.!?](?:\s|$)', words[0])) < len(words[0].split()) / 40:   # the photo captions run together
            words = words[1:]
        told = set(dates(' '.join(words)))
        if told - {when} or len(' '.join(words)) < 300:
            continue
        place = 'Gandhinagar' if 'Gandhinagar' in title else 'New Delhi'
        days[when[5:]].setdefault(when[:4], {}).setdefault('st', []).append({'t': title, 'p': place, 'w': words, 'ph': shots[url][:8]})
        n += 1
    return n


MORE_SITES = ('swaminarayan-org', 'wayback-mandir-org', 'wayback-kids-swaminarayan-org', 'kids-baps-org', 'londonmandir-baps-org', 'research-baps-org')
GURU_CHANGE = '2016-08-13'
# Bapa himself there that day: 'in the presence of Pramukh Swami Maharaj', 'Swamishri blessed the assembly'
PRESENT = re.compile(r"in the (?:divine )?presence of (?:His Holiness |HH |Param Pujya )?(Pramukh|Mahant) Swami|"
                     r"(Swamishri|Pramukh Swami Maharaj|Mahant Swami Maharaj) (?:also |then |personally |himself )?(?:arrived|visited|blessed|performed|"
                     r"inaugurated|presided|graced|consecrated|sanctified|addressed|met|welcomed|greeted|was welcomed|gave darshan|laid|unveiled|attended|led)\b", re.I)
ELSEWHERE = re.compile(r"\b(?:years? ago|previous|earlier (?:that|this) (?:day|year)|webcast|video|montage|live telecast|in (?:19|20)\d\d\b|will |to be held|announce)", re.I)


def more_sites(folder, days):
    """Darpan, 21 Nov 2026 ('would be nice to add all this information in, as best as possible, when appropriate'): the
    other sites the website project saved (the old swaminarayan.org News, the old London mandir.org, the kids sites,
    londonmandir.baps.org, research.baps.org). A page joins a day only when it gives one exact date and says Bapa himself
    was there (Pramukh Swami Maharaj before 13 Aug 2016, Mahant Swami Maharaj after), in a sentence about that day, not a
    memory of another year, a webcast or an announcement. Its photos: only ones whose own words name Bapa."""
    n = 0
    for site in MORE_SITES:
        path = os.path.join(folder, site + '-pages.jsonl')
        if not os.path.exists(path):
            continue
        shots = collections.defaultdict(list)
        ph = os.path.join(folder, site + '-photos.jsonl')
        for line in open(ph, encoding='utf-8') if os.path.exists(ph) else []:
            p = json.loads(line)
            words = ' '.join(p.get(k) or '' for k in ('caption', 'alt', 'words_beside'))
            if p.get('size') != 'small' and re.search(r'Swamishri|Pramukh Swami|Mahant Swami|Bapa\b', words) and re.search(r'\.jpe?g$', p.get('drive_path') or '', re.I):
                if p['drive_path'] not in shots[p['page_url']]:
                    shots[p['page_url']].append(p['drive_path'])
        seen = set()
        for line in open(path, encoding='utf-8'):
            r = json.loads(line)
            d = r.get('date_first') or ''
            if not re.fullmatch(r'\d{4}-\d\d-\d\d', d) or d != r.get('date_last') or d < '1950':
                continue
            paras = []
            for p in (' '.join(p.split()) for p in (r.get('words') or '').split('\n\n')):
                if re.match(r'(?i)(recent (news|posts)|previous post|share:|related)', p):
                    break
                if len(p.split()) >= 20 and re.search(r'[.!?](\s|$)', p):
                    paras.append(p)
            text = ' '.join(paras)
            guru = 'Pramukh' if d < GURU_CHANGE else 'Mahant'
            ok = False
            for sent in re.split(r'(?<=[.!?])\s+', text):
                m = PRESENT.search(sent)
                who = m and (m.group(1) or m.group(2) or '')
                if m and (who.lower() == 'swamishri' or who.lower().startswith(guru.lower())) and not ELSEWHERE.search(sent) \
                        and not any(y != d[:4] for y in re.findall(r'\b(?:19|20)\d\d\b', sent)):
                    ok = True
                    break
            title = re.sub(r'^\s*(?:News of BAPS|BAPS Kidz News|News & Events-News|News|Announcements)\s*-\s*', '', r.get('title') or '')
            title = re.sub(r'\s*[-|–]\s*(?:BAPS[^-|–]*|Shri Swaminarayan Mandir[^-|–]*)$', '', title).strip(' -–|')
            if not ok or not title or title.startswith('–') or (d, title[:40]) in seen:
                continue
            seen.add((d, title[:40]))
            y = days[d[5:]].setdefault(d[:4], {})
            told = ' '.join(y.get('w') or []).lower()
            if paras and paras[0].lower()[:80] in told:   # the old website's day report already says it
                continue
            y.setdefault('st', []).append({'t': title, 'p': r.get('place') or '', 'w': paras[:12], 'ph': shots.get(r['page_url'], [])[:8]})
            n += 1
    return n


def videos(folder, days):
    """What BAPS's own videos of one exact day call it, when that is more than 'Guruhari Darshan' ('Parshad Diksha',
    'Diwali Celebration'): a line for a card that says nothing of its day."""
    path = os.path.join(folder, 'youtube-days.json')
    if not os.path.exists(path):
        return 0
    mon = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?'
    n = 0
    for d, vs in json.load(open(path, encoding='utf-8')).items():
        if not re.fullmatch(r'\d{4}-\d\d-\d\d', d):
            continue
        for v in vs:
            t = ' '.join((v.get('title') or '').split())
            if re.search(rf'\d{{1,2}}\s*(?:-|to)\s*\d{{1,2}}\s+{mon}|{mon}\s+\d{{1,2}}\s*(?:-|to)\s*\d', t):   # a video of several days
                continue
            parts = [p.strip() for p in re.split(r'[,:|]', t) if p.strip()]
            occ = next((p for p in parts if not re.search(rf'(?i)guruhari|darshan$|ashirwad|\b(?:19|20)\d\d\b|{mon}|india|usa|uk\b|^\d', p)
                        and len(p.split()) >= 2), '')
            occ = occ.split(' - ')[-1]
            occ = re.sub(r'(?i)\s*(?:with|of)\s+(?:HH|His Holiness|Param Pujya)?\s*(?:Pramukh|Mahant) Swami Maharaj\b', '', occ).strip()
            occasion = re.compile(r"(?i)celebrat|utsav|mahotsav|diksha|\bdin\b|day\b|jayanti|purnima|ekadashi|diwali|annakut|new year|patotsav|"
                                  r"pratishtha|shilanyas|bhumi|inaugur|festival|samaiya|yagna|convention|shibir|holi|fuldol|janmashtami|navratri|dussehra|\brath")
            if occ and len(occ) < 60 and occasion.search(occ) and not re.search(r"(?i)pramukh swami maharaj's|mahant swami maharaj's|vicharan|highlights|live|katha|kirtan|^shri", occ):
                y = days[d[5:]].setdefault(d[:4], {})
                if occ not in y.setdefault('yt', []):
                    y['yt'].append(occ); n += 1
    return n


def old_captions(folder):
    """The old website's own caption for a baps.org photo whose baps.org caption is only its album's title."""
    path = os.path.join(folder, 'sorg-captions.json')
    if not os.path.exists(path):
        return {}
    out = {}
    for k, v in json.load(open(path, encoding='utf-8')).items():
        new, old = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', v.get('swaminarayan_org') or '')).split()), ' '.join(html.unescape(v.get('baps_org') or '').split())
        if new and new.lower().rstrip('. ') != old.lower().rstrip('. ') and len(new.split()) >= 3 and len(new) > len(old):   # only when the old website says more
            out[k.lower()] = [old, new]
    return out


def main():
    folder = sys.argv[1]
    days = collections.defaultdict(dict)
    reports(folder, days)
    towns_of_days(folder, days)
    satsang(folder, days)
    n_jc = life_story(folder, days)
    n_ph = photos(folder, days)
    n_st = site_stories(folder, days)
    n_more = more_sites(folder, days)
    n_yt = videos(folder, days)
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, '??-??.json')):
        os.remove(f)
    for mmdd, years in sorted(days.items()):
        years = {y: v for y, v in sorted(years.items()) if any(v.get(k) for k in ('w', 'pr', 'ds', 'st', 'ph', 'o', 'pl', 'jc', 'yt'))}
        json.dump(years, open(os.path.join(OUT, mmdd + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    caps = old_captions(folder)
    json.dump(caps, open(os.path.join(OUT, 'captions.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    count = lambda k: sum(len(v.get(k) or []) if k != 'w' else bool(v.get('w')) for ys in days.values() for v in ys.values())
    print(f"{len(days)} days: {count('w')} day reports, {count('pr')} prasangs, {count('ds')} Daily Satsang prasangs, "
          f"{n_st} akshardham.com stories, {n_more} stories from other sites, {n_yt} video occasions, {n_jc} Jivan Charitra days, {n_ph} old website photos of Bapa, {len(caps)} old captions")


if __name__ == '__main__':
    main()
