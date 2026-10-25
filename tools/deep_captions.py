"""A sentence about each photo from the open Florence-2 model, to compare with the tag words (tools/deep_tags.py).
Website only, test for now: python3 tools/deep_captions.py --photos photos --n 120 --out captions.json
"""
import argparse, json, os, random, time
from unittest.mock import patch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photos', required=True)
    ap.add_argument('--n', type=int, default=120)
    ap.add_argument('--model', default='microsoft/Florence-2-large')
    ap.add_argument('--out', default='captions.json')
    a = ap.parse_args()
    import torch
    from PIL import Image
    from transformers import AutoModelForCausalLM, AutoProcessor
    from transformers.dynamic_module_utils import get_imports
    torch.set_num_threads(os.cpu_count() or 4)

    def no_flash(f):   # Florence lists flash_attn, which only matters on a graphics card
        return [i for i in get_imports(f) if i != 'flash_attn']
    with patch('transformers.dynamic_module_utils.get_imports', no_flash):
        model = AutoModelForCausalLM.from_pretrained(a.model, trust_remote_code=True, attn_implementation='eager').eval()
        proc = AutoProcessor.from_pretrained(a.model, trust_remote_code=True)
    files = sorted(os.path.relpath(os.path.join(r, f), a.photos) for r, _, fs in os.walk(a.photos) for f in fs)
    files = random.Random(1).sample(files, min(a.n, len(files)))
    out, t0 = {}, time.time()
    task = '<MORE_DETAILED_CAPTION>'
    for n, f in enumerate(files, 1):
        im = Image.open(os.path.join(a.photos, f)).convert('RGB')
        x = proc(text=task, images=im, return_tensors='pt')
        with torch.no_grad():
            ids = model.generate(input_ids=x['input_ids'], pixel_values=x['pixel_values'], max_new_tokens=160, num_beams=3)
        text = proc.batch_decode(ids, skip_special_tokens=False)[0]
        out[f] = proc.post_process_generation(text, task=task, image_size=im.size)[task]
        print(f'{n} {time.time() - t0:.0f}s {f}: {out[f]}', flush=True)
    json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)
    # sheets to check by eye: each photo with its sentence
    import textwrap
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    W, H = 520, 240
    keys = list(out)
    for s in range(0, len(keys), 12):
        sheet = Image.new('RGB', (2 * (W + 8), 6 * (H + 8)), 'white')
        d = ImageDraw.Draw(sheet)
        for c, f in enumerate(keys[s:s + 12]):
            x, y = (c % 2) * (W + 8), (c // 2) * (H + 8)
            im = Image.open(os.path.join(a.photos, f)).convert('RGB')
            im.thumbnail((240, H))
            sheet.paste(im, (x, y))
            d.multiline_text((x + 248, y), textwrap.fill(out[f], 36), fill='black', font=font)
        sheet.save(os.path.splitext(a.out)[0] + f'-{s // 12 + 1:02d}.jpg', quality=80)


if __name__ == '__main__':
    main()
