"""Redraw a wide layout from photos saved by make.py (preview/<date>-photos-<style>/), without downloading anything.
python relayout.py 2026-10-18 W2 out.png"""
import json, os, sys, datetime
from PIL import Image
import make

date, style, out = sys.argv[1], sys.argv[2], sys.argv[3]
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview', f'{date}-photos-{style}')
photos = json.load(open(os.path.join(folder, 'photos.json')))
for i, x in enumerate(photos):
    x['im'] = Image.open(os.path.join(folder, f'{i:02d}.jpg')).convert('RGB')
    if x.get('face') is not None:
        x['face'] = tuple(x['face'])
day = datetime.date.fromisoformat(date)
im = make.compose(photos, day, seed=f'{day:%m-%d}', style=style)
im.save(out, optimize=True)
print('made', out)
