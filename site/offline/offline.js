/* bapas-diary.com with no internet (Darpan, 25 Oct 2026). Goes with offline.css and /sw.js; added to every page by
   tools/web_offline.py at deploy time. Website only: nothing here touches the daily 2pm picture.
     every page   starts the helper (/sw.js) that keeps each page opened on this phone or computer, and shows a
                  small "No internet" note while there is none
     phones       a save button in the top strip, next to About: "Save for travelling" keeps the next 7 days with
                  their photos, all of Search, Travels and Bapa through the years, and tops itself up each day */
(() => {
  if (!('serviceWorker' in navigator) || !window.caches) return;
  navigator.serviceWorker.register('/sw.js').catch(() => {});

  const DAYS = 7, PER_YEAR = 8, SAVED = 'bd-saved';
  const store = {
    get: () => { try { return JSON.parse(localStorage.getItem('bapas-diary-offline')) || null; } catch (e) { return null; } },
    set: v => { try { localStorage.setItem('bapas-diary-offline', JSON.stringify(v)); } catch (e) {} },
  };
  const el = (t, c, h) => { const e = document.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; };
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const pad = n => String(n).padStart(2, '0');
  const DEVICE = /iPad/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1) ? 'iPad' : 'phone';
  const ios = /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const installed = matchMedia('(display-mode: standalone)').matches || navigator.standalone;

  function ready(fn) { document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', fn) : fn(); }

  /* ---------- the "No internet" note ---------- */
  ready(() => {
    const note = el('div', 'bd-off-note', 'No internet, showing what is saved');
    note.setAttribute('role', 'status');
    document.body.append(note);
    const show = () => note.classList.toggle('on', !navigator.onLine);
    addEventListener('online', show); addEventListener('offline', show); show();
  });

  /* ---------- Save for travelling ---------- */
  // what to keep: the build's list (/offline/files.json) plus the next days and the first photos of every year on them
  async function plan() {
    const F = await (await fetch('/offline/files.json')).json();
    const urls = F.pack.slice(), years = new Set(F.photoYears), now = new Date();
    for (let i = 0; i < DAYS; i++) {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
      const u = '/data/day/' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + '.json';
      urls.push(u);
      let D;
      try { D = await (await fetch(u)).json(); } catch (e) { continue; }
      for (const Y of D.years) {
        if (!years.has(Y.y)) continue;
        const p = Y.p.length ? Y.p : Y.t || [];
        const first = Math.max(0, p.findIndex(x => x[3]));   // the card opens on a darshan of Bapa and fades on
        for (let k = 0; k < Math.min(PER_YEAR, p.length); k++) {
          const x = p[(first + k) % p.length];
          urls.push(F.photos + 's/' + x[0] + '/' + x[1]);
        }
      }
    }
    return {urls: [...new Set(urls)], mb: F.packMB};
  }

  async function get(u) {
    if (!/^https?:/.test(u) || u.startsWith(location.origin)) return fetch(u);
    const r = await fetch(u, {mode: 'cors', credentials: 'omit'}).catch(() => null);
    return r || fetch(u, {mode: 'no-cors', credentials: 'omit'});
  }

  let running = null;
  function save(progress, quiet) {
    if (running) return running;
    running = (async () => {
      const {urls} = await plan();
      const c = await caches.open(SAVED), have = new Set((await c.keys()).map(r => r.url));
      const want = new Set(urls.map(u => new URL(u, location.href).href));
      let done = 0, failed = 0, i = 0;
      const work = async () => {
        while (i < urls.length) {
          const u = urls[i++], abs = new URL(u, location.href).href;
          if (!have.has(abs)) {
            try {
              const r = await get(u);
              if (r.ok || r.type === 'opaque') await c.put(abs, r); else failed++;
            } catch (e) { failed++; }
          }
          done++;
          if (progress) progress(done, urls.length);
        }
      };
      await Promise.all(Array.from({length: quiet ? 2 : 5}, work));
      for (const r of await c.keys()) if (!want.has(r.url)) await c.delete(r);   // days that are now in the past
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
      const v = {at: Date.now(), n: urls.length - failed, failed};
      store.set(v);
      return v;
    })().finally(() => { running = null; });
    return running;
  }

  async function removeSaved() {
    await caches.delete(SAVED);
    await caches.delete('bd-photos');
    store.set(null);
  }

  async function used() {
    try { const e = await navigator.storage.estimate(); return Math.round(e.usage / 1048576); } catch (e) { return null; }
  }

  // once saved, it keeps itself up to date: a quiet top up once a day while there is internet
  ready(() => {
    const s = store.get();
    if (s && navigator.onLine && Date.now() - s.at > 20 * 3600e3) setTimeout(() => save(null, true).then(mark, () => {}), 6000);
  });

  /* ---------- the button and the sheet (phones) ---------- */
  const narrow = matchMedia('(max-width: 760px)');
  let btn = null;
  function mark() { if (btn) btn.classList.toggle('saved', !!store.get()); }

  // iPads too (Darpan: go live on ipad fix, 26 Oct 2026): there the button sits in the top right corner beside Aa and the
  // language switch. Computers with a mouse don't get it.
  const tablet = ios || matchMedia('(pointer: coarse) and (hover: none)').matches;
  ready(() => setTimeout(() => {
    const top = narrow.matches ? document.querySelector('.ph-top') : tablet && document.querySelector('nav.site-menu');
    if (!top) return;
    btn = el('button', 'bd-off-btn', '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19h14"/></svg><i></i>');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Save for travelling, to open with no internet');
    if (!narrow.matches) top.append(btn);
    else {
      const right = el('span', 'bd-off-right'), about = top.querySelector('.ph-about');
      if (about) { about.before(right); right.append(btn, about); } else { top.append(right); right.append(btn); }
    }
    btn.onclick = openSheet;
    mark();
  }, 0));

  function when(t) { const d = new Date(t); return d.getDate() + ' ' + MONTHS[d.getMonth()]; }

  async function openSheet() {
    const F = await fetch('/offline/files.json').then(r => r.json()).catch(() => ({packMB: 80}));
    const back = el('div', 'bd-off-back'), sheet = el('div', 'bd-off-sheet');
    sheet.setAttribute('role', 'dialog'); sheet.setAttribute('aria-modal', 'true'); sheet.setAttribute('aria-labelledby', 'bd-off-h');
    sheet.innerHTML = `<div class="bd-off-grip"></div>
      <h2 id="bd-off-h">Save for travelling</h2>
      <p>Every page you open is kept on this ${DEVICE}, so Bapa's Diary opens even with no internet.</p>
      <p>Tap below to also keep the next ${DAYS} days of darshan with their photos, all of Search, Travels and
        Bapa through the years. It needs about ${F.packMB + 10} MB, so WiFi is best.</p>
      <div class="bd-off-state" aria-live="polite"></div>
      <div class="bd-off-bar" hidden><b></b></div>
      <button type="button" class="bd-off-go">Save for travelling</button>
      ${ios && !installed ? `<p class="bd-off-tip">On iPhone and iPad, also add Bapa's Diary to your Home Screen (tap Share, then Add to Home Screen) so the saved pages always stay.</p>` : ''}
      <div class="bd-off-row"><button type="button" class="bd-off-del">Remove saved photos</button><button type="button" class="bd-off-close">Close</button></div>`;
    document.body.append(back, sheet);
    requestAnimationFrame(() => { back.classList.add('on'); sheet.classList.add('on'); });
    const $ = s => sheet.querySelector(s), go = $('.bd-off-go'), state = $('.bd-off-state'), bar = $('.bd-off-bar');
    const close = () => { back.classList.remove('on'); sheet.classList.remove('on'); setTimeout(() => { back.remove(); sheet.remove(); }, 300); btn && btn.focus(); };
    back.onclick = close; $('.bd-off-close').onclick = close;
    sheet.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

    async function show() {
      const s = store.get(), mb = await used();
      $('.bd-off-del').hidden = !s;
      if (s) {
        state.innerHTML = `<b>✓ Saved on this ${DEVICE}</b> on ${when(s.at)}. It tops itself up each day you have internet.` +
          (mb ? ` Using about ${mb} MB.` : '');
        go.textContent = 'Save again now';
      } else {
        state.textContent = '';
        go.textContent = 'Save for travelling';
      }
      go.disabled = !navigator.onLine;
      if (!navigator.onLine) state.textContent = 'No internet right now. Saving starts when you are back online.';
    }
    go.onclick = async () => {
      go.disabled = true; bar.hidden = false; state.textContent = 'Getting ready…';
      try {
        await save((n, all) => {
          state.textContent = `Saving ${n.toLocaleString()} of ${all.toLocaleString()}…`;
          bar.firstChild.style.width = (100 * n / all) + '%';
        });
      } catch (e) {
        state.textContent = 'Saving stopped. Please try again when the internet is good.';
        go.disabled = false; bar.hidden = true; return;
      }
      bar.hidden = true; mark(); show();
    };
    $('.bd-off-del').onclick = async () => { await removeSaved(); mark(); show(); };
    show();
    go.focus();
  }
})();
