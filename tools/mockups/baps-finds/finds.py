"""Mockup pictures of baps.org finds 2 to 5 on the LIVE bapas-diary.com pages (Darpan, 17 Nov 2026: "The other four
baps.org finds, a mockup for each. hurry up"). Everything is added in this browser only; nothing on the website changes,
and the daily 2pm picture is never touched. Fetches a handful of image files only (never pages), a pause between each.
Usage: finds.py OUTDIR
"""
import base64, datetime, io, sys, time, traceback
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SITE = 'https://bapas-diary.com'
LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.append(s)

DS = 'https://www.baps.org/Data/Sites/1/Media/dailysatsang/2025/'
# Daily Satsang "Swamishri's Darshan" photos, with the month and place baps.org gives (read in his Chrome, Nov 2026)
DARSHAN = [('1995', 'June 1995', 'Tithal', DS + '250530S.jpg'),
           ('1997', 'April 1997', 'Bahrain', DS + '250814S.jpg'),
           ('1997b', 'January 1997', 'Sankari', DS + '251026S.jpg'),
           ('1998', 'October 1998', 'London', DS + '250216S.jpg'),
           ('1998b', 'December 1998', 'Gadhada', DS + '250223S.jpg')]
BAPS = 'https://www.baps.org/Data/Sites/1/Media/'
WALL = {f'2016-{m:02d}': BAPS + f'DownloadableFile/2016{m:02d}_baps_wallpaper_h' + ('' if m == 1 else '_001') + '.jpg' for m in (3, 8)}
LIFE = 'https://pramukhswami.org/PSM/media/life/'
PSM_LIFE = [   # pramukhswami.org's life timeline photos, our own short words, English dates only
    ('t_1940_diksha.jpg', '1940', 'Becomes a sadhu, initiated by Shastriji Maharaj in Gondal'),
    ('t_1971_pramukhswamimaharaj_appointed_guru.jpg', '1971', 'Becomes guru of BAPS'),
    ('t_1974_key_to_the_city.jpg', '1974', 'First journey abroad as guru'),
    ('t_1984_pope-john-paul-II.jpg', '1984', 'Meets Pope John Paul II, Vatican City'),
    ('t_1985-london-suvarna-tula.jpg', '1985', 'Cultural Festival of India, London'),
    ('t_1992_akshardham-gandhinagar.jpg', '1992', 'Opens Akshardham, Gandhinagar'),
    ('t_1995_Mandir-Neasden-London.jpg', '1995', 'Opens the mandir in Neasden, London'),
    ('t_2000_world-peace-summit-UN.jpg', '2000', 'Speaks at the United Nations, New York'),
    ('t_akshardham_opening.jpg', '2005', 'Opens Akshardham, New Delhi'),
    ('t_2014_robbinsville_mandir.jpg', '2014', 'Opens the mandir in Robbinsville'),
    ('t_2016_centenary-celebration-sarangpur.jpg', '2016', 'Sarangpur mandir centenary'),
]

S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
def grab(url, width=1400):
    time.sleep(2)
    try:
        r = S.get(url, timeout=40)
        if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image'):
            log('  no image', r.status_code, url); return None
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
        if im.width > width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, 'JPEG', quality=86)
        log('  got', url.split('/')[-1], im.size)
        return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    except Exception as e:
        log('  failed', url, e); return None

log('Fetching samples')
darshan = {k: grab(u) for k, _, _, u in DARSHAN}
wall = {k: grab(u, 1600) for k, u in WALL.items()}
life = {f: grab(LIFE + f, 700) for f, _, _ in PSM_LIFE}

OPTS = {'computer': dict(viewport={'width': 1600, 'height': 1000}),
        'phone': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)}
MARK = 'outline:2px dashed rgba(217,164,65,.6);outline-offset:8px;border-radius:6px'

def shot(page, name, el=None):
    p = OUT / name
    (page.locator(el).first.screenshot(path=str(p), type='jpeg', quality=82) if el else page.screenshot(path=str(p), type='jpeg', quality=82))
    log('  saved', name)

def kill_timers(page):
    page.evaluate("""() => { let id = setTimeout(() => {}, 0), k = 0; while (id-- > 0 && k++ < 100000) { clearTimeout(id); clearInterval(id); } }""")

msm = []   # Mahant Swami Maharaj photos from Today, for the About page and beside the month pictures
def msm_from_today(br):
    pg = br.new_context(**OPTS['computer']).new_page()
    pg.clock.install(time=datetime.datetime(2026, 11, 3, 12, 0))
    pg.goto(SITE + '/', wait_until='networkidle'); time.sleep(5)
    pg.evaluate("() => { const a = document.getElementById('all'); if (a) a.hidden = false; }"); time.sleep(1)
    for y in range(2025, 2016, -1):
        r = pg.evaluate("""(y) => { const g = document.getElementById('y' + y); if (!g) return null;
            const i = g.querySelector('.thumb img, img'); if (!i) return null;
            const words = [...g.querySelectorAll('h2, h3, .place, .where, .yp, .card-place')].map(e => e.textContent.trim()).find(s => s && !/^\d{4}$/.test(s));
            return [i.currentSrc || i.src, words || (i.alt || '').split('.')[0]] }""", y)
        if r: msm.append([y] + r)
    log('  msm photos', len(msm)); pg.context.close()

def years(page, tag, key):
    d = darshan.get(key)
    if not d: log('  no photo for', key); return
    when, where = next((w, p) for k, w, p, _ in DARSHAN if k == key)
    y = int(when[-4:]); m = datetime.datetime.strptime(when, '%B %Y').month
    age = y - 1921 - (1 if m < 12 else 0)
    page.goto(SITE + '/through-the-years/#psm', wait_until='networkidle'); time.sleep(4); kill_timers(page)
    page.evaluate("""([src, when, where, age, y, older, mark]) => {
      for (const id of ['imgA', 'imgB']) { const i = document.getElementById(id); i.src = src; i.style.cssText = 'width:100%;height:100%;object-fit:contain;transform:none;left:0;top:0'; }
      document.getElementById('imgB').className = 'on rest'; document.getElementById('imgA').className = '';
      for (const id of ['intro', 'eyes']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
      document.getElementById('age').textContent = 'Bapa aged ' + age;
      document.getElementById('date').textContent = when;
      document.getElementById('place').textContent = where;
      document.getElementById('cap').textContent = "Swamishri's darshan";
      document.getElementById('cal').textContent = '';
      document.getElementById('count').textContent = '';
      document.getElementById('frame').style.cssText += ';' + mark;
      const t = document.querySelector('#tab-psm .yrs'); if (t) t.textContent = older[0] + ' to 13 August 2016';
      const list = document.getElementById('years'), first = list.firstElementChild;
      if (first) for (const oy of older.slice().reverse()) {
        const b = first.cloneNode(true); b.dataset.y = oy; b.classList.remove('on', 'past');
        b.querySelectorAll('*').forEach(n => { if (/^\\d{4}$/.test(n.textContent.trim())) n.textContent = oy; });
        if (/^\\d{4}$/.test(b.textContent.trim())) b.textContent = oy;
        if (oy === y) b.classList.add('on');
        b.style.cssText += ';' + mark; list.insertBefore(b, list.firstElementChild);
      }
      first && first.classList.remove('on');
    }""", [d, when, where, age, y, [1995, 1997, 1998], MARK])
    time.sleep(2)
    shot(page, f'7-years-{key}-{tag}.jpg')

ESSAY = {'t': 'Question Time with Pramukh Swami Maharaj', 'when': 'Mumbai, 4 March 1978',
         'x': 'Pramukh Swami Maharaj attended a youth assembly on the rooftop of the BAPS mandir in Dadar and answered their questions. Asked what youths should bear in mind when sharing satsang with others, Swamishri said: "You must be living it. If you have conviction, you can pass it on."'}
def ask(page, tag):
    page.goto(SITE + '/search/', wait_until='networkidle'); time.sleep(3)
    page.fill('#q', 'When was Bapa in Mumbai in 1978?'); page.press('#q', 'Enter'); time.sleep(8)
    page.evaluate("""([E, mark]) => {
      const box = document.getElementById('answer');
      if (box.hidden || !box.innerHTML.trim()) { box.hidden = false; box.innerHTML = `<div class="ask-q">You asked <b>When was Bapa in Mumbai in 1978?</b></div><div class="ask-a"></div>`; }
      const a = box.querySelector('.ask-a'); if (a) a.textContent = 'There are no photos of Bapa in Mumbai in 1978 in the diary yet, but an essay remembers 4 March 1978.';
      const sb = box.querySelector('.ask-sub'); if (sb) sb.remove();
      box.insertAdjacentHTML('beforeend', `<div style="margin-top:18px;padding:16px 18px;${mark};background:rgba(251,246,236,.7);text-align:left">
        <div style="font:700 11px/1 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:var(--gold-deep)">From an essay</div>
        <div style="margin-top:8px;font:600 22px/1.25 var(--serif);color:var(--maroon)">${E.t}</div>
        <div style="margin-top:4px;font:400 14px/1.4 var(--sans);color:var(--muted)">${E.when}</div>
        <p style="margin:10px 0 0;font:400 18px/1.5 var(--serif);color:var(--ink)">${E.x}</p>
        <div style="margin-top:8px;font:500 15px var(--serif);color:var(--gold-deep);text-decoration:underline;text-underline-offset:3px">Read the whole essay</div></div>`);
    }""", [ESSAY, MARK])
    page.evaluate("() => { const r = document.getElementById('answer').getBoundingClientRect(); scrollBy(0, r.top - 70); }"); time.sleep(2)
    shot(page, f'8-ask-essay-{tag}.jpg')

def month_pic(page, tag, key):
    w = wall.get(key)
    if not w: log('  no wallpaper', key); return
    page.goto(SITE + f'/calendar/#{key}', wait_until='networkidle'); time.sleep(5)
    m2 = msm[0][1] if msm else w
    ok = page.evaluate("""([a, b, mark]) => {
      const name = new Date(2000, +location.hash.slice(6) - 1, 1).toLocaleString('en-GB', {month: 'long'});
      const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n, r = null;
      while ((n = tw.nextNode())) { if (!n.nodeValue.trim().startsWith(name) || n.parentElement.closest('nav')) continue;
        const rg = document.createRange(); rg.selectNodeContents(n.parentElement); const q = rg.getBoundingClientRect();
        if (q.width > 0 && q.top > 0 && q.top < 600) { r = q; break; } }
      if (!r) return false;
      const h = Math.max(34, Math.min(70, r.height * 1.1)), w = Math.min(h * 16 / 9, Math.max(60, r.left - 30)), top = r.top + r.height / 2 - h / 2 + scrollY;
      const f = (s, x) => `<img src="${s}" alt="" style="position:absolute;z-index:99;top:${top}px;left:${x}px;height:${h}px;width:${w}px;object-fit:cover;object-position:50% 30%;border-radius:8px;box-shadow:0 0 0 2px #d9a441,0 6px 18px rgba(0,0,0,.45);${mark}">`;
      document.body.insertAdjacentHTML('beforeend', f(a, Math.max(8, r.left - w - 22)) + f(b, r.right + 22));
      return true;
    }""", [w, m2, MARK])
    log('  month name found' if ok else '  month name NOT found'); time.sleep(2)
    shot(page, f'9-calendar-month-{key}-{tag}.jpg')

def about(page, tag):
    P = [[life[f], y, t] for f, y, t in PSM_LIFE if life.get(f)]
    M = [[s, str(y), (p or 'Darshan')[:70]] for y, s, p in msm[:8]][::-1]
    page.goto(SITE + '/about/', wait_until='networkidle'); time.sleep(2)
    page.evaluate("""([P, M, mark]) => {
      const fig = ([src, y, t]) => `<figure style="flex:0 0 190px;margin:0;scroll-snap-align:start;background:linear-gradient(#fdf9f0,#efe4cd);padding:8px 8px 10px;border-radius:6px;box-shadow:0 10px 26px rgba(0,0,0,.4)"><img src="${src}" alt="" style="display:block;width:100%;aspect-ratio:4/3;object-fit:cover;object-position:50% 30%;border-radius:3px"><figcaption style="margin-top:8px;text-transform:none;letter-spacing:0"><b style="display:block;font:700 17px/1.1 Lora,Georgia,serif;color:#8a1c2b">${y}</b><span style="font:400 13px/1.35 Poppins,system-ui,sans-serif;color:#3b1219">${t}</span></figcaption></figure>`;
      const row = (who, list) => `<h3 style="margin:30px 0 14px;font:600 14px Cinzel,Georgia,serif;letter-spacing:.2em;text-transform:uppercase;color:#d9a441;text-align:center">${who}</h3><div style="display:flex;gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px 2px 14px">${list.map(fig).join('')}</div>`;
      const card = document.querySelector('.card');
      card.insertAdjacentHTML('afterend', `<section style="margin-top:56px;${mark};outline-offset:14px">
        <h2 style="text-align:center;color:#ffe296;font:600 clamp(24px,3.6vw,34px)/1.2 Cinzel,Georgia,serif;letter-spacing:.04em;text-transform:none">Bapa's life in pictures</h2>
        ${row('Pramukh Swami Maharaj, 1921 to 2016', P)}${row('Mahant Swami Maharaj, guru since 2016', M)}</section>`);
    }""", [P, M, MARK])
    time.sleep(3)
    page.evaluate("() => { const s = document.querySelector('.card').nextElementSibling; s.scrollIntoView(); scrollBy(0, -40); }"); time.sleep(1)
    shot(page, f'10-about-life-{tag}.jpg')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    try: msm_from_today(b)
    except Exception: log(traceback.format_exc()[-1500:])
    for tag, opts in OPTS.items():
        ctx = b.new_context(**opts); page = ctx.new_page()
        jobs = [('years 1995', lambda: years(page, tag, '1995')), ('ask', lambda: ask(page, tag)),
                ('month 2016-03', lambda: month_pic(page, tag, '2016-03')), ('about', lambda: about(page, tag))]
        if tag == 'computer':
            jobs += [('years 1998', lambda: years(page, tag, '1998')), ('years 1997', lambda: years(page, tag, '1997')),
                     ('month 2016-08', lambda: month_pic(page, tag, '2016-08'))]
        for name, fn in jobs:
            log(tag, name)
            try: fn()
            except Exception: log(traceback.format_exc()[-1500:])
        ctx.close()
    b.close()
(OUT / 'log-finds.txt').write_text('\n'.join(LOG))
