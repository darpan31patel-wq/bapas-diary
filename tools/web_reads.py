"""The written things from baps.org for the website's Search: the Daily Satsang prasangs first (Darpan, 13 Nov 2026:
"Daily Satsang in Search. About 5,000 days of prasangs and thoughts become searchable, each linked to its date"),
built so the Enlightening Essays and the Gujarati lekhmala can join the same list later.

    python tools/web_reads.py --prasang prasang.json --satsang dailysatsang.json --out reads.json

Writes one list, oldest first, one row per item (tools/build_search.py puts it in the search as data/reads.json):
  [date, place, kind, title, [English paragraphs], [Gujarati paragraphs], source address, page date]
    date    the day it happened: a prasang's own dated line ("તા. 5-8-2010, Gondal"), else the page's own date
    kind    "prasang", "essay", "lekhmala" (the page says each one's name)
    English our own translation, shown first and called "English translation" on the page; [] when there is none yet
    source  the baps.org page it came from, so every item says where it is from (Darpan, 13 Nov 2026)
    page    the date of the Daily Satsang page (or the essay's own date), which can differ from the prasang's date

Where the words come from:
  --prasang   data/baps/prasang.json from the baps.org finds thread: {page date: {d, place, who, title, gu, en}},
              the same wording as Today and the Calendar
  --satsang   the raw Daily Satsang pages (crawl/baps-org/dailysatsang.json): {page date: {url, head, text, imgs}};
              used for any page the prasang file does not have yet, Gujarati only, until its translation arrives
  --essays, --lekhmala   {page path: {title, date, text, imgs, url}} (later)
  --reports   the old BAPS website's day reports and prasangs, out/data/reports/MM-DD.json (tools/sorg_reports.py),
              kind "vicharan" for a day's report and "prasang" for its prasangs (Darpan, 16 Nov 2026: "I would also like
              all this information to be on the search page")
  --akshardham  akshardham.com's dated news stories (akshardham-com-pages.jsonl, release `database`), kind "story":
              the words between the story's title and the "BAPS News" list, nothing of the site's menus
Nothing is cut: every paragraph of every item is kept.
"""
import argparse, json, os, re

DIGITS = str.maketrans('૦૧૨૩૪૫૬૭૮૯', '0123456789')
SITE = 'https://www.baps.org'
# the dated line under a prasang: "તા. 5-8-2010, ગોંડલ" (the digits are sometimes Gujarati ones)
DATED = re.compile(r'તા\.?\s*([0-9૦-૯]{1,2})\s*[-/.]\s*([0-9૦-૯]{1,2})\s*[-/.]\s*([0-9૦-૯]{4})\s*,?\s*([^\n]*)')


def iso(d, m, y):
    d, m, y = (int(x.translate(DIGITS)) for x in (d, m, y))
    return f'{y:04d}-{m:02d}-{d:02d}' if 1 <= m <= 12 and 1 <= d <= 31 else ''


def page_url(page):
    y, m, d = page.split('-')
    return f'{SITE}/Daily-Satsang.aspx?dt={int(m)}-{int(d)}-{y}'


def paras(t):
    if isinstance(t, list):
        return [p.strip() for p in t if p and p.strip()]
    return [p.strip() for p in re.split(r'\n\s*\n|\n', t or '') if p.strip()]


def from_raw(page, day):
    """The Gujarati prasang of one raw Daily Satsang page: from its heading (પ્રેરણા પરિમલ) to the next part
    (Vachanamrut Gems), with the dated line it ends on. None when the page has no prasang."""
    text = day.get('text') or ''
    a = text.find('પ્રેરણા પરિમલ')
    if a < 0:
        return None
    b = min([i for i in (text.find(w, a) for w in ('Vachanamrut Gems', 'Vachanamrut', ' in history', 'Audio Satsang')) if i > a] or [len(text)])
    lines = paras(text[a + len('પ્રેરણા પરિમલ'):b])
    if not lines:
        return None
    d, place = '', ''
    for i, line in enumerate(lines):
        m = DATED.search(line)
        if m:
            d, place = iso(*m.groups()[:3]), m.group(4).strip(' .,')
            del lines[i]
            break
    title = lines.pop(0) if len(lines) > 1 and len(lines[0]) < 80 else ''
    return {'d': d, 'place': place, 'title': title, 'gu': lines, 'en': []}


def reports(folder):
    """Every day report and prasang of the old BAPS website, under its own day. English only, no source on the site."""
    rows = []
    if not folder or not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if not re.match(r'\d\d-\d\d\.json$', name):
            continue
        for y, items in json.load(open(os.path.join(folder, name), encoding='utf-8')).items():
            d = f'{y}-{name[:5]}'
            for r in items:
                if r.get('k') in ('jc', 'm'):   # Jivan Charitra lines: tools/web_bio.py adds those to Search itself
                    continue
                w = [t for t in (r.get('w') or []) if t.strip()]
                if not w:
                    continue
                where = ', '.join(p for i, p in enumerate(r.get('pl') or []) if i == 0 or p != r['pl'][i - 1])
                if r.get('k') == 'p':
                    rows.append([d, where, 'prasang', r.get('t') or '', w, [], '', d])
                else:
                    rows.append([d, where, 'vicharan', r.get('o') or '', w, [], '', d])
    return rows


MONTH_DAY = re.compile(r'^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})$')


def akshardham(path):
    """akshardham.com's own dated stories: a title line, its date ("October 2, 2010"), the words, then "BAPS News"."""
    rows, seen = [], set()
    if not path or not os.path.exists(path):
        return rows
    months = 'January February March April May June July August September October November December'.split()
    for line in open(path, encoding='utf-8'):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        url, title = r.get('page_url') or '', re.sub(r'\s+[\u2013-]\s+Swaminarayan Akshardham.*$', '', r.get('title') or '').strip()
        if '/testimonial' in url or '/explore' in url or '/about-us' in url or not title or url in seen:
            continue
        lines = [t.strip() for t in (r.get('words') or '').split('\n') if t.strip()]
        for i in range(len(lines) - 1):
            m = MONTH_DAY.match(lines[i + 1])
            if lines[i] == title and m:
                body = []
                for t in lines[i + 2:]:
                    if t in ('BAPS News', 'BAPS Charities News', 'Loading..'):
                        break
                    body.append(t)
                if body:
                    d = f'{int(m[3]):04d}-{months.index(m[1]) + 1:02d}-{int(m[2]):02d}'
                    rows.append([d, 'Akshardham, New Delhi', 'story', title, body, [], url, d])
                    seen.add(url)
                break
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prasang', help='data/baps/prasang.json (translated prasangs)')
    ap.add_argument('--satsang', help='crawl/baps-org/dailysatsang.json (the raw pages)')
    ap.add_argument('--essays')
    ap.add_argument('--lekhmala')
    ap.add_argument('--reports', help='out/data/reports (MM-DD.json from tools/sorg_reports.py)')
    ap.add_argument('--akshardham', help='akshardham-com-pages.jsonl')
    ap.add_argument('--out', default='reads.json')
    a = ap.parse_args()
    load = lambda p: json.load(open(p, encoding='utf-8')) if p and os.path.exists(p) else {}
    done, raw = load(a.prasang), load(a.satsang)
    rows = []
    for page in sorted(set(done) | set(raw)):
        if not re.match(r'\d{4}-\d{2}-\d{2}$', page):
            continue
        if (done.get(page) or {}).get('who') == 'yogiji':   # Yogiji Maharaj stories hidden until Darpan decides (19 Nov 2026)
            continue
        p = done.get(page) or from_raw(page, raw.get(page) or {})
        if not p or not p.get('en'):   # English first, always (Darpan, 14 Nov 2026: "Wait for English")
            continue
        url = p.get('src') or (raw.get(page) or {}).get('url') or page_url(page)
        rows.append([p.get('d') or page, p.get('place') or '', 'prasang', p.get('title') or '',
                     paras(p.get('en')), paras(p.get('gu')), url, page])
    for kind, path in (('essay', a.essays), ('lekhmala', a.lekhmala)):
        for key, e in load(path).items():
            date = (e.get('date') or '')[:10]
            if not re.match(r'\d{4}-\d{2}-\d{2}$', date):
                continue
            body = paras(e.get('text'))
            en, gu = (body, []) if kind == 'essay' else (paras(e.get('en')), body)
            rows.append([date, e.get('place') or '', kind, e.get('title') or '', en, gu,
                         e.get('url') or SITE + '/' + key.lstrip('/'), date])
    rows += reports(a.reports) + akshardham(a.akshardham)
    rows.sort(key=lambda r: (r[0], r[7]))
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, separators=(',', ':'))
    print(len(rows), 'written things ->', a.out)


if __name__ == '__main__':
    main()
