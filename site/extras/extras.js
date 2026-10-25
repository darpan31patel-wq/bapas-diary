// Favourites, Share a day and the TV slideshow for every page of bapas-diary.com (Darpan typed yes to all three,
// 24 Oct 2026). Website only: nothing here touches the daily 2pm picture. The deploy adds this file and extras.css
// to every page (tools/web_extras.py), so pages built by other threads need no changes. A page can also use the
// hooks directly:
//   <button data-fav="ALBUM/FILE" data-date="YYYY-MM-DD" data-place="..." data-cap="...">   a heart
//   <button data-share-day="MM-DD">                                                         the share choices
//   BapaDiary.slideshow([{src, date, place, cap}, ...], 'Title')                            full screen, for the TV
// Favourites live in this browser only (localStorage), so there is no login.
(function () {
  'use strict';
  const PHOTOS = window.BAPA_PHOTOS || 'https://photos.bapas-diary.com/';
  const KEY = 'bapas-diary-favourites';
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const HEART = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.3 3 4.5 6.7 4.5c2.2 0 3.6 1.2 5.3 3.1 1.7-1.9 3.1-3.1 5.3-3.1 3.7 0 5.8 3.8 4.3 7.3C19.5 16.4 12 21 12 21z"/></svg>';
  const SHARE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 13v7h14v-7"/></svg>';
  const PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4l13 8-13 8z"/></svg>';
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pad = n => String(n).padStart(2, '0');
  const niceDay = mmdd => `${+mmdd.slice(3)} ${MONTHS[+mmdd.slice(0, 2) - 1]}`;
  const niceDate = d => /^\d{4}-\d\d-\d\d$/.test(d || '') ? `${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1]} ${d.slice(0, 4)}` : (d || '');
  const keyOf = src => { const m = /\/[sm]\/([^/]+\/[^/?#]+)/.exec(src || ''); return m ? decodeURIComponent(m[1]) : null; };
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };

  // ---- favourites ------------------------------------------------------------------------------------------------
  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) { return []; } }
  function save(list) { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { toast('Your browser would not keep this. Is it in private mode?'); } }
  const fav = {
    list: load,
    has: k => load().some(f => f.k === k),
    toggle(item) {
      const list = load(), on = list.some(f => f.k === item.k);
      save(on ? list.filter(f => f.k !== item.k) : [{ k: item.k, d: item.d || '', p: item.p || '', c: item.c || '', at: Date.now() }, ...list]);
      sync();
      toast(on ? 'Taken out of your favourites' : 'Kept in your favourites 💛', on ? null : ['See them', '/favourites/']);
      return !on;
    },
    addAll(items) { const list = load(), have = new Set(list.map(f => f.k)); save([...items.filter(i => !have.has(i.k)), ...list]); sync(); },
  };
  function sync() {
    const have = new Set(load().map(f => f.k));
    document.querySelectorAll('[data-fav]').forEach(b => {
      const on = have.has(b.dataset.fav);
      b.setAttribute('aria-pressed', on);
      b.setAttribute('aria-label', on ? 'In your favourites. Tap to take it out' : 'Keep in my favourites');
      b.title = on ? 'In your favourites' : 'Keep in my favourites';
      const t = b.querySelector('.bd-t'); if (t) t.textContent = on ? 'In favourites' : 'Favourite';
    });
    document.dispatchEvent(new CustomEvent('bapa-favourites'));
  }
  function heart(item, withText) {
    const b = el('button', 'bd-heart' + (withText ? ' bd-pill' : ''), HEART + (withText ? '<span class="bd-t">Favourite</span>' : ''));
    b.type = 'button';
    Object.assign(b.dataset, { fav: item.k, date: item.d || '', place: item.p || '', cap: item.c || '' });
    return b;
  }

  // ---- little message at the bottom --------------------------------------------------------------------------------
  let toastTimer;
  function toast(text, link) {
    let t = document.querySelector('.bd-toast');
    if (!t) { t = el('div', 'bd-toast'); t.setAttribute('role', 'status'); document.body.append(t); }
    t.innerHTML = esc(text) + (link ? ` <a href="${esc(link[1])}">${esc(link[0])}</a>` : '');
    t.classList.add('on'); clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('on'), 3200);
  }

  // ---- share a day ---------------------------------------------------------------------------------------------------
  async function sharePicture(mmdd) {
    const url = `/share/day/${mmdd}.jpg`, text = `A smruti of Bapa for ${niceDay(mmdd)} 🙏🏽`;
    try {
      const blob = await (await fetch(url)).blob();
      const file = new File([blob], `bapas-diary-${mmdd}.jpg`, { type: 'image/jpeg' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) { await navigator.share({ files: [file], text }); return; }
    } catch (e) { if (e && e.name === 'AbortError') return; }
    window.open(url, '_blank', 'noopener');   // a computer: the picture opens, ready to save or drag into WhatsApp Web
    toast('The picture is open in a new tab. Save it, then send it.');
  }
  async function shareLink(mmdd) {
    const url = `${location.origin}/day/${mmdd}/`, text = `A smruti of Bapa for ${niceDay(mmdd)}. Open His diary to see where He was.`;
    if (navigator.share) { try { await navigator.share({ title: `${niceDay(mmdd)} · Bapa's Diary`, text, url }); return; } catch (e) { if (e.name === 'AbortError') return; } }
    window.open('https://wa.me/?text=' + encodeURIComponent(text + '\n' + url), '_blank', 'noopener');
  }
  function shareDay(mmdd) {
    if (!/^\d\d-\d\d$/.test(mmdd || '')) return;
    const d = el('dialog', 'bd-sheet');
    d.setAttribute('aria-label', 'Share ' + niceDay(mmdd));
    d.innerHTML = `<div class="bd-h">Share ${esc(niceDay(mmdd))}</div>
      <img class="bd-prev" alt="The picture of ${esc(niceDay(mmdd))}" src="/share/day/${mmdd}.jpg">
      <button type="button" data-a="pic"><span class="bd-i">${SHARE}</span><span>Send the picture<small>A ready picture of this day, for WhatsApp or your status</small></span></button>
      <button type="button" data-a="link"><span class="bd-i"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg></span><span>Send a link<small>Opens this day on bapas-diary.com</small></span></button>
      <a download="bapas-diary-${mmdd}.jpg" href="/share/day/${mmdd}.jpg"><span class="bd-i"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg></span><span>Save the picture<small>Keep it in your photos</small></span></a>
      <button type="button" class="bd-x" data-a="x">Close</button>`;
    document.body.append(d);
    d.addEventListener('close', () => d.remove());
    d.addEventListener('click', e => {
      if (e.target === d) return d.close();
      const a = e.target.closest('[data-a]'); if (!a) return;
      if (a.dataset.a === 'pic') sharePicture(mmdd);
      if (a.dataset.a === 'link') shareLink(mmdd);
      d.close();
    });
    d.showModal();
  }

  // ---- the slideshow, for the TV -------------------------------------------------------------------------------------
  const SPEEDS = [['Calm', 9], ['Gentle', 6], ['Quick', 4]];
  function slideshow(items, title) {
    items = (items || []).filter(i => i && i.src);
    if (!items.length) return toast('There are no photos to play yet.');
    const box = el('div', 'bd-show');
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', title || 'Slideshow'); box.tabIndex = -1;
    box.innerHTML = `<div class="bd-badge">Bapa's Diary${title ? ' · ' + esc(title) : ''}</div><div class="bd-slides"></div>
      <div class="bd-words" aria-live="polite"><span class="bd-k"></span><span class="bd-d"></span><span class="bd-p"></span><span class="bd-c"></span></div>
      <div class="bd-bar"><button type="button" data-s="prev">‹ Back</button><button type="button" data-s="play">Pause</button><button type="button" data-s="next">Next ›</button>
      <button type="button" data-s="speed">Calm · 9 s</button><span class="bd-grow"><i></i></span><span class="bd-n"></span>
      <button type="button" data-s="full">Full screen</button><button type="button" data-s="close">Close</button></div>`;
    document.body.append(box);
    document.documentElement.classList.add('bd-showing');
    const slides = box.querySelector('.bd-slides'), grow = box.querySelector('.bd-grow i'), q = s => box.querySelector(s);
    let i = -1, playing = true, sp = 0, t0 = 0, frozen = 0, wake = 0, lock = null, raf = 0, last = null;
    function slide(k) {
      const s = items[k], d = el('div', 'bd-slide');
      d.innerHTML = `<div class="bd-frame"><div class="bd-in"><img alt="${esc(s.cap || 'Darshan')}" src="${esc(s.src)}"></div></div>`;
      d.querySelector('img').onerror = () => { d.innerHTML = '<div class="bd-soon">Photo coming soon</div>'; };
      return d;
    }
    function show(k) {
      i = (k + items.length) % items.length;
      const s = items[i], d = slide(i), old = last;
      slides.append(d); requestAnimationFrame(() => d.classList.add('on'));
      if (old) { old.classList.remove('on'); setTimeout(() => old.remove(), 1800); }
      last = d;
      const y = +(s.date || '').slice(0, 4);
      q('.bd-k').textContent = !y ? '' : (s.date < '2016-08-13' ? 'Pramukh Swami Maharaj' : 'Mahant Swami Maharaj');
      q('.bd-d').textContent = /^\d{4}-\d\d-\d\d$/.test(s.date || '') ? niceDay(s.date.slice(5)) : (s.date || '');
      q('.bd-p').textContent = [y || '', s.place || ''].filter(Boolean).join(' · ');
      q('.bd-c').textContent = s.cap || '';
      q('.bd-n').textContent = `${i + 1} of ${items.length}`;
      const n = items[(i + 1) % items.length]; if (n) new Image().src = n.src;   // the next photo is ready in time
      t0 = performance.now(); frozen = 0;
    }
    function tick(now) {
      const dur = SPEEDS[sp][1] * 1000;
      if (playing) { const f = Math.min(1, (now - t0) / dur); grow.style.width = f * 100 + '%'; if (f >= 1) show(i + 1); }
      else t0 = now - frozen * dur;
      raf = requestAnimationFrame(tick);
    }
    function poke() { box.classList.add('awake'); clearTimeout(wake); wake = setTimeout(() => box.classList.remove('awake'), 2600); }
    function toggle() {
      playing = !playing; frozen = parseFloat(grow.style.width || 0) / 100;
      q('[data-s=play]').textContent = playing ? 'Pause' : 'Play'; box.classList.toggle('paused', !playing); poke();
    }
    async function full() {
      try { document.fullscreenElement ? await document.exitFullscreen() : await box.requestFullscreen(); } catch (e) {}
      try { lock = lock || await navigator.wakeLock.request('screen'); } catch (e) {}   // keeps the TV awake
    }
    function close() {
      cancelAnimationFrame(raf); clearTimeout(wake);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      try { lock && lock.release(); } catch (e) {}
      box.remove(); document.documentElement.classList.remove('bd-showing');
    }
    box.addEventListener('click', e => {
      const b = e.target.closest('[data-s]'); poke(); if (!b) return;
      ({ prev: () => show(i - 1), next: () => show(i + 1), play: toggle, full, close,
         speed: () => { sp = (sp + 1) % SPEEDS.length; b.textContent = SPEEDS[sp][0] + ' · ' + SPEEDS[sp][1] + ' s'; } })[b.dataset.s]();
    });
    box.addEventListener('mousemove', poke);
    box.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight') show(i + 1); else if (e.key === 'ArrowLeft') show(i - 1);
      else if (e.key === 'Escape' && !document.fullscreenElement) close();
      else if ((e.key === ' ' || e.key === 'Enter') && !e.target.closest('button')) { e.preventDefault(); toggle(); }
      poke();
    });
    let sx = null;
    box.addEventListener('touchstart', e => { sx = e.touches[0].clientX; poke(); }, { passive: true });
    box.addEventListener('touchend', e => { if (sx === null) return; const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) show(i + (dx < 0 ? 1 : -1)); sx = null; });
    show(0); poke(); box.focus(); raf = requestAnimationFrame(tick);
    full();
  }
  const photoOf = f => ({ src: `${PHOTOS}m/${f.k}`, date: f.d, place: f.p, cap: f.c });

  // ---- clicks anywhere on the site -----------------------------------------------------------------------------------
  document.addEventListener('click', e => {
    const h = e.target.closest('[data-fav]');
    if (h) { e.preventDefault(); e.stopPropagation(); fav.toggle({ k: h.dataset.fav, d: h.dataset.date, p: h.dataset.place, c: h.dataset.cap }); return; }
    const s = e.target.closest('[data-share-day]');
    if (s) { e.preventDefault(); e.stopPropagation(); shareDay(s.dataset.shareDay || todayOnPage()); }
  }, true);
  addEventListener('storage', e => { if (e.key === KEY) sync(); });

  // ---- the Search page: a heart on every photo, share on every date, Heart / Share / See the day in the big view --
  const dates = new Map();   // ALBUM/FILE -> its date, place and caption, as the search shows them
  function onSearch() {
    const results = document.getElementById('results'), big = document.getElementById('big');
    if (!results) return;
    const top = document.querySelector('header.top');
    if (top && !top.querySelector('.bd-favlink')) { const a = el('a', 'bd-favlink', HEART + '<span>My favourites</span>'); a.href = '/favourites/'; top.append(a); }
    const status = document.querySelector('.status');
    let searchHits = null;
    try { searchHits = () => hits; searchHits(); } catch (e) { searchHits = null; }   // the search page's own results (a top level let)
    if (status && searchHits) {
      const b = el('button', 'bd-play', PLAY + '<span>Play these as a slideshow</span>'); b.type = 'button';
      b.onclick = () => {
        slideshow(searchHits().filter(p => p.kind === 'photo').slice(0, 600).map(p => ({ src: `${PHOTOS}m/${p.g[3]}/${p.file}`, date: p.d, place: (p.g[2] || '').split(',')[0], cap: p.cap })), 'Search');
      };
      status.after(b);
    }
    const decorate = () => {
      let day = '';
      results.querySelectorAll('.day-head, article.card').forEach(n => {
        if (n.classList.contains('day-head')) {
          const w = n.querySelector('.when'); day = w ? w.dataset.day || '' : '';
          if (/^\d{4}-\d\d-\d\d$/.test(day) && !n.querySelector('.bd-share')) {
            const b = el('button', 'bd-share', SHARE + '<span>Share this day</span>'); b.type = 'button'; b.dataset.shareDay = day.slice(5); n.append(b);
          }
          return;
        }
        if (n.querySelector('.bd-heart')) return;
        const img = n.querySelector('.pic img'), k = img && keyOf(img.getAttribute('src'));
        if (!k) return;
        const item = { k, d: day, p: ((n.querySelector('.place') || {}).textContent || '').split(',')[0].trim(), c: ((n.querySelector('.cap:not(.empty)') || {}).textContent || '').trim() };
        dates.set(k, item);
        n.querySelector('.pic').append(heart(item));
      });
      sync();
    };
    new MutationObserver(decorate).observe(results, { childList: true, subtree: true });
    decorate();
    if (big) new MutationObserver(() => {
      const info = document.getElementById('big-info'), img = document.querySelector('#big-pic img');
      if (!info || info.querySelector('.bd-acts')) return;
      const k = img && keyOf(img.getAttribute('src')), item = k && (dates.get(k) || { k });
      const acts = el('div', 'bd-acts');
      if (item) acts.append(heart(item, true));
      const d = item && item.d;
      if (d && /^\d{4}-\d\d-\d\d$/.test(d)) {
        const s = el('button', 'bd-pill', SHARE + '<span>Share the day</span>'); s.type = 'button'; s.dataset.shareDay = d.slice(5); acts.append(s);
      }
      info.append(acts); sync();
    }).observe(big, { childList: true, subtree: true });
  }

  // ---- the Today page: Share this day beside Slideshow, a heart in the photo view ----------------------------------
  function todayOnPage() {
    const h = location.hash.slice(1);
    if (/^\d\d-\d\d$/.test(h)) return h;
    const n = new Date(); return pad(n.getMonth() + 1) + '-' + pad(n.getDate());
  }
  function onToday() {
    const controls = document.getElementById('controls'), stage = document.getElementById('vstage');
    if (!controls || !stage) return;
    const s = el('button', 'pill bd-today-share', 'Share this day'); s.type = 'button'; s.dataset.shareDay = '';
    const f = el('a', 'pill', 'My favourites'); f.href = '/favourites/';
    controls.append(s, f);
    const nav = document.querySelector('.vnav');
    new MutationObserver(() => {
      const img = stage.querySelector('img'), k = img && keyOf(img.getAttribute('src'));
      const old = nav && nav.querySelector('.bd-heart'); if (old) old.remove();
      if (!k || !nav) return;
      const line = ((stage.querySelector('figcaption div') || {}).textContent || '').split(' · ');
      const y = (/\b(19|20)\d\d\b/.exec(line[0] || '') || [''])[0];
      const item = { k, d: y ? `${y}-${todayOnPage()}` : '', p: (line[1] || '').split(',')[0], c: ((stage.querySelector('figcaption p') || {}).textContent || '') };
      nav.prepend(heart(item, true)); sync();
    }).observe(stage, { childList: true });
  }

  // ---- text size, for older family members (Darpan typed yes, 24 Oct 2026) -------------------------------------------
  // The whole page grows together (CSS zoom on the page). tools/web_extras.py also puts a one line script in the head
  // that sets the size before the page is drawn, so it never jumps.
  const SIZE = 'bapas-diary-text', SIZES = [['Normal', 1, 18], ['Large', 1.3, 24], ['Larger', 1.6, 30]];
  const getSize = () => { try { return +localStorage.getItem(SIZE) || 1; } catch (e) { return 1; } };
  function setSize(z) {
    try { z === 1 ? localStorage.removeItem(SIZE) : localStorage.setItem(SIZE, z); } catch (e) {}
    document.documentElement.style.zoom = z === 1 ? '' : z;
    document.documentElement.style.setProperty('--bd-zoom', z);
  }
  function textSize() {
    const nav = document.querySelector('nav.site-menu');
    if (!nav || nav.querySelector('.bd-aa')) return;
    const b = el('button', 'bd-aa', 'A<b>A</b>'); b.type = 'button'; b.setAttribute('aria-label', 'Text size'); b.setAttribute('aria-haspopup', 'dialog');
    // on phones the menu is the tab bar at the bottom, so the Aa goes in the top strip beside the other round buttons
    // (in the tab bar it made a sixth tab and pushed About and Search wider than the screen)
    const narrow = matchMedia('(max-width: 760px)');
    const place = () => {
      if (!narrow.matches) { if (b.parentNode !== nav) nav.append(b); return; }
      const top = document.querySelector('.ph-top');
      if (!top) return;   // not drawn yet: never put it in the tab bar, not even for a moment
      const next = top.querySelector('.bd-off-right, .ph-about');
      next ? next.before(b) : top.append(b);
    };
    place(); setTimeout(place, 0); setTimeout(place, 300); setTimeout(place, 1000);
    narrow.addEventListener && narrow.addEventListener('change', place);
    b.addEventListener('click', e => {
      e.preventDefault();
      const d = el('dialog', 'bd-sheet bd-size');
      d.setAttribute('aria-label', 'Text size');
      const now = getSize();
      d.innerHTML = '<div class="bd-h">Text size</div><div class="bd-row">' +
        SIZES.map(([name, z, px]) => `<button type="button" data-z="${z}" aria-pressed="${z === now}"><b style="font-size:${px}px">A</b>${name}</button>`).join('') +
        '</div><button type="button" class="bd-x" data-z="0">Done</button>';
      document.body.append(d);
      d.addEventListener('close', () => d.remove());
      d.addEventListener('click', ev => {
        if (ev.target === d) return d.close();
        const c = ev.target.closest('[data-z]'); if (!c) return;
        if (+c.dataset.z) { setSize(+c.dataset.z); d.querySelectorAll('[data-z]').forEach(x => x.setAttribute('aria-pressed', x === c)); } else d.close();
      });
      d.showModal();
    });
  }
  document.documentElement.style.setProperty('--bd-zoom', getSize());

  // Windows has no flag pictures in its emoji, so a flag shows as two letters (GB, US, IN). On Windows only, flags are
  // drawn with the free Twemoji Country Flags font (it holds nothing but flags, so all other text stays as it is).
  if (/Windows/.test(navigator.userAgent)) {
    const css = document.createElement('style');
    css.textContent = "@font-face { font-family: 'Bd Flags'; unicode-range: U+1F1E6-1F1FF, U+1F3F4, U+E0062-E007F; font-display: swap;" +
      " src: url('https://cdn.jsdelivr.net/npm/country-flag-emoji-polyfill@0.1.8/dist/TwemojiCountryFlags.woff2') format('woff2'); }" +
      " .bd-flag { font-family: 'Bd Flags', 'Segoe UI Emoji', sans-serif; font-style: normal; }";
    document.head.append(css);
    const FLAG = /(?:[\u{1F1E6}-\u{1F1FF}]{2})+/u;
    const wrap = root => {
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: n => FLAG.test(n.data) && !(n.parentNode.closest && n.parentNode.closest('.bd-flag, script, style, textarea, input')) ? 1 : 2 });
      const hits = []; while (w.nextNode()) hits.push(w.currentNode);
      for (const n of hits) {
        const f = document.createDocumentFragment();
        n.data.split(/((?:[\u{1F1E6}-\u{1F1FF}]{2})+)/u).forEach((t, i) => { if (!t) return; if (i % 2) { const s = document.createElement('span'); s.className = 'bd-flag'; s.textContent = t; f.append(s); } else f.append(t); });
        n.replaceWith(f);
      }
    };
    const go = () => { wrap(document.body); new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(x => x.nodeType === 1 ? wrap(x) : x.nodeType === 3 && x.parentNode && wrap(x.parentNode)))).observe(document.body, { childList: true, subtree: true }); };
    document.body ? go() : document.addEventListener('DOMContentLoaded', go);
  }

  window.BapaDiary = { fav, shareDay, slideshow, photoOf, toast, niceDate, PHOTOS };
  const ready = () => {
    const path = location.pathname;
    textSize();
    if (path.startsWith('/search')) onSearch();
    else if (path === '/' || path === '/index.html') onToday();
    sync();
  };
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', ready) : ready();
})();
