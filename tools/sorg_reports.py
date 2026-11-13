"""Bapa's day by day vicharan reports from the old BAPS website, swaminarayan.org, for the website (Darpan, 13 Nov 2026:
"Vicharan reports on each day. The written report of what Bapa did that day, shown under the photos on a clicked
Calendar day" and "Travels filled in for the early years. The same reports say where Bapa was each day").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from swaminarayan.org. It reads the
detail list the "Collect other BAPS websites" thread makes from its saved copy (pages.jsonl, release `database` asset
swaminarayan-org-pages.jsonl, tools/sites_index.py on branch claude/project-thread-2nikpj).

    python3 tools/sorg_reports.py --pages swaminarayan-org-pages.jsonl --out out/data/reports --full sorg-reports.jsonl --days sorg-days.json

Each travelogue page (vicharan/YYYY/MM/NN/index.htm) has a heading for every day it tells:
    "22 April 2004 (V.S. 2060, Vaishakh sud 3) Thursday, Amdavad"
    "11 October 2002 (V.S. 2058, Aso sud 6) Friday, Mandvi, Koday, Talvana, Khakhar, Bhuj"
    "2 April 2001 (V.S.2057, Chaitra Sud 9) Monday, Mumbai, 221st Hari Jayanti Festival"
and, after the days, short prasangs: a title heading ("Time Management") then a dated heading ("24 April 2004, (V.S.
2060, Vaishakh sud 5) Saturday, London"). Many pages also have "Swamishri's Itinerary": every day of the fortnight and
the places he went ("1 to 4: Gandhinagar", "11: Mandvi, Koday, Talvana, Khakhar, Bhuj").

Writes
  out/MM-DD.json        {"2004": [{"pl": ["Amdavad"], "o": "occasion", "w": [paragraphs]}, {"k": "p", "t": "Time Management",
                         "pl": [...], "w": [...]}]}   the Calendar's day box (live/photos/index.html) shows these under the photos.
                         English date only: the Indian date in the heading is left out (Darpan: English date always).
                         No source line on the website (Darpan: the source is "only needed for our database").
  --full FILE           the same, one line per day or prasang, with the page address, the heading exactly as written and
                         where each place came from, for the database export (Darpan, 13 Nov 2026: full detail)
  --days FILE           {"YYYY-MM-DD": {"pl": [places in the order he went], "from": "heading" | "itinerary"}} for Travels
"""
import argparse, collections, json, os, re, sys

MONTHS = 'january february march april may june july august september october november december'.split()
MON = {m: i + 1 for i, m in enumerate(MONTHS)}
MON.update({m[:3]: i + 1 for i, m in enumerate(MONTHS)})
MON['sept'] = 9
MRX = '|'.join(sorted(MON, key=len, reverse=True))
WDAYS = 'monday tuesday wednesday thursday friday saturday sunday'.split()
WRX = '|'.join(WDAYS)
# "22 April 2004 (V.S. 2060, Vaishakh sud 3) Thursday, Amdavad", "1 February 1999 : Monday (Maha vad 1) , Badalpur",
# "24 Sept. 99: Friday (Bhadarva Sud 14, V.S. 2055), Mwanza", "24 April 2004, (V.S. 2060, ...) Saturday, London"
DAYHEAD = re.compile(r'^\s*(\d{1,2})(?:st|nd|rd|th)?\s+(' + MRX + r')\.?,?\s+\'?(\d{4}|\d{2})\b\s*[,:]?\s*(?:\([^)]*\)\s*)?[,:]?\s*'
                     r'(' + WRX + r')\b\s*(?:\([^)]*\)\s*)?[,:]?\s*(.*)$', re.I)
# the itinerary's day labels: "1 to 4:", "15 & 16:", "19:"
LABEL = re.compile(r'^\s*(\d{1,2})(?:\s*(?:to|&|-|and)\s*(\d{1,2}))?\s*:\s*$', re.I)
MONTHHEAD = re.compile(r'^\s*(' + MRX + r')\.?,?\s+(\d{4})\s*$', re.I)
NOT_PLACE = re.compile(r'\b(festival|day|jayanti|mahotsav|celebration|utsav|parayan|sabha|ceremony|assembly|shibir|'
                       r'convention|pratishtha|samaiyo|samaiya|diksha|patotsav|annakut|diwali|janmashtami|ekadashi|'
                       r'purnima|punam|anniversary|inauguration|function|program|programme|parva|yatra|abhishek|'
                       r'mandir|darshan|vidhi|puja|samarpan|samaroh|nirvan|vihar|katha)\b', re.I)
FOOT = re.compile(r'^\s*\|\s*Home\b', re.I)


def flat(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def year4(y):
    y = int(y)
    return y if y > 999 else (1900 + y if y > 50 else 2000 + y)


def day_iso(d, m, y):
    try:
        return f'{year4(y):04d}-{MON[m.lower().rstrip(".")]:02d}-{int(d):02d}'
    except (KeyError, ValueError):
        return ''


def split_places(rest, known):
    """'Mumbai, 221st Hari Jayanti Festival' -> (['Mumbai'], '221st Hari Jayanti Festival')
    'Mandvi, Koday, Talvana, Khakhar, Bhuj' -> (['Mandvi', 'Koday', 'Talvana', 'Khakhar', 'Bhuj'], '')"""
    places, other = [], []
    for seg in [flat(x).strip(' .:;') for x in re.split(r',', rest)]:
        if not seg:
            continue
        if other:   # once the words are an occasion, the rest belongs to it
            other.append(seg)
            continue
        low = seg.lower()
        if low in known or (re.fullmatch(r"[A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,2}", seg) and not NOT_PLACE.search(seg)
                            and low not in ('india', 'uk', 'usa', 'u.k.', 'u.s.a.')):
            places.append(seg)
        else:
            other.append(seg)
    return places, ', '.join(other)


def lines_of(words):
    """the page's lines, with a date heading that the page source broke over two lines put back together
    ("8 October\n2002 (V.S. 2058, Aso sud 2) Tuesday, Gandhidham, Bhuj")"""
    raw = [flat(l) for l in (words or '').split('\n')]
    out = []
    for l in raw:
        if not l:
            out.append('')
            continue
        if out and out[-1] and re.fullmatch(r'\d{1,2}(?:st|nd|rd|th)?(?:\s+(?:' + MRX + r')\.?)?', out[-1], re.I):
            out[-1] = out[-1] + ' ' + l
        else:
            out.append(l)
    return out


def paragraphs(lines):
    """the report's paragraphs: a blank line always ends one; without blank lines (a page source that wrapped every few
    words), a line that ends a sentence and is clearly shorter than the usual line ends one too"""
    lines = list(lines)
    if any(not l for l in lines):
        paras, cur = [], []
        for l in lines + ['']:
            if l:
                cur.append(l)
            elif cur:
                paras.append(' '.join(cur)); cur = []
        return [p for p in paras if p]
    full = sorted(len(l) for l in lines if l)
    usual = full[len(full) * 3 // 4] if full else 60
    paras, cur = [], []
    for l in lines:
        cur.append(l)
        if re.search(r'[.!?]["”’\']?$', l) and len(l) < .7 * usual:
            paras.append(' '.join(cur)); cur = []
    if cur:
        paras.append(' '.join(cur))
    return [re.sub(r'\s+([,.;:!?])', r'\1', p).strip() for p in paras if p.strip()]


def itinerary(lines, i, known):
    """'Swamishri's Itinerary' at line i: the month, the day labels, then as many lines of places"""
    j, month = i + 1, None
    while j < min(len(lines), i + 6):
        m = MONTHHEAD.match(lines[j])
        if m:
            month = (int(m[2]), MON[m[1].lower().rstrip('.')])
            j += 1
            break
        j += 1
    if not month:
        return {}
    labels = []
    while j < len(lines) and (LABEL.match(lines[j]) or not lines[j]):
        if lines[j]:
            m = LABEL.match(lines[j])
            labels.append((int(m[1]), int(m[2] or m[1])))
        j += 1
    vals = []
    while j < len(lines) and len(vals) < len(labels):
        l = lines[j]
        j += 1
        if not l:
            continue
        if l.startswith('(') and vals:   # "(Kachchh)" belongs to the line above
            continue
        vals.append(l)
    out = {}
    if len(vals) != len(labels):
        return out
    y, mo = month
    for (a, b), v in zip(labels, vals):
        pl = [flat(x).strip(' .') for x in re.split(r',', re.sub(r'\([^)]*\)', ' ', v)) if flat(x).strip(' .')]
        if not pl or any(re.search(r'\d', p) for p in pl):
            continue
        for d in range(a, b + 1):
            try:
                out[f'{y:04d}-{mo:02d}-{d:02d}'] = pl
            except ValueError:
                pass
    return out


def read_page(pg, known):
    """one travelogue page -> (day reports, prasangs, itinerary); a prasang keeps its own title (the short heading just
    before its dated heading), and every dated heading after the first prasang is a prasang too"""
    lines = lines_of(pg.get('words', ''))
    heads = [i for i, l in enumerate(lines) if DAYHEAD.match(l)]
    itin = {}
    for i, l in enumerate(lines):
        if re.search(r"itinerary", l, re.I) and len(l) < 40:
            itin.update(itinerary(lines, i, known))
    days, prs, title, in_pr = [], [], '', False
    for n, i in enumerate(heads):
        m = DAYHEAD.match(lines[i])
        date = day_iso(m[1], m[2], m[3])
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        body = []
        for k in range(i + 1, end):
            if FOOT.match(lines[k]):
                break
            body.append(lines[k])
        while body and not body[-1]:
            body.pop()
        next_title = ''
        if n + 1 < len(heads) and body and len(body[-1]) < 60 and not re.search(r'[.!?,;:"”]$', body[-1]):
            next_title = body.pop()
        if title:
            in_pr = True
        w = [p for p in paragraphs(body) if not re.fullmatch(r'(Download|\(.*KB\)|.*Mp3.*KB.*)', p, re.I)]
        places, occasion = split_places(m[5], known)
        it = dict(date=date, heading=flat(lines[i]), pl=places, o=occasion, w=w)
        if date and w:
            if in_pr:
                it['t'] = title
                prs.append(it)
            else:
                days.append(it)
        title = next_title
    return days, prs, itin


def known_places(paths):
    """towns the website already knows (Travels and the photos' places), so 'Bhuj' is a place and 'Bal-Kishore Day' is not"""
    k = set()
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        if isinstance(d, dict):
            for key, v in d.items():
                k.add(key.lower())
                if isinstance(v, dict):
                    for n in v.get('names', []) + [v.get('name', ''), (v.get('place') or '').split(',')[0]]:
                        if n:
                            k.add(n.lower().strip())
        elif isinstance(d, list):
            k.update(str(x).lower() for x in d)
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True, help='pages.jsonl from tools/sites_index.py')
    ap.add_argument('--out', required=True, help='folder for MM-DD.json (the day box)')
    ap.add_argument('--full', help='every day and prasang with its source, for the database export')
    ap.add_argument('--days', help='places by day, for Travels')
    ap.add_argument('--known', nargs='*', default=['places.json'], help='place lists (places.json, a Travels places dump)')
    a = ap.parse_args()
    known = known_places(a.known)
    by_md = collections.defaultdict(lambda: collections.defaultdict(list))
    places = {}
    full = open(a.full, 'w', encoding='utf-8') if a.full else None
    pages = n_days = n_pr = 0
    seen = set()
    for line in open(a.pages, encoding='utf-8'):
        try:
            pg = json.loads(line)
        except ValueError:
            continue
        url = pg.get('page_url', '')
        if pg.get('section') != 'vicharan' and '/vicharan/' not in url:
            continue
        days, prs, itin = read_page(pg, known)
        if not (days or prs or itin):
            continue
        pages += 1
        for d, pl in itin.items():
            places.setdefault(d, {'pl': pl, 'from': 'itinerary'})
        for kind, items in (('r', days), ('p', prs)):
            for it in items:
                key = (it['date'], kind, it.get('t', ''), it['w'][0][:80])
                if key in seen:   # the same day told on two pages (a summary page and its fortnight)
                    continue
                seen.add(key)
                y, md = it['date'][:4], it['date'][5:]
                row = {'pl': it['pl'], 'w': it['w']}
                if it['o']:
                    row['o'] = it['o']
                if kind == 'p':
                    row['k'] = 'p'
                    row['t'] = it.get('t', '')
                by_md[md][y].append(row)
                if kind == 'r' and it['pl']:
                    places[it['date']] = {'pl': it['pl'], 'from': 'heading'}
                if full:
                    full.write(json.dumps(dict(site='swaminarayan.org', kind='prasang' if kind == 'p' else 'day report',
                                               date=it['date'], heading_as_written=it['heading'], title=it.get('t', ''),
                                               places=it['pl'], places_from='the day heading', occasion=it['o'],
                                               paragraphs=it['w'], page_url=url, page_title=pg.get('title', ''),
                                               page_drive_path=pg.get('drive_path', '')), ensure_ascii=False) + '\n')
                n_days += kind == 'r'
                n_pr += kind == 'p'
    os.makedirs(a.out, exist_ok=True)
    for md, years in by_md.items():
        # day reports first, then that day's prasangs, years in order
        doc = {y: sorted(v, key=lambda r: r.get('k') == 'p') for y, v in sorted(years.items())}
        json.dump(doc, open(os.path.join(a.out, md + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    if a.days:
        json.dump(dict(sorted(places.items())), open(a.days, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    yrs = collections.Counter(d[:4] for d in places)
    print(f'swaminarayan.org reports: {pages:,} pages, {n_days:,} day reports, {n_pr:,} prasangs, '
          f'{len(by_md):,} calendar days, places for {len(places):,} days ({", ".join(f"{y}: {n}" for y, n in sorted(yrs.items()))})')


if __name__ == '__main__':
    main()
