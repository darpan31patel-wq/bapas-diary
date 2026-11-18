"""Bapa Through The Years in the site's maroon and gold (Darpan, 18 Nov 2026: "Through the years is orange and
charcoal, so it looks like a different site next to the maroon and gold tabs. FIX").

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site, after web_type.py:

    python3 tools/web_years_look.py --out out

The page itself is built on its own branch (faces-years.yml, unpacked into out/through-the-years/), and every colour on
it comes from a few CSS variables, so this step only puts a small style block at the end of the page that gives those
variables the colours of Legacy and About (maroon #42101c to #160509, gold #d9a441, paper #f3ead9). It also keeps the
page one screen tall when the Aa text size button makes the page bigger (the page zooms, so its height is divided by
the zoom). Running it twice changes nothing.
"""
import argparse, os

MARK = 'id="years-look"'
STYLE = """<style id="years-look">
/* the site's maroon and gold (Darpan, 18 Nov 2026), from tools/web_years_look.py */
:root { --bg: #1d070d; --panel: #3a0e19; --line: #6b4a2a; --ink: #f3ead9; --muted: #c9b79a; --saffron: #d9a441;
  --glow: rgba(217,164,65,.16); }
html, body { background: radial-gradient(120% 80% at 50% 0%, #42101c, #160509 70%) fixed, #160509; }
.tab[aria-selected="true"] { color: #2a0912; background: linear-gradient(#ffe296, #d9a441); border-color: #d9a441; }
.tab[aria-selected="true"] .yrs { color: #2a0912; }
.tab:not([aria-selected="true"]) { background: rgba(58,14,25,.85); border-color: rgba(217,164,65,.35); }
.more { background: rgba(58,14,25,.85); border-color: rgba(217,164,65,.45); }
.more:hover, .tab:hover { border-color: #ffe296; }
.age, .intro .ia { color: #d9a441; }
.intro { background: radial-gradient(closest-side, rgba(29,7,13,.88), rgba(29,7,13,.62)); }
/* phones: the full screen look's dark bands in maroon too (site/phone/phone.css draws them in near black) */
html.ph-years-page .ph-top { background: linear-gradient(rgba(29,7,13,.8), rgba(29,7,13,0)); }
html.ph-years-page .frame { background: #1d070d; }
html.ph-years-page .stage::after { background: linear-gradient(rgba(29,7,13,0), rgba(29,7,13,.8) 45%, rgba(29,7,13,.95)); }
html.ph-years-page .top { background: rgba(42,9,18,.6); border-color: rgba(217,164,65,.3); }
html.ph-years-page .date, html.ph-years-page .cal { color: #e3d3bb; }
html.ph-years-page .more { box-shadow: 0 4px 14px rgba(217,164,65,.3); }
/* phones at a bigger text size: the two guru names wrap onto two lines instead of being cut off */
html[style*="zoom"].ph-years-page body .tab .who { white-space: normal; text-wrap: balance; line-height: 1.1; }
/* one screen tall at any text size: the page zooms with the Aa button, so its height shrinks by the same amount */
body { height: calc(100dvh / var(--bd-zoom, 1)); }
</style>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    p = os.path.join(a.out, 'through-the-years', 'index.html')
    if not os.path.exists(p):
        print('years look: no through-the-years page')
        return
    s = open(p, encoding='utf-8').read()
    if MARK in s:
        print('years look: already there')
        return
    # at the very end of the page, so it comes after the page's own styles and wins (the page has no </head>)
    s = s.replace('</body>', STYLE + '</body>', 1) if '</body>' in s else s + '\n' + STYLE
    open(p, 'w', encoding='utf-8').write(s)
    print('years look: maroon and gold on Through the years')


if __name__ == '__main__':
    main()
