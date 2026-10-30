"""The undated photos for Search, made ready (Darpan, 30 Oct 2026: "rotate them and scale them and maybe edit them
slightly as you see fit, but you can add them into the search database").

Website only: nothing here touches the daily 2pm picture chain. The photos come from the release undated-raw
(tools/undated_fetch.py), never from baps.org.

    python3 tools/undated_process.py raw/ out/

For every photo in raw/ (raw/manifest.json):
  1. same photo twice (a small fingerprint of it, the dHash, nearly the same): only the biggest copy is kept
  2. turned upright, only when no face is found as it came and Bapa's face is found clearly in another turn
     (the website's face check, tools/web_bapa_rules.py)
  3. plain black or white bars round the photo cut off, then touched up lightly: a little more contrast where the photo is flat, a gentle sharpen, nothing that changes it
  4. made in the website's sizes, as tools/hires_photos.py does: o/ the touched up full photo, l/ 2560, m/ 1200, s/ 480
     wide, all under the album "undated" (out/o/undated/u0001.jpg ...)
Writes out/undated.json: [{"file", "post", "text", "turn", "psm", "msm", "face": [x, y, w, h], "front", "sharp", "W", "H",
"faces", "dupe_of"}] (psm, msm: the best face's likeness to each guru, 0 to 1; the same as the dated photos' face check).
"""
import io, json, os, sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageStat

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
import web_bapa_rules as R

SIZES = (('l', 2560, 86), ('m', 1200, 82))   # as tools/hires_photos.py
SMALL = 480
ALBUM = 'undated'


def dhash(im, n=8):
    g = np.asarray(im.convert('L').resize((n + 1, n), Image.LANCZOS), np.int16)
    return int(''.join('1' if b else '0' for b in (g[:, 1:] > g[:, :-1]).flatten()), 2)


def faces(im):
    """Every face in im with its likeness to each guru: [(score, psm, msm, box, front)], best first."""
    m = R.models()
    small = im.copy(); small.thumbnail((1280, 1280))
    k = im.width / small.width
    bgr = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2BGR)
    m['detect'].setInputSize((bgr.shape[1], bgr.shape[0]))
    found = m['detect'].detect(bgr)[1]
    out = []
    for f in found if found is not None else []:
        e = m['recognise'].feature(m['recognise'].alignCrop(bgr, f))[0]
        e = e / np.linalg.norm(e)
        psm, msm = float(m['bapa']['psm'] @ e), float(m['bapa']['msm'] @ e)
        out.append((float(f[14]), psm, msm, tuple(float(v) * k for v in f[:4]), R.front_view(f)))
    return sorted(out, key=lambda f: -max(f[1], f[2]))


def upright(im):
    """The turn (0, 90, 180, 270 degrees) that stands the photo up, and the faces seen that way. Nearly every photo in
    the channel is already upright, and a face seen sideways can still score well (a first try turned 13 upright photos
    over), so a photo is only turned when no face at all is found as it came and Bapa is found clearly in another turn."""
    fs = faces(im)
    if fs:
        return 0, im, fs
    best = (0, 0, im, fs)
    for turn in (90, 180, 270):
        t = im.rotate(turn, expand=True)
        f2 = faces(t)
        guru = max((max(f[1], f[2]) for f in f2), default=0)
        if guru >= .6 and guru > best[0]:
            best = (guru, turn, t, f2)
    return best[1], best[2], best[3]


def trim_bars(im):
    """Plain black or white bars round a photo (a letterboxed resend) cut off, when they are clearly bars: rows or
    columns that are one flat colour, very dark or very light, from the edge inwards."""
    g = np.asarray(im.convert('L'), np.float32)
    flat = lambda a: a.std() < 3 and (a.mean() < 14 or a.mean() > 245)
    t, b, l, r = 0, g.shape[0], 0, g.shape[1]
    while t < b - 20 and flat(g[t, l:r]): t += 1
    while b > t + 20 and flat(g[b - 1, l:r]): b -= 1
    while l < r - 20 and flat(g[t:b, l]): l += 1
    while r > l + 20 and flat(g[t:b, r - 1]): r -= 1
    cut = (t + g.shape[0] - b) / g.shape[0] + (l + g.shape[1] - r) / g.shape[1]
    return im.crop((l, t, r, b)) if cut > .03 else im


def touch_up(im):
    """A light touch: contrast stretched only as far as the darkest and lightest 0.5%, half strength, a little colour
    back for the faded ones, and a gentle sharpen for the softness of a resend."""
    lo = ImageOps.autocontrast(im, cutoff=.5)
    im = Image.blend(im, lo, .5)
    sat = ImageStat.Stat(im.convert('HSV').split()[1]).mean[0]
    if sat < 70:
        from PIL import ImageEnhance
        im = ImageEnhance.Color(im).enhance(1.08)
    return im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=45, threshold=3))


def save(im, path, q):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, 'JPEG', quality=q, optimize=True, progressive=True)


def main(raw, out):
    rows = json.load(open(os.path.join(raw, 'manifest.json'), encoding='utf-8'))
    ims, hashes = {}, {}
    for r in rows:
        try:
            im = Image.open(os.path.join(raw, r['file']))
            im = ImageOps.exif_transpose(im).convert('RGB')
        except Exception as e:
            print(r['file'], e); continue
        ims[r['file']] = im.size
        hashes[r['file']] = dhash(im)
    # the same photo posted more than once: the biggest copy is kept
    keep, dupe = [], {}
    for r in sorted((r for r in rows if r['file'] in ims), key=lambda r: -ims[r['file']][0] * ims[r['file']][1]):
        h = hashes[r['file']]
        same = next((k for k in keep if bin(hashes[k] ^ h).count('1') <= 6), None)
        if same:
            dupe[r['file']] = same
        else:
            keep.append(r['file'])
    order = [r for r in rows if r['file'] in ims]   # numbered in the channel's own order
    done, n = [], 0
    for r in order:
        rec = dict(file=r['file'], post=r['post'], text=r.get('text', ''))
        if r['file'] in dupe:
            rec['dupe_of'] = dupe[r['file']]
            done.append(rec); continue
        n += 1
        name = f'u{n:04d}.jpg'
        im = ImageOps.exif_transpose(Image.open(os.path.join(raw, r['file']))).convert('RGB')
        turn, im, fs = upright(trim_bars(im))
        im = touch_up(im)
        save(im, os.path.join(out, 'o', ALBUM, name), 92)
        for tier, side, q in SIZES:
            t = im.copy(); t.thumbnail((side, side), Image.LANCZOS)
            save(t, os.path.join(out, tier, ALBUM, name), q)
        s = im.copy(); s.thumbnail((SMALL, 10 * SMALL), Image.LANCZOS)
        save(s, os.path.join(out, 's', ALBUM, name), 82)
        best = fs[0] if fs else None
        sharp = R.face_quality(im, best[3])[0] if best else 0
        rec.update(name=name, turn=turn, W=im.width, H=im.height, faces=len(fs),
                   psm=round(best[1], 3) if best else 0, msm=round(best[2], 3) if best else 0,
                   face=[round(v / d, 4) for v, d in zip(best[3], (im.width, im.height, im.width, im.height))] if best else None,
                   front=round(best[4], 2) if best else 0, sharp=round(sharp))
        done.append(rec)
        if n % 100 == 0:
            print(n, 'photos ready', flush=True)
    json.dump(done, open(os.path.join(out, 'undated.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(n, 'photos ready,', len(dupe), 'repeats left out,', sum(1 for d in done if d.get('turn')), 'turned upright')


if __name__ == '__main__':
    main(*sys.argv[1:3])
