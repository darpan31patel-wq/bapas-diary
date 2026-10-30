"""The Darshan tab's BAPS calendar words (Darpan, 29 Oct 2026: "yes" to the murti darshan archive, "split by design or
colour or festivals"). Website only; run by .github/workflows/website-deploy.yml on the built site, after live/ is copied.

Writes out/darshan/cal.js: for every day from 2025 on that the BAPS calendar has, the Indian date and the day's festival
(the calendar's festival, else a smrutiparva, jayanti, ekadashi, punam or other special day from its notes), for the
day squares and the By festival view. The photos and their colours come from photos.bapas-diary.com/darshan/archive.js,
written each morning by the screensaver darshan robot (tools/screensaver/darshan_archive.py).

    python3 tools/web_darshan.py --db bapas.db --out out
"""
import argparse, json, os, re, sqlite3

# a guru's or the mandir's own day first, then the other special days; never a shraddh or a national day
FIRST = re.compile(r'smrutiparv|jayanti|janma|birthday|patotsav|pratishtha', re.I)
SPECIAL = re.compile(r'ekadashi|punam|purnima|mahotsav|navratri|dashmi|diwali|divali|annakut|chaturthi|utsav|holi|dhuleti|samaiyo', re.I)
NOT = re.compile(r'shraddh|shradh|gandhi|sardar|saradar|vruddhi', re.I)


def festival(fest, notes):
    if fest and fest.strip():
        return fest.strip()
    parts = [re.sub(r'\s*\((?:fast|smart|da\. gu\.)\)\s*', ' ', p, flags=re.I).strip(' /')
             for p in re.split(r'\s*/\s*|,\s*(?=[A-Z])', notes or '')]
    parts = [p for p in parts if p and not NOT.search(p)]
    for want in (FIRST, SPECIAL):
        for p in parts:
            if want.search(p):
                return p
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    db = sqlite3.connect(a.db)
    cal = {}
    for d, ind, fest, notes in db.execute("SELECT date, indian_date, festivals, notes FROM calendar WHERE date >= '2025-01-01' ORDER BY date"):
        f = festival(fest, notes)
        cal[d] = [ind or '', f] if f else [ind or '']
    os.makedirs(os.path.join(a.out, 'darshan'), exist_ok=True)
    with open(os.path.join(a.out, 'darshan', 'cal.js'), 'w', encoding='utf-8') as fh:
        fh.write('window.DARSHAN_CAL=' + json.dumps(cal, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'darshan: calendar words for {len(cal)} days, {sum(len(v) > 1 for v in cal.values())} with a festival')


if __name__ == '__main__':
    main()
