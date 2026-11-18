"""Automatic look check for bapas-diary.com (Darpan, 17 Nov 2026: "Automatic look check after every website update
... do it").

Website only: it just OPENS the public website like a visitor would. It touches nothing in the daily 2pm picture chain,
fetches nothing from baps.org, and changes nothing on the site.

It opens the main tabs (Today, Calendar, Search, Travels, Through the years, Legacy) on a computer (1440x900), a tablet
(1280x800) and a phone (390x844), saves a picture of each, and looks for things a person would notice:
  - the page did not open, or came up nearly empty
  - a JavaScript error on the page
  - a file or photo of the site that failed to load (404 and so on)
  - the page scrolls sideways (something is wider than the screen)
  - buttons or links sitting on top of each other, or the words of two buttons running into each other
  - photos on screen that did not show

It writes problems.json and a short report. With --send it emails Darpan ONLY when the list of problems is different
from the last check (the last list is kept in the GitHub release "look-check"), so a problem that is already known
does not email again after every rebuild, and a fix sends one "all clear" email.

The repo is public, so its run logs are too: this prints only page names and problem types, never secrets.
By hand:  python3 tools/look_check.py --out look   (pictures and report in look/, sends nothing)
"""
import argparse, json, os, re, sys, time, urllib.request
from playwright.sync_api import sync_playwright

SITE = 'https://bapas-diary.com'
PAGES = [('Today', '/'), ('Calendar', '/calendar/'), ('Search', '/search/'), ('Travels', '/travels/'),
         ('Through the years', '/through-the-years/'), ('Legacy', '/then-and-now/')]
SIZES = [('computer', 1440, 900), ('tablet', 1280, 800), ('phone', 390, 844)]
OURS = re.compile(r'^https://(www\.|photos\.)?bapas-diary\.com/')
# Files a page asks for that are allowed to be missing on some days (the page simply leaves that part out)
OPTIONAL = [re.compile(p) for p in (r'/data/bprasang/\d\d-\d\d\.json$',)]
FROM = "Bapa's Diary <hello@bapas-diary.com>"
TO = 'hello@bapas-diary.com'

# Runs inside the page: finds sideways scroll, overlapping buttons, words running together, broken photos
PROBE = r"""() => {
  const out = {};
  const vw = innerWidth, vh = innerHeight;
  out.sideways = document.documentElement.scrollWidth > vw + 2;
  out.words = (document.body.innerText || '').trim().length;
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 4 && r.height > 4 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05 &&
           r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw; };
  const name = e => ((e.innerText || e.getAttribute('aria-label') || e.title || '').trim().replace(/\s+/g, ' ')).slice(0, 30);
  const pinned = e => { for (let n = e; n && n !== document.body; n = n.parentElement) {
      const s = getComputedStyle(n); if (s.position === 'fixed' || s.position === 'sticky') return true; } return false; };
  const scroller = e => { for (let n = e.parentElement; n && n !== document.body; n = n.parentElement) {
      const s = getComputedStyle(n); if (/(auto|scroll|hidden)/.test(s.overflowX + s.overflowY)) return n; } return null; };
  const btns = [...document.querySelectorAll('a, button, [role=button], select, input')].filter(vis);
  const textBox = e => {  // the box of the words you can actually see (hidden spans left out)
    let l = 1e9, t = 1e9, r = -1e9, b = -1e9;
    const w = document.createTreeWalker(e, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const p = n.parentElement;
      if (!n.textContent.trim() || !p || !p.checkVisibility({opacityProperty: true, visibilityProperty: true})) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const q of rg.getClientRects()) { if (q.width < 1) continue;
        l = Math.min(l, q.left); t = Math.min(t, q.top); r = Math.max(r, q.right); b = Math.max(b, q.bottom); }
    }
    return r < l ? {left: 0, right: 0, top: 0, bottom: 0, width: 0, height: 0}
                 : {left: l, right: r, top: t, bottom: b, width: r - l, height: b - t};
  };
  const overlap = [], runs = [];
  for (let i = 0; i < btns.length; i++) {
    const a = btns[i], ra = a.getBoundingClientRect();
    for (let j = i + 1; j < btns.length; j++) {
      const b = btns[j];
      if (a.contains(b) || b.contains(a)) continue;
      // a bar pinned to the screen (top menu, phone tab bar) or a sliding row passing under arrows is normal
      if (pinned(a) !== pinned(b) || scroller(a) !== scroller(b)) continue;
      const rb = b.getBoundingClientRect();
      const x = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const y = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (x > 3 && y > 3 && x * y > 0.15 * Math.min(ra.width * ra.height, rb.width * rb.height))
        overlap.push(name(a) + ' / ' + name(b));
      // words of two buttons side by side touching or running into each other ("20002001")
      if ((a.innerText || '').trim() && (b.innerText || '').trim()) {
        const ta = textBox(a), tb = textBox(b);
        const ty = Math.min(ta.bottom, tb.bottom) - Math.max(ta.top, tb.top);
        const gap = Math.max(ta.left, tb.left) - Math.min(ta.right, tb.right);
        if (ta.width > 0 && tb.width > 0 && ty > 0.5 * Math.min(ta.height, tb.height) && gap <= 0)
          runs.push(name(a) + name(b));
      }
    }
  }
  out.overlap = [...new Set(overlap)].slice(0, 6);
  out.runs = [...new Set(runs)].slice(0, 6);
  out.broken = [...document.images].filter(i => vis(i) && i.complete && i.naturalWidth === 0 &&
                 /^https?:/.test(i.currentSrc || i.src || ''))
                 .map(i => i.currentSrc || i.src).slice(0, 6);
  return out;
}"""


def check(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    problems, rows = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for size, w, h in SIZES:
            phone = size == 'phone'
            ctx = b.new_context(viewport={'width': w, 'height': h}, is_mobile=phone, has_touch=phone,
                                device_scale_factor=2 if phone else 1, locale='en-GB', timezone_id='Europe/London')
            for page_name, path in PAGES:
                pg = ctx.new_page()
                pg.route('**/*cloudflareinsights*', lambda r: r.abort())  # never count the robot as a visitor
                errs, bad = [], []
                pg.on('pageerror', lambda e, errs=errs: errs.append(str(e).split('\n')[0][:140]))
                pg.on('response', lambda r, bad=bad: bad.append(f'{r.status} {r.url}') if r.status >= 400 and OURS.match(r.url)
                      and not any(o.search(r.url.split('?')[0]) for o in OPTIONAL) else None)
                t0 = time.time()
                status = None
                try:
                    resp = pg.goto(SITE + path, wait_until='domcontentloaded', timeout=60000)
                    status = resp.status if resp else None
                    try:
                        pg.wait_for_load_state('load', timeout=30000)
                        pg.wait_for_load_state('networkidle', timeout=15000)
                    except Exception:
                        pass  # Today keeps a live webcast check running, so it never goes fully quiet
                    pg.wait_for_timeout(2500)
                except Exception as e:
                    errs.append('did not open: ' + str(e).split('\n')[0][:100])
                secs = round(time.time() - t0, 1)
                shot = f'{page_name.lower().replace(" ", "-")}-{size}.jpg'
                try:
                    pg.screenshot(path=os.path.join(out_dir, shot), type='jpeg', quality=80)
                    m = pg.evaluate(PROBE)
                except Exception as e:
                    m = {}
                    errs.append('could not be checked: ' + str(e).split('\n')[0][:100])
                where = f'{page_name} on {size}'
                def add(kind, detail=''):
                    problems.append({'page': page_name, 'size': size, 'kind': kind, 'detail': detail, 'picture': shot})
                if status and status >= 400:
                    add('page did not open', f'answered {status}')
                if m and m.get('words', 0) < 40:
                    add('page looks empty')
                for e in errs[:3]:
                    add('error on the page', e)
                for x in sorted(set(bad))[:4]:
                    add('file did not load', x.replace(SITE, ''))
                if m.get('sideways'):
                    add('page scrolls sideways', 'something is wider than the screen')
                for x in m.get('overlap', [])[:3]:
                    add('buttons on top of each other', x)
                if m.get('runs'):
                    add('words run into each other', ', '.join(m['runs'][:4]))
                for x in m.get('broken', [])[:3]:
                    add('photo did not show', x.replace(SITE, ''))
                rows.append({'page': page_name, 'size': size, 'seconds': secs, 'picture': shot})
                print(f'{where}: {secs}s, ' + ('ok' if not [q for q in problems if q['page'] == page_name and q['size'] == size]
                                                   else 'problems'))
                pg.close()
            ctx.close()
        b.close()
    json.dump({'problems': problems, 'pages': rows}, open(os.path.join(out_dir, 'problems.json'), 'w'), indent=1)
    return problems


def key(problems):
    """What makes two checks 'the same': which page, size and kind (not changing details such as a photo name)."""
    return sorted({(q['page'], q['size'], q['kind']) for q in problems})


def email(problems, before, run_url):
    esc = lambda s: str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    if not problems:
        subject = "Bapa's Diary look check: all clear again"
        lines = ['<p>The website looks right again on computer, tablet and phone. Nothing to do.</p>']
    else:
        new = [q for q in problems if (q['page'], q['size'], q['kind']) not in {tuple(x) for x in before}]
        subject = f"Bapa's Diary look check: {len({(q['page'], q['kind']) for q in problems})} thing(s) to look at"
        lines = ['<p>The automatic look check found something on bapas-diary.com. Nothing was changed; '
                 'ask Claude in the project to fix it.</p><ol>']
        for q in problems:
            tag = ' <b>(new)</b>' if q in new else ''
            lines.append(f"<li><b>{esc(q['page'])}</b> on {esc(q['size'])}: {esc(q['kind'])}"
                         f"{(' (' + esc(q['detail']) + ')') if q['detail'] else ''}{tag}</li>")
        lines.append('</ol>')
    lines.append(f'<p>Pictures of every tab: <a href="{run_url}">open the check on GitHub</a>, then Artifacts.</p>')
    html = ('<div style="font-family:Georgia,serif;color:#2e1a14;background:#fffaf0;padding:18px">'
            '<h2 style="color:#5a1626;margin:0 0 10px">Bapa\'s Diary look check</h2>' + ''.join(lines) + '</div>')
    body = {'from': FROM, 'to': [os.environ.get('SUMMARY_TO') or TO], 'subject': subject, 'html': html}
    req = urllib.request.Request('https://api.resend.com/emails', method='POST', data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + os.environ['RESEND_API_KEY'],
                                          'Content-Type': 'application/json', 'User-Agent': 'bapas-diary-look-check'})
    with urllib.request.urlopen(req, timeout=60) as r:
        print('email sent' if json.loads(r.read() or b'{}').get('id') else 'Resend did not take the email')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='look')
    ap.add_argument('--before', help='last check\'s problems.json (to email only when something changed)')
    ap.add_argument('--send', action='store_true')
    ap.add_argument('--run-url', default='')
    a = ap.parse_args()
    problems = check(a.out)
    before = []
    if a.before and os.path.exists(a.before):
        try:
            before = key(json.load(open(a.before)).get('problems', []))
        except Exception:
            before = []
    now = key(problems)
    print(f'{len(problems)} problem(s) found; ' + ('same as last check' if now == before else 'different from last check'))
    with open(os.path.join(a.out, 'changed'), 'w') as f:
        f.write('yes' if now != before else 'no')
    if a.send and now != before:
        email(problems, before, a.run_url)


if __name__ == '__main__':
    main()
