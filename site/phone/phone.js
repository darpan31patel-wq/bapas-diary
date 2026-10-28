/* bapas-diary.com on phones (Darpan typed yes to the phone design, 24 Oct 2026). Goes with phone.css; added to every
   page by tools/web_phone.py at deploy time. Website only: nothing here touches the daily 2pm picture.
   Only acts on narrow screens; on a computer it does nothing at all.
     every page   a small "Bapa's Diary" and a round About button in the strip at the top
     Today        One year (swipe from year to year) or All years together, zoomed with + and − or a pinch
                  (1 to 4 cards a row, remembered); swipe down on a full screen photo closes it
     Calendar     the months scroll up and down instead of sideways, the tapped day's card, and at the top one bar with
                  the years and every place Bapa stayed: tap a place and its days glow (Darpan, 25 Oct 2026) */
(() => {
  const narrow = matchMedia('(max-width: 760px)');
  narrow.addEventListener('change', () => location.reload());   // turning a tablet: lay the page out again
  if (!narrow.matches) return;
  const root = document.documentElement, path = location.pathname;
  const store = {
    get: k => { try { return localStorage.getItem('phone.' + k); } catch (e) { return null; } },
    set: (k, v) => { try { localStorage.setItem('phone.' + k, v); } catch (e) {} },
  };
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  // slide a row sideways so this item is in the middle (never scrolls the page up or down)
  const centre = x => { const r = x.parentNode; r.scrollTo({left: x.offsetLeft - (r.clientWidth - x.offsetWidth) / 2, behavior: 'smooth'}); };

  function ready(fn) { document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', fn) : fn(); }

  ready(() => {
    // the top strip: name on the left, About on the right (About is no longer a tab)
    const top = el('div', 'ph-top');
    top.innerHTML = (path === '/' ? '<span class="ph-brand">Bapa\'s Diary</span>' : '<a class="ph-brand" href="/">Bapa\'s Diary</a>') +
      (path.startsWith('/about') ? '' : '<a class="ph-about" href="/about/" aria-label="About Bapa\'s Diary"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/></svg></a>');
    document.body.prepend(top);
    if (/^\/(calendar|travels|through-the-years)\//.test(path)) root.classList.add('ph-fixed');
    if (path.startsWith('/travels')) root.classList.add('ph-travels');
    if (path.startsWith('/through-the-years')) root.classList.add('ph-years-page');
    if (document.getElementById('cards') && document.getElementById('board')) today();
    if (path.startsWith('/calendar')) calendar();
  });

  /* ---------- Today ---------- */
  function today() {
    const $ = id => document.getElementById(id);
    const board = $('board'), cards = $('cards');
    let mode = store.get('todayMode') === 'all' ? 'all' : 'one';
    let cols = Math.max(1, Math.min(4, +store.get('todayCols') || 2));

    const sw = el('div', 'ph-switch');
    sw.setAttribute('role', 'group'); sw.setAttribute('aria-label', 'How to see this day');
    sw.innerHTML = '<button type="button" data-m="one">One year</button><button type="button" data-m="all">All years together</button>';
    board.before(sw);
    const hint = el('p', 'ph-hint-one', 'Swipe sideways for each year');
    board.after(hint);
    const zoom = el('div', 'ph-zoom');
    zoom.setAttribute('role', 'group'); zoom.setAttribute('aria-label', 'Zoom');
    zoom.innerHTML = '<button type="button" data-z="-1" aria-label="Zoom in, bigger pictures"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></button>' +
      '<button type="button" data-z="1" aria-label="Zoom out, see more years"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M5 12h14"/></svg></button>';
    document.body.append(zoom);

    const redraw = () => requestAnimationFrame(() => dispatchEvent(new Event('resize')));   // the day page redraws its cords on resize
    function apply() {
      root.classList.toggle('ph-one', mode === 'one');
      root.classList.toggle('ph-all', mode === 'all');
      [1, 2, 3, 4].forEach(n => root.classList.toggle('ph-c' + n, mode === 'all' && n === cols));
      root.style.setProperty('--ph-cols', cols);
      sw.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', b.dataset.m === mode));
      zoom.querySelector('[data-z="-1"]').disabled = cols <= 1;
      zoom.querySelector('[data-z="1"]').disabled = cols >= 4;
      store.set('todayMode', mode); store.set('todayCols', cols);
      redraw();
    }
    sw.onclick = e => { const b = e.target.closest('button'); if (b) { mode = b.dataset.m; apply(); } };
    zoom.onclick = e => { const b = e.target.closest('button'); if (b) { cols = Math.max(1, Math.min(4, cols + +b.dataset.z)); apply(); } };
    apply();

    // the zoom buttons show only while the cards are on the screen
    new IntersectionObserver(es => es.forEach(x => root.classList.toggle('ph-board', x.isIntersecting))).observe(board);
    cards.addEventListener('scroll', redraw, {passive: true});
    // One year opens on the first year with photos (the older years before it are On this day stories)
    let filled = null;
    new MutationObserver(() => {
      clearTimeout(filled);
      filled = setTimeout(() => {
        const slot = [...cards.children].find(x => x.querySelector('.photo:not(.story)'));
        if (mode === 'one' && slot) cards.scrollLeft = slot.offsetLeft - (cards.clientWidth - slot.offsetWidth) / 2;
      }, 300);
    }).observe(cards, {childList: true});

    // two finger pinch on the cards: apart for bigger pictures, together for more years
    let pinch = null;
    const dist = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);
    board.addEventListener('touchstart', e => { if (mode === 'all' && e.touches.length === 2) pinch = {d: dist(e.touches), c: cols}; }, {passive: true});
    board.addEventListener('touchmove', e => {
      if (!pinch || e.touches.length !== 2) return;
      e.preventDefault();
      const n = Math.max(1, Math.min(4, Math.round(pinch.c / (dist(e.touches) / pinch.d))));
      if (n !== cols) { cols = n; apply(); }
    }, {passive: false});
    board.addEventListener('touchend', e => { if (e.touches.length < 2) pinch = null; });

    // swipe down on a full screen photo closes it
    const viewer = $('viewer');
    if (viewer) {
      let s = null;
      viewer.addEventListener('touchstart', e => { s = e.touches.length === 1 ? {x: e.touches[0].clientX, y: e.touches[0].clientY} : null; }, {passive: true});
      viewer.addEventListener('touchend', e => {
        if (!s) return;
        const t = e.changedTouches[0], dx = t.clientX - s.x, dy = t.clientY - s.y;
        if (dy > 90 && Math.abs(dx) < 70 && $('vclose')) $('vclose').click();
        s = null;
      });
    }
  }

  /* ---------- Calendar ---------- */
  function calendar() {
    const DATA = typeof DATA_URL !== 'undefined' ? DATA_URL : '/data/calendar.json';
    const PH = typeof PHOTOS !== 'undefined' ? PHOTOS : 'https://photos.bapas-diary.com/';
    const SR = typeof SEARCH !== 'undefined' ? SEARCH : '/search/';
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'], WDL = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    root.classList.add('ph-cal');
    const wrap = el('div', 'ph-cal-wrap');
    wrap.setAttribute('aria-label', 'Calendar of days, scroll up and down');
    wrap.innerHTML = '<p style="text-align:center;font-style:italic;color:#c9a98a;margin-top:40px">Opening the calendar…</p>';
    document.body.append(wrap);
    const card = el('a', 'ph-card'); card.hidden = true; document.body.append(card);

    fetch(DATA).then(r => r.json()).then(D => {
      const keys = Object.keys(D.m).sort();
      // the FUTURE CALENDAR: the days after today, and where Bapa is going (FUTURE VICHARAN), as on the computer
      const FUT = D.fut || null, V = D.v || {};
      let TODAY = new Date(Date.now() - new Date().getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
      if (FUT) { const t = new Date(FUT + 'T12:00:00Z'); t.setUTCDate(t.getUTCDate() - 1); TODAY = t.toISOString().slice(0, 10); }
      // where Bapa was each day: a day with no place takes the place of the days around it when both agree (as on the computer)
      const placeCache = {};
      const places = k => placeCache[k] || (placeCache[k] = (() => {
        const pl = D.m[k].map(d => d[3] || null);
        for (let i = 0; i < pl.length; i++) if (!pl[i]) { let a = i - 1, b = i; while (b < pl.length && !pl[b]) b++; if (a >= 0 && b < pl.length && pl[a] === pl[b]) for (let j = i; j < b; j++) pl[j] = pl[a]; i = b; }
        return pl;
      })());

      wrap.innerHTML = '';
      // one bar that stays at the top: the years, every place Bapa stayed (1999 to today, a gold year where each year
      // starts), and a line about the place picked
      const bar = el('div', 'ph-jbar');
      const yrs = el('div', 'ph-years'); yrs.setAttribute('role', 'group'); yrs.setAttribute('aria-label', 'Years');
      const jrow = el('div', 'ph-jrow'); jrow.setAttribute('aria-label', 'Where Bapa was, swipe sideways');
      const note = el('div', 'ph-jnote'); note.setAttribute('aria-live', 'polite');
      bar.append(yrs, jrow, note);
      wrap.append(bar);
      const years = [...new Set(keys.map(k => k.slice(0, 4)))];
      years.forEach(y => { const b = el('button', FUT && y > FUT.slice(0, 4) ? 'ph-fy' : '', y); b.type = 'button'; b.dataset.y = y; b.onclick = () => { unpick(); go(keys.find(k => k.startsWith(y))); const m = jrow.querySelector(`.ph-ymark[data-y="${y}"]`); if (m) jrow.scrollTo({left: m.offsetLeft - 16, behavior: 'smooth'}); browsed = Date.now(); }; yrs.append(b); });
      const MN = MONTHS.map(x => x.slice(0, 3)), pad2 = n => String(n).padStart(2, '0');
      const stays = [], monthStays = {};
      { let lastP = null, cur = null, lastY = null, gap = 0, futMark = false;   // a stay carries on over up to 3 days with no place (as on the computer)
        keys.forEach(k => { const y = k.slice(0, 4); places(k).forEach((p, i) => {
          if (!p) { if (++gap > 3) lastP = null; return; }
          const fut = !!FUT && `${k}-${pad2(i + 1)}` >= FUT;   // the coming stays start afresh after today
          if (cur && p === lastP && cur.fut === fut) { cur.k1 = k; cur.d1 = i + 1; gap = 0; }
          else {
            if (fut && !futMark) { jrow.append(el('span', 'ph-fmark', 'Future vicharan')); futMark = true; lastY = y; }
            else if (y !== lastY) { const m = el('span', 'ph-ymark', y); m.dataset.y = y; jrow.append(m); lastY = y; }
            cur = {p, k0: k, d0: i + 1, k1: k, d1: i + 1, i: stays.length, fut}; stays.push(cur); gap = 0;
            cur.el = el('button', 'ph-stay' + (fut ? ' future' : '')); cur.el.type = 'button'; cur.el.dataset.i = cur.i; jrow.append(cur.el);
          }
          lastP = p; (monthStays[k] = monthStays[k] || new Set()).add(cur.i);
        }); });
      }
      stays.forEach(x => {
        const [y0, m0] = x.k0.split('-').map(Number), [y1, m1] = x.k1.split('-').map(Number), a = `${x.d0} ${MN[m0 - 1]}`, b = `${x.d1} ${MN[m1 - 1]}`;
        x.when = x.k0 === x.k1 && x.d0 === x.d1 ? a : x.k0 === x.k1 ? `${x.d0} to ${b}` : `${a} to ${b}`;
        x.from = `${x.k0}-${pad2(x.d0)}`; x.to = `${x.k1}-${pad2(x.d1)}`; x.y1 = y1;
        x.days = Math.round((new Date(x.to) - new Date(x.from)) / 864e5) + 1;
        x.el.innerHTML = `<b>${esc(x.p)}</b><small>${x.when}</small>`;
        x.el.setAttribute('aria-label', x.fut ? `Future vicharan: Bapa is going to ${x.p}, ${x.when} ${y0}. Light up these days` : `Bapa was in ${x.p}, ${x.when} ${y0}. Light up these days`);
      });
      let browsed = 0, pickI = null, curStays = new Set(), wantDate = '';
      ['touchstart', 'wheel', 'pointerdown'].forEach(ev => jrow.addEventListener(ev, () => browsed = Date.now(), {passive: true}));
      jrow.addEventListener('click', e => { const b = e.target.closest('.ph-stay'); if (b) { const i = +b.dataset.i; pickI === i ? unpick() : pickStay(i); } });
      // a tap anywhere else puts everything back to normal (Darpan, 25 Oct); a glowing day still shows its card
      document.addEventListener('click', e => {
        if (pickI == null || e.target.closest('.ph-jbar, .ph-card, nav')) return;
        const d = e.target.closest('.ph-day'); if (d && d.classList.contains('lit')) return;
        if (d) { e.preventDefault(); e.stopPropagation(); } unpick();
      }, true);
      const lit = b => { const x = stays[pickI]; b.classList.toggle('lit', !!x && b._date >= x.from && b._date <= x.to); };
      function pickStay(i) {
        const x = stays[i];
        if (pickI != null) stays[pickI].el.classList.remove('on');
        pickI = i; x.el.classList.add('on'); centre(x.el);
        wrap.classList.add('ph-picking'); wrap.querySelectorAll('.ph-day').forEach(lit);
        note.innerHTML = (x.fut ? '<i>Future vicharan</i> ' : '') + `<b>${esc(x.p)}</b> ${x.when} ${x.y1} · ${x.days} ${x.days === 1 ? 'day' : 'days'} ` + (x.fut ? '' : `<a href="${SR}#place=${encodeURIComponent(x.p)}&from=${x.from}&to=${x.to}">Photos</a>`) + `<button type="button" aria-label="Clear">✕</button>`;
        note.querySelector('button').onclick = unpick;
        go(x.k0, x.d0);
      }
      function unpick() {
        if (pickI == null) return;
        stays[pickI].el.classList.remove('on'); pickI = null;
        wrap.classList.remove('ph-picking'); wrap.querySelectorAll('.ph-day.lit').forEach(b => b.classList.remove('lit'));
        note.textContent = '';
      }

      const barH = () => wrap.style.setProperty('--ph-jbar', bar.offsetHeight + 'px');
      barH(); addEventListener('resize', barH);
      // every month gets its place at once (so the scroll bar is right); its days are drawn when it comes near the screen
      const sections = keys.map(k => {
        const [y, m] = k.split('-').map(Number), first = new Date(y, m - 1, 1).getDay(), rows = Math.ceil((first + D.m[k].length) / 7);
        const s = el('section', 'ph-month');
        s.dataset.k = k;
        s._rows = rows;
        s.innerHTML = `<div class="ph-mt"><b>${MONTHS[m - 1]}</b><span>${y}</span>${FUT && k + '-01' >= FUT ? '<em class="ph-ftag">Future calendar</em>' : ''}</div>`;
        wrap.append(s);
        return s;
      });
      // every month is exactly as tall before and after its days are drawn, so the scroll never jumps
      draw(sections[0]);
      const one = sections[0], cellH = one.querySelector('.ph-day').offsetHeight + 4, extra = one.offsetHeight - one._rows * cellH;
      sections.forEach(s => s.style.height = (extra + s._rows * cellH) + 'px');
      let sel = null;
      function draw(s) {
        if (s._done) return; s._done = true;
        const k = s.dataset.k, [y, m] = k.split('-').map(Number), days = D.m[k], pl = places(k), first = new Date(y, m - 1, 1).getDay();
        const g = el('div', 'ph-grid');
        WD.forEach(w => g.append(el('span', 'wk', w)));
        for (let i = 0; i < first; i++) g.append(el('span'));
        days.forEach((d, i) => {
          const day = i + 1, b = el('button', 'ph-day'); b.type = 'button';
          const date = `${k}-${pad2(day)}`, fut = !!FUT && date >= FUT;
          if (fut) b.classList.add('ph-future');
          if (fut && V[date]) b.classList.add('ph-vev');
          if (date === TODAY) b.classList.add('ph-today');
          const fest = [d[1], d[2]].filter(Boolean).join('; ').split('; ').filter(n => n && !/^(Fast|Sud|Vad) ?\w*$/.test(n));
          if (fest.length) b.classList.add('fest');
          b.setAttribute('aria-label', `${WDL[new Date(y, m - 1, day).getDay()]} ${day} ${MONTHS[m - 1]} ${y}${pl[i] ? ', ' + pl[i] : ''}${fest.length ? ', ' + fest.join(', ') : ''}`);
          b.setAttribute('aria-pressed', 'false');
          if (d[4] && !fut) {
            const im = new Image(); im.alt = ''; im.loading = 'lazy'; im.decoding = 'async';
            // the tiny copy (R2 t/, about 10 KB) first, the 480 px one if a new photo has no tiny copy yet (website review, 28 Oct 2026)
            im.onerror = () => { if (im.src.includes('/t/')) { im.src = im.src.replace('/t/', '/s/'); return; } im.remove(); b.querySelector('i') && b.querySelector('i').remove(); b.prepend(String(day)); };
            im.src = `${PH}t/${d[4]}/${encodeURIComponent(d[5])}`;
            b.append(im, el('i', '', day));
          } else b.textContent = day;
          b._date = `${k}-${pad2(day)}`; if (pickI != null) lit(b); if (b._date === wantDate) b.classList.add('want');
          b.onclick = () => pick(s, b, k, day, d, pl[i], fest, fut);
          g.append(b);
        });
        s.append(g);
      }
      function pick(s, b, k, day, d, place, fest, fut) {
        if (sel) sel.setAttribute('aria-pressed', 'false');
        sel = b; b.setAttribute('aria-pressed', 'true');
        const [y, m] = k.split('-').map(Number), date = `${k}-${String(day).padStart(2, '0')}`;
        const im = b.querySelector('img');
        card.href = `${SR}#date=${date}`;
        card.setAttribute('aria-label', `Open the photos of ${day} ${MONTHS[m - 1]} ${y}`);
        if (fut) {   // a FUTURE CALENDAR day: where Bapa is going and what is planned, nothing to open yet
          card.removeAttribute('href'); card.classList.add('ph-fcard');
          card.setAttribute('aria-label', `${day} ${MONTHS[m - 1]} ${y}, future calendar`);
          card.innerHTML = `<span class="t"><span class="k">Future calendar · ${WDL[new Date(y, m - 1, day).getDay()]} ${day} ${MONTHS[m - 1]} ${y}</span>` +
            `<span class="p">${place ? 'Future vicharan: ' + esc(place) : esc(d[0] || 'This day')}</span>` +
            `<span class="c">${esc([V[date], place && d[0], fest.join(' · ')].filter(Boolean).join(' · ') || d[0] || '')}</span></span>`;
          card.hidden = false; wrap.classList.add('has-card');
          return;
        }
        card.classList.remove('ph-fcard');
        card.innerHTML = (im ? `<img alt="" src="${esc(im.src)}">` : '') +
          `<span class="t"><span class="k">${WDL[new Date(y, m - 1, day).getDay()]} ${day} ${MONTHS[m - 1]} ${y}</span>` +
          `<span class="p">${place ? 'Bapa was in ' + esc(place) : esc(d[0] || 'This day')}</span>` +
          `<span class="c">${esc([d[6], fest.join(' · '), place && d[0]].filter(Boolean)[0] || 'Open this day')}</span></span>`;
        card.hidden = false; wrap.classList.add('has-card');
      }
      const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) draw(x.target); }), {root: wrap, rootMargin: '900px 0px'});
      sections.forEach(s => io.observe(s));

      // the year buttons follow the scroll
      let curY = null, curK = null;
      const mark = () => {
        const t = wrap.getBoundingClientRect().top + bar.offsetHeight + 60;
        const s = sections.find(x => x.getBoundingClientRect().bottom > t) || sections[0];
        const y = s.dataset.k.slice(0, 4);
        if (s.dataset.k !== curK) {
          curK = s.dataset.k;
          curStays.forEach(i => stays[i].el.classList.remove('cur')); curStays = monthStays[curK] || new Set();
          curStays.forEach(i => stays[i].el.classList.add('cur'));
          if (pickI == null && Date.now() - browsed > 6000 && curStays.size) { const a = [...curStays]; centre(stays[a[Math.floor(a.length / 2)]].el); }
          else if (pickI == null && Date.now() - browsed > 6000) { let j = -1; stays.forEach((x, i) => { if (x.k0 <= curK) j = i; }); if (j >= 0) centre(stays[j].el); }
        }
        if (y !== curY) {
          curY = y;
          yrs.querySelectorAll('button').forEach(b => { const on = b.dataset.y === y; b.setAttribute('aria-pressed', on); if (on) centre(b); });
        }
        try { history.replaceState(null, '', '#' + s.dataset.k); } catch (e) {}
      };
      let tick = false;
      wrap.addEventListener('scroll', () => { if (!tick) { tick = true; requestAnimationFrame(() => { tick = false; mark(); }); } }, {passive: true});
      function go(k, day) {
        const s = sections[Math.max(0, keys.indexOf(k))];
        wrap.scrollTop = s.offsetTop - bar.offsetHeight + 2;
        if (day) { draw(s); const b = s.querySelectorAll('.ph-day')[day - 1]; if (b) wrap.scrollTop = Math.max(wrap.scrollTop, b.offsetTop - bar.offsetHeight - 70); }
        mark();
      }
      // Search's Calendar button, as on the computer (Darpan, 28 Oct 2026): #2014-10-24 lights up the stay that day was
      // part of, rings the day and shows its card
      function fromLink() {
        const date = location.hash.slice(1);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !D.m[date.slice(0, 7)]) return false;
        const i = stays.findIndex(x => !x.fut && x.from <= date && x.to >= date);
        wantDate = date;
        wrap.querySelectorAll('.ph-day.want').forEach(x => x.classList.remove('want'));
        if (i >= 0) { unpick(); pickStay(i); }
        const k = date.slice(0, 7), day = +date.slice(8);
        go(k, day);
        const s = sections[keys.indexOf(k)], btn = s && s.querySelectorAll('.ph-day')[day - 1];
        if (btn) { btn.classList.add('want'); btn.click(); }
        return true;
      }
      const h = location.hash.slice(1);
      if (!fromLink()) go(D.m[h] ? h : D.start);
      addEventListener('hashchange', () => { if (location.hash.slice(1) !== curK) fromLink(); });
    }).catch(() => { wrap.innerHTML = '<p style="text-align:center;font-style:italic;color:#c9a98a;margin-top:40px">The calendar could not load. Please refresh the page.</p>'; });
  }
})();
