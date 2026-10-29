"""The screensaver on the Today page of bapas-diary.com (Darpan, 29 Oct 2026: "a big screensaver button ... 75% of the
slide is a picture ... daily Murti Darshan, the latest pictures of Bapa, and on this day ... completely self-reliant").

Built from the darshan screensaver kit Darpan's other project made (site/screensaver/index.html, used as it is apart
from where its photos come from and how it is left). Website only: nothing here touches the daily 2pm picture. Runs in
the deploy on the built site, after web_player.py:

    python3 tools/web_screensaver.py --out out --db bapa.db --schedule schedule.json

  out/screensaver/index.html, sw.js, fonts/   the screensaver page and its photo keeper, from site/screensaver/
  out/screensaver/version.txt                 this build's name, so a device showing an old kept copy reloads
  out/screensaver/data/latest.json            Latest Vicharan: Bapa's 10 newest days of photos, from bapa.db (Bapa in
                                              person only, with the captions the Today page shows), newest first
  out/screensaver/data/schedule.json          where Bapa is and what he is doing: site/screensaver/data/schedule.json
                                              brought up to date from Bapa's Diary's read of the BAPS vicharan schedule page
  out/screensaver/launch.js, launch.css       the Screensaver button, the "entering screensaver state" box and the frame
and puts the button and those two files on the Today page. The mandir's daily photos are not made here: the robot
.github/workflows/screensaver-darshan.yml copies them to photos.bapas-diary.com/darshan/ each morning.
"""
import argparse, datetime, json, os, shutil, sqlite3, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'tools', 'screensaver'))
import common, schedule as schedule_page   # noqa: E402  (the kit's schedule reader, in tools/screensaver/)

SRC = os.path.join(HERE, 'site', 'screensaver')
FILES = ('index.html', 'sw.js', 'launch.js', 'launch.css')
DAYS, MOST = 10, 150   # as the kit: the 10 newest days with photos, at most 150 a day spread through the day
TAGS = '<link rel="stylesheet" href="/screensaver/launch.css">\n<script src="/screensaver/launch.js" defer></script>\n'
DIYA = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.5c1.8 2.4 2.6 4 2.2 5.6-.3 1.3-1.3 2-2.2 2s-1.9-.7-2.2-2C9.4 6.5 10.2 4.9 12 2.5z"/>'
        '<path d="M2.5 12.5h19c-.6 4.2-4.6 7-9.5 7s-8.9-2.8-9.5-7z"/><rect x="9" y="20.2" width="6" height="1.6" rx=".8"/></svg>')
BUTTON = f'<div class="ss-launch"><button type="button" id="screensaverButton" class="ss-big">{DIYA}Screensaver</button></div>\n'


def latest(db_path, schedule):
    """Bapa's newest days of photos, newest first, in the kit's shape: img, iso, when, place, caption, tz.
    Close ups and activity alike (Darpan, 29 Oct 2026: "can show activity too"): every photo the face check kept, as the
    Today page shows them, best darshan first. A day whose photos the face check hasn't seen yet (not in the photo copy
    yet) waits until it has."""
    db = sqlite3.connect(db_path)
    seen = "p.date IS NOT NULL AND b.why NOT LIKE 'caption only%'"
    dates = [r[0] for r in db.execute("SELECT DISTINCT p.date FROM photos p JOIN bapa_pick b USING (album, file) "
                                      f"WHERE {seen} ORDER BY p.date DESC LIMIT ?", (DAYS,))]
    out = []
    for d in dates:
        rows = db.execute("SELECT p.album, p.file, p.caption, p.place, b.close FROM photos p JOIN bapa_pick b USING (album, file) "
                          f"WHERE p.date = ? AND {seen} ORDER BY b.rank, p.album, p.file", (d,)).fetchall()
        day = datetime.date.fromisoformat(d)
        for album, file, cap, place, close in common.spread(rows, MOST):
            out.append({'img': f'https://photos.bapas-diary.com/l/{album}/{file}', 'iso': d, 'when': f'{day.day} {day:%B %Y}',
                        'place': place or '', 'caption': common.clean(cap), 'tz': common.tz_of(place or '', day, schedule),
                        'close': int(close or 0)})   # 1 = a close up of Bapa; the screensaver shows activity photos first (Darpan, 29 Oct 2026)
        print(f'  {d}: {len(rows)} photos of Bapa')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--db', required=True, help='bapa.db: only photos with Bapa in them, captions as the Today page shows them')
    ap.add_argument('--schedule', help="Bapa's Diary's read of the BAPS vicharan schedule page (crawl/schedule/latest.json)")
    ap.add_argument('--build', default=(os.environ.get('GITHUB_SHA') or 'dev')[:7])
    a = ap.parse_args()
    dest = os.path.join(a.out, 'screensaver')
    os.makedirs(os.path.join(dest, 'data'), exist_ok=True)
    for f in FILES:
        shutil.copy(os.path.join(SRC, f), os.path.join(dest, f))
    shutil.copytree(os.path.join(SRC, 'fonts'), os.path.join(dest, 'fonts'), dirs_exist_ok=True)
    p = os.path.join(dest, 'index.html')
    page = open(p, encoding='utf-8').read().replace("'DARSHAN_BUILD_ID'", repr(a.build), 1)
    open(p, 'w', encoding='utf-8').write(page)
    open(os.path.join(dest, 'version.txt'), 'w').write(a.build + '\n')

    # Bapa's schedule: the kit's copy, brought up to date from the page as Bapa's Diary last read it
    sched = json.load(open(os.path.join(SRC, 'data', 'schedule.json')))
    if a.schedule and os.path.exists(a.schedule):
        try:
            page = json.load(open(a.schedule))
            sched = schedule_page.from_page(page, sched, datetime.datetime.now(ZoneInfo('Europe/London')).date())
            print(f"schedule: {len(sched['stays'])} stays, {len(sched['days'])} days with events, page read {page.get('read', '')[:10]}")
        except Exception as e:   # the page not understood: the kit's copy stays
            print('schedule: page not understood, kept as it was:', e)
    json.dump(sched, open(os.path.join(dest, 'data', 'schedule.json'), 'w'), indent=1, ensure_ascii=False)

    print('latest vicharan:')
    items = latest(a.db, sched)
    json.dump(items, open(os.path.join(dest, 'data', 'latest.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'  {len(items)} photos')

    # the button and its files on the Today page
    p = os.path.join(a.out, 'index.html')
    s = open(p, encoding='utf-8').read()
    if '/screensaver/launch.js' not in s:
        s = s.replace('</head>', TAGS + '</head>', 1) if '</head>' in s else s.replace('</title>', '</title>\n' + TAGS, 1)
        assert s.count('</header>') == 1, 'the Today page has no header'
        s = s.replace('</header>', BUTTON + '</header>', 1)   # inside the header, so on computers it can sit beside the date
        open(p, 'w', encoding='utf-8').write(s)
    print('screensaver: button on index.html')


if __name__ == '__main__':
    main()
