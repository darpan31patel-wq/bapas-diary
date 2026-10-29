"""Bapa's schedule (memories/schedule.json) from the BAPS upcoming vicharan schedule page, as read by Bapa's Diary.

The page lists the stays ("Morbi / 20 Oct 2026 to 4 Nov 2026"), then one table per place with that place's usual
times ("Morning: 6.00 am to 8.00 am") and a row per day: a Morning and an Evening cell, or one cell across both
("No Events", "Swagat", "Viday"). A cell can carry its own times ("Vishvashanti Mahayagna-1 Morning: 7.30 to 12.00").
Bapa's Diary saves the page's text (one line per piece) and its tables (one string per cell); the lines say where
one event ends and the next begins, the tables say which ones are morning and which evening.

    from_page(schedule_page, old_schedule, today) -> new schedule, in the same format as before
"""
import datetime, re

import common as update

DAY = re.compile(r'^(\d{1,2}) (\w{3})\w* (\d{4}),')
SPAN = re.compile(r'^(\d{1,2} \w{3}\w* \d{4}) to (\d{1,2} \w{3}\w* \d{4})$')
TIMES = re.compile(r'^(Morning|Evening):\s*(\d{1,2})[.:](\d\d)\s*(am|pm)?\s*to\s*(\d{1,2})[.:](\d\d)\s*(am|pm)?', re.I)
UPDATED = re.compile(r'^\d{1,2} \w+ \d{4}$')
WORDS = 25   # the "Now:" tag keeps to one line


def date_of(s):
    for f in ('%d %b %Y', '%d %B %Y'):
        try:
            return datetime.datetime.strptime(s.strip(), f).date()
        except ValueError:
            pass
    m = DAY.match(s)
    return datetime.datetime.strptime(' '.join(m.groups()), '%d %b %Y').date() if m else None


def clock(h, mi, ampm, evening, after=None):
    h = int(h)
    if ampm:
        h = h % 12 + (12 if ampm.lower() == 'pm' else 0)
    elif evening and h < 12:
        h += 12
    elif after is not None and h * 60 + int(mi) <= after:       # "9.00 to 1.00": one in the afternoon
        h += 12
    return h * 60 + int(mi)


def hhmm(m):
    return f'{m // 60:02d}:{m % 60:02d}'


def times(line, evening):
    m = TIMES.match(line)
    if not m:
        return None
    a = clock(m[2], m[3], m[4], evening)
    return a, clock(m[5], m[6], m[7], evening, after=a)


def what(events, place):
    """One short name for a morning or evening: the special one rather than the daily Puja Darshan."""
    names = [re.sub(r'\s*-\s*\d+$', '', e).strip() for e in events if e.strip() not in ('-', '')]
    if not names:
        return None
    special = [n for n in names if n.lower() != 'puja darshan']
    name = (special or names)[0]
    if len(name) > WORDS and ' / ' in name:
        name = name.split(' / ')[-1]
    if name.lower() == 'aagman':
        name = f'Aagman in {place.split(",")[0]}'
    return name[:WORDS].strip()


def full_place(city):
    p = update.PLACES.get(city)
    if p:
        return p['place'], update.TZ.get(p['place'].split(', ')[-1], 'Asia/Kolkata')
    return f'{city}, India', 'Asia/Kolkata'


def from_page(page, old, today):
    lines = [l.strip() for l in page.get('text', '').split('\n') if l.strip()]
    tables = page.get('tables') or []
    # the page's own date, and the stays listed at the top
    try:
        top = next(i for i, l in enumerate(lines) if l.endswith('Upcoming Vicharan Schedule'))
    except StopIteration:
        raise ValueError('not the schedule page')
    updated = date_of(lines[top + 1]) if UPDATED.match(lines[top + 1]) else None
    stays = []
    for i in range(top + 1, len(lines)):
        if lines[i].startswith('Schedule of Swamishri'):
            break
        m = SPAN.match(lines[i])
        if m:
            place, tz = full_place(lines[i - 1])
            stays.append({'place': place, 'tz': tz, 'from': str(date_of(m[1])), 'to': str(date_of(m[2]))})
    if not stays:
        raise ValueError('no stays on the schedule page')

    # each place's table: its usual times from the text, the rows from the tables
    days = {}
    starts = [i for i, l in enumerate(lines) if l.startswith('Schedule of Swamishri')]
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]
        place = full_place(block[1])[0]
        usual = {'Morning': (360, 480), 'Evening': (1020, 1200)}
        for l in block[2:5]:
            t = times(l, l.lower().startswith('evening'))
            if t:
                usual[l.split(':')[0].title()] = t
        rows = [r for r in (tables[n] if n < len(tables) else []) if r and DAY.match(r[0])]
        heads = [i for i, l in enumerate(block) if DAY.match(l)]
        for k, i in enumerate(heads):
            d = date_of(block[i])
            body = block[i + 1:heads[k + 1] if k + 1 < len(heads) else len(block)]
            body = [l for l in body if l not in ('Please note that this schedule is subject to change.',)]
            row = next((r for r in rows if date_of(r[0]) == d), None)
            cells = row[1:] if row else [' '.join(body)]
            if len(cells) >= 2:     # find where the morning cell's lines end
                split = next((j for j in range(len(body) + 1) if ' '.join(body[:j]) == cells[0]), 1)
                parts = [('Morning', body[:split]), ('Evening', body[split:])]
            else:
                one = ' '.join(body)
                if not body or one.lower() in ('no events', 'viday', '-'):
                    continue
                parts = [('Evening' if 'sabha' in one.lower() else 'Morning', body)]
            events = []
            for when, ls in parts:
                t = next((times(l, when == 'Evening') for l in ls if TIMES.match(l)), None) or usual[when]
                name = what([l for l in ls if not TIMES.match(l)], place)
                if name and name.lower() not in ('no events', 'viday'):
                    events.append({'from': hhmm(t[0]), 'to': hhmm(t[1]), 'what': name})
            if events:
                days[str(d)] = events

    first = min(s['from'] for s in stays)
    out = dict(old)
    out['stays'] = [s for s in old.get('stays', []) if s['to'] <= first and s['from'] < first] + stays
    out['days'] = {**{k: v for k, v in old.get('days', {}).items() if k < first}, **days}
    if updated:
        out['page_updated'] = str(updated)
    out['checked'] = str(today)
    return out
