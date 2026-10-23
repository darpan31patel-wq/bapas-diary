#!/usr/bin/env python3
"""The BAPS calendar (baps.org/Calendar) for every day it covers, as one searchable list (Darpan, 23 Oct 2026:
'every calendar and all the information ... the year, the month, the day, the Indian name for that date, the
festival that was happening on that day, and then anything specific and special to know').

    python tools/baps_calendar.py            calendar/raw/*.txt  ->  calendar/baps-calendar.json, .csv, checklist.md

baps.org's calendar starts in January 2010 (2009 and earlier pages are empty) and runs to December 2027.
Its pages sit behind Cloudflare, so the raw files were read on 23 Oct 2026 in Darpan's own Chrome as normal page
visits (READ_IN_CHROME below), never by GitHub or a server. The muhurat (auspicious timings) pages were left out
on purpose: he doesn't want them.

calendar/raw/days.txt, one block per month:
    M 2012-01 January 2012 Posh-Maha, Vikram Samvat 2068
    day|tithi as the tooltip says it|extra lines under the tithi (; between)|cell kind|festival picture
A festival day shows only a picture on baps.org (no number, no tithi), so it is written '|||kind|picture' and
gets its date from the gaps; its tithi and name then come from the festival list.
calendar/raw/festivals.txt: the year's festival list, 'Month DD : Tithi || (Name) || Dn' with the D lines holding
the meaning baps.org gives for each festival.
"""
import calendar, csv, datetime, json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, 'calendar', 'raw')
OUT = os.path.join(HERE, 'calendar')

# What baps.org's festival pictures stand for, for a picture day the festival list doesn't name.
PICTURES = {
    'uttarayan': 'Makar Sankranti (Uttarayan)', 'makarsankranti': 'Makar Sankranti (Uttarayan)',
    'poshipurnima': 'Aksharbrahma Gunatitanand Swami Diksha Day (Poshi Punam)',
    'gunatitdikshadin': 'Aksharbrahma Gunatitanand Swami Diksha Day (Poshi Punam)',
    'republicday': 'Republic Day', 'vasantpanchami': 'Vasant Panchami (Shastriji Maharaj Jayanti)',
    'mahashivratri': 'Maha Shivratri', 'pragjibhaktajayanti': "Holi, Bhagatji Maharaj's Jayanti",
    'fuldolotsav': 'Dhuleti, Pushpadolotsav', 'dhuleti': 'Dhuleti, Pushpadolotsav', 'rangpanchami': 'Rang Panchami',
    'swaminarayanjayanti': 'Swaminarayan Jayanti and Ramnavmi', 'yogijimaharajjayanti': 'Yogi Jayanti',
    'pramukhvarnidin': 'Pramukh Varni Din', 'rathyatra': 'Rathyatra', 'gurupurnima': 'Guru Purnima',
    'independenceday': 'Independence Day', 'indipendenceday': 'Independence Day', 'rakshabandhan': 'Raksha Bandhan',
    'janmashthami': 'Janmashtami', 'janmashthmi': 'Janmashtami', 'janmashtami': 'Janmashtami',
    'ganeshchaturthi': 'Ganesh Chaturthi', 'ganeshchaturthu': 'Ganesh Chaturthi',
    'jaljhilniekadashi': 'Jal Jhilani Ekadashi', 'jaljilniekadashi': 'Jal Jhilani Ekadashi',
    'jaljhilaniekadashi': 'Jal Jhilani Ekadashi',
    'mahantswami': 'Mahant Swami Maharaj Janma Jayanti', 'mahantswamimaharajjanmajayanti': 'Mahant Swami Maharaj Janma Jayanti',
    'dashera': 'Vijaya Dashmi (Dashera)', 'dushera': 'Vijaya Dashmi (Dashera)',
    'sharadpurnima': "Sharad Punam, Gunatitanand Swami's Jayanti", 'diwali': 'Diwali',
    'newyear': 'Annakut and Bestu Varas (New Year)', 'annakutosav': 'Annakut and Bestu Varas (New Year)',
    'pramukhswamijayanti': "Pramukh Swami Maharaj's Jayanti", 'pramukhswamimaharajpragatyotsav': "Pramukh Swami Maharaj's Jayanti",
}
TITHIS = ['Padvo', 'Bij', 'Trij', 'Choth', 'Pancham', 'Chhath', 'Satam', 'Atham', 'Nom', 'Dasham', 'Ekadashi',
          'Baras', 'Teras', 'Chaudas', 'Punam', 'Amas']
ALIASES = {'Chaudash': 'Chaudas', 'Terash': 'Teras', 'Barash': 'Baras', 'Amash': 'Amas', 'Navmi': 'Nom'}
TITHI_RE = re.compile(r'^(?:(Adhik|Nij)[ _]?)?([A-Z][a-z]+)?\s*(Sud|Vad)\s+(.+)$')
NAME_FIX = {'Bhadarva': 'Bhadarvo', 'Vaishak': 'Vaishakh', 'Kartik': 'Kartak', 'Chaitra;': 'Chaitra'}


def picture_name(img):
    key = re.sub(r'^\d+-|-01$|-\d{4}$|\.(jpg|png)$', '', img.lower())
    key = re.sub(r'-01$', '', key)
    return PICTURES.get(key, key)


def read_festivals():
    """{date: [(name, meaning, tithi)]} from the yearly festival lists."""
    out, desc, year = {}, {}, None
    for line in open(os.path.join(RAW, 'festivals.txt'), encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('Y '):
            year = int(line[2:])
        elif re.match(r'^D\d+ ', line) or re.match(r'^D\d+$', line):
            k, _, text = line.partition(' ')
            desc[k] = text.strip()
        elif ' || ' in line:
            head, name, k = line.split(' || ')
            md, _, tithi = head.partition(' : ')
            date = datetime.datetime.strptime(f'{md} {year}', '%B %d %Y').date()
            name = name.strip()[1:-1].strip() if name.strip().startswith('(') else name.strip()
            meaning = desc.get(k, '')
            if meaning.startswith('../'):                     # a stray link in front of a few meanings
                meaning = meaning.split(',', 1)[1] if ',' in meaning else ''
            out.setdefault(date.isoformat(), []).append(dict(name=name or meaning, about=meaning.strip(), tithi=tithi.strip()))
    return out


def split_tithi(raw):
    """'Adhik_Vaishakh Sud Padvo' -> ('Adhik Vaishakh', 'Sud', 'Padvo'); month may be blank when baps.org left it off."""
    t = raw.replace('_', ' ').replace('AdhikAso', 'Adhik Aso').replace('AdhikJeth', 'Adhik Jeth').replace('Nij ', '')
    t = re.sub(r'\s+', ' ', t).strip()
    m = TITHI_RE.match(t)
    if not m:
        return '', '', ''
    adhik, month, paksha, rest = m.groups()
    month = NAME_FIX.get(month, month) if month else ''
    if adhik == 'Adhik' and month:
        month = 'Adhik ' + month
    words = re.findall(r'[A-Za-z]+', rest)
    tithi = []                                                # 'Atham/Nom', 'Padvo Bij' (two tithis on one day)
    for w in words:
        w = ALIASES.get(w.capitalize(), w.capitalize())
        if w in TITHIS:
            tithi.append(w)
        elif tithi:
            break
    return month, paksha, '/'.join(tithi)


def build():
    fests = read_festivals()
    months, cur = [], None
    for line in open(os.path.join(RAW, 'days.txt'), encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('M '):
            _, ym, head = line.split(' ', 2)
            cur = dict(ym=ym, head=head, cells=[])
            months.append(cur)
        elif line:
            p = (line.split('|') + [''] * 5)[:5]
            cur['cells'].append(dict(n=p[0], tip=p[1], extra=p[2], kind=p[3], img=p[4]))

    days, gaps = [], []
    for mo in months:
        y, m = map(int, mo['ym'].split('-'))
        nd = calendar.monthrange(y, m)[1]
        samvat = re.search(r'Samvat (\d{4})(?:-(\d{4}))?', mo['head'])
        lunar = re.search(r'\d{4}\s+(.+?), Vikram', mo['head']).group(1).strip()
        cells = mo['cells']
        first = next((i for i, c in enumerate(cells) if c['n'] == '1'), 0)
        # the calendar grid wraps the last days of a long month into the empty boxes of its first row
        order = cells[first:] + cells[:first]
        numbered = {int(c['n']) for c in order if c['n']}
        missing = iter(sorted(set(range(1, nd + 1)) - numbered))
        by_day = {}
        for c in order:
            d = int(c['n']) if c['n'] else next(missing, None)
            if d is None or d > nd:
                continue
            by_day.setdefault(d, c)
        for d in range(1, nd + 1):
            date = datetime.date(y, m, d)
            c = by_day.get(d)
            fl = fests.get(date.isoformat(), [])
            if not c:
                gaps.append(date.isoformat())
                c = dict(n='', tip='', extra='', kind='', img='')
            tip = c['tip'] or (fl[0]['tithi'] if fl else '')
            month, paksha, tithi = split_tithi(tip)
            notes = [x.strip() for x in re.split(r';', c['extra']) if x.strip()]
            notes = [x for x in notes if x.lstrip('- ').capitalize() not in TITHIS and x not in (month, f'{paksha} {tithi}')]
            kind = re.sub(r'\d+$', '', c['kind']).replace('Amash', 'Amas')
            festivals = [dict(name=f['name'], about=f['about']) for f in fl]
            if c['img'] and not festivals:
                festivals = [dict(name=picture_name(c['img']), about='')]
            s1, s2 = samvat.groups()
            vs = int(s2) if s2 and month.endswith('Kartak') and d > 0 and m in (10, 11) else int(s1)
            days.append(dict(
                date=date.isoformat(), weekday=date.strftime('%A'),
                vikram_samvat=vs, lunar_months=lunar,
                month=month, paksha=paksha, tithi=tithi,
                indian_date=' '.join(x for x in (month, paksha, tithi) if x),
                festivals=festivals, notes=notes,
                ekadashi=kind == 'Ekadashi' or 'Ekadashi' in ' '.join(notes) and '(Fast)' in c['extra'],
                punam=kind == 'Punam' or tithi.endswith('Punam'), amas=kind == 'Amas' or tithi.endswith('Amas'),
                picture=c['img'], baps_text=tip,
                source=f'https://www.baps.org/Calendar/{y}/{calendar.month_name[m]}.aspx'))
    return days, gaps, months


def write(days, gaps, months):
    with open(os.path.join(OUT, 'baps-calendar.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(source='baps.org/Calendar, read 23 Oct 2026 in Darpan\'s Chrome', first=days[0]['date'],
                       last=days[-1]['date'], days=days), f, ensure_ascii=False, indent=0)
    with open(os.path.join(OUT, 'baps-calendar.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'weekday', 'vikram_samvat', 'indian_date', 'festivals', 'notes', 'ekadashi', 'punam', 'amas'])
        for x in days:
            w.writerow([x['date'], x['weekday'], x['vikram_samvat'], x['indian_date'],
                        ' / '.join(f['name'] for f in x['festivals']), ' / '.join(x['notes']),
                        'yes' if x['ekadashi'] else '', 'yes' if x['punam'] else '', 'yes' if x['amas'] else ''])
    lines = ['# BAPS calendar: what we have saved', '',
             'Read from baps.org/Calendar on 23 October 2026. baps.org has calendars from **January 2010 to December 2027**;',
             'the pages for 2009 and earlier exist but are empty.', '',
             '| Year | Months | Days | Indian date found | Festivals | Ekadashi | Done |', '|---|---|---|---|---|---|---|']
    for y in sorted({d['date'][:4] for d in days}):
        yd = [d for d in days if d['date'].startswith(y)]
        nm = len({d['date'][:7] for d in yd})
        ok = sum(1 for d in yd if d['tithi'])
        lines.append(f"| {y} | {nm} of 12 | {len(yd)} | {ok} | {sum(len(d['festivals']) for d in yd)} | "
                     f"{sum(d['ekadashi'] for d in yd)} | {'✅' if nm == 12 and ok == len(yd) else '⚠️'} |")
    lines += ['', '1999 to 2009 are not on baps.org. Those years would need a different source (for example a printed',
              'calendar, or working the tithi out from the moon), so they are not ticked.']
    miss = [d['date'] for d in days if not d['tithi']]
    if miss or gaps:
        lines += ['', f'Days where baps.org itself left the tithi blank ({len(miss)}): ' + ', '.join(miss)]
    open(os.path.join(OUT, 'checklist.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'{len(days)} days, {len(miss)} without a tithi, {len(gaps)} gaps')


# Run in Chrome's console on any baps.org/Calendar page to read the month grids again (normal page loads, one
# at a time). The festival lists are drawn by the page's own script, so they are read through a hidden frame.
READ_IN_CHROME = r"""
const M=['January','February','March','April','May','June','July','August','September','October','November','December'];
const CAL={}; for(let y=2010;y<=2027;y++) for(let m=0;m<12;m++){
  const d=new DOMParser().parseFromString(await (await fetch(`/Calendar/${y}/${M[m]}.aspx`)).text(),'text/html');
  const head=[...d.querySelectorAll('div,span,h1,h2,h3')].map(x=>x.children.length==0?x.textContent.trim():'').find(t=>/Vikram Samvat/.test(t))||'';
  CAL[`${y}-${String(m+1).padStart(2,'0')}`]={head, days:[...d.querySelectorAll('.cal-row-fluid .cal-cell')].map(c=>({
    n:(c.querySelector('[class^=cal_date_no],[class^=cal_date_Sun]')||{}).textContent?.trim()||'',
    cls:c.className.split(/\s+/)[1], tip:(c.querySelector('[data-tooltip]')||{}).dataset?.tooltip?.trim()||'',
    l2:[...c.querySelectorAll('.cal_date_l2')].map(x=>x.textContent.trim()).filter(Boolean),
    img:(c.querySelector('img')?.getAttribute('src')||'').split('?')[0].split('/').pop()}))};
}
"""

if __name__ == '__main__':
    write(*build())
