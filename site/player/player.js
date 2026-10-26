// The full screen player for the Today page of bapas-diary.com, for a TV in a mandir room or at home (Darpan, 26 Oct 2026:
// "Darshan of the moment: a gentle full screen mode for a TV, slowly showing today's photos. Just a full screen player").
// Website only: nothing here touches the daily 2pm picture. tools/web_player.py adds this file and player.css to the
// Today page. The Today page's Slideshow button becomes "Full screen", and bapas-diary.com/?play opens straight into it,
// so a TV can keep it as its home page. It plays the day's own photos of Bapa (the site's Bapa only data), one year after
// another, slowly fading from one to the next, and on a day shown as today it moves on to the new day at midnight.
(function () {
  'use strict';
  if (typeof SRC === 'undefined' || !document.getElementById('controls')) return;   // only on the Today page
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const SPEEDS = [['Calm', 20], ['Gentle', 12], ['Quick', 7]];
  const KEY = 'bapas-diary-player-speed';
  const ART = window.BAPA_PLAYER_ART || '/player/';
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const pad2 = n => String(n).padStart(2, '0');
  const today = () => { const n = new Date(); return pad2(n.getMonth() + 1) + '-' + pad2(n.getDate()); };
  const dayName = m => `${+m.slice(3)} ${MONTHS[+m.slice(0, 2) - 1]}`;
  const txt = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // the day's photos, one year after another: 1999, 2000, ... then each year's second photo, and so on. A year with no
  // photo on the day itself uses the photos of its trip around the day, as the cards do.
  function order(D) {
    const years = D.years.map(Y => ({ Y, list: Y.p.length ? Y.p : (Y.t || []) })).filter(x => x.list.length).sort((a, b) => a.Y.y - b.Y.y);
    const out = [];
    for (let k = 0; years.some(x => x.list[k]); k++)
      years.forEach(({ Y, list }) => { const p = list[k]; if (p) out.push({ p, y: Y.y, where: Y.place, cal: D.cal && D.cal[Y.y], trip: !Y.p.length && Y.trip }); });
    return out;
  }

  function player(mmdd, begin) {
    if (document.querySelector('.pl-show')) return;
    const follow = mmdd === today();   // a day shown as today moves on with the calendar
    const box = document.createElement('div');
    box.className = 'pl-show'; box.tabIndex = -1;
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true'); box.setAttribute('aria-label', 'Full screen darshan');
    const both = `<span class="pl-gurus"><img src="${ART}psm.jpg" alt="Pramukh Swami Maharaj"><img src="${ART}msm.jpg" alt="Mahant Swami Maharaj"></span>`;
    box.innerHTML = `<div class="pl-slides"></div>
      <div class="pl-badge">${both}<span><b>Bapa's Diary</b><i class="pl-day"></i></span></div>
      <div class="pl-words" aria-live="polite"></div>
      <div class="pl-bar"><button type="button" data-a="prev" aria-label="Back">‹</button><button type="button" data-a="play">Pause</button>
        <button type="button" data-a="next" aria-label="Next">›</button><button type="button" data-a="speed"></button>
        <span class="pl-grow"><i></i></span><button type="button" data-a="close">Close</button></div>
      <div class="pl-start" hidden>${both}<h2>Today's darshan</h2><p class="pl-day"></p>
        <button type="button" data-a="begin">Begin 🙏🏽</button><small>Photos of Bapa from this day, through the years</small></div>`;
    document.body.append(box);
    document.documentElement.classList.add('pl-showing');
    const $ = s => box.querySelector(s), slides = $('.pl-slides'), grow = $('.pl-grow i');
    let D = null, list = [], i = -1, playing = true, sp = 0, t0 = 0, held = 0, raf = 0, wake = 0, lock = null, last = null, busy = false, day = mmdd;
    try { const s = +localStorage.getItem(KEY); if (SPEEDS[s]) sp = s; } catch (e) {}
    const speedText = () => { $('[data-a=speed]').textContent = `${SPEEDS[sp][0]} · ${SPEEDS[sp][1]} s`; };
    speedText();

    const label = m => box.querySelectorAll('.pl-day').forEach(e => e.textContent = (m === today() ? 'Today, ' : '') + dayName(m));
    label(mmdd);
    if (mmdd !== today()) $('.pl-start h2').textContent = 'Darshan of the day';
    async function load(m) {
      day = m; label(m);
      try { D = await SRC.day(m); } catch (e) { D = null; }
      list = D ? order(D) : [];
      if (!list.length) { slides.innerHTML = '<div class="pl-none">The photos of this day are not ready yet.</div>'; return false; }
      return true;
    }
    // each photo fills the screen as far as it can, never cut; the space around it shows the same photo, soft and dark
    function slide(k) {
      return new Promise(done => {
        const it = list[k], url = SRC.big(it.p) || SRC.photo(it.p), d = document.createElement('div');
        d.className = 'pl-slide';
        const f = it.p[4], at = f ? `${(f[0] * 100).toFixed(0)}% ${(f[1] * 100).toFixed(0)}%` : '50% 35%';   // drift towards his face
        d.innerHTML = `<img class="pl-bg" alt="" aria-hidden="true"><div class="pl-drift" style="transform-origin:${at}"><img class="pl-im" alt="${txt(it.p[2] || 'Darshan')}"></div>`;
        const im = d.querySelector('.pl-im'), bg = d.querySelector('.pl-bg');
        let over = false;
        const end = ok => { if (over) return; over = true; clearTimeout(slow); done(ok ? d : null); };
        const slow = setTimeout(() => end(false), 15000);
        im.onload = () => { bg.src = url; end(true); };
        im.onerror = () => end(false);
        im.src = url;
      });
    }
    async function show(k, dir = 1) {
      if (busy || !list.length) return;
      busy = true;
      let d = null;
      while (!d && list.length && box.isConnected) {   // a photo not on the website yet is left out
        k = (k + list.length) % list.length;
        d = await slide(k);
        if (!d) { list.splice(k, 1); if (k < i) i--; if (dir < 0) k--; }
      }
      busy = false;
      if (!list.length) slides.innerHTML = '<div class="pl-none">The photos of this day are not ready yet.</div>';
      if (!d || !box.isConnected) return;
      i = k;
      const it = list[i], old = last;
      d.style.setProperty('--pl-time', SPEEDS[sp][1] + 4 + 's');
      slides.append(d); last = d;
      requestAnimationFrame(() => requestAnimationFrame(() => d.classList.add('on')));
      if (old) { old.classList.remove('on'); setTimeout(() => old.remove(), 3200); }
      const words = $('.pl-words');
      words.classList.remove('on');
      setTimeout(() => {
        // one centred line across the whole screen: the year, the place, the Indian date and what Bapa does (the day is in the corner)
        // (Darpan, 26 Oct 2026: "center all the text ... in one line you can get year, location, caption")
        const fest = it.cal ? (it.cal[1] || '').split(/;\s*/)[0] : '';
        const parts = [it.where, it.trip && 'From the same trip', it.cal && it.cal[0], fest].filter(Boolean).map(t => `<span>${txt(t)}</span>`);
        const cap = it.p[5] || it.p[2] || '';
        if (cap) parts.push(`<i>${txt(cap)}</i>`);
        words.innerHTML = `<b>${it.y}</b>` + parts.join('');
        words.classList.add('on');
      }, old ? 1200 : 0);
      t0 = performance.now(); held = 0;
    }
    function tick(now) {
      const dur = SPEEDS[sp][1] * 1000;
      if (playing && !busy && list.length) {
        const f = Math.min(1, (now - t0) / dur);
        grow.style.width = f * 100 + '%';
        if (f >= 1) {
          if (follow && day !== today()) load(today()).then(ok => ok && show(0));   // midnight: the new day begins
          else show(i + 1);
        }
      } else if (!playing) t0 = now - held * dur;
      raf = requestAnimationFrame(tick);
    }
    function poke() { box.classList.add('awake'); clearTimeout(wake); wake = setTimeout(() => box.classList.remove('awake'), 3000); }
    function toggle() {
      playing = !playing; held = parseFloat(grow.style.width || 0) / 100;
      $('[data-a=play]').textContent = playing ? 'Pause' : 'Play';
      box.classList.toggle('paused', !playing); poke();
    }
    async function keepAwake() { try { if (!lock || lock.released) lock = await navigator.wakeLock.request('screen'); } catch (e) {} }   // the TV stays on
    async function full() {
      try { if (!document.fullscreenElement && box.requestFullscreen) await box.requestFullscreen({ navigationUI: 'hide' }); } catch (e) {}
      keepAwake();
    }
    const vis = () => { if (!document.hidden) keepAwake(); };
    document.addEventListener('visibilitychange', vis);
    function close() {
      cancelAnimationFrame(raf); clearTimeout(wake);
      document.removeEventListener('visibilitychange', vis);
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
      try { lock && lock.release(); } catch (e) {}
      box.remove(); document.documentElement.classList.remove('pl-showing');
      if (/[?&]play\b/.test(location.search)) history.replaceState(null, '', location.pathname + location.hash);
      const b = document.getElementById('slideshow'); b && b.focus();
    }
    async function go() {
      $('.pl-start').hidden = true; box.classList.remove('waiting');
      full(); box.focus(); poke();
      if (await load(day)) { show(0); raf = requestAnimationFrame(tick); }
    }
    const acts = {
      prev: () => show(i - 1, -1), next: () => show(i + 1), play: toggle, close, begin: go,
      speed: () => { sp = (sp + 1) % SPEEDS.length; speedText(); try { localStorage.setItem(KEY, sp); } catch (e) {} },
    };
    box.addEventListener('click', e => { const b = e.target.closest('[data-a]'); poke(); if (b) acts[b.dataset.a](); });
    box.addEventListener('mousemove', poke);
    box.addEventListener('keydown', e => {   // a TV remote's arrows, OK and Back work too
      if (!$('.pl-start').hidden) { if (e.key === 'Escape' || e.key === 'GoBack' || e.key === 'BrowserBack') close(); return; }
      const onButton = e.target.closest && e.target.closest('button');
      if (e.key === 'ArrowRight') show(i + 1);
      else if (e.key === 'ArrowLeft') show(i - 1, -1);
      else if ((e.key === ' ' || e.key === 'Enter') && !onButton) { e.preventDefault(); toggle(); }
      else if (e.key === 'Escape' || e.key === 'GoBack' || e.key === 'BrowserBack' || e.key === 'Backspace') { if (!document.fullscreenElement || e.key !== 'Escape') { e.preventDefault(); close(); } }
      else if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); $('[data-a=play]').focus(); }
      poke();
    });
    let sx = null;
    box.addEventListener('touchstart', e => { sx = e.touches[0].clientX; poke(); }, { passive: true });
    box.addEventListener('touchend', e => { if (sx === null) return; const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 50) dx < 0 ? show(i + 1) : show(i - 1, -1); sx = null; });
    if (begin) go();
    else { box.classList.add('waiting'); $('.pl-start').hidden = false; box.focus(); $('[data-a=begin]').focus(); }   // a browser only goes full screen after a tap
  }

  // the Today page's Slideshow button opens the player for the day on the page
  const b = document.getElementById('slideshow');
  if (b) {
    b.textContent = 'Full screen';
    b.classList.add('pl-open');
    b.onclick = () => player(typeof showing === 'string' && showing ? showing : today(), true);
  }
  window.BapaPlayer = player;
  if (/[?&]play\b/.test(location.search)) player(/^#\d\d-\d\d$/.test(location.hash) ? location.hash.slice(1) : today(), false);
})();
