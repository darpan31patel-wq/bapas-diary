"""What is happening in each photo, for the website search (Darpan, 23 Oct 2026: "smiling, laughing, glasses, eating...
not just from the caption, but from your assessment of the image").

Website only: nothing here touches the daily 2pm picture. Runs on GitHub (.github/workflows/website-tags.yml) with an
open CLIP model (no Claude, no paid service). Each tag is one sentence; every photo gets a similarity to each.

    python3 tools/photo_tags.py --photos small --out tags.json

--photos is a folder of the small R2 photos (ALBUM/FILE); tags.json holds {"tags": [...], "photos": {"ALBUM/FILE":
[similarity per tag]}}, every score kept, so the bars can be tuned later without running the model again.
"""
import argparse, json, os, sys

# tag: what the photo shows. CLIP compares each photo with each sentence; the search build keeps a tag only where the
# photo stands out from all the others for that sentence (see TAG_Z in tools/build_search.py), because a single
# score on its own says little.
TAGS = {
    'smiling': 'a close photo of an old Indian monk with a big warm smile',
    'laughing': 'a photo of an old Indian monk laughing with his mouth open',
    'glasses': 'a photo of an old Indian monk wearing spectacles',
    'eating': 'a photo of a monk eating a meal with his hand from a plate',
    'food': 'a photo of many plates and bowls of Indian sweets and food',
    'blessing': 'a photo of an Indian monk raising his right hand to bless people',
    'folded hands': 'a photo of an Indian monk with palms joined together in namaste',
    'garland': 'a photo of an Indian monk wearing a thick garland of flowers around his neck',
    'arti': 'a photo of a monk holding a burning arti lamp with flames',
    'puja': 'a photo of a monk seated doing morning puja with small idols on a cloth in front of him',
    'murti': 'a photo of richly dressed Hindu idols in a temple shrine',
    'microphone': 'a photo of a monk speaking into a microphone',
    'reading': 'a photo of a monk reading a book',
    'writing': 'a photo of a monk writing a letter with a pen',
    'children': 'a photo of an Indian monk with small children',
    'crowd': 'a photo of a vast crowd of thousands of people',
    'stage': 'a photo of a monk seated on a big decorated stage in front of an audience',
    'walking': 'a photo of an old monk walking, supported by other monks',
    'car': 'a photo of a monk sitting inside a car',
    'plane': 'a photo of an aeroplane at an airport',
    'elephant': 'a photo of an elephant',
    'cow': 'a photo of cows',
    'flowers': 'a photo of a stage covered in flower decorations',
    'umbrella': 'a photo of a monk walking under an umbrella',
    'water': 'a photo of a river or the sea',
    'night': 'a photo taken at night with bright lights',
    'mandir': 'a photo of the outside of a carved stone Hindu temple',
    'close up': 'a close up portrait of an old monk\'s face',
    'turban': 'a photo of an old monk wearing a turban',
    'shawl': 'a photo of an old monk wrapped in a woollen shawl',
    'meditating': 'a photo of a monk with eyes closed holding a prayer mala',
    'gifts': 'a photo of a man presenting a gift to a monk',
    'pointing': 'a photo of a monk pointing with his finger',
    'tilak': 'a photo of a man putting a chandlo tilak mark on a monk\'s forehead',
    'swing': 'a photo of a monk sitting on a decorated swing hindolo',
    'boat': 'a photo of people in a boat',
    'rain': 'a photo of people in the rain',
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
        t = model.encode_text(tok([TAGS[n] for n in names]))
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
            sims = v @ t.T
        for (f, _), row in zip(keep, sims.tolist()):
            out[f] = [round(x, 4) for x in row]
        print(f'{min(i + a.batch, len(files))} of {len(files)}', flush=True)
    json.dump({'tags': names, 'photos': out}, open(a.out, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main()
