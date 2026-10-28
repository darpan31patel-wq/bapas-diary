"""Website only (bapas-diary.com): the Calendar shows all seven days on an upright tablet (tablet check, 28 Oct 2026).

The Calendar sizes its days from the screen's height, so on an upright iPad or Android tablet a month came out wider
than the screen and Saturday and Sunday were cut off. Here the days are also kept narrow enough for all seven to fit
across, a little taller than wide. Phones (their own Calendar) and computers and sideways tablets (where the height
already decides) look exactly as before. The Calendar page is built from another thread's pinned commit, so the line
is swapped after the build; if the Calendar's code has changed and the line is not found, the page is left as it was.

    python3 tools/web_tablet.py --out out
"""
import argparse
import pathlib

OLD = """const h=(track.clientHeight-14)*Z, g=Math.max(3,Math.min(10,innerHeight*.009)*Z), bh=0;
  const rh=(h-26*Z-5*g)/5, cw=Math.max(30,Math.round(rh*1.08));"""
NEW = """let h=(track.clientHeight-14)*Z; const g=Math.max(3,Math.min(10,innerHeight*.009)*Z), bh=0;
  let rh=(h-26*Z-5*g)/5, cw=Math.max(30,Math.round(rh*1.08));
  /* an upright tablet: all seven days across the screen, the days a little taller than wide (tablet check, 28 Oct 2026) */
  const fitW=Math.floor((track.clientWidth*.97-6*g)/7);
  if(cw>fitW){cw=Math.max(30,fitW); rh=Math.min(rh,cw*1.3); h=26*Z+5*rh+5*g}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    page = pathlib.Path(ap.parse_args().out) / 'calendar' / 'index.html'
    html = page.read_text(encoding='utf-8')
    if html.count(OLD) != 1:
        print('Calendar: size line not found, left as it was (tablet fit not used)')
        return
    page.write_text(html.replace(OLD, NEW), encoding='utf-8')
    print('Calendar: all seven days fit across an upright tablet')


if __name__ == '__main__':
    main()
