"""Download every photo of a public Telegram channel for the undated photos in Search (Darpan, 30 Oct 2026:
"I have about 2,000 random pictures ... add them into the search database").

    python tools/tg_fetch.py pramukhswamimaharaj posts.json
    python tools/undated_fetch.py posts.json raw/

Writes raw/p<post>-<n>.jpg for each photo and raw/manifest.json: [{"file", "post", "posted", "text"}, ...].
The post date is only when it was shared, not when the photo was taken, so it is never used as the photo's date.
"""
import json, os, sys, time, urllib.request


def get(url):
    for n in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception as e:
            print('retry', url[:80], e); time.sleep(5 * (n + 1))
    return None


def main(posts, out):
    os.makedirs(out, exist_ok=True)
    seen, rows = set(), []
    for p in json.load(open(posts, encoding='utf-8')):
        for n, url in enumerate(p.get('images') or []):
            if url in seen:
                continue
            seen.add(url)
            name = f"p{p['id']}-{n + 1}.jpg"
            path = os.path.join(out, name)
            if not os.path.exists(path):
                data = get(url)
                if not data:
                    continue
                open(path, 'wb').write(data)
                time.sleep(0.2)
            rows.append(dict(file=name, post=p['id'], posted=p.get('posted'), text=(p.get('text') or '').strip()))
            if len(rows) % 200 == 0:
                print(len(rows), 'photos', flush=True)
    json.dump(rows, open(os.path.join(out, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('saved', len(rows), 'photos')


if __name__ == '__main__':
    main(*sys.argv[1:3])
