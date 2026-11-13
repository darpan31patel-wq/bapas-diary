"""Full detail for every page and photo copied from the other BAPS websites (Darpan, 13 Nov 2026: "Everything from
the other websites need to have full detail. So all the captions, all the date information, any location, where the
actual resource is from, so that when we export our master database, all the information is logged").

Reads the saved copy of a site (the files exactly as the site served them) and writes two lists:
  pages.jsonl   one line per page:  site, page address, Drive path, title, every heading, every English date the page
                names, the date range and place it is about, the words, every photo and every audio, zip or video link
  photos.jsonl  one line per photo: site, photo address, Drive path, the page and gallery it came from (address, title,
                heading), its caption (the site's caption, its alt text and the words printed next to it), the date
                (the nearest date written above it on the page, else the page's dates, else the month in the address,
                each kept as written and as YYYY-MM-DD), the place (from the caption, the gallery name, the heading,
                the address), whether it is the full size or the small copy and the other one's address, and the
                file's own details from the copy (bytes, type, the server's Last-Modified date) where known
Nothing is guessed silently: every field says where it came from (date_from, place_from).

    python3 tools/sites_index.py --site swaminarayan.org --files mirror --headers files.jsonl --out out
"""
import argparse, html, json, os, re, sys, urllib.parse

MONTHS = 'january february march april may june july august september october november december'.split()
MON = {m: i + 1 for i, m in enumerate(MONTHS)}
MON.update({m[:3]: i + 1 for i, m in enumerate(MONTHS)})
MON['sept'] = 9
MRX = '|'.join(sorted(MON, key=len, reverse=True))
# 18 to 23 May 2000 | 30 May to 2 June 2000 | 21 May, 2000 | 21st May 2000 | May 21, 2000 | May 2000
D1 = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:(' + MRX + r')\.?,?\s*)?(?:to|till|until|-|–|&|and)\s*(\d{1,2})'
                r'(?:st|nd|rd|th)?\s+(' + MRX + r')\.?,?\s+(\d{4})\b', re.I)
D2 = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + MRX + r')\.?,?\s+(\d{4})\b', re.I)
D3 = re.compile(r'\b(' + MRX + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b', re.I)
D5 = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + MRX + r')\.?,?\s+\'?(\d{2})\b(?!\d)', re.I)
D4 = re.compile(r'\b(' + MRX + r')\.?,?\s+(\d{4})\b', re.I)
FULLIMG = re.compile(r"""fullimage\w*\(\s*'((?:[^'\\]|\\.)*)'\s*,\s*'([^']+)'""", re.I)
IMG = re.compile(r'<img\b[^>]*>', re.I)
TOKEN = re.compile(r"""fullimage\w*\(\s*'(?:[^'\\]|\\.)*'\s*,\s*'[^']+'|<img\b[^>]*>""", re.I)
HEAD = re.compile(r'(?is)<(h[1-6]|b|strong|font[^>]*size\s*=\s*["\']?[3-7])[^>]*>(.*?)</(?:h[1-6]|b|strong|font)>')
OTHER = re.compile(r'\.(?:mp3|wav|wma|ram?|rm|zip|wmv|avi|mpe?g|mp4|mov|flv|swf)$', re.I)
NOT_PLACE = {'index', 'photo', 'photos', 'image', 'images', 'gallery', 'page', 'main', 'default'}


def text(s):
    s = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', s)
    s = re.sub(r'(?i)<br\s*/?>|</(p|div|tr|td|h\d|li|table)>', '\n', s)
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s)).replace('\xa0', ' ')
    s = re.sub(r'[ \t\r]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n', s).strip()


def flat(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def iso(y, m, d=None):
    try:
        y, m = int(y), MON[m.lower().rstrip('.')] if isinstance(m, str) else int(m)
        if d is not None:
            d = int(d)
            if not 1 <= d <= 31:
                return ''
            return f'{y:04d}-{m:02d}-{d:02d}'
        return f'{y:04d}-{m:02d}'
    except (KeyError, ValueError):
        return ''


def dates(s):
    """every English date written in s, in order: [{written, from, to}] (to = from for one day; a month alone is YYYY-MM)"""
    s = flat(s)
    out, used = [], []
    for rx, kind in ((D1, 'range'), (D2, 'day'), (D3, 'mdy'), (D5, 'day2'), (D4, 'month')):
        for m in rx.finditer(s):
            if any(a < m.end() and m.start() < b for a, b in used):
                continue
            g = m.groups()
            if kind == 'range':
                d0, m0, d1, m1, y = g
                f, t = iso(y, m0 or m1, d0), iso(y, m1, d1)
                if m0 and MON.get(m0.lower().rstrip('.'), 0) > MON.get(m1.lower().rstrip('.'), 0):
                    f = iso(int(y) - 1, m0, d0)
            elif kind == 'day':
                f = t = iso(g[2], g[1], g[0])
            elif kind == 'day2':
                yy = int(g[2])
                f = t = iso(1900 + yy if yy > 50 else 2000 + yy, g[1], g[0])
            elif kind == 'mdy':
                f = t = iso(g[2], g[0], g[1])
            else:
                f = t = iso(g[1], g[0])
            if f:
                used.append((m.start(), m.end()))
                out.append(dict(written=m.group(0), start=m.start(), **{'from': f, 'to': t}))
    out.sort(key=lambda x: x['start'])
    return out


def path_bits(path):
    """month and place from the address: vicharan/2000/05/02/photo/bharuch/index.htm -> 2000-05, Bharuch"""
    parts = path.split('/')
    section = parts[0] if len(parts) > 1 else ''
    m = re.match(r'[^/]+/(\d{4})(?:/(\d{2}))?', path)
    month = (m[1] + (f'-{m[2]}' if m[2] else '')) if m else ''
    place = ''
    pm = re.search(r'/photos?/([a-z][a-z0-9 _-]*)/', path, re.I)
    if pm:
        place = pm[1]
    else:
        fm = re.search(r'/([a-z][a-z _-]*?)\d*[ab]?\.html?$', path, re.I)
        if fm and fm[1].lower() not in NOT_PLACE:
            place = fm[1]
    place = re.sub(r'\d+$', '', place).replace('_', ' ').replace('-', ' ').strip().title()
    return section, month, place


def caption_place(cap):
    """'Releasing balloons ..., Mahelav' -> 'Mahelav' (the site writes the place after the last comma)"""
    m = re.search(r',\s*([A-Z][A-Za-z.\' ]{2,30}?)\s*\.?$', flat(cap))
    if m and len(m[1].split()) <= 3 and not dates(m[1]) and m[1].strip().lower() not in COUNTRIES:
        return m[1].strip()
    return ''


COUNTRIES = {'india', 'uk', 'u.k.', 'usa', 'u.s.a.', 'england', 'kenya', 'tanzania', 'uganda', 'canada', 'africa',
             'australia', 'new zealand', 'gujarat'}
DAYS = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}


def heading_place(h):
    """'Bharuch, 18 to 23 May 2000' -> 'Bharuch'; '24 Sept. 99: Friday (Bhadarva Sud 14, V.S. 2055), Mwanza' -> 'Mwanza';
    '17 February 1999, Wednesday, Atladra, India: Tribal Upliftment Day.' -> 'Atladra'"""
    h = flat(h)
    m = re.match(r'\s*([A-Z][A-Za-z.\' ]{2,30}?)\s*,\s*(?:\d|' + MRX + ')', h, re.I)
    if m and m[1].lower() not in DAYS:
        return m[1].strip()
    if not dates(h):
        return ''
    whole = re.sub(r'\([^)]*\)', ' ', h)
    for head in ([whole.split(':')[0]] if ':' in whole else []) + [whole]:
        for seg in reversed([x.strip(' .:') for x in head.split(',')]):
            if (re.fullmatch(r"[A-Z][A-Za-z.' ]{2,30}", seg) and seg.lower() not in DAYS
                    and seg.lower() not in COUNTRIES and not dates(seg) and not re.fullmatch(MRX, seg, re.I)):
                return seg
    return ''


def index_page(site, url, rel, raw, headers, base_url):
    body = raw.decode('cp1252', errors='replace')
    tm = re.search(r'(?is)<title>(.*?)</title>', body)
    title = flat(html.unescape(tm[1])) if tm else ''
    heads = [flat(text(h[1])) for h in HEAD.findall(body)]
    heads = [h for h in heads if 2 < len(h) < 200]
    words = text(body)
    pdates = dates(title + '\n' + words)
    section, month, ppath = path_bits(rel)
    hplace = next((heading_place(h) for h in heads if heading_place(h)), '')
    page_place = ppath or hplace
    media = set()
    for m in re.finditer(r"""(?:href|src)\s*=\s*["']?([^"'\s>]+)""", body, re.I):
        u = urllib.parse.urljoin(url, html.unescape(m[1]))
        if OTHER.search(urllib.parse.urlsplit(u).path):
            media.add(u)
    photos = []
    full_of = {}
    for cap, f in FULLIMG.findall(body):
        full_of[f.rsplit('/', 1)[-1].lower()] = cap
    last = 0
    for m in TOKEN.finditer(body):
        tok = m.group(0)
        before_html = body[:m.start()]
        near = flat(text(body[last:m.start()]))[-300:]
        last = m.end()
        if tok.lower().startswith('<img'):
            src = re.search(r"""src\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", tok, re.I)
            src = next((g for g in src.groups() if g), '') if src else ''
            if not src or re.search(r'\.gif$|/js/|\.js$', src, re.I):
                continue
            chrome = urllib.parse.urlsplit(urllib.parse.urljoin(url, src)).path.strip('/').split('/')
            if len(chrome) <= 3 and 'images' in chrome[:-1] and not re.search(r'\d', chrome[0]):
                continue   # the site's own buttons and banners (/images/home.jpg, /vicharan/images/photo.gif)
            alt = re.search(r"""(?:alt|title)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tok, re.I)
            alt = html.unescape(next((g for g in alt.groups() if g is not None), '')) if alt else ''
            u = urllib.parse.urljoin(url, html.unescape(src))
            kind, cap = 'small', ''
            stem = u.rsplit('/', 1)[-1]
            big = re.sub(r'h(\.\w+)$', r'f\1', stem, flags=re.I)
            if big.lower() in full_of:
                cap = full_of[big.lower()]
                other = u.rsplit('/', 1)[0] + '/' + big
            else:
                other = ''
        else:
            cm = FULLIMG.match(tok)
            cap, f = cm[1].replace("\\'", "'"), cm[2]
            u = urllib.parse.urljoin(url, f)
            kind, alt = 'full', ''
            small = re.sub(r'f(\.\w+)$', r'h\1', u.rsplit('/', 1)[-1], flags=re.I)
            other = u.rsplit('/', 1)[0] + '/' + small if small != u.rsplit('/', 1)[-1] else ''
        above = dates(text(before_html))
        heads_above = [flat(text(h[1])) for h in HEAD.findall(before_html)]
        heads_above = [h for h in heads_above if 2 < len(h) < 200]
        heading = heads_above[-1] if heads_above else ''
        cdates = dates(cap + ' ' + alt)
        if cdates:
            d, dfrom = cdates[-1], 'caption'
        elif above:
            d, dfrom = above[-1], 'written above the photo on the page'
        elif pdates:
            d, dfrom = pdates[0], 'page'
        elif month:
            d, dfrom = {'written': '', 'from': month, 'to': month}, 'address'
        else:
            d, dfrom = {'written': '', 'from': '', 'to': ''}, ''
        cplace = caption_place(cap) or caption_place(alt)
        hp = next((heading_place(h) for h in reversed(heads_above) if heading_place(h)), '')
        if cplace:
            place, pfrom = cplace, 'caption'
        elif ppath:
            place, pfrom = ppath, 'gallery address'
        elif hp:
            place, pfrom = hp, 'heading above the photo'
        else:
            place, pfrom = '', ''
        prel = urllib.parse.unquote(urllib.parse.urlsplit(u).path).lstrip('/')
        h = headers.get(u) or headers.get(u.replace('https://', 'http://')) or {}
        photos.append(dict(
            site=site, photo_url=u, drive_path=f'sites/{site}/{prel}', size=kind, other_size_url=other,
            caption=flat(cap), alt=flat(alt), words_beside=near,
            date=d.get('from', ''), date_to=d.get('to', ''), date_written=flat(d.get('written', '')), date_from=dfrom,
            place=place, place_from=pfrom, gallery_place=ppath, heading=heading,
            page_url=url, page_title=title, page_drive_path=f'sites/{site}/{rel}', section=section, page_month=month,
            page_dates=[flat(x['written']) for x in pdates[:10]],
            bytes=h.get('bytes'), content_type=h.get('type'), last_modified=h.get('last_modified'),
            fetched_at=h.get('fetched_at')))
    seen, uniq = set(), []
    for p in photos:   # the same photo linked twice on a page (thumbnail link and caption link): keep the fuller one
        k = (p['photo_url'], p['size'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(p)
    page = dict(site=site, page_url=url, drive_path=f'sites/{site}/{rel}', title=title, headings=heads[:60],
                section=section, month=month, place=page_place, place_from='address' if ppath else
                ('heading' if hplace else ''), dates=[{k: v for k, v in x.items() if k != 'start'} for x in pdates[:40]],
                date_first=pdates[0]['from'] if pdates else month, date_last=pdates[-1]['to'] if pdates else month,
                photos=len(uniq), media=sorted(media), words=words[:30000],
                last_modified=(headers.get(url) or {}).get('last_modified'),
                fetched_at=(headers.get(url) or {}).get('fetched_at'))
    return page, uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site', required=True)
    ap.add_argument('--files', required=True, help='the saved copy: <files>/<path on the site>')
    ap.add_argument('--base', default='', help='the site address, default https://www.<site>/')
    ap.add_argument('--headers', default='', help='files.jsonl from the copier (bytes, type, Last-Modified)')
    ap.add_argument('--out', default='out')
    a = ap.parse_args()
    base = a.base or f'https://www.{a.site}/'
    headers = {}
    if a.headers and os.path.exists(a.headers):
        for line in open(a.headers, encoding='utf-8'):
            try:
                r = json.loads(line)
                headers[r['url']] = r
            except Exception:
                pass
    os.makedirs(a.out, exist_ok=True)
    np = nf = 0
    with open(os.path.join(a.out, 'pages.jsonl'), 'w', encoding='utf-8') as P, \
            open(os.path.join(a.out, 'photos.jsonl'), 'w', encoding='utf-8') as F:
        for root, _, files in os.walk(a.files):
            for fn in sorted(files):
                if not re.search(r'\.(html?|php)$', fn, re.I) and '__' not in fn:
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, a.files).replace(os.sep, '/')
                if rel.startswith('_state/'):
                    continue
                url = base + urllib.parse.quote(rel.split('__')[0])
                try:
                    page, photos = index_page(a.site, url, rel, open(full, 'rb').read(), headers, base)
                except Exception as e:
                    print('could not read', rel, e, file=sys.stderr)
                    continue
                P.write(json.dumps(page, ensure_ascii=False) + '\n')
                for p in photos:
                    F.write(json.dumps(p, ensure_ascii=False) + '\n')
                np += 1
                nf += len(photos)
    print(json.dumps(dict(site=a.site, pages=np, photos=nf)))


if __name__ == '__main__':
    main()
