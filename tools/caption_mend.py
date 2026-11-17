"""Put right the photo captions that carry on from the photo before them (Darpan, 14 Nov 2026).

baps.org often writes a caption that carries on from the one before it, starting with "...":

    Youths perform a traditional dance
    ... with Swamishri after their performance

tools/build_db.py turns each of those into "Swamishri <the rest>". That reads well for "... and performs arti"
("Swamishri performs arti"), but not when the rest has its own subject or is only a few words, which gave
"Swamishri with Swamishri after their performance", "Swamishri fruit juices and water" and "Swamishri swamishri catches it".
On 14 Nov 2026 a 2006 London card on the 2pm picture said "Bapa with Bapa after their performance".

Here the wrong ones are written out in full again from the photo before them:

    "Youths with Swamishri after their performance"
    "Offering of fruits at 4 pm and fruit juices and water"
    "Swamishri tosses a flower ball to Pujya Anandswarupdas Swami ... and Swamishri catches it"

  python3 tools/caption_mend.py list --crawl crawl --out tools/caption-mend.json   # once, from the raw baps.org pages
  python3 tools/caption_mend.py apply --db bapas.db                               # every website deploy

apply only changes a photo whose caption is still exactly the wrong one, keeps the old words in photos.caption_was
(the database keeps everything), works out is_bapa again, and fails the deploy if a doubled name is still there.
"""
import argparse, datetime, glob, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIST = os.path.join(HERE, 'caption-mend.json')

DOTS = re.compile(r'^(?:\.\.\.|…|\.\.)\s*')
TAIL = re.compile(r'\s*(?:\.\.\.|…|\.\.)\s*$')
GURU = re.compile(r"\b(?:Swamishri|Pramukh Swami|Mahant Swami|Bapa|he|his|him)\b", re.I)
GROUP = re.compile(r"^((?:BAPS |Young |Senior |The )?(?:[A-Z][\w\-]* )*?(?:youths|yuvaks|yuvatis|kishores|kishoris|balaks|balikas|children|devotees|"
                   r"sadhus|swamis|volunteers|karyakars|students|performers|dancers|artists|participants|girls|boys|men|women|bhaktas)(?: and [\w\-]+)?)"
                   r" (?:perform|present|enact|dance|sing|play)", re.I)
ADVERB = r"(?:finally|eagerly|humbly|also|lovingly|affectionately|personally|joyfully|happily|thereafter|again|warmly|graciously|later|now|then|first|briefly|keenly|patiently|smilingly|devoutly|gently|playfully|quietly|reverentially|lastly)"
NOT_VERB = r"(?:this|his|is|was|class|kalashas|sadhus|devotees|volunteers|kishores|youths|balaks|children|swamis|performers|parshads|kirtans|bhajans|murtis|thus|as|across|always|towards|various|famous|previous|glorious|numerous|delicious|precious|joyous|its|us|yes|bus|plus|less|unless|process|progress|congress|address|princess|mattress|actress|business|witness|kindness|happiness|bliss|class|grass|glass|mass|dress|press)"
VERB = re.compile(rf"^(?:{ADVERB}[, ]+)*(?!{NOT_VERB}\b)[a-z]+(?:es|s)\b", re.I)
DANGLING = re.compile(r"(?:\b(?:and|or|of|with|to|the|a|an|for|by|from|at|in)|[,:;\-])\s*(?:\.\.\.|…|\.\.)?\s*$", re.I)
PLACE_TAIL = re.compile(r"^(.*\b(?:for|at|of|in|to))\s+[A-Z][\w\-']*(?:,? (?:and )?[A-Z][\w\-']*)*\W*$")


def rest_of(raw):
    """The words after the "..." ('... and Swamishri catches it' -> 'and Swamishri catches it')."""
    return TAIL.sub('', DOTS.sub('', raw)).strip()


def bare(raw):
    return re.sub(r'^(?:(?:and|then|And|Then)\s+)+', '', rest_of(raw))


def wrong(now, raw, raw_before=''):
    """Is build_db's 'Swamishri <rest>' wrong for this caption? Only when it reads wrong; a short description
    ('... in a contemplative mood') is left alone, as the website drops the name in front anyway."""
    r = bare(raw)
    if not r or not now.startswith('Swamishri '):
        return False
    g = {w.lower() for w in GURU.findall(r)}
    if g and not VERB.match(r):   # the rest names him itself: 'with Swamishri', 'and Swamishri catches it'
        return True
    if PLURAL.match(r) or GROUP_START.match(r):  # the rest is about others: '... perform a celebratory dance', '... the children enjoy'
        return True
    if r[:1].isupper() and not VERB.match(r):   # a name or place made lower case: 'Swamishri sojitra', 'Swamishri pramukh Swami Maharaj'
        return True
    joins = DANGLING.search(raw_before or '') or re.match(r'and\b', rest_of(raw), re.I)   # '... and fruit juices and water' goes on a list
    return bool(joins) and not VERB.match(r) and not CARRY.match(r)


CARRY = re.compile(r"^(?:and|as|while|which|who|whom|whose|with|during|before|after|to|eager|eagerly|even|also|in|on|at|for|from|by|"
                   r"including|where|when|that|then|thus|finally|ensuring|accepting|affirming|depicting|imparting|interspersing|"
                   r"extolling|greeting|awaiting|symbolising|creating|being)\b", re.I)


PLURAL = re.compile(r"^(?:perform|present|sing|play|enact|dance|offer|receive|greet|welcome|recite|chant|listen|watch|join|take|seek|line|wait|gather|pray|bow)\b", re.I)
GROUP_START = re.compile(r"^(?:the |all |many |hundreds|thousands|senior |young )?(?:youths|yuvaks|kishores|kishoris|balaks|balikas|children|devotees|sadhus|swamis|"
                         r"volunteers|karyakars|students|performers|perfomers|dancers|participants|hundreds|thousands|bhaktas|everyone)\b", re.I)


def whole(raw, before):
    """The caption written out in full from the one before it (before is that photo's own full caption)."""
    r, base = rest_of(raw), TAIL.sub('', before or '').strip().rstrip('.').strip()
    b = re.sub(r'^(?:(?:and|then|And|Then)\s+)+', '', r)
    if base and base.lower().endswith(b.lower()):           # the same words again
        out = base
    elif b[:1].isupper() and not VERB.match(b) and not GURU.match(b):
        m = PLACE_TAIL.match(base)
        out = m.group(1) + ' ' + b if m and len(b.split()) <= 6 else b   # '... rituals for Bhadarniya' + '... Sojitra'
    elif GROUP_START.match(b):
        out = b                                             # '... kishores and youths with Swamishri'
    elif re.match(r'with\b', b) and GROUP.match(base):
        out = GROUP.match(base).group(1) + ' ' + b          # 'Youths perform a traditional dance' + '... with Swamishri after ...'
    elif base and len(base) <= 160 and not base.startswith(('"', "'")) and (CARRY.match(b) or DANGLING.search(before or '') or re.match(r'and\b', r, re.I) or not VERB.match(b)):
        out = base + ' ' + r                                # 'Swamishri tosses a flower ball ...' + '... and Swamishri catches it'
    else:
        out = b                                             # the rest has its own subject: 'During this dialogue Bill Clinton ...'
    out = re.sub(r'\b(\w+) \1\b', r'\1', re.sub(r'\s+', ' ', out).strip())   # 'station to to South London'
    return out[0].upper() + out[1:]


def make_list(crawl):
    import build_db as B
    out, keys = [], set()

    def page(rows, when, where):
        new = B.continued(rows, when)
        full_prev, raw_prev, fixed_prev, prev_now = '', '', '', ''
        for r, n in zip(rows, new):
            raw = re.sub(r'<[^>]+>', '', r[2] or '').replace('�', "'").strip()
            fixed = n[2]
            if DOTS.match(raw):
                if raw == raw_prev:                        # galleries repeat a caption: it reads as the one before
                    fixed = full_prev if fixed_prev != prev_now else n[2]
                elif wrong(n[2], raw, raw_prev):
                    fixed = whole(raw, full_prev)
                if fixed != n[2] and (n[0], n[1]) not in keys:
                    keys.add((n[0], n[1]))
                    out.append({'year': when.year, 'album': n[0], 'file': n[1], 'page': where, 'baps_org': raw,
                                'before': full_prev, 'was': n[2], 'now': fixed})
            full_prev, raw_prev, fixed_prev, prev_now = fixed, raw, fixed, n[2]

    for f in sorted(glob.glob(os.path.join(crawl, 'bapas-diary-[12][0-9][0-9][0-9].json'))):
        d = json.load(open(f, encoding='utf-8'))
        if 'year' not in d:
            continue
        y = d['year']
        for p in d['pages']:
            span = B.page_dates(p['p'], p.get('t', ''), y)
            page(p.get('rows') or [], span[0] if span else datetime.date(y, 7, 1), p['p'])
    return out


def apply(path, rows):
    import build_db as B
    db = sqlite3.connect(path)
    cols = [r[1] for r in db.execute('PRAGMA table_info(photos)')]
    if 'caption_was' not in cols:
        db.execute('ALTER TABLE photos ADD COLUMN caption_was TEXT')
    done = 0
    for x in rows:
        for rowid, day, y in db.execute('SELECT rowid, coalesce(date, date_from), year FROM photos WHERE album = ? AND file = ? AND caption = ?',
                                        (x['album'], x['file'], x['was'])).fetchall():
            when = datetime.date.fromisoformat(day[:10]) if day else datetime.date(int(y or x['year']), 7, 1)
            db.execute('UPDATE photos SET caption_was = coalesce(caption_was, caption), caption = ?, is_bapa = ? WHERE rowid = ?',
                       (x['now'], int(B.about_bapa(x['now'], when)), rowid))
            done += 1
    for rowid, cap in db.execute("SELECT rowid, caption FROM photos WHERE caption LIKE '%Swamishri Swamishri%'").fetchall():
        new = re.sub(r'\b(Swamishri)\s+Swamishri\b', r'\1', cap, flags=re.I)   # baps.org's own 'Swamishri Swamishri conducts a class'
        db.execute('UPDATE photos SET caption_was = coalesce(caption_was, caption), caption = ? WHERE rowid = ?', (new, rowid))
        done += 1
    db.commit()
    left = db.execute("SELECT count(*) FROM photos WHERE caption LIKE 'Swamishri with Swamishri%' OR caption LIKE '%Swamishri Swamishri%'").fetchone()[0]
    print(f'{path}: {done} photo captions written out in full again, {left} doubled names left')
    if left:
        sys.exit('caption_mend: captions still say "Swamishri with Swamishri" or "Swamishri swamishri"')
    return done


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='do', required=True)
    a = sub.add_parser('list'); a.add_argument('--crawl', required=True); a.add_argument('--out', default=LIST)
    b = sub.add_parser('apply'); b.add_argument('--db', action='append', required=True); b.add_argument('--list', default=LIST)
    o = ap.parse_args()
    if o.do == 'list':
        rows = make_list(o.crawl)
        json.dump(rows, open(o.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(len(rows), 'captions to put right ->', o.out)
    else:
        rows = json.load(open(o.list, encoding='utf-8'))
        for p in o.db:
            apply(p, rows)
