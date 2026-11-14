# Mockup pictures of the Daily Satsang prasangs in English on Today and on a Calendar day (Darpan, 13 Nov 2026: "Yes to
# all", "keep a little button nearby that can translate everything into English, back into Gujarati"). Opens the LIVE
# bapas-diary.com pages on the runner, adds the prasang in the browser only (same markup and style as branch
# claude/project-thread-0f0un6), and saves screenshots. Changes nothing on the website, never touches the 2pm picture.
import datetime, json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = 'https://bapas-diary.com'
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
P = json.loads(Path('data/baps/prasang.json').read_text())
by = {}
for page, s in P.items():
    if s.get('d') and s.get('en'):
        by.setdefault(s['d'], []).append(s)
# short, clear stories first, from different places and years
WANT = ['2010-03-16', '2010-01-14', '2008-06-13', '2010-04-02', '2007-02-28', '2010-03-30', '2010-02-12', '2008-01-02']
CANDS = [d for d in WANT if d in by] + sorted(by, reverse=True)

CSS = """
.bpr .flip{margin-left:10px;padding:0;border:0;background:none;font:500 13px var(--serif);font-style:normal;color:var(--gold-soft, var(--gold));text-decoration:underline;text-decoration-color:rgba(217,164,65,.45);text-underline-offset:3px;cursor:pointer}
.bpr .src{margin:6px 0 0;font:400 12px/1.4 var(--sans);color:var(--cream, var(--paper));opacity:.6}
.bpr .src a{color:inherit}
.bpr [hidden]{display:none}
.bpr.mock{outline:2px dashed rgba(217,164,65,.55);outline-offset:10px;border-radius:4px}
"""
JS = """([css, cls, lineCls, label, stories, sel, where]) => {
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
  const ps = l => l.map(t => `<p class="more">${esc(t)}</p>`).join('');
  const html = stories.map(s => `<div class="${cls} bpr mock" translate="no"><p class="${lineCls}"><b>Prasang</b>${esc(label)}` +
    `<button type="button" class="flip">ગુજરાતી</button></p><div class="paras" lang="en">${ps(s.en)}</div>` +
    `<div class="paras" lang="gu" hidden>${ps(s.gu)}</div><p class="src">English translation of the <a href="${esc(s.src)}">baps.org Daily Satsang</a> prerna parimal</p></div>`).join('');
  const t = document.querySelector(sel); if (!t) return false;
  t.insertAdjacentHTML(where, html);
  document.querySelectorAll('.bpr .flip').forEach(b => b.onclick = () => { const [en, gu] = b.closest('.bpr').querySelectorAll('.paras');
    const toGu = gu.hidden; en.hidden = toGu; gu.hidden = !toGu; b.textContent = toGu ? 'English' : 'ગુજરાતી'; });
  return true;
}"""
OPTS = {'computer': dict(viewport={'width': 1600, 'height': 1000}),
        'phone': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)}

def nice(d):
    x = datetime.date.fromisoformat(d); return f'{x.day} {x.strftime("%B")} {x.year}'

def shot(loc, name):
    loc.screenshot(path=str(OUT / name), type='jpeg', quality=82); print('saved', name, flush=True)

with sync_playwright() as pw:
    br = pw.chromium.launch()
    chosen = None
    for d in CANDS[:8]:   # find a day whose year has photos on Today (the prasang sits under that year)
        y, md = d[:4], d[5:]
        ctx = br.new_context(**OPTS['computer']); pg = ctx.new_page()
        pg.clock.install(time=datetime.datetime(2026, int(md[:2]), int(md[3:]), 12, 0))   # Today shows only today's date
        pg.goto(SITE + '/', wait_until='networkidle'); time.sleep(5)
        ok = pg.evaluate(f"() => !!document.querySelector('#y{y} .arts')")
        print(d, 'year on Today' if ok else 'no year section', flush=True)
        ctx.close()
        if ok: chosen = d; break
    chosen = chosen or CANDS[0]
    y, md, S = chosen[:4], chosen[5:], by[chosen][:1]
    place = S[0].get('place', '')
    (OUT / 'prasang-day.txt').write_text(f'{chosen} {place}\n')
    for tag in ('computer', 'phone'):
        ctx = br.new_context(**OPTS[tag]); pg = ctx.new_page()
        pg.clock.install(time=datetime.datetime(2026, int(md[:2]), int(md[3:]), 12, 0))
        pg.goto(SITE + '/', wait_until='networkidle'); time.sleep(5)
        pg.evaluate("() => { const a = document.getElementById('all'); if (a) a.hidden = false; }")
        if pg.evaluate(JS, [CSS, 'day-story', 'story-line', ', '.join(filter(None, [place, nice(chosen)])), S, f'#y{y} .arts', 'afterend']):
            pg.locator(f'#y{y}').scroll_into_view_if_needed(); time.sleep(2)
            shot(pg.locator(f'#y{y}'), f'6-today-prasang-en-{tag}.jpg')
            pg.locator('.bpr .flip').first.click(); time.sleep(1)
            shot(pg.locator(f'#y{y}'), f'6-today-prasang-gu-{tag}.jpg')
        ctx.close()
        ctx = br.new_context(**OPTS[tag]); pg = ctx.new_page()
        pg.goto(f'{SITE}/photos/#date={chosen}&place={place}', wait_until='networkidle'); time.sleep(6)
        if pg.evaluate(JS, [CSS, 'tell', 'line', ', '.join(filter(None, [place, nice(chosen)])), S, '.grid', 'beforebegin']):
            pg.locator('.bpr').first.scroll_into_view_if_needed(); time.sleep(1)
            shot(pg, f'6-calendar-prasang-en-{tag}.jpg')
        ctx.close()
    br.close()
