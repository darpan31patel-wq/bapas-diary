"""Contact sheet of chosen baps.org photos, so Darpan can compare a year's options side by side.

    python tools/candidates.py --out out/sheet.jpg "4679:20111018-002f:18 Oct, blesses an ailing boy" ...

Each argument is album:photo id:label. Runs on GitHub Actions (this container cannot reach baps.org)."""
import argparse, concurrent.futures, os, sys, textwrap, urllib.request
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bapas-diary)'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:
            err = e
    print('  could not download', url, err)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='out/candidates.jpg')
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--title', default='')
    ap.add_argument('photos', nargs='+', help='album:id:label')
    a = ap.parse_args()
    items = []
    for p in a.photos:
        album, pid, label = p.split(':', 2)
        items.append({'url': f'https://www.baps.org/Data/Sites/1/Media/GalleryImages/{album}/WebImages/{pid}.jpg',
                      'id': pid, 'label': label})
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        datas = list(pool.map(lambda x: fetch(x['url']), items))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    W, pad, cap_h = 640, 24, 96
    font = ImageFont.truetype(os.path.join(HERE, 'fonts', 'Arimo-Bold.woff2'), 22) if os.path.exists(os.path.join(HERE, 'fonts', 'Arimo-Bold.woff2')) else ImageFont.load_default()
    tiles = []
    for x, data in zip(items, datas):
        if not data:
            continue
        open(os.path.join(os.path.dirname(a.out) or '.', x['id'] + '.jpg'), 'wb').write(data)
        im = Image.open(__import__('io').BytesIO(data)).convert('RGB')
        h = round(W * im.height / im.width)
        tiles.append((x, im.resize((W, h), Image.LANCZOS)))
    if not tiles:
        sys.exit('nothing downloaded')
    th = max(t[1].height for t in tiles) + cap_h
    rows = -(-len(tiles) // a.cols)
    top = 80 if a.title else pad
    sheet = Image.new('RGB', (a.cols * (W + pad) + pad, top + rows * (th + pad)), (250, 246, 238))
    dr = ImageDraw.Draw(sheet)
    if a.title:
        dr.text((pad, 24), a.title, fill=(60, 20, 20), font=ImageFont.truetype(os.path.join(HERE, 'fonts', 'Arimo-Bold.woff2'), 34) if os.path.exists(os.path.join(HERE, 'fonts', 'Arimo-Bold.woff2')) else font)
    for n, (x, im) in enumerate(tiles):
        cx = pad + (n % a.cols) * (W + pad)
        cy = top + (n // a.cols) * (th + pad)
        sheet.paste(im, (cx, cy))
        text = f'{n + 1}. {x["label"]}'
        y = cy + im.height + 8
        for line in textwrap.wrap(text, 48)[:3]:
            dr.text((cx, y), line, fill=(40, 20, 20), font=font)
            y += 28
    sheet.save(a.out, quality=88)
    print('wrote', a.out, len(tiles), 'photos')


if __name__ == '__main__':
    main()
