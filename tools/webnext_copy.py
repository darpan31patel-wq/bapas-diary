"""The photos of baps.org's new style News pages (/<region>/news/<slug>, photos on static.wn.baps-apps.org), which the
GalleryImages copy never sees: saved into Darpan's Drive archive and the website's photo store (R2), like every other
baps.org photo (Darpan, 13 Nov 2026: "faster").

    python3 tools/webnext_copy.py --webnext webnext.json --articles articles.json --work work --list webnext-photos.json

webnext.json is crawl/news/webnext.json on the database branch (the nightly thread reads each gallery page in his
Chrome and keeps "files", the full address of each photo, in the same order as "names"). Each photo gets
  album  webnext-<folder number>   (the number in .../news/27189/display/)
  file   its file name on static.wn
saved at photos/baps.org/<year>/<date> <place>/<name> (<file>) in work/, and its R2 copies (o l m s t, made by
hires_photos.make) in work/r2/. webnext-photos.json lists every photo saved, for the database to take in later.
A Cloudflare check page stops it at once: it never tries to get past one.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from build_archive import clean   # noqa: E402  (the same safe names as every other Drive photo)


class Check(Exception):
    pass


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bapas-diary archive)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        body, kind = r.read(), r.headers.get('Content-Type', '')
    if not kind.startswith('image'):
        if b'Just a moment' in body[:5000] or b'challenge' in body[:5000]:
            raise Check(url)
        return None
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--webnext', required=True)
    ap.add_argument('--articles', required=True)
    ap.add_argument('--work', default='work')
    ap.add_argument('--list', default='webnext-photos.json')
    ap.add_argument('--have', help='Drive paths already saved (rclone lsf -R), skipped')
    ap.add_argument('--gap', type=float, default=1.0)
    a = ap.parse_args()
    W = json.load(open(a.webnext, encoding='utf-8'))
    A = json.load(open(a.articles, encoding='utf-8'))
    have = set(open(a.have).read().split('\n')) if a.have and os.path.exists(a.have) else set()
    import hires_photos
    rows, saved, skipped, failed = [], 0, 0, 0
    for path, g in sorted(W.items()):
        files, names = g.get('files') or [], g.get('names') or []
        if not files:
            continue
        art = A.get(path) or {}
        when = g.get('date') or art.get('date') or ''
        place = art.get('place') or ''
        y = when[:4] or 'undated'
        town = re.sub(r',\s*India$', '', place)
        folder = clean(f'{when} {town}', 70)
        for i, src in enumerate(files):
            if 'static.wn.baps-apps.org' not in src or '/display/' not in src:
                continue   # YouTube thumbnails and the page's banner crops
            m = re.search(r'/(\d+)/display/', src)   # the folder number is in each photo's own address (a few
            if not m:                                 # galleries' folder field is a video page, 13 Nov 2026)
                continue
            album = f'webnext-{m[1]}'
            file = urllib.parse.unquote(src.split('?')[0].rsplit('/', 1)[1])
            stem, ext = os.path.splitext(file)
            cap = names[i] if i < len(names) else ''
            cap = clean(cap.replace('_', ' '), 80)
            name = f'{cap} ({stem}){ext or ".jpg"}' if cap else file
            if len(name.encode()) > 200:
                name = f'{cap[:40]} ({stem[:60]}){ext or ".jpg"}'
            local = f'photos/baps.org/{y}/{folder}/{name}'
            row = dict(album=album, file=file, date=when, place=place, caption=names[i] if i < len(names) else '',
                       article=path, src=src, local_path=local)
            dst = os.path.join(a.work, local)
            if local in have:
                rows.append(row); skipped += 1; continue
            try:
                body = get(src)
            except Check as e:
                print(f'A Cloudflare check page at {e}: stopping here, never trying to get past it')
                break
            except Exception as e:
                print(f'  could not fetch {src}: {e}'); failed += 1; continue
            if not body:
                failed += 1; continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(body)
            err = hires_photos.make((dst, os.path.join(a.work, 'r2'), f'{album}/{file}'))
            if err:
                print('  ', err)
            rows.append(row); saved += 1
            time.sleep(a.gap)
        else:
            continue
        break
    json.dump(rows, open(a.list, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'New style News photos: {saved} saved, {skipped} already in Drive, {failed} could not be fetched; '
          f'{len(rows)} listed in {a.list}')


if __name__ == '__main__':
    main()
