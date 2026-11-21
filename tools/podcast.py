"""The BAPS Better Living podcast (Darpan, 13 Nov 2026: "Yes to all"; "Everything from the other websites need to
have full detail"): every episode's sound file and cover, and one line per episode with its full detail (title, date,
words, length, where the file came from), for his Drive archive. Gentle: one file at a time, a pause between each.
Never touches the 2pm picture, the website, R2 or bapas.db.

  python3 tools/podcast.py --apple-id 1507712213 --work work --state state
"""
import argparse, datetime as dt, email.utils, html, json, os, re, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

UA = 'Mozilla/5.0 (bapas-diary archive; gentle)'
IT = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read(), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return e.code, {}, b'', url
            time.sleep(20 * (i + 1))
        except Exception:
            time.sleep(20 * (i + 1))
    return None, {}, b'', url


def plain(s):
    s = re.sub(r'(?i)<br\s*/?>|</p>', '\n', s or '')
    return re.sub(r'[ \t]+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def safe(s):
    return re.sub(r'[^\w .,()&\'-]+', '_', s).strip(' ._')[:120] or 'episode'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apple-id', required=True)
    ap.add_argument('--feed', default='')
    ap.add_argument('--work', default='work')
    ap.add_argument('--state', default='state')
    ap.add_argument('--have', default='')
    ap.add_argument('--gap', type=float, default=5)
    ap.add_argument('--stop-at', default='')
    a = ap.parse_args()
    os.makedirs(a.state, exist_ok=True)
    files = os.path.join(a.work, 'files')
    os.makedirs(files, exist_ok=True)
    stop = None
    if a.stop_at:
        h, m = map(int, a.stop_at.split(':'))
        n = dt.datetime.now(dt.timezone.utc)
        stop = n.replace(hour=h, minute=m, second=0, microsecond=0)
        if stop <= n:
            stop += dt.timedelta(days=1)
    show = {}
    feed = a.feed
    if not feed:
        st, _, body, _ = get(f'https://itunes.apple.com/lookup?id={a.apple_id}&entity=podcast')
        res = json.loads(body or b'{}').get('results') or [{}]
        show = res[0]
        feed = show.get('feedUrl', '')
    print('feed:', feed, flush=True)
    st, hd, body, _ = get(feed)
    if st != 200:
        raise SystemExit(f'feed answered {st}')
    open(os.path.join(a.state, 'feed.xml'), 'wb').write(body)
    ch = ET.fromstring(body).find('channel')
    title = (ch.findtext('title') or show.get('collectionName') or 'BAPS Better Living').strip()
    img = ch.find(IT + 'image')
    about = dict(podcast=title, author=ch.findtext(IT + 'author') or ch.findtext('author'),
                 description=plain(ch.findtext('description')), link=ch.findtext('link'), feed=feed,
                 apple_id=a.apple_id, apple_url=show.get('collectionViewUrl'), language=ch.findtext('language'),
                 cover=img.get('href') if img is not None else ch.findtext('image/url'),
                 categories=[c.get('text') for c in ch.iter(IT + 'category')])
    have = set(x for x in open(a.have, encoding='utf-8').read().split('\n') if x) if a.have and os.path.exists(a.have) else set()
    eps = []
    for it in ch.findall('item'):
        enc = it.find('enclosure')
        url = enc.get('url') if enc is not None else ''
        pub = it.findtext('pubDate') or ''
        try:
            when = email.utils.parsedate_to_datetime(pub)
            day = when.date().isoformat()
        except Exception:
            when, day = None, ''
        t = (it.findtext('title') or '').strip()
        ext = os.path.splitext(urllib.parse.urlsplit(url).path)[1] or '.mp3'
        im = it.find(IT + 'image')
        eps.append(dict(podcast=title, title=t, date=day, published=when.isoformat() if when else pub,
                        season=it.findtext(IT + 'season'), episode=it.findtext(IT + 'episode'),
                        duration=it.findtext(IT + 'duration'), guid=it.findtext('guid'), link=it.findtext('link'),
                        description=plain(it.findtext('description') or it.findtext(IT + 'summary')),
                        sound_url=url, sound_type=enc.get('type') if enc is not None else '',
                        sound_bytes_listed=enc.get('length') if enc is not None else '',
                        image=im.get('href') if im is not None else about['cover'],
                        file=f"episodes/{day or 'undated'} {safe(t)}{ext}", source=f'{title} podcast feed {feed}'))
    print(json.dumps(dict(podcast=title, episodes=len(eps))), flush=True)
    done = 0
    finished = True
    if about['cover'] and 'cover.jpg' not in have:
        st, _, b, _ = get(about['cover'])
        if st == 200:
            open(os.path.join(files, 'cover.jpg'), 'wb').write(b)
    for e in eps:
        if not e['sound_url'] or e['file'] in have:
            continue
        if stop and dt.datetime.now(dt.timezone.utc) >= stop:
            finished = False
            break
        st, hd, b, final = get(e['sound_url'])
        e['fetched_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        if st != 200:
            e['missing'] = st
            continue
        fn = os.path.join(files, e['file'])
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        open(fn, 'wb').write(b)
        e.update(bytes=len(b), type=hd.get('content-type'), last_modified=hd.get('last-modified'), served_from=final)
        done += 1
        time.sleep(a.gap)
    old = {}
    p = os.path.join(a.state, 'episodes.jsonl')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            r = json.loads(l)
            old[r['file']] = r
    with open(p, 'w', encoding='utf-8') as f:
        for e in eps:
            keep = old.get(e['file'], {})
            row = {**keep, **{k: v for k, v in e.items() if v not in (None, '') or k not in keep}}
            txt = (row.get('title') or '') + ' ' + (row.get('description') or '')
            row['gurus_named'] = [g for g, r in (('Pramukh Swami Maharaj', r'(?i)pramukh\s*swami|\bpsm\b|bapa'),
                                                 ('Mahant Swami Maharaj', r'(?i)mahant\s*swami|\bmsm\b')) if re.search(r, txt)]
            row['in_drive'] = e['file'] in have or 'bytes' in e or bool(keep.get('in_drive'))
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    json.dump(about, open(os.path.join(a.state, 'podcast.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    out = dict(episodes=len(eps), saved_now=done, finished=finished, at=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'))
    json.dump(out, open(os.path.join(a.state, 'last-run.json'), 'w'))
    print(json.dumps(out), flush=True)


if __name__ == '__main__':
    main()
