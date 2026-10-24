/* bapas-diary.com on phones (Darpan typed yes to the phone design, 24 Oct 2026). Goes with phone.css; added to every
   page by tools/web_phone.py at deploy time. Website only: nothing here touches the daily 2pm picture.
   Only acts on narrow screens; on a computer it does nothing at all.
     every page   a small "Bapa's Diary" and a round About button in the strip at the top
     Today        One year (swipe from year to year) or All years together, zoomed with + and − or a pinch
                  (1 to 4 cards a row, remembered); swipe down on a full screen photo closes it
     Calendar     the months scroll up and down instead of sideways, with where Bapa was, and the tapped day's card */
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
      // where Bapa was each day: a day with no place takes the place of the days around it when both agree (as on the computer)
      const placeCache = {};
      const places = k => placeCache[k] || (placeCache[k] = (() => {
        const pl = D.m[k].map(d => d[3] || null);
        for (let i = 0; i < pl.length; i++) if (!pl[i]) { let a = i - 1, b = i; while (b < pl.length && !pl[b]) b++; if (a >= 0 && b < pl.length && pl[a] === pl[b]) for (let j = i; j < b; j++) pl[j] = pl[a]; i = b; }
        return pl;
      })());
      const staysOf = k => {
        const out = [];
        places(k).forEach((p, i) => { const last = out[out.length - 1]; if (!p) return; if (last && last.p === p && last.b === i) last.b = i + 1; else out.push({p, a: i + 1, b: i + 1}); });
        return out;
      };

      wrap.innerHTML = '';
      const yrs = el('div', 'ph-years'); yrs.setAttribute('role', 'group'); yrs.setAttribute('aria-label', 'Years');
      wrap.append(yrs);
      const years = [...new Set(keys.map(k => k.slice(0, 4)))];
      years.forEach(y => { const b = el('button', '', y); b.type = 'button'; b.dataset.y = y; b.onclick = () => go(keys.find(k => k.startsWith(y))); yrs.append(b); });

      // every month gets its place at once (so the scroll bar is right); its days are drawn when it comes near the screen
      const sections = keys.map(k => {
        const [y, m] = k.split('-').map(Number), first = new Date(y, m - 1, 1).getDay(), rows = Math.ceil((first + D.m[k].length) / 7);
        const s = el('section', 'ph-month');
        s.dataset.k = k;
        s._rows = rows;
        s.innerHTML = `<div class="ph-mt"><b>${MONTHS[m - 1]}</b><span>${y}</span></div>`;
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
        const st = el('div', 'ph-stays');
        staysOf(k).forEach(x => {
          const c = el('div', 'ph-stay', `<b>${esc(x.p)}</b><small>${x.a === x.b ? x.a : x.a + ' to ' + x.b} ${MONTHS[m - 1].slice(0, 3)}</small>`);
          c.dataset.a = x.a; c.dataset.b = x.b; st.append(c);
        });
        const g = el('div', 'ph-grid');
        WD.forEach(w => g.append(el('span', 'wk', w)));
        for (let i = 0; i < first; i++) g.append(el('span'));
        days.forEach((d, i) => {
          const day = i + 1, b = el('button', 'ph-day'); b.type = 'button';
          const fest = [d[1], d[2]].filter(Boolean).join('; ').split('; ').filter(n => n && !/^(Fast|Sud|Vad) ?\w*$/.test(n));
          if (fest.length) b.classList.add('fest');
          b.setAttribute('aria-label', `${WDL[new Date(y, m - 1, day).getDay()]} ${day} ${MONTHS[m - 1]} ${y}${pl[i] ? ', ' + pl[i] : ''}${fest.length ? ', ' + fest.join(', ') : ''}`);
          b.setAttribute('aria-pressed', 'false');
          if (d[4]) {
            const im = new Image(); im.alt = ''; im.loading = 'lazy'; im.decoding = 'async';
            im.onerror = () => { im.remove(); b.querySelector('i') && b.querySelector('i').remove(); b.prepend(String(day)); };
            im.src = `${PH}s/${d[4]}/${encodeURIComponent(d[5])}`;
            b.append(im, el('i', '', day));
          } else b.textContent = day;
          b.onclick = () => pick(s, b, k, day, d, pl[i], fest);
          g.append(b);
        });
        s.append(st, g);
      }
      function pick(s, b, k, day, d, place, fest) {
        if (sel) sel.setAttribute('aria-pressed', 'false');
        sel = b; b.setAttribute('aria-pressed', 'true');
        wrap.querySelectorAll('.ph-stay.on').forEach(x => x.classList.remove('on'));
        s.querySelectorAll('.ph-stay').forEach(x => { if (day >= +x.dataset.a && day <= +x.dataset.b) { x.classList.add('on'); centre(x); } });
        const [y, m] = k.split('-').map(Number), date = `${k}-${String(day).padStart(2, '0')}`;
        const im = b.querySelector('img');
        card.href = `${SR}#date=${date}`;
        card.setAttribute('aria-label', `Open the photos of ${day} ${MONTHS[m - 1]} ${y}`);
        card.innerHTML = (im ? `<img alt="" src="${esc(im.src)}">` : '') +
          `<span class="t"><span class="k">${WDL[new Date(y, m - 1, day).getDay()]} ${day} ${MONTHS[m - 1]} ${y}</span>` +
          `<span class="p">${place ? 'Bapa was in ' + esc(place) : esc(d[0] || 'This day')}</span>` +
          `<span class="c">${esc([d[6], fest.join(' · '), place && d[0]].filter(Boolean)[0] || 'Open this day')}</span></span>`;
        card.hidden = false; wrap.classList.add('has-card');
      }
      const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) draw(x.target); }), {root: wrap, rootMargin: '900px 0px'});
      sections.forEach(s => io.observe(s));

      // the year buttons follow the scroll
      let curY = null;
      const mark = () => {
        const t = wrap.getBoundingClientRect().top + 120;
        const s = sections.find(x => x.getBoundingClientRect().bottom > t) || sections[0];
        const y = s.dataset.k.slice(0, 4);
        if (y !== curY) {
          curY = y;
          yrs.querySelectorAll('button').forEach(b => { const on = b.dataset.y === y; b.setAttribute('aria-pressed', on); if (on) centre(b); });
        }
        try { history.replaceState(null, '', '#' + s.dataset.k); } catch (e) {}
      };
      let tick = false;
      wrap.addEventListener('scroll', () => { if (!tick) { tick = true; requestAnimationFrame(() => { tick = false; mark(); }); } }, {passive: true});
      function go(k) {
        const s = sections[Math.max(0, keys.indexOf(k))];
        wrap.scrollTop = s.offsetTop - yrs.offsetHeight + 2;
        mark();
      }
      const h = location.hash.slice(1);
      go(D.m[h] ? h : D.start);
    }).catch(() => { wrap.innerHTML = '<p style="text-align:center;font-style:italic;color:#c9a98a;margin-top:40px">The calendar could not load. Please refresh the page.</p>'; });
  }
})();
