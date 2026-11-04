"""The weekly private summary email for Darpan (Darpan, 4 Nov 2026: "yes" to "Weekly private summary email to you:
visitors, countries, top tabs, missed searches and feedback from the last 7 days, in one short email every Monday").

Website only: nothing here touches the daily 2pm picture, and nothing is fetched from baps.org. Everything comes from
the website's own private answers, the same ones the Interaction page (bapas-diary.com/interaction/) reads with his word:
  /api/visitors?days=14   Cloudflare's own totals (visitors, page views, countries, tabs, how people found the site)
  /api/missed             searches that found nothing, by day
  /api/feedback           the About page's feedback box
The word is the GitHub secret MISSED_KEY, the email goes out through Resend (RESEND_API_KEY) from and to
hello@bapas-diary.com, which forwards to Darpan, unless the GitHub secret SUMMARY_TO names another address.

The repo is public, so its run logs are too: this prints no numbers, no searches and no feedback, only "sent" or what
went wrong, and keeps no copy of the email anywhere.

Runs on GitHub every Monday (.github/workflows/summary-email.yml). By hand:
  python3 tools/web_summary.py --sample made-up.json --out summary.html   (a preview, sends nothing)
"""
import argparse, datetime, json, os, sys, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

SITE = 'https://bapas-diary.com/'
FROM = "Bapa's Diary <hello@bapas-diary.com>"
TO = 'hello@bapas-diary.com'
UK = ZoneInfo('Europe/London')
UA = 'Mozilla/5.0 (bapas-diary.com summary email)'
C = {'maroon': '#5a1626', 'gold': '#d9a441', 'pale': '#ffe296', 'cream': '#faf1de', 'paper': '#fffaf0',
     'ink': '#2e1a14', 'muted': '#7a5c48', 'line': '#e6d6b8', 'amber': '#a06a1c', 'soft': '#fbf0d6'}
SERIF = "'EB Garamond', Georgia, 'Times New Roman', serif"
SANS = 'Arimo, Arial, Helvetica, sans-serif'

# Cloudflare gives two letter country codes; the ones most likely to visit get their name, the rest keep the code
COUNTRY = {
    'GB': 'United Kingdom', 'IN': 'India', 'US': 'United States', 'CA': 'Canada', 'AU': 'Australia', 'NZ': 'New Zealand',
    'KE': 'Kenya', 'UG': 'Uganda', 'TZ': 'Tanzania', 'ZA': 'South Africa', 'AE': 'UAE', 'SG': 'Singapore', 'HK': 'Hong Kong',
    'MY': 'Malaysia', 'BH': 'Bahrain', 'OM': 'Oman', 'QA': 'Qatar', 'KW': 'Kuwait', 'SA': 'Saudi Arabia', 'PT': 'Portugal',
    'FR': 'France', 'DE': 'Germany', 'NL': 'Netherlands', 'BE': 'Belgium', 'IE': 'Ireland', 'IT': 'Italy', 'ES': 'Spain',
    'SE': 'Sweden', 'CH': 'Switzerland', 'NP': 'Nepal', 'BD': 'Bangladesh', 'LK': 'Sri Lanka', 'JP': 'Japan', 'CN': 'China',
    'MU': 'Mauritius', 'FJ': 'Fiji', 'ZM': 'Zambia', 'ZW': 'Zimbabwe', 'BW': 'Botswana', 'MW': 'Malawi', 'NG': 'Nigeria',
}


def flag(code):
    return ''.join(chr(0x1F1E6 + ord(c) - 65) for c in code) if len(code or '') == 2 and code.isalpha() and code.isupper() else ''


def esc(s):
    return str(s if s is not None else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def get(path, key):
    url = SITE + path + ('&' if '?' in path else '?') + 'key=' + urllib.parse.quote(key)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b'{}')
    except Exception as e:   # one missing part must not stop the rest of the email
        return {'error': type(e).__name__}


def week_of(today):
    """The seven days before today: last Monday to yesterday, Sunday."""
    end = today - datetime.timedelta(days=1)
    return end - datetime.timedelta(days=6), end


def gather(key, today):
    first, last = week_of(today)
    return {'first': first.isoformat(), 'last': last.isoformat(),
            'visitors': get('api/visitors?days=14', key), 'visitors7': get('api/visitors?days=7', key),
            'missed': get('api/missed', key), 'feedback': get('api/feedback', key)}


def nice(iso, fmt='%A %-d %B'):
    return datetime.date.fromisoformat(iso).strftime(fmt)


def num(n):
    return f'{int(n):,}'


def summarise(data):
    first, last = data['first'], data['last']
    p_first = (datetime.date.fromisoformat(first) - datetime.timedelta(days=7)).isoformat()
    v, v7 = data.get('visitors') or {}, data.get('visitors7') or {}
    days = [d for d in v.get('days') or [] if first <= d[0] <= last]
    before = [d for d in v.get('days') or [] if p_first <= d[0] < first]
    s = {'first': first, 'last': last, 'have_visitors': bool(v.get('days')) and not v.get('error'),
         'visitors': sum(d[1] for d in days), 'views': sum(d[2] for d in days),
         'visitors_before': sum(d[1] for d in before) if len(before) >= 6 else None,
         'busiest': max(days, key=lambda d: d[1]) if days else None,
         'countries': (v7.get('countries') or [])[:8], 'tabs': (v7.get('tabs') or [])[:8], 'tabs_from': v7.get('tabsFrom') or '',
         'found': (v7.get('found') or [])[:6], 'devices': v7.get('devices') or []}
    words = {}
    for day, items in (data.get('missed') or {}).get('days') or []:
        if first <= day <= last:
            for w, n in items:
                words[w] = words.get(w, 0) + n
    s['missed'] = sorted(words.items(), key=lambda x: (-x[1], x[0]))
    s['missed_total'] = sum(words.values())
    s['feedback'] = [f for f in (data.get('feedback') or {}).get('items') or [] if first <= (f.get('day') or '') <= last]
    s['gaps'] = [name for name, part in (('visitors', v), ('missed searches', data.get('missed') or {}),
                                         ('feedback', data.get('feedback') or {})) if part.get('error')]
    return s


def bars(rows, label, total=None):
    """A simple list with a thin gold bar under each name, the way every email app shows it."""
    if not rows:
        return f'<div style="font:15px/1.5 {SERIF};color:{C["muted"]};font-style:italic">Nothing yet this week.</div>'
    top = max(n for _, n in rows) or 1
    out = []
    for name, n in rows:
        w = max(2, round(100 * n / top))
        out.append(f'<tr><td style="padding:5px 0 0;font:15px/1.3 {SANS};color:{C["ink"]}">{label(name)}</td>'
                   f'<td align="right" style="padding:5px 0 0 10px;font:700 15px {SANS};color:{C["maroon"]};white-space:nowrap">{num(n)}</td></tr>'
                   f'<tr><td colspan="2" style="padding:3px 0 4px"><div style="height:5px;width:{w}%;background:{C["gold"]};border-radius:3px"></div></td></tr>')
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(out)}</table>'


def section(title, body, note=''):
    n = f'<div style="font:12px/1.4 {SANS};color:{C["muted"]};padding-top:8px">{note}</div>' if note else ''
    return (f'<tr><td style="padding:20px 24px;border-bottom:1px solid {C["line"]}">'
            f'<div style="font:700 11px {SANS};letter-spacing:2px;text-transform:uppercase;color:{C["amber"]};padding-bottom:10px">{title}</div>{body}{n}</td></tr>')


def render(s):
    first, last = s['first'], s['last']
    span = f"{nice(first, '%-d')} to {nice(last, '%-d %B %Y')}" if first[5:7] == last[5:7] else f"{nice(first, '%-d %B')} to {nice(last, '%-d %B %Y')}"
    parts = []

    # 1. the big numbers
    if s['have_visitors']:
        change = ''
        if s['visitors_before']:
            d = s['visitors'] - s['visitors_before']
            pc = round(100 * d / s['visitors_before'])
            change = (f'{"up" if d >= 0 else "down"} {abs(pc)}% on the week before ({num(s["visitors_before"])})' if pc
                      else f'the same as the week before ({num(s["visitors_before"])})')
        busy = f'Busiest day: {nice(s["busiest"][0])}, {num(s["busiest"][1])} visitors.' if s['busiest'] and s['busiest'][1] else ''
        cell = lambda n, what: (f'<td width="50%" align="center" style="padding:14px 6px;background:{C["soft"]};border-radius:8px">'
                                f'<div style="font:600 34px/1 {SERIF};color:{C["maroon"]}">{num(n)}</div>'
                                f'<div style="font:12px/1.4 {SANS};color:{C["muted"]};padding-top:4px">{what}</div></td>')
        body = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{cell(s["visitors"], "visitors")}'
                f'<td width="12" style="width:12px;font-size:0">&nbsp;</td>{cell(s["views"], "pages opened")}</tr></table>'
                f'<div style="font:15px/1.5 {SERIF};color:{C["ink"]};padding-top:12px">{" ".join(x for x in (change.capitalize() + "." if change else "", busy) if x)}</div>')
        parts.append(section('Visitors', body))
        parts.append(section('Where they came from',
                             bars(s['countries'], lambda c: f'{flag(c)} &nbsp;{esc(COUNTRY.get(c, c))}'),
                             'Cloudflare counts every visit to the site, so these numbers are a little higher than real people.'))
        tabs_note = f'From {esc(s["tabs_from"])}.' if s['tabs_from'] and 'page views' not in s['tabs_from'] else ''
        parts.append(section('Most used tabs', bars(s['tabs'], esc), tabs_note))
        extra = []
        if s['found']:
            extra.append(bars(s['found'], esc))
        if s['devices']:
            tot = sum(n for _, n in s['devices']) or 1
            extra.append(f'<div style="font:15px/1.5 {SERIF};color:{C["ink"]};padding-top:{14 if s["found"] else 0}px">'
                         + ', '.join(f'{esc(k)} {round(100 * n / tot)}%' for k, n in s['devices']) + '.</div>')
        if extra:
            parts.append(section('How they found the site', ''.join(extra)))
    else:
        parts.append(section('Visitors', f'<div style="font:15px/1.5 {SERIF};color:{C["muted"]};font-style:italic">'
                                         'The visitor numbers could not be read this week. The Interaction page has them.</div>'))

    # 2. searches that found nothing
    if s['missed']:
        rows = ''.join(f'<tr><td style="padding:6px 0;border-top:1px solid {C["line"]};font:16px/1.3 {SERIF};color:{C["ink"]}">“{esc(w)}”</td>'
                       f'<td align="right" style="padding:6px 0 6px 10px;border-top:1px solid {C["line"]};font:13px {SANS};color:{C["muted"]};white-space:nowrap">'
                       f'{"once" if n == 1 else f"{n} times"}</td></tr>' for w, n in s['missed'][:15])
        more = len(s['missed']) - 15
        note = f'And {more} more on the Interaction page.' if more > 0 else ''
        body = (f'<div style="font:15px/1.5 {SERIF};color:{C["ink"]};padding-bottom:8px">{num(s["missed_total"])} '
                f'search{"" if s["missed_total"] == 1 else "es"} found nothing this week:</div>'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>')
        parts.append(section('Searches that found nothing', body, note))
    else:
        parts.append(section('Searches that found nothing', f'<div style="font:15px/1.5 {SERIF};color:{C["ink"]}">'
                                                            'Every search found something this week 🙏🏽</div>'))

    # 3. feedback, every word as it was typed
    if s['feedback']:
        cards = ''.join(f'<div style="background:{C["soft"]};border-left:3px solid {C["gold"]};border-radius:6px;padding:12px 14px;margin-top:{10 if i else 0}px">'
                        f'<div style="font:16px/1.5 {SERIF};color:{C["ink"]};white-space:pre-wrap">{esc(f["message"])}</div>'
                        f'<div style="font:12px/1.4 {SANS};color:{C["muted"]};padding-top:6px">{esc(f["name"]) + " · " if f.get("name") else ""}{nice(f["day"])}</div></div>'
                        for i, f in enumerate(s['feedback']))
        parts.append(section(f'Feedback ({len(s["feedback"])})', cards))
    else:
        parts.append(section('Feedback', f'<div style="font:15px/1.5 {SERIF};color:{C["muted"]};font-style:italic">No new messages this week.</div>'))

    gaps = f' ({", ".join(s["gaps"])} could not be read this time)' if s['gaps'] else ''
    pre = f"{num(s['visitors'])} visitors, {num(s['missed_total'])} searches that found nothing, {len(s['feedback'])} feedback." if s['have_visitors'] else 'This week on Bapa\'s Diary.'
    img = lambda f, alt: (f'<td width="50%" align="center" style="padding:0 6px"><img src="{SITE}about/img/{f}.jpg" width="84" height="84" alt="{alt}" '
                          f'style="display:block;width:84px;height:84px;border-radius:50%;border:2px solid {C["gold"]};object-fit:cover"></td>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta name="color-scheme" content="light"><title>This week on Bapa's Diary</title></head>
<body style="margin:0;padding:0;background:{C["cream"]}">
<div style="display:none;max-height:0;overflow:hidden">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{C["cream"]}"><tr><td align="center" style="padding:22px 8px 30px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{C["paper"]}">
<tr><td align="center" style="background:{C["maroon"]};padding:24px 20px 20px">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>{img("psm", "Pramukh Swami Maharaj")}{img("msm", "Mahant Swami Maharaj")}</tr></table>
<div style="font:700 11px {SANS};letter-spacing:4px;text-transform:uppercase;color:{C["gold"]};padding-top:14px">Bapa's Diary · just for you</div>
<div style="font:600 30px/1.1 {SERIF};color:{C["pale"]};padding:8px 0 6px">This week on the website</div>
<div style="font:italic 17px {SERIF};color:#f3e4c6">{span}</div></td></tr>
<tr><td style="padding:20px 24px 4px;font:17px/1.45 {SERIF};color:{C["ink"]}"><b style="color:{C["maroon"]};font-weight:600">Jay Swaminarayan Darpan 🙏🏽</b><br>
Here is how the last seven days went on bapas-diary.com.</td></tr>
{"".join(parts)}
<tr><td align="center" style="padding:20px 24px 26px;font:12px/1.6 {SANS};color:{C["muted"]}">
<a href="{SITE}interaction/" style="display:inline-block;font:700 13px {SANS};color:#3d0e19;background:{C["gold"]};padding:11px 20px;border-radius:999px;text-decoration:none">Open the Interaction page</a>
<div style="padding-top:14px">Only you get this email, every Monday morning{gaps}.</div></td></tr>
</table></td></tr></table></body></html>''', pre


def subject_of(s):
    bits = []
    if s['have_visitors']:
        bits.append(f"{num(s['visitors'])} visitors")
    if s['feedback']:
        bits.append(f"{len(s['feedback'])} new feedback")
    return "Bapa's Diary this week" + (': ' + ', '.join(bits) if bits else '')


def send(html, pre, subject, to):
    body = {'from': FROM, 'to': [to], 'subject': subject, 'html': html, 'text': pre + '\n\n' + SITE + 'interaction/'}
    req = urllib.request.Request('https://api.resend.com/emails', method='POST', data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'],
                                          'Content-Type': 'application/json', 'User-Agent': 'bapas-diary-summary'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b'{}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', help='make the email from this saved JSON instead of the website (a preview)')
    ap.add_argument('--out', help='write the email here as an HTML file (only for a preview: the repo is public)')
    ap.add_argument('--send', action='store_true', help='send it (to SUMMARY_TO, else hello@bapas-diary.com)')
    ap.add_argument('--today', help='pretend today is this date (the email covers the 7 days before it)')
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.datetime.now(UK).date()
    if a.sample:
        with open(a.sample) as f:
            data = json.load(f)
    else:
        key = os.environ.get('MISSED_KEY', '')
        if not key:
            sys.exit('No MISSED_KEY: add the GitHub secret (the same word as the Interaction page).')
        data = gather(key, today)
    s = summarise(data)
    html, pre = render(s)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(html)
        print('written', a.out)
    if a.send:
        r = send(html, pre, subject_of(s), os.environ.get('SUMMARY_TO') or TO)
        print('sent' if r.get('id') else 'Resend did not take it')
        if s['gaps']:
            print('could not read:', ', '.join(s['gaps']))


if __name__ == '__main__':
    main()
