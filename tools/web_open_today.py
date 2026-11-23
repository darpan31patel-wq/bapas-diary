"""Every tab opens on today's date, London time (Darpan, 23 Nov 2026: "When I open any of the website tabs, it's
still not opening on today's date. Remember, I told you it always needs to open on today's date.")

Two faults, fixed in the built site after every other step:
1. The Calendar (computer and phone) took "today" and its opening month from the day the site was last built
   (the nightly build runs about 9:40pm, so all the next day it opened on yesterday). It now works out today
   from the London clock each time the page opens.
2. The Calendar, Darshan and Travels write the month or day you are looking at into the address (#2026-10).
   Opening the tab again (a reload, a restored tab, the Back button, a saved link, the phone's home screen icon)
   brought back that old date. Now a date in the address is kept only when you came by a link from another page
   of the website (a Calendar link on Today, a Search result); otherwise the tab opens on today. A tab left open
   reloads on today when you come back to it on a new day.

    python3 tools/web_open_today.py --out out
"""
import argparse, re
from pathlib import Path

LONDON = "new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/London'}).format(new Date())"

HEAD = """<script>/* opens on today (Darpan, 23 Nov 2026) */(function(){try{
var h=location.hash.slice(1), dated=/^(\\d{4}-\\d{2}(-\\d{2})?|\\d{2}-\\d{2})$/.test(h);
var n=performance.getEntriesByType&&performance.getEntriesByType('navigation')[0], how=n?n.type:'navigate';
var r=document.referrer, fromSite=false;
try{var u=new URL(r);fromSite=u.origin===location.origin&&u.pathname!==location.pathname}catch(e){}
if(dated&&!(how==='navigate'&&fromSite))history.replaceState(null,'',location.pathname+location.search);
var day=function(){return %s};
var opened=day();
var back=function(){if(day()!==opened)location.replace(location.pathname+location.search)};
addEventListener('pageshow',function(e){if(e.persisted)back()});
document.addEventListener('visibilitychange',function(){if(!document.hidden)back()});
}catch(e){}})();</script>
""" % LONDON

PAGES = ['calendar/index.html', 'darshan/index.html', 'travels/index.html']


def head(s):
    if 'opens on today (Darpan' in s:
        return s
    m = re.search(r'<head[^>]*>', s, re.I)
    return s[:m.end()] + '\n' + HEAD + s[m.end():] if m else HEAD + s


def calendar(s):
    """The computer Calendar: today and the opening month from the London clock, not the build day."""
    old = "if(FUT){const t=new Date(FUT+'T12:00:00Z');t.setUTCDate(t.getUTCDate()-1);TODAY=t.toISOString().slice(0,10)}"
    if old in s:
        s = s.replace(old, f"TODAY={LONDON};")
    old = "goTo(D.m[h]?h:D.start,false)"
    if old in s:
        s = s.replace(old, "goTo(D.m[h]?h:D.m[TODAY.slice(0,7)]?TODAY.slice(0,7):D.start,false)")
    return s


def phone(s):
    """The phone Calendar (phone.js): the same."""
    old = "if (FUT) { const t = new Date(FUT + 'T12:00:00Z'); t.setUTCDate(t.getUTCDate() - 1); TODAY = t.toISOString().slice(0, 10); }"
    if old in s:
        s = s.replace(old, f"TODAY = {LONDON};")
    old = "go(D.m[H0] ? H0 : D.start)"
    if old in s:
        s = s.replace(old, "go(D.m[H0] ? H0 : D.m[TODAY.slice(0, 7)] ? TODAY.slice(0, 7) : D.start)")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='out')
    a = ap.parse_args()
    out = Path(a.out)
    for p in PAGES:
        f = out / p
        if not f.exists():
            print(f'open on today: no {p}')
            continue
        s = f.read_text(encoding='utf-8')
        t = head(s)
        if p.startswith('calendar/'):
            t = calendar(t)
        if t != s:
            f.write_text(t, encoding='utf-8')
        print(f'open on today: {p} {"changed" if t != s else "as it was"}')
    f = out / 'phone.js'
    if f.exists():
        s = f.read_text(encoding='utf-8')
        t = phone(s)
        if t != s:
            f.write_text(t, encoding='utf-8')
        print(f'open on today: phone.js {"changed" if t != s else "as it was"}')


if __name__ == '__main__':
    main()
