"""Website only (bapas-diary.com): the Calendar's day squares use the tiny photo copies (whole website review, 28 Oct 2026).

R2 t/ holds a 240 px WebP of every photo (about 10 KB, made by .github/workflows/website-tiny.yml from s/). The
Calendar page is built from another thread's pinned commit, so its photo address is swapped here after the build:
t/ first, and the 480 px s/ copy if a brand new photo has no tiny copy yet, so a square is never left blank.
If the Calendar's code has changed and the line is not found, the page is left exactly as it was.

    python3 tools/web_tiny.py --out out
"""
import argparse
import pathlib

OLD = "im.onerror=()=>blank(win,d,y,m,day); im.src=`${PHOTOS}s/${d[4]}/${encodeURIComponent(d[5])}`;"
NEW = ("im.onerror=()=>{if(im.src.includes('/t/')){im.src=im.src.replace('/t/','/s/');return}blank(win,d,y,m,day)}; "
       "im.src=`${PHOTOS}t/${d[4]}/${encodeURIComponent(d[5])}`;")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    page = pathlib.Path(ap.parse_args().out) / 'calendar' / 'index.html'
    html = page.read_text(encoding='utf-8')
    if html.count(OLD) != 1:
        print('Calendar: photo line not found, left as it was (tiny copies not used)')
        return
    page.write_text(html.replace(OLD, NEW), encoding='utf-8')
    print('Calendar: day squares use the tiny photo copies')


if __name__ == '__main__':
    main()
