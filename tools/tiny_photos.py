"""Tiny copies of every photo for the website's small squares (whole website review, 28 Oct 2026). Website only.

The Calendar's day squares, the Today cards and the Search grid show photos 60 to 200 pixels across, but each one
downloads the 480 px copy in R2 s/ (about 50 KB). This makes t/ALBUM/FILE from s/ALBUM/FILE: the short side
240 px (sharp on a phone's screen at twice the size), WebP, about 8 KB. The name keeps the .jpg ending so the pages
only swap s/ for t/; R2 sends it as image/webp. Nothing is fetched from baps.org: s/ is already in our own R2.

    python3 tools/tiny_photos.py --src s --out t      # every .jpg under s/ becomes the same path under t/
"""
import argparse
import io
import pathlib
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageOps

SHORT = 240
QUALITY = 74


def tiny(job):
    src, dst = job
    try:
        im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
        w, h = im.size
        k = SHORT / min(w, h)
        if k < 1:
            im = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
        b = io.BytesIO()
        im.save(b, 'WEBP', quality=QUALITY, method=6)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b.getvalue())
        return None
    except Exception as e:   # a broken file is skipped and named, never stops the rest
        return f'{src}: {e}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    src, out = pathlib.Path(a.src), pathlib.Path(a.out)
    jobs = [(p, out / p.relative_to(src)) for p in src.rglob('*') if p.is_file()]
    bad = 0
    with ProcessPoolExecutor() as pool:
        for err in pool.map(tiny, jobs, chunksize=64):
            if err:
                bad += 1
                print('skipped', err)
    print(f'{len(jobs) - bad} tiny copies made, {bad} skipped', flush=True)


if __name__ == '__main__':
    main()
