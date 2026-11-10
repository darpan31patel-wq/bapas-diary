"""Mockup pictures of the five baps.org finds on the LIVE bapas-diary.com pages (Darpan, 9 Nov 2026).

Everything is added in this browser only, nothing on the website changes. A handful of sample images are fetched
once from baps.org and pramukhswami.org (image files only, a pause between each). Usage: shoot.py OUTDIR
"""
import base64, datetime, io, json, sys, time, traceback
from pathlib import Path

import requests
from PIL import Image
from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
SITE = 'https://bapas-diary.com'
LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.append(s)

BAPS = 'https://www.baps.org/Data/Sites/1/Media/'
PSM = 'https://pramukhswami.org/PSM/wp-content/uploads/2016/07/'
DAILY = {   # baps.org Daily Satsang "Swamishri's Darshan", with the month and place it gives
    '1990': ('April 1990', 'Talaja', 'Bapa aged 68', BAPS + 'dailysatsang/2019/191103S.jpg'),
    '1996a': ('January 1996', 'Dhulia', 'Bapa aged 74', BAPS + 'dailysatsang/2022/221103S.jpg'),
    '1996b': ('May 1996', 'London', 'Bapa aged 74', BAPS + 'dailysatsang/2023/231103S.jpg'),
}
WALL24 = {f'2024-{m:02d}': BAPS + f'DownloadableFile/2024_{m}_h_001.jpg' for m in (3, 8, 11)}
WALL = {f'2016-{m:02d}': BAPS + f'DownloadableFile/2016{m:02d}_baps_wallpaper_h' + ('' if m == 1 else '_001') + '.jpg' for m in range(1, 13)}
PSM_PICS = [
    ('pramukh_swami_in_canada_parliament_house.jpg', 'At the Parliament of Canada'),
    ('pramukh_swami_with_tony_blair.jpg', 'With Tony Blair'),
    ('pramukh_swami_vasudev_pande_trinidad_pm.jpg', 'With the Prime Minister of Trinidad'),
    ('pramukh_swami_yoveri_kagura_museveni_president_uganada.jpg', 'With President Museveni of Uganda'),
]

S = requests.Session(); S.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
def grab(url, width=1600):
    time.sleep(2)
    try:
        r = S.get(url, timeout=40)
        if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image'):
            log('  no image', r.status_code, url); return None
        im = Image.open(io.BytesIO(r.content)).convert('RGB')
        if im.width > width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        b = io.BytesIO(); im.save(b, 'JPEG', quality=86)
        log('  got', url.split('/')[-1], im.size)
        return im, 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    except Exception as e:
        log('  failed', url, e); return None

def sheet(name, items):   # a contact sheet of what was fetched, to look at by eye
    ims = [(k, v[0]) for k, v in items.items() if v]
    if not ims: return
    cols, w = 4, 400
    rows = (len(ims) + cols - 1) // cols
    th = [im.resize((w, round(im.height * w / im.width))) for _, im in ims]
    h = max(t.height for t in th)
    out = Image.new('RGB', (cols * w, rows * h), 'white')
    for i, t in enumerate(th): out.paste(t, ((i % cols) * w, (i // cols) * h))
    out.save(OUT / name, quality=80)

log('Fetching samples')
daily = {k: grab(v[3]) for k, v in DAILY.items()}
wall = {k: grab(v, 2000) for k, v in {**WALL, **WALL24}.items()}
psm = {f: grab(PSM + f, 900) for f, _ in PSM_PICS}
sheet('sheet-daily-darshan.jpg', daily); sheet('sheet-wallpapers-2016.jpg', wall); sheet('sheet-pramukhswami-org.jpg', {k: v for k, v in psm.items()})

PR_TODAY = ['ભોજન દરમ્યાન દિવ્યસંકલ્પ સ્વામી, યતિરાજ સ્વામી તથા વિવેકશીલ સ્વામીએ ગીતામાં દર્શાવેલા પ્રત્યક્ષ અક્ષરબ્રહ્મ યોગ સંબંધી પ્રવચનો કર્યાં. છેલ્લે વિવેકશીલ સ્વામી કહે : ‘આપના દ્વારા પ્રત્યક્ષ પરમાત્માનો યોગ થયો છે.’',
            'સ્વામીશ્રી કહે : ‘યોગીજી મહારાજની આજ્ઞાથી સાધુ થયા છીએ એ યોગ છે. એમની સાથે જેટલો યોગ થાય એટલો પ્રત્યક્ષ યોગ.’']
PR_CAL = ['ભોજન પૂર્ણ કરીને સ્વામીશ્રી નોર્થ-ઈસ્ટ રિજિયનમાંથી સાધુ થવાની ઇચ્છા રાખનારા યુવકોને પ્રેરણા આપતાં કહે : ‘બહુ મોટો સંકલ્પ કર્યો છે. ફોજ કે મિલિટરીમાં તો એક વખતે પાર. આ તો આખી જિંદગી કુસ્તી કરવાની છે. કુસ્તીમાં તો મહારાજ, યોગીબાપા અને પ્રમુખસ્વામી મહારાજ સાથે છે, એટલે વાંધો નહીં આવે. આ બાવા કે વૈરાગીનો માર્ગ નથી. આ તો પ્રમુખસ્વામીનો માર્ગ છે. તમે બહુ સારા માર્ગે છો. જેમ જેમ જ્ઞાન થશે તેમ તેમ ખ્યાલ આવશે.’',
          'કેટલું બળ ભર્યું છે આ શબ્દોમાં !']

def kill_timers(page):
    page.evaluate("""() => { let id = setTimeout(() => {}, 0), k = 0; while (id-- > 0 && k++ < 100000) { clearTimeout(id); clearInterval(id); } }""")

def shot(page, name, el=None):
    p = OUT / name
    (page.locator(el).first.screenshot(path=str(p), type='jpeg', quality=82) if el else page.screenshot(path=str(p), type='jpeg', quality=82))
    log('  saved', name)

msm_pics = []
OPTS = {'computer': dict(viewport={'width': 1600, 'height': 1000}),
        'phone': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)}

def today(page, tag):
    page = page.context.browser.new_context(**OPTS[tag]).new_page()   # its own window, so the pretend clock stays here
    page.clock.install(time=datetime.datetime(2026, 11, 3, 12, 0))   # Today always shows today's date: pretend it is 3 November
    page.goto(SITE + '/', wait_until='networkidle'); page.wait_for_selector('#y2010', state='attached', timeout=45000); time.sleep(4)
    page.evaluate("() => { const a = document.getElementById('all'); if (a) a.hidden = false; }")
    page.evaluate("""(P) => {
      const g = document.getElementById('y2010'), a = g.querySelector('.arts');
      const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
      a.insertAdjacentHTML('afterend', `<div class="day-story" style="outline:2px dashed rgba(217,164,65,.55);outline-offset:10px;border-radius:4px"><p class="story-line"><b>Prasang</b>Gondal, 3 November 2010 · પ્રેરણા પરિમલ</p><div class="paras">${P.map(t => `<p class="more" lang="gu">${esc(t)}</p>`).join('')}</div></div>`);
    }""", PR_TODAY)
    if tag == 'computer':
        for y in range(2025, 2016, -1):
            src = page.evaluate("(y) => { const i = document.querySelector('#y' + y + ' .thumb img'); return i ? [i.currentSrc || i.src, i.alt] : null }", y)
            if src: msm_pics.append([y] + src)
    page.locator('#y2010').scroll_into_view_if_needed(); time.sleep(2)
    shot(page, f'1-today-prasang-{tag}.jpg', '#y2010')
    page.context.close()

def calendar_prasang(page, tag):
    def fix(route):
        r = route.fetch(); D = r.json()
        for Y in D.get('years', []):
            if Y.get('y') == 2017:
                Y['day'] = (Y.get('day') or []) + [['', 'Edison, 9 September 2017 · પ્રેરણા પરિમલ', PR_CAL, 0]]
        route.fulfill(response=r, body=json.dumps(D), headers={**r.headers, 'content-type': 'application/json'})
    if tag == 'phone':   # on a phone the day opens as its own page
        page.goto(SITE + '/photos/#date=2017-09-09&place=Edison', wait_until='networkidle'); time.sleep(5)
    else:
        page.goto(SITE + '/calendar/#2017-09', wait_until='networkidle'); time.sleep(4)
        page.locator('#ribbon .month[data-k="2017-09"] a.card[data-d="9"]').first.click(force=True); time.sleep(7)
    for f in page.frames:
        if '/photos/' in f.url or f == page.main_frame:
            f.evaluate("""(P) => { const g = document.querySelector('.grid'); if (!g || document.getElementById('mock-tell')) return;
              const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
              g.insertAdjacentHTML('beforebegin', `<div class="tell" id="mock-tell" style="outline:2px dashed rgba(217,164,65,.55);outline-offset:8px;border-radius:4px;margin-bottom:22px"><p class="line"><b>Prasang</b>Edison, 9 September 2017 · પ્રેરણા પરિમલ</p><div class="paras">${P.map(t => `<p lang="gu">${esc(t)}</p>`).join('')}</div></div>`); }""", PR_CAL)
    time.sleep(1)
    shot(page, f'1-calendar-prasang-{tag}.jpg')

def years(page, tag, key):
    d = daily.get(key)
    if not d: log('  no photo for', key); return
    when, where, age = DAILY[key][:3]
    page.goto(SITE + '/through-the-years/#psm', wait_until='networkidle'); time.sleep(4); kill_timers(page)
    page.evaluate("""([src, when, where, age, y]) => {
      for (const id of ['imgA', 'imgB']) { const i = document.getElementById(id); i.src = src; i.style.objectPosition = '50% 30%'; }
      document.getElementById('imgB').className = 'on rest'; document.getElementById('imgA').className = '';
      for (const id of ['intro', 'eyes']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
      document.getElementById('age').textContent = age;
      document.getElementById('date').textContent = when;
      document.getElementById('place').textContent = where;
      document.getElementById('cap').textContent = 'Daily darshan, from the baps.org Daily Satsang page';
      document.getElementById('count').textContent = 'Darshan 1';
      const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
      while ((n = tw.nextNode())) { if (n.parentElement.closest('nav')) continue; const v = n.nodeValue.trim();
        if (v === '1999') n.nodeValue = n.nodeValue.replace('1999', y); else if (v === 'Mumbai') n.nodeValue = n.nodeValue.replace('Mumbai', where); }
      const t = document.querySelector('#tab-psm .yrs'); if (t) t.textContent = '1990 to 13 August 2016';
    }""", [d[1], when, where, age, when.slice(-4)])
    time.sleep(2)
    shot(page, f'2-years-{key}-{tag}.jpg')

ESSAY = {'t': 'Question Time with Pramukh Swami Maharaj (Part 1)', 'by': 'Sadhu Amrutvijaydas', 'when': 'Mumbai, 4 March 1978',
         'x': 'Pramukh Swami Maharaj attended a yuvak assembly on the rooftop of the BAPS Mandir in Dadar. Swamishri replied to their questions. Q: What should youths bear in mind when promoting satsang to others? Swamishri: You must be living it. If you have conviction you can pass it on.'}
def ask(page, tag):
    page.goto(SITE + '/search/', wait_until='networkidle'); time.sleep(3)
    page.fill('#q', 'When was Bapa in Mumbai in 1978?'); page.press('#q', 'Enter'); time.sleep(8)
    page.evaluate("""(E) => {
      const box = document.getElementById('answer');
      if (box.hidden || !box.innerHTML.trim()) { box.hidden = false; box.innerHTML = `<div class="ask-q">You asked <b>When was Bapa in Mumbai in 1978?</b></div>`; }
      const a = box.querySelector('.ask-a'); if (a) a.textContent = 'The diary has no photos of Bapa in Mumbai in 1978, but an essay on baps.org remembers 4 March 1978.';
      const sb = box.querySelector('.ask-sub'); if (sb) sb.remove();
      box.insertAdjacentHTML('beforeend', `<div style="margin-top:18px;padding:16px 18px;border:2px dashed rgba(207,152,64,.6);border-radius:12px;background:rgba(251,246,236,.7);text-align:left">
        <div style="font:700 11px/1 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:var(--gold-deep)">From an essay on baps.org</div>
        <div style="margin-top:8px;font:600 22px/1.25 var(--serif);color:var(--maroon)">${E.t}</div>
        <div style="margin-top:4px;font:400 14px/1.4 var(--sans);color:var(--muted)">${E.when} · ${E.by}</div>
        <p style="margin:10px 0 0;font:400 18px/1.5 var(--serif);color:var(--ink)">${E.x}</p>
        <div style="margin-top:8px;font:400 14px var(--sans);color:var(--gold-deep);text-decoration:underline">Read the whole essay on baps.org</div></div>`);
      const res = document.getElementById('results');
      res.insertAdjacentHTML('afterbegin', `<section style="margin:22px 0;padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)">
        <h2 style="margin:0 0 10px;font:600 26px/1.2 var(--serif);color:var(--maroon)">Essays that mention this</h2>
        ${[[E.t, E.when], ['Question Time with Pramukh Swami Maharaj (Part 2)', 'Mumbai, 1978'], ['Pramukh Swami Maharaj: Secrets of His Success and Popularity (Part 1)', '2024 essay']].map(([t, w]) =>
          `<div style="display:flex;gap:14px;align-items:baseline;padding:7px 0;border-bottom:1px solid rgba(110,20,36,.1)"><b style="font:700 15px var(--serif);color:var(--gold-deep);min-width:9ch">${w}</b><span style="font:500 18px/1.35 var(--serif);color:var(--ink);text-decoration:underline;text-decoration-color:rgba(207,152,64,.5)">${t}</span></div>`).join('')}
      </section>`);
    }""", ESSAY)
    page.evaluate("() => { const r = document.getElementById('answer').getBoundingClientRect(); scrollBy(0, r.top - 70); }"); time.sleep(2)
    shot(page, f'3-ask-essays-{tag}.jpg')

def month_pic(page, tag, key):
    w = wall.get(key)
    if not w: log('  no wallpaper', key); return
    page.goto(SITE + f'/calendar/#{key}', wait_until='networkidle'); time.sleep(4)
    m2 = msm_pics[0][1] if msm_pics else w[1]
    page.evaluate("""([a, b]) => {
      const t = document.getElementById('t1'), r = t.getBoundingClientRect(), hd = document.querySelector('header');
      const h = Math.max(40, Math.min(70, r.height * 1.1)), w = h * 16 / 9, top = r.top + r.height / 2 - h / 2 + scrollY;
      const f = (s, x) => `<img src="${s}" alt="" style="position:absolute;z-index:5;top:${top}px;left:${x}px;height:${h}px;width:${w}px;object-fit:cover;object-position:50% 30%;border-radius:8px;box-shadow:0 0 0 2px #d9a441,0 6px 18px rgba(0,0,0,.45);outline:2px dashed rgba(217,164,65,.6);outline-offset:5px">`;
      document.body.insertAdjacentHTML('beforeend', f(a, r.left - w - 22) + f(b, r.right + 22));
    }""", [w[1], m2])
    time.sleep(2)
    shot(page, f'4-calendar-month-{key}-{tag}.jpg')

def about(page, tag):
    pics = [(psm[f][1], c) for f, c in PSM_PICS if psm.get(f)]
    page.goto(SITE + '/about/', wait_until='networkidle'); time.sleep(2)
    page.evaluate("""([P, M]) => {
      const fig = (src, cap) => `<figure style="margin:0;background:linear-gradient(#fdf9f0,#efe4cd);padding:8px 8px 10px;border-radius:6px;box-shadow:0 10px 26px rgba(0,0,0,.4)"><img src="${src}" alt="" style="display:block;width:100%;aspect-ratio:3/2;object-fit:cover;object-position:50% 30%;border-radius:3px"><figcaption style="margin-top:8px;font:500 13px/1.35 Lora,Georgia,serif;letter-spacing:0;text-transform:none;color:#3b1219">${cap}</figcaption></figure>`;
      const row = (who, list) => `<h3 style="margin:30px 0 14px;font:600 14px Cinzel,Georgia,serif;letter-spacing:.2em;text-transform:uppercase;color:#d9a441;text-align:center">${who}</h3><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:16px">${list.map(([s, c]) => fig(s, c)).join('')}</div>`;
      const card = document.querySelector('.card');
      card.insertAdjacentHTML('afterend', `<section style="margin-top:56px;outline:2px dashed rgba(217,164,65,.5);outline-offset:14px;border-radius:6px">
        <h2 style="text-align:center;color:#ffe296;font:600 clamp(24px,3.6vw,34px)/1.2 Cinzel,Georgia,serif;letter-spacing:.04em;text-transform:none">Bapa's life in pictures</h2>
        <p style="text-align:center;color:#f3ead9;opacity:.85;margin:0 auto;max-width:56ch;font-size:16px">Moments from Pramukh Swami Maharaj's life chosen by pramukhswami.org, beside Mahant Swami Maharaj from Bapa's Diary.</p>
        ${row('Pramukh Swami Maharaj', P)}${row('Mahant Swami Maharaj', M)}</section>`);
    }""", [pics, [[s, f'{y} · {a or "Darshan"}'] for y, s, a in msm_pics[:4]]])
    time.sleep(3)
    page.evaluate("() => { const s = document.querySelector('.card').nextElementSibling; s.scrollIntoView(); scrollBy(0, -40); }"); time.sleep(1)
    shot(page, f'5-about-pictures-{tag}.jpg')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for tag, opts in OPTS.items():
        ctx = b.new_context(**opts); page = ctx.new_page()
        jobs = [('calendar prasang', lambda: calendar_prasang(page, tag)),
                ('years 1990', lambda: years(page, tag, '1990')), ('ask', lambda: ask(page, tag)),
                ('month 2016-03', lambda: month_pic(page, tag, '2016-03')), ('about', lambda: about(page, tag))]
        if tag == 'computer':
            jobs += [('years 1996b', lambda: years(page, tag, '1996b')), ('years 1996a', lambda: years(page, tag, '1996a')),
                     ('month 2016-08', lambda: month_pic(page, tag, '2016-08'))]
        jobs = [('today', lambda: today(page, tag))] + jobs
        for name, fn in jobs:
            log(tag, name)
            try: fn()
            except Exception: log(traceback.format_exc()[-1500:])
        ctx.close()
    b.close()
(OUT / 'log.txt').write_text('\n'.join(LOG))
