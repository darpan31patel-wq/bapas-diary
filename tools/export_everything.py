"""Export everything Bapa's Diary knows, sorted by date, for Darpan's own use (5 Nov 2026: "export a massive database,
organised by date, with ALL the information we have, photo, location, caption, date, database info, article, any
tagging").

Read only: it never changes bapas.db, the website or the daily 2pm picture. Photos are links, never files.

    python3 tools/export_everything.py --db bapas.db --bapa bapa.db --tags deep-tags.json --yt days.json \
        [--moments data/video-moments] [--articles articles.json] [--workbook 2018=rows.json] --out OUT_FOLDER

  bapas.db       release `database` (bapas.db.gz): photos, Telegram channels, 2pm picture record, BAPS calendar
  bapa.db        release `website-faces` (bapa.db.gz): which photos show Bapa in person, close up or activity
  deep-tags.json release `deep-tags`: photo tags {ALBUM/FILE: "smiling, garland"}
  days.json      data/youtube/days.json on the website branch: Video Darshan videos by day
  --moments      data/video-moments/*.json (video moments), when there are any
  --articles     baps.org News articles: a JSON list, or a SQLite file with a table holding them (see load_articles)
  --workbook     a day by day workbook Darpan gave (YEAR=rows.json, as made for 2018), may be given more than once
  --sites        a folder of <site>-pages.jsonl and <site>-photos.jsonl (tools/sites_index.py, release `database`):
                 every page and photo copied from the other BAPS websites, with full detail (Darpan, 13 Nov 2026:
                 "all the captions, all the date information, any location, where the actual resource is from")
  --writings     baps.org writings saved by the News crawl (dailysatsang.json, essays.json, lekhmala.json,
                 wallpapers.json, pramukhswami.json), may be given more than once

News articles now come from bapas.db itself (tables articles and article_photos) unless --articles is given.

Writes into OUT_FOLDER:
  years/Bapas Diary YYYY.xlsx   one workbook per year (Days, Photos, Articles, On this day, Channel posts, Videos,
                                Video moments, About); "Before 1999.xlsx" holds the older history
  Bapas Diary everything.db     one SQLite file with every table plus `everything_photos` (all photo fields joined)
  All photos.csv                every photo with every field, one row each (opens in Excel: under a million rows)
  All days.csv                  one row per day with everything known about it
  All articles.csv              every News article with its full text
  All other website pages.csv   every page from the other BAPS websites with its words, headings, dates and place
  All writings.csv              every Daily Satsang prasang, essay, lekhmala and the rest with full text
"""
import argparse, collections, csv, datetime, glob, json, os, re, shutil, sqlite3

import openpyxl
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SITE = 'https://bapas-diary.com'
PH = 'https://photos.bapas-diary.com'
BAPS = 'https://www.baps.org/Data/Sites/1/Media/GalleryImages'
CELL_MAX = 32000          # Excel keeps at most 32,767 letters in one cell
CHANNEL = {'history': 'Today in BAPS History', 'satpurush': 'Satpurush in UK & Europe'}


def guru(d):
    # Darpan, 31 Oct 2026: before 13 Aug 2016 Swamishri is Pramukh Swami Maharaj, after it Mahant Swami Maharaj
    return 'Pramukh Swami Maharaj' if d < '2016-08-13' else 'Mahant Swami Maharaj'


def clean(v):
    if isinstance(v, str):
        v = ILLEGAL_CHARACTERS_RE.sub('', v)
    return v


def cut(v, where='All articles.csv'):
    if isinstance(v, str) and len(v) > CELL_MAX:
        return v[:CELL_MAX] + f' ... (cut here because Excel cells are full; the whole text is in {where})'
    return v


MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def day_of(v):
    """YYYY-MM-DD from '2006-11-04' or the way baps.org writes dates ('4 November 2006', 'November 4, 2006')."""
    v = str(v or '').strip()
    if re.match(r'\d{4}-\d\d-\d\d', v): return v[:10]
    m = re.search(r'(\d{1,2})\s*([A-Za-z]{3})[a-z]*,?\s*(\d{4})', v) or re.search(r'([A-Za-z]{3})[a-z]*\s*(\d{1,2}),?\s*(\d{4})', v)
    if not m: return None
    g = m.groups()
    dd, mon = (g[0], g[1]) if g[0].isdigit() else (g[1], g[0])
    if mon.lower() not in MONTHS: return None
    return f'{g[2]}-{MONTHS[mon.lower()]:02d}-{int(dd):02d}'


def load_articles(path):
    """Articles as dicts {date, place, title, url, text, albums, photos}. Accepts a JSON list/dict or a SQLite file.

    Field names are matched loosely so the tool works with the News crawl's own shape: t/title, d/date, text/body,
    p/path/url, place, g (galleries {path: {t, rows}}) or albums."""
    if not path:
        return []
    if path.endswith('.db'):
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        names = [n for (n,) in con.execute("select name from sqlite_master where type='table'")]
        name = next((n for n in names if 'article' in n.lower() or 'news' in n.lower()), None)
        raw = [dict(r) for r in con.execute(f'select * from "{name}"')] if name else []
    else:
        raw = json.load(open(path))
        if isinstance(raw, dict):
            raw = [dict(v, path=k) if isinstance(v, dict) else {'path': k, 'text': v} for k, v in raw.items()]
    out = []
    for a in raw:
        g = a.get('g') or a.get('galleries') or {}
        if isinstance(g, str):
            try: g = json.loads(g)
            except ValueError: g = {}
        albums, photos, pics = [], 0, []
        if isinstance(g, dict):
            for gp, gv in g.items():
                rows = (gv or {}).get('rows') or []
                pics += [(r[0], r[1], r[2] if len(r) > 2 else None, (gv or {}).get('t') or gp) for r in rows if len(r) > 1]
                photos += len(rows)
                al = rows[0][0] if rows and rows[0] else (re.findall(r'-(\d+)\.aspx', gp) or [None])[0]
                if al: albums.append(str(al))
        elif isinstance(g, list):
            albums = [str(x) for x in g]
        own = a.get('own') or []
        if isinstance(own, str):
            try: own = json.loads(own)
            except ValueError: own = []
        photos += len(own)
        pics += [(r[0], r[1], r[2] if len(r) > 2 else None, 'inside the article') for r in own if len(r) > 1]
        albums += [str(r[0]) for r in own if r]
        if a.get('albums'):
            albums = [str(x) for x in (json.loads(a['albums']) if isinstance(a['albums'], str) else a['albums'])]
        url = a.get('url') or a.get('p') or a.get('path') or ''
        if url and not url.startswith('http'):
            url = 'https://www.baps.org' + ('' if url.startswith('/') else '/') + url
        d = day_of(a.get('date') or a.get('d'))
        out.append({'date': d, 'place': a.get('place'), 'title': a.get('title') or a.get('t'),
                    'url': url or None, 'text': a.get('text') or a.get('body'),
                    'albums': ', '.join(dict.fromkeys(albums)) or None, 'photos': photos or a.get('photos'),
                    'pics': pics})
    out.sort(key=lambda x: (x['date'] or '9999', x['title'] or ''))
    return out


def articles_from_db(db):
    """News stories from bapas.db: articles + article_photos (with each photo's caption as its alt text)."""
    names = {n for (n,) in db.execute("select name from sqlite_master where type='table'")}
    if 'articles' not in names:
        return []
    pics = collections.defaultdict(list)
    if 'article_photos' in names:
        for path, al, f, gal, cap in db.execute('select ap.path, ap.album, ap.file, ap.gallery, p.caption from article_photos ap '
                                                'left join photos p on p.album = ap.album and p.file = ap.file'):
            pics[path].append((str(al), str(f), cap, gal or 'inside the article'))
    out = []
    for path, url, d, place, title, text, nph in db.execute(
            'select path, url, date, place, title, text, photos from articles'):
        url = url or ''
        if url and not url.startswith('http'):
            url = 'https://www.baps.org' + ('' if url.startswith('/') else '/') + url
        ps = pics.get(path, [])
        out.append({'date': day_of(d), 'place': place, 'title': title, 'url': url or None, 'text': text,
                    'albums': ', '.join(dict.fromkeys(p[0] for p in ps)) or None, 'photos': nph or len(ps) or None,
                    'pics': ps, 'written': d})
    out.sort(key=lambda x: (x['date'] or '9999', x['title'] or ''))
    return out


GU = str.maketrans('૦૧૨૩૪૫૬૭૮૯', '0123456789')
PRASANG = re.compile(r'તા\.?\s*([0-9]{1,2})\s*[-/.]\s*([0-9]{1,2})\s*[-/.]\s*([0-9]{4})\s*,?\s*([^\n,.;:()]{0,40})')
MONTH_YEAR = re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s*,?\s*(\d{4})\b', re.I)


def ds_url(d):
    y, m, dd = d.split('-')
    return f'https://www.baps.org/Daily-Satsang.aspx?dt={int(m)}-{int(dd)}-{y}'


def load_writings(paths):
    """baps.org writings: rows for the Writings sheet, plus the photos they hold (with alt and title kept whole)."""
    rows, pics = [], []
    for fn in paths:
        kind = {'dailysatsang': 'Daily Satsang', 'essays': 'Enlightening Essay', 'lekhmala': 'Satsang lekhmala',
                'wallpapers': 'Wallpaper', 'pramukhswami': 'pramukhswami.org'}.get(
                    os.path.splitext(os.path.basename(fn))[0].lower(), os.path.splitext(os.path.basename(fn))[0])
        raw = json.load(open(fn, encoding='utf-8'))
        items = raw.items() if isinstance(raw, dict) else ((x.get('path') or x.get('url') or '', x) for x in raw)
        for key, v in items:
            if not isinstance(v, dict) or v.get('status') in ('missing', 'empty', 404):
                continue
            text = (v.get('text') or '').strip()
            page_day = key if re.fullmatch(r'\d{4}-\d\d-\d\d', key) else day_of(v.get('date'))
            url = v.get('url') or (ds_url(key) if kind == 'Daily Satsang' and page_day == key else
                                   ('https://www.baps.org' + ('' if key.startswith('/') else '/') + key if key and not key.startswith('http') else key))
            own, written, place = None, None, None
            m = PRASANG.search(text.translate(GU))
            if m:
                try:
                    own = datetime.date(int(m[3]), int(m[2]), int(m[1])).isoformat()
                    written = m.group(0).strip(' ,')
                    place = m[4].strip() or None
                except ValueError:
                    pass
            imgs = v.get('imgs') or []
            rows.append([own or page_day, page_day if own and own != page_day else None, written or v.get('date'),
                         'the prasang\'s own date' if own else ('the page date' if page_day else None), place, kind,
                         v.get('head') or v.get('title'), text or None, v.get('en') or v.get('english'), len(imgs) or None,
                         '\n'.join(('https://www.baps.org' if str(x).startswith('/') else '') + str(x)
                                   for x in ((i[0] if isinstance(i, list) else i) for i in imgs) if x) or None, url or None])
            for i in imgs:
                src, alt, title = ((list(i) + [None, None])[:3]) if isinstance(i, list) else (i, None, None)
                if not src: continue
                if src.startswith('/'): src = 'https://www.baps.org' + src
                cap = ' | '.join(x for x in dict.fromkeys([alt, title]) if x) or None
                mm = MONTH_YEAR.search(cap or '')
                pd = f'{mm[2]}-{MONTHS[mm[1][:3].lower()]:02d}' if mm else page_day
                pics.append(dict(site='baps.org ' + kind, photo_url=src, caption=cap, alt=alt, date=pd,
                                 date_written=mm.group(0) if mm else None,
                                 date_from='the caption' if mm else 'the day the page showed it',
                                 place=(re.search(r',\s*([A-Z][A-Za-z ]{2,30})\s*$', cap or '') or [None, None])[1],
                                 place_from='the caption', page_url=url, page_title=v.get('head') or v.get('title'),
                                 heading=kind))
    rows.sort(key=lambda r: (r[0] or '9999', r[5] or ''))
    return rows, pics


def load_sites(folder):
    pages, photos = [], []
    if not folder:
        return pages, photos
    for fn in sorted(glob.glob(os.path.join(folder, '*-pages.jsonl'))):
        pages += [json.loads(l) for l in open(fn, encoding='utf-8') if l.strip()]
    for fn in sorted(glob.glob(os.path.join(folder, '*-photos.jsonl'))):
        photos += [json.loads(l) for l in open(fn, encoding='utf-8') if l.strip()]
    return pages, photos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--bapa')
    ap.add_argument('--tags')
    ap.add_argument('--yt')
    ap.add_argument('--moments')
    ap.add_argument('--articles')
    ap.add_argument('--workbook', action='append', default=[])
    ap.add_argument('--sites')
    ap.add_argument('--writings', action='append', default=[])
    ap.add_argument('--years', help='only these years, e.g. 2018 or 2017-2019 (the full files are still made)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, 'years'), exist_ok=True)

    db = sqlite3.connect(a.db)
    bapa = {}
    if a.bapa:
        for al, f, rk, close, why, fx, fy, sim in sqlite3.connect(a.bapa).execute(
                'select album, file, rank, close, why, fx, fy, sim from bapa_pick'):
            bapa[(al, f)] = (rk, close, why, fx, fy, sim)
    tags = json.load(open(a.tags)) if a.tags else {}
    yt = json.load(open(a.yt)) if a.yt else {}
    moments = []
    if a.moments:
        for fn in sorted(glob.glob(os.path.join(a.moments, '*.json'))):
            v = json.load(open(fn))
            for m in v.get('m', []):
                at, end, text, mtags, mb = (list(m) + [None] * 5)[:5]
                moments.append([v.get('date'), v.get('place'), v.get('title'), at, end, text, mtags,
                                'yes' if mb else 'no', f'https://youtu.be/{v["id"]}?t={int(at or 0)}'])
    moments.sort(key=lambda r: (r[0] or '', r[3] or 0))
    articles = load_articles(a.articles) if a.articles else articles_from_db(db)
    site_pages, site_photos = load_sites(a.sites)
    writings, writing_pics = load_writings(a.writings)
    workbooks = {}
    for w in a.workbook:
        y, fn = w.split('=', 1)
        for r in json.load(open(fn)):
            if r[2] and r[2] != 'None':
                d = r[2][:10]
                if d.startswith('2013-12') and y == '2018': d = y + d[4:]   # 2018 workbook typo, see workbook-2018
                workbooks[d] = r
            elif r[0] and 'Wk. 53' in str(r[0]) and r[6]:
                workbooks.setdefault(f'{y}-12-31', [None, None, f'{y}-12-31', None, None, None, r[6]])

    # ---- photos, one row each with every field
    P_COLS = ['Date', 'Date from', 'Date to', 'Year', 'Place', 'Caption', 'Bapa in photo', 'Close up or activity',
              'How Bapa was found', 'Bapa face rank', 'Face position across', 'Face position down', 'Face likeness',
              'Photo tags', 'Guru', 'High quality photo', 'Small photo', 'Original on baps.org',
              'baps.org web size', 'Google Drive file (Bapa\'s Archive)', 'Album', 'File', 'How it was found',
              'baps.org marked as Bapa', 'News article', 'News gallery',
              # full detail for every source (Darpan, 13 Nov 2026)
              'Source website', 'Source page', 'Source page title', 'Date as written', 'Where the date came from',
              'Where the place came from', 'Gallery or heading', 'Alt text', 'Words beside the photo',
              'Other size of the photo', 'File size (bytes)', 'File type', 'Date on the website server', 'Copied on']
    SRC = {'news': 'baps.org News gallery', 'page': 'baps.org vicharan page', 'button': 'baps.org daily page',
           'scan': 'baps.org album scan'}
    def extra(site=None, page=None, title=None, written=None, dfrom=None, pfrom=None, gal=None, alt=None, near=None,
              other=None, size=None, typ=None, server=None, copied=None):
        return [site, page, title, written, dfrom, pfrom, gal, alt, near, other, size, typ, server, copied]
    in_article = {}
    for x in articles:
        for al, f, alt, gal in x['pics']:
            in_article.setdefault((str(al), str(f)), (x, alt, gal))
    photos = []
    for (y, d, df, dt, place, al, f, cap, isb, src, lp) in db.execute(
            'select year, date, date_from, date_to, place, album, file, caption, is_bapa, source, local_path '
            'from photos order by coalesce(date, date_from), album, file'):
        day = d or df
        b = bapa.get((al, f))
        web = str(al).startswith('webnext-')   # new style baps.org News pages: the file came from the new photo server
        art = in_article.get((al, f))
        photos.append([day, df if not d else None, dt, y, place, cap,
                       'yes' if b else 'no', (('close up' if b[1] else 'activity') if b else None),
                       b[2] if b else None, b[0] if b else None, b[3] if b else None, b[4] if b else None,
                       b[5] if b else None, tags.get(f'{al}/{f}'), guru(day),
                       f'{PH}/l/{al}/{f}', f'{PH}/s/{al}/{f}', None if web else f'{BAPS}/{al}/FullSizeImages/{f}',
                       None if web else f'{BAPS}/{al}/WebImages/{f}', lp, al, f,
                       SRC.get(src, src), {1: 'yes', 0: 'no'}.get(isb)]
                      + ([art[0]['url'], art[2]] if art else [None, None])
                      + extra('baps.org', art[0]['url'] if art else None,
                              art[0]['title'] if art else None, art[0].get('written') if art else None,
                              'the News story' if art else 'the baps.org album', 'the baps.org album' if place else None,
                              art[2] if art else None, (art[1] if art and art[1] != cap else None)))
    # News gallery photos the database does not hold yet (the News thread loads them later): from the articles file
    have = {(p[20], p[21]) for p in photos}
    for (al, f), (x, alt, gal) in in_article.items():
        if (al, f) in have: continue
        day = x['date']
        photos.append([day, None, None, int(day[:4]) if day else None, x['place'], (alt or '').strip() or None,
                       'not checked yet', None, None, None, None, None, None, tags.get(f'{al}/{f}'),
                       guru(day) if day else None, None, None, f'{BAPS}/{al}/FullSizeImages/{f}',
                       f'{BAPS}/{al}/WebImages/{f}', None, al, f, 'baps.org News gallery', None, x['url'], gal]
                      + extra('baps.org', x['url'], x['title'], x.get('written'), 'the News story', 'the News story', gal, alt))
    # photos copied from the other BAPS websites and from baps.org writings, each with every detail its page gave
    for q in site_photos + writing_pics:
        day = q.get('date') or None
        u = q.get('photo_url')
        site = q.get('site')
        dp = q.get('drive_path')
        photos.append([day, None, q.get('date_to') if q.get('date_to') not in (None, '', day) else None,
                       int(day[:4]) if day and day[:4].isdigit() else None, q.get('place') or q.get('gallery_place') or None,
                       q.get('caption') or None, 'not checked yet', None, None, None, None, None, None, None,
                       guru(day) if day else None, None, None, u, None,
                       f"Bapa's Archive/{dp}" if dp else None, site, u, site, None, None, None]
                      + extra(site, q.get('page_url'), q.get('page_title'), q.get('date_written') or None,
                              q.get('date_from') or None, q.get('place_from') or None,
                              q.get('heading') or q.get('gallery_place') or None,
                              q.get('alt') if q.get('alt') and q.get('alt') != q.get('caption') else None,
                              q.get('words_beside') or None,
                              (f"{q.get('size')} copy; other size {q.get('other_size_url')}" if q.get('other_size_url')
                               else (q.get('size') or None)),
                              q.get('bytes'), q.get('content_type'), q.get('last_modified'), q.get('fetched_at')))
    photos.sort(key=lambda p: (p[0] or '', str(p[20]), str(p[21])))
    byday = collections.defaultdict(list)
    for p in photos: byday[p[0]].append(p)

    cal = {r[0]: r for r in db.execute('select date, weekday, vikram_samvat, lunar_months, month, paksha, tithi, '
                                       'indian_date, festivals, festival_about, notes, ekadashi, punam, amas, source '
                                       'from calendar')}
    pick = collections.defaultdict(list)
    for d, y, url, cap in db.execute('select date, year, photo_url, caption from diary order by year'):
        pick[f'{y}-{d[5:]}'].append([d, url, cap])
    otd = collections.defaultdict(list)
    otd_rows = []
    for ch, d, place, line, story, special, headline, g, posts, data in db.execute(
            'select channel, date, place, line, story, special, headline, guru, posts, data from tg_events order by date'):
        j = json.loads(data or '{}')
        otd[d].append(line)
        otd_rows.append([d, place, headline, line, story, j.get('whatsapp'), j.get('card'), 'yes' if special else 'no',
                         CHANNEL.get(ch, ch), j.get('url'), j.get('video'), posts])
    for d, card, g, data in db.execute('select date, card, guru, data from tg_cards order by date'):
        otd[d].append(card)
        otd_rows.append([d, None, None, card, None, None, card, None, 'Today in BAPS History (guru card)', None, None, None])
    otd_rows.sort(key=lambda r: r[0] or '')
    posts = []
    for ch, pid, posted, d, place, text, np, nv, nf, fwd, links, url, folder in db.execute(
            'select channel, id, posted, date, place, text, photos, videos, files, forwarded_from, links, url, '
            'local_folder from tg_posts order by coalesce(date, substr(posted, 1, 10)), channel, id'):
        posts.append([d, posted[:16].replace('T', ' ') if posted else None, CHANNEL.get(ch, ch), place, text, np, nv, nf,
                      fwd or None, (', '.join(json.loads(links)) if links and links != '[]' else None), url, folder, pid])
    vids, seen = [], set()
    for d in sorted(yt):
        for v in yt[d]:
            if v['id'] in seen: continue
            seen.add(v['id'])
            vids.append([d, v.get('title'), round((v.get('secs') or 0) / 60, 1), f'https://youtu.be/{v["id"]}'])
    art_by = collections.defaultdict(list)
    for x in articles: art_by[x['date']].append(x)
    mom_by = collections.defaultdict(list)
    for m in moments: mom_by[m[0]].append(m)
    # other website pages: one row each, on the first day they talk about
    G_COLS = ['Date', 'Last date', 'Website', 'Section', 'Title', 'Place', 'Where the place came from', 'Headings',
              'Every date written on the page', 'Photos', 'Audio, video and zip files', 'Words on the page',
              'Page link', "Google Drive copy (Bapa's Archive)", 'Date on the website server', 'Copied on']
    grows = []
    for g in site_pages:
        d0 = g.get('date_first') or g.get('month') or None
        grows.append([d0, g.get('date_last') if g.get('date_last') not in (None, '', d0) else None, g.get('site'),
                      g.get('section') or None, g.get('title') or None, g.get('place') or None, g.get('place_from') or None,
                      '\n'.join(g.get('headings') or []) or None,
                      '\n'.join(f"{x.get('written')} ({x.get('from')}{' to ' + x['to'] if x.get('to') not in (None, x.get('from')) else ''})"
                                for x in g.get('dates') or []) or None,
                      g.get('photos'), '\n'.join(g.get('media') or []) or None, g.get('words') or None, g.get('page_url'),
                      f"Bapa's Archive/{g['drive_path']}" if g.get('drive_path') else None, g.get('last_modified'),
                      g.get('fetched_at')])
    grows.sort(key=lambda r: (r[0] or '9999', r[2] or '', r[12] or ''))
    page_by = collections.defaultdict(list)
    for r in grows: page_by[r[0]].append(r)
    W_COLS = ['Date', 'Page date', 'Date as written', 'Where the date came from', 'Place', 'Kind', 'Heading', 'Full text',
              'English translation', 'Photos', 'Photo links', 'Source page']
    writ_by = collections.defaultdict(list)
    for r in writings: writ_by[r[0]].append(r)

    # ---- days: every date that has anything at all
    every = (set(byday) | set(cal) | set(otd) | set(pick) | set(yt) | set(art_by) | set(workbooks) | set(mom_by)
             | set(page_by) | set(writ_by))
    first = min(d for d in every if d and d >= '1999-01-01')
    d0, last = datetime.date.fromisoformat(first), max(d for d in every if d)
    span = set()
    while d0.isoformat() <= last:
        span.add(d0.isoformat()); d0 += datetime.timedelta(1)
    D_COLS = ['Date', 'Weekday', 'Tithi', 'Vikram Samvat', 'Festivals', 'About the festival', 'Calendar notes',
              'Ekadashi, Punam or Amas', 'Places', 'Photos', 'Photos with Bapa', 'Articles', 'On this day',
              '2pm daily picture photo', 'Workbook place', 'Workbook occasion', 'Workbook day note', 'Video Darshan',
              'Video moments', 'Guru', 'See the day on bapas-diary.com', 'BAPS calendar page',
              'Pages from other BAPS websites', 'Writings (Daily Satsang, essays and more)', 'Sources']
    days = []
    for d in sorted(span | {x for x in every if x}):
        try: wd = datetime.date.fromisoformat(d).strftime('%A')
        except ValueError: wd = None
        c, w, ps = cal.get(d), workbooks.get(d), byday.get(d, [])
        places = [p for p, _ in collections.Counter(p[4] for p in ps if p[4]).most_common()]
        if not places and art_by.get(d): places = [x['place'] for x in art_by[d] if x['place']]
        v = yt.get(d, [])
        days.append([d, wd, c[7] if c else None, c[2] if c else None, (c[8] or None) if c else None,
                     (c[9] or None) if c else None, (c[10] or None) if c else None,
                     ', '.join(n for n, k in (('Ekadashi', c[11]), ('Punam', c[12]), ('Amas', c[13])) if k) or None if c else None,
                     '; '.join(dict.fromkeys(places)) or None, len(ps), sum(1 for p in ps if p[6] == 'yes'),
                     '\n'.join(x['title'] or '' for x in art_by.get(d, [])) or None,
                     '\n'.join(x for x in otd.get(d, []) if x) or None,
                     '\n'.join(f'{u} (made {pd})' for pd, u, _ in pick.get(d, [])) or None,
                     ((w[4] or '').strip() or None) if w else None, ((w[5] or '').strip() or None) if w else None,
                     w[6] if w else None, '\n'.join(f'https://youtu.be/{x["id"]}' for x in v) or None,
                     len(mom_by.get(d, [])) or None, guru(d) if d >= '1999' else None,
                     f'{SITE}/search/#date={d}' if ps and d[:4].isdigit() and len(d) == 10 else None, c[14] if c else None,
                     '\n'.join(f'{r[2]}: {r[4] or r[12]}' for r in page_by.get(d, [])) or None,
                     '\n'.join(f'{r[5]}: {(r[6] or "")[:80]}' for r in writ_by.get(d, [])) or None,
                     ', '.join(sorted({p[26] for p in ps if p[26]} | {r[2] for r in page_by.get(d, []) if r[2]}
                                      | ({'baps.org'} if art_by.get(d) or writ_by.get(d) else set()))) or None])

    A_COLS = ['Date', 'Place', 'Title', 'Full text', 'Gallery albums', 'Gallery photos', 'Article on baps.org']
    arows = [[x['date'], x['place'], x['title'], x['text'], x['albums'], x['photos'], x['url']] for x in articles]
    O_COLS = ['Date', 'Place', 'Headline', 'Line', 'Story', 'Short message', 'Card', 'Special day', 'Source',
              'Source link', 'Video', 'Posts']
    C_COLS = ['Date', 'Posted', 'Channel', 'Place', 'Text', 'Photos', 'Videos', 'Files', 'Forwarded from', 'Links',
              'Post link', 'Google Drive folder', 'Post number']
    V_COLS = ['First day', 'Title', 'Minutes', 'YouTube']
    M_COLS = ['Date', 'Place', 'Video', 'From second', 'To second', 'What happens', 'Tags', 'Bapa in it', 'YouTube']

    # ---- full files
    def write_csv(name, cols, rows):
        with open(os.path.join(a.out, name), 'w', newline='', encoding='utf-8-sig') as fh:
            wr = csv.writer(fh); wr.writerow(cols); wr.writerows(rows)
    write_csv('All photos.csv', P_COLS, photos)
    write_csv('All days.csv', D_COLS, days)
    write_csv('All articles.csv', A_COLS, arows)
    write_csv('All other website pages.csv', G_COLS, grows)
    write_csv('All writings.csv', W_COLS, writings)

    full = os.path.join(a.out, 'Bapas Diary everything.db')
    if os.path.exists(full): os.remove(full)
    shutil.copyfile(a.db, full)
    fx = sqlite3.connect(full)
    def table(name, cols, rows):
        keys = [re.sub(r'\W+', '_', c.lower()).strip('_') for c in cols]
        fx.execute(f'drop table if exists {name}')
        fx.execute(f"create table {name} ({', '.join(chr(34) + k + chr(34) for k in keys)})")
        fx.executemany(f'insert into {name} values ({",".join("?" * len(keys))})', rows)
    table('everything_photos', P_COLS, photos)
    table('everything_days', D_COLS, days)
    table('news_articles', A_COLS, arows)
    table('on_this_day', O_COLS, otd_rows)
    table('videos', V_COLS, vids)
    table('video_moments', M_COLS, moments)
    table('other_website_pages', G_COLS, grows)
    table('writings', W_COLS, writings)
    if bapa:
        fx.execute('drop table if exists bapa_pick')
        fx.execute('create table bapa_pick (album, file, rank, close, why, fx, fy, sim)')
        fx.executemany('insert into bapa_pick values (?,?,?,?,?,?,?,?)',
                       [(al, f, *v) for (al, f), v in bapa.items()])
    fx.execute('create index if not exists ep_date on everything_photos(date)')
    fx.execute("insert or replace into about values ('export', ?)", (json.dumps({
        'made': datetime.date.today().isoformat(), 'photos': len(photos), 'days': len(days), 'articles': len(arows),
        'on_this_day': len(otd_rows), 'channel_posts': len(posts), 'videos': len(vids), 'video_moments': len(moments),
        'other_website_pages': len(grows), 'other_website_photos': len(site_photos), 'writings': len(writings)}),))
    fx.commit(); fx.execute('vacuum'); fx.close()

    # ---- one workbook per year
    HEAD = Font(bold=True, color='FFFFFF'); FILL = PatternFill('solid', fgColor='7A1F2B')
    BLUE = Font(color='0563C1', underline='single'); WRAP = Alignment(wrap_text=True, vertical='top')

    def sheet(X, name, cols, rows, widths, links=(), wrap=(), first=False):
        ws = X.active if first else X.create_sheet(name)
        ws.title = name
        ws.append(cols)
        for c in ws[1]: c.font = HEAD; c.fill = FILL; c.alignment = WRAP
        for r in rows: ws.append([clean(cut(v)) for v in r])
        for i, wdt in enumerate(widths, 1): ws.column_dimensions[get_column_letter(i)].width = wdt
        for col in links:
            for (cell,) in ws.iter_rows(min_row=2, min_col=col, max_col=col):
                v = cell.value
                if isinstance(v, str) and v.startswith('http') and '\n' not in v:
                    cell.hyperlink = v; cell.font = BLUE
        for col in wrap:
            for (cell,) in ws.iter_rows(min_row=2, min_col=col, max_col=col): cell.alignment = WRAP
        ws.freeze_panes = 'B2'; ws.auto_filter.ref = ws.dimensions

    want = None
    if a.years:
        lo, _, hi = a.years.partition('-'); want = range(int(lo), int(hi or lo) + 1)
    groups = [('Without a date', lambda d: not d), ('Before 1999', lambda d: bool(d) and d < '1999')] + [
        (str(y), (lambda Y: lambda d: (d or '').startswith(Y))(str(y))) for y in range(1999, int(last[:4]) + 1)]
    for label, inside in groups:
        if want and (not label.isdigit() or int(label) not in want): continue
        X = openpyxl.Workbook()
        dd = [r for r in days if inside(r[0])]
        sheet(X, 'Days', D_COLS, dd, [11, 10, 20, 8, 26, 30, 24, 12, 26, 7, 8, 40, 40, 30, 20, 20, 50, 26, 8, 22, 30, 30],
              links=(14, 18, 21, 22), wrap=(6, 12, 13, 14, 17, 18, 23, 24), first=True)
        pp = [r for r in photos if inside(r[0])]
        sheet(X, 'Photos', P_COLS, pp, [11, 11, 11, 6, 22, 60, 8, 11, 12, 7, 8, 8, 8, 30, 20, 34, 34, 34, 34, 40, 8, 26, 18, 9, 40, 30,
                                       18, 40, 30, 20, 18, 18, 24, 30, 40, 30, 10, 12, 20, 18],
              links=(16, 17, 18, 19, 25, 28))
        aa = [r for r in arows if inside(r[0])]
        sheet(X, 'Articles', A_COLS, aa, [11, 22, 40, 100, 16, 8, 40], links=(7,), wrap=(4,))
        sheet(X, 'On this day', O_COLS, [r for r in otd_rows if inside(r[0])],
              [11, 22, 30, 50, 80, 50, 30, 8, 24, 30, 30, 12], links=(10, 11), wrap=(4, 5, 6))
        cc = [r for r in posts if inside(r[0] or r[1])]
        sheet(X, 'Channel posts', C_COLS, cc, [11, 16, 22, 22, 80, 7, 7, 7, 20, 30, 30, 50, 8], links=(11,), wrap=(5,))
        sheet(X, 'Videos', V_COLS, [r for r in vids if inside(r[0])], [11, 80, 8, 32], links=(4,))
        sheet(X, 'Video moments', M_COLS, [r for r in moments if inside(r[0])], [11, 22, 40, 8, 8, 60, 30, 8, 40], links=(9,))
        gg = [r for r in grows if inside(r[0])]
        sheet(X, 'Other website pages', G_COLS, gg, [11, 11, 18, 14, 40, 18, 12, 40, 40, 7, 30, 100, 40, 40, 20, 18],
              links=(13,), wrap=(8, 9, 11, 12))
        ww = [r for r in writings if inside(r[0])]
        sheet(X, 'Writings', W_COLS, ww, [11, 11, 22, 16, 18, 18, 40, 100, 100, 7, 40, 40], links=(12,), wrap=(7, 8, 9, 11))
        sheet(X, 'About', ['Item', 'Value'], [
            ['Year', label], ['Made', datetime.date.today().isoformat()],
            ['Days', len(dd)], ['Photos', len(pp)], ['Photos with Bapa', sum(1 for p in pp if p[6] == 'yes')],
            ['Articles', len(aa)], ['Channel posts', len(cc)],
            ['Pages from other BAPS websites', len(gg)], ['Writings', len(ww)],
            ['Photos by source', '; '.join(f'{k}: {v:,}' for k, v in collections.Counter(p[26] or 'unknown' for p in pp).most_common())],
            ['Full detail', 'Every photo and page says where it came from (Source website, Source page), the date as the '
                            'website wrote it and where that date came from, the place and where it came from, the '
                            'caption, alt text and words beside it, and the Google Drive copy'],
            ['Photos', 'Links only: "High quality photo" is our copy, "Original on baps.org" is the first upload. '
                       'The Google Drive file is the copy in Bapa\'s Archive.'],
            ['Bapa in photo', 'Found by face check: only photos with Bapa himself in person, not murtis or portraits'],
            ['Guru names', 'Before 13 Aug 2016 Swamishri means Pramukh Swami Maharaj, from then on Mahant Swami Maharaj'],
            ['Long text', 'Excel holds 32,000 letters in a cell; anything longer is whole in All articles.csv'],
            ['Everything', 'All years together: Bapas Diary everything.db, All photos.csv, All days.csv, All articles.csv, '
                           'All other website pages.csv, All writings.csv'],
        ], [22, 100], wrap=(2,))
        X.save(os.path.join(a.out, 'years', f'Bapas Diary {label}.xlsx'))
        print('saved', label, len(dd), 'days', len(pp), 'photos', len(aa), 'articles', flush=True)
    print('done', len(photos), 'photos', len(days), 'days', len(arows), 'articles', len(otd_rows), 'on this day',
          len(posts), 'channel posts', len(vids), 'videos', len(moments), 'moments')


if __name__ == '__main__':
    main()
