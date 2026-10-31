"""Put the right guru's name back in photo captions (Darpan, 31 Oct 2026: "why do all these pictures say mahant swami
maharaj instead of pramukh swami maharaj?!").

baps.org files 36 pages of 1999 (Africa, Egypt, Israel and Gujarat tours) under "HH Mahant Swami Maharaj's Vicharan",
though they are Pramukh Swami Maharaj's. tools/build_db.py (24 Oct 2026) trusted that title and turned the "Swamishri"
at the start of 335 captions into "Mahant Swami Maharaj", which also marked 334 of those photos as not of Bapa.
build_db.py no longer does that; this step mends a bapas.db built before the fix, and stops it ever coming back:

  before 13 August 2016 Bapa (Swamishri) is Pramukh Swami Maharaj. A caption from then that STARTS with plain
  "Mahant Swami Maharaj" (not "Pujya Mahant Swami", how baps.org writes about him as a senior sadhu) is put back to
  "Swamishri ...", the wrong text is kept in photos.caption_was (the database keeps everything), and is_bapa is worked out again.

    python3 tools/guru_names.py --db bapas.db [--db more.db]
"""
import argparse, datetime, os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_db   # noqa: E402  (about_bapa, PSM_TO_MSM)

WRONG = re.compile(r'^Mahant\s+Swami\s+Maharaj\b', re.I)


def mend(path):
    db = sqlite3.connect(path)
    cols = [r[1] for r in db.execute('PRAGMA table_info(photos)')]
    if 'caption' not in cols:
        return 0
    if 'caption_was' not in cols:
        db.execute('ALTER TABLE photos ADD COLUMN caption_was TEXT')
    when = "coalesce(date, date_from)"
    rows = db.execute(f"SELECT rowid, {when}, caption FROM photos WHERE {when} < ? AND caption LIKE 'Mahant Swami Maharaj%'",
                      (build_db.PSM_TO_MSM.isoformat(),)).fetchall()
    for rowid, day, cap in rows:
        new = WRONG.sub('Swamishri', cap).strip()
        bapa = int(build_db.about_bapa(new, datetime.date.fromisoformat(day[:10])))
        db.execute('UPDATE photos SET caption_was = coalesce(caption_was, caption), caption = ?, is_bapa = ? WHERE rowid = ?',
                   (new, bapa, rowid))
        if len(rows) < 6 or rowid == rows[0][0]:
            print(f'  {day}: "{cap[:70]}" -> "{new[:70]}"')
    db.commit()
    left = db.execute(f"SELECT count(*) FROM photos WHERE {when} < ? AND caption LIKE 'Mahant Swami Maharaj%'",
                      (build_db.PSM_TO_MSM.isoformat(),)).fetchone()[0]
    print(f'{path}: {len(rows)} captions before 13 Aug 2016 put back to Swamishri (Pramukh Swami Maharaj), {left} left')
    if left:
        sys.exit('guru_names: captions still name Mahant Swami Maharaj as Bapa before 13 Aug 2016')
    return len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', action='append', required=True)
    for p in ap.parse_args().db:
        mend(p)
