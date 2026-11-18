"""Download again the baps.org News galleries we only got part of (Darpan, 18 Nov 2026: 109 stories short by 1,406
photos; the cloud cannot open baps.org, so this runs on his own computer overnight).

    python3 tools/news_regrab.py                     reads tools/news_regrab_list.json, writes news-regrab.json

Gentle on baps.org: one page at a time, GAP seconds apart, and it stops by itself at 04:15 UK time (the daily
picture's morning starts 04:30) or as soon as baps.org shows a check page or says no. It saves after every page, so
running it again carries on where it stopped. Standard library only.

news-regrab.json: {story path: {"g": {gallery path: {"t": title, "rows": [[album, file, caption], ...]}}, "done": true}}
(the same shape as crawl/news/articles.json, so the cloud merges it in).
"""
import datetime, html, json, os, re, sys, time, urllib.error, urllib.request

BASE = 'https://www.baps.org'
GAP = 4
STOP_AT = datetime.time(4, 15)   # UTC; the UK is on UTC in winter
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = os.path.join(HERE, 'tools', 'news_regrab_list.json')
OUT = os.path.join(HERE, 'news-regrab.json')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/130.0 Safari/537.36')


class Stop(Exception):
    pass


last = [0.0]


def get(path):
    if datetime.datetime.utcnow().time() >= STOP_AT and datetime.datetime.utcnow().hour < 12:
        raise Stop('04:15 reached, stopping for the morning picture')
    wait = last[0] + GAP - time.time()
    if wait > 0:
        time.sleep(wait)
    url = path if path.startswith('http') else BASE + path
    for i in range(3):
        last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-GB,en;q=0.9'})
            with urllib.request.urlopen(req, timeout=40) as r:
                text = r.read().decode('utf-8', 'replace')
            if re.search(r'cf-challenge|captcha|verify you are human|Just a moment', text, re.I):
                raise Stop('baps.org showed a check page')
            return text
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise Stop(f'baps.org said {e.code}')
            if e.code == 404:
                return ''
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(15 * (i + 1))
    return ''


def rows(text):
    out, seen = [], set()
    for tag in re.findall(r'<img\b[^>]*>', text, re.I):
        m = re.search(r'GalleryImages/(\d+)/WebImages/([^/"\'?#]+\.jpe?g)', tag, re.I)
        if not m or (m[1], m[2].lower()) in seen:
            continue
        seen.add((m[1], m[2].lower()))
        cap = re.search(r'\b(?:alt|title)="([^"]*)"', tag, re.I)
        out.append([m[1], m[2], re.sub(r'\s+', ' ', html.unescape(cap[1] if cap else '')).strip()])
    return out


def links(text, pattern):
    found = []
    for h in re.findall(r'href="([^"]+)"', text, re.I):
        h = html.unescape(h).replace('https://www.baps.org', '').replace('http://www.baps.org', '')
        if re.match(pattern, h, re.I) and h not in found:
            found.append(h)
    return found


def gallery(path):
    """Every photo of one gallery, following its page links (?page=2 and the like)."""
    first = get(path)
    title = re.search(r'<title>([^<]*)', first, re.I)
    allrows, todo, done = rows(first), [], {path.lower()}
    stem = re.escape(path.split('?')[0])
    todo += [h for h in links(first, stem + r'\?.+') if h.lower() not in done]
    while todo and len(done) < 40:
        p = todo.pop(0)
        if p.lower() in done:
            continue
        done.add(p.lower())
        t = get(p)
        have = {(a, f.lower()) for a, f, _ in allrows}
        allrows += [r for r in rows(t) if (r[0], r[1].lower()) not in have]
        todo += [h for h in links(t, stem + r'\?.+') if h.lower() not in done]
    return {'t': html.unescape(title[1]).strip() if title else '', 'rows': allrows}


def main():
    todo = json.load(open(LIST))
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    try:
        for n, s in enumerate(todo, 1):
            story = s['story']
            if out.get(story, {}).get('done'):
                continue
            rec = out.setdefault(story, {'g': {}})
            page = get(story)
            gals = list(dict.fromkeys(s['galleries'] + links(page, r'^/?photos/\d{4}/[^/?#]+\.aspx$')))
            for g in gals:
                if g in rec['g']:
                    continue
                rec['g'][g] = gallery(g)
                json.dump(out, open(OUT, 'w'))
            rec['done'] = True
            json.dump(out, open(OUT, 'w'))
            got = sum(len(v['rows']) for v in rec['g'].values())
            print(f'{n}/{len(todo)}  {got} photos (baps.org says {s["said"]}, we had {s["have"]})  {story}', flush=True)
    except Stop as e:
        print('Stopped:', e, flush=True)
    except KeyboardInterrupt:
        print('Stopped by hand', flush=True)
    json.dump(out, open(OUT, 'w'))
    done = sum(1 for v in out.values() if v.get('done'))
    print(f'{done} of {len(todo)} stories done. Saved {OUT}', flush=True)


if __name__ == '__main__':
    sys.exit(main())
