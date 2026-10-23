"""What is happening in each photo, for the website search (Darpan, 23 Oct 2026: "smiling, laughing, glasses, eating...
not just from the caption, but from your assessment of the image").

Website only: nothing here touches the daily 2pm picture. Runs on GitHub (.github/workflows/website-tags.yml) with an
open CLIP model (no Claude, no paid service). Each tag is a pair of descriptions, one for and one against; the photo
gets a score from 0 to 1 for each tag, and the search build keeps the tags whose score clears that tag's bar.

    python3 tools/photo_tags.py --photos small --out tags.json

--photos is a folder of the small R2 photos (ALBUM/FILE); tags.json maps "ALBUM/FILE" to {tag: score} for every
tag scoring at least 0.3, so the bars can be tuned later without running the model again.
"""
import argparse, json, os, sys

# tag: (what the photo shows when the tag fits, what it shows when it doesn't)
TAGS = {
    'smiling': ('a photo of a smiling old monk', 'a photo of a serious old monk'),
    'laughing': ('a photo of an old monk laughing heartily', 'a photo of an old monk with a calm face'),
    'glasses': ('a photo of a monk wearing glasses', 'a photo of a monk without glasses'),
    'eating': ('a photo of a monk eating food', 'a photo of a monk not eating'),
    'food': ('a photo of plates of food offerings', 'a photo with no food'),
    'blessing': ('a photo of a monk raising his hand in blessing', 'a photo of a monk with his hands down'),
    'folded hands': ('a photo of a person with hands folded in namaste', 'a photo of a person with hands apart'),
    'garland': ('a photo of a monk wearing a flower garland', 'a photo of a monk without a garland'),
    'arti': ('a photo of a person waving an arti lamp with a flame', 'a photo with no lamp or flame'),
    'puja': ('a photo of a monk doing puja with small murtis in front of him', 'a photo of a monk with nothing in front of him'),
    'murti': ('a photo of decorated Hindu deity statues in a shrine', 'a photo of people, no statues'),
    'microphone': ('a photo of a monk speaking into a microphone', 'a photo with no microphone'),
    'reading': ('a photo of a monk reading a book or letter', 'a photo of a monk not reading'),
    'writing': ('a photo of a monk writing with a pen', 'a photo of a monk not writing'),
    'children': ('a photo with young children', 'a photo with only adults'),
    'crowd': ('a photo of a huge crowd of people', 'a photo of a few people'),
    'stage': ('a photo of a monk seated on a decorated stage', 'a photo of a monk not on a stage'),
    'walking': ('a photo of a monk walking', 'a photo of a monk sitting'),
    'car': ('a photo of a monk in or beside a car', 'a photo with no car'),
    'plane': ('a photo of an aeroplane or an airport', 'a photo with no aeroplane'),
    'elephant': ('a photo of an elephant', 'a photo with no elephant'),
    'cow': ('a photo of a cow', 'a photo with no cow'),
    'flowers': ('a photo full of flower decorations', 'a photo with few flowers'),
    'umbrella': ('a photo of a monk under an umbrella', 'a photo with no umbrella'),
    'water': ('a photo of a river, lake or sea', 'a photo with no water'),
    'night': ('a photo taken at night with lights', 'a photo taken in daylight'),
    'outdoors': ('a photo taken outdoors under the sky', 'a photo taken indoors'),
    'mandir': ('a photo of a carved stone Hindu temple building', 'a photo with no temple building'),
    'close up': ('a close up portrait photo of a monk\'s face', 'a photo of a wide scene'),
    'saffron turban': ('a photo of a monk wearing a turban or headdress', 'a photo of a monk with a bare head'),
    'shawl': ('a photo of a monk wrapped in a shawl', 'a photo of a monk without a shawl'),
    'sleeping': ('a photo of a monk resting with eyes closed', 'a photo of a monk with eyes open'),
    'meditating': ('a photo of a monk meditating with a rosary mala', 'a photo of a monk not meditating'),
    'gifts': ('a photo of someone giving a gift to a monk', 'a photo with no gift'),
    'pointing': ('a photo of a monk pointing with his finger', 'a photo of a monk not pointing'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photos', required=True)
    ap.add_argument('--out', default='tags.json')
    ap.add_argument('--batch', type=int, default=64)
    a = ap.parse_args()
    import torch, open_clip
    from PIL import Image
    torch.set_num_threads(os.cpu_count() or 4)
    model, _, prep = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
    tok = open_clip.get_tokenizer('ViT-B-32')
    model.eval()
    names = list(TAGS)
    with torch.no_grad():
        t = model.encode_text(tok([p for n in names for p in TAGS[n]]))
        t = t / t.norm(dim=-1, keepdim=True)
    files = sorted(os.path.relpath(os.path.join(r, f), a.photos) for r, _, fs in os.walk(a.photos) for f in fs)
    out = {}
    for i in range(0, len(files), a.batch):
        part = files[i:i + a.batch]
        ims = []
        for f in part:
            try:
                ims.append(prep(Image.open(os.path.join(a.photos, f)).convert('RGB')))
            except Exception:
                ims.append(None)
        keep = [(f, im) for f, im in zip(part, ims) if im is not None]
        if not keep:
            continue
        with torch.no_grad():
            v = model.encode_image(torch.stack([im for _, im in keep]))
            v = v / v.norm(dim=-1, keepdim=True)
            pair = (100 * v @ t.T).view(len(keep), len(names), 2).softmax(dim=-1)[:, :, 0]
        for (f, _), row in zip(keep, pair.tolist()):
            out[f] = {n: round(s, 2) for n, s in zip(names, row) if s >= .3}
        print(f'{min(i + a.batch, len(files))} of {len(files)}', flush=True)
    json.dump(out, open(a.out, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
