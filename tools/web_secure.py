"""Website only (bapas-diary.com): the globe's two helper scripts come from our own site, not another one.

Whole website review, 28 Oct 2026: Travels loaded d3 and topojson from cdnjs.cloudflare.com with no fingerprint
check, so if that site were ever broken into, its code would run on ours. Copies of the same versions live in
live/travels/lib/; this swaps every page's links to them. Any other outside script left is printed so it is seen.
Runs in website-deploy before web_offline.py, so the saved (no internet) copy picks up the new addresses.

    python3 tools/web_secure.py --out out
"""
import argparse
import pathlib
import re

OWN = {
    'https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js': '/travels/lib/d3-7.8.5.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js': '/travels/lib/topojson-3.0.2.min.js',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    out = pathlib.Path(ap.parse_args().out)
    for local in OWN.values():
        assert (out / local.lstrip('/')).is_file(), f'missing {local}'
    swapped = 0
    for page in sorted(out.rglob('*.html')):
        html = page.read_text(encoding='utf-8')
        new = html
        for far, near in OWN.items():
            new = new.replace(f'src="{far}"', f'src="{near}"')
        if new != html:
            page.write_text(new, encoding='utf-8')
            swapped += 1
        for src in re.findall(r'<script[^>]+src="(https?://[^"]+)"', new):
            print(f'outside script still on {page.relative_to(out)}: {src}')
    print(f'own copies of d3 and topojson on {swapped} pages')


if __name__ == '__main__':
    main()
