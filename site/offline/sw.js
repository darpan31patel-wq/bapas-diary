/* bapas-diary.com with no internet (Darpan, 25 Oct 2026: "save the phone version so it opens even with no internet,
   which is great for travelling"). Website only: nothing here touches the daily 2pm picture.
   tools/web_offline.py fills in VERSION and SHELL at deploy time and puts this file at /sw.js.

     bd-shell-VERSION  every page and what it needs, saved the first time anyone opens the site (about 2 MB)
     bd-site           everything else of the site that has been opened: day lists, search lists, page photos
     bd-photos         photos from photos.bapas-diary.com that have been looked at (the newest PHOTO_MAX kept)
     bd-saved          what "Save for travelling" (offline.js) put away: the next days with their photos

   Pages and lists: the internet first (so nothing is ever out of date), what is saved if there is no answer within
   a few seconds. Photos, fonts and pictures: what is saved first, the internet only for ones never seen before. */
const VERSION = '__VERSION__';
const SHELL = __SHELL__;
const SHELL_CACHE = 'bd-shell-' + VERSION;
const PHOTOS = 'https://photos.bapas-diary.com/';
const PHOTO_MAX = 1500;
const WAIT = 4000;   // ms to wait for the internet before using the saved copy

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(SHELL_CACHE);
    // one by one, so one missing file never stops the rest from being saved
    await Promise.all(SHELL.map(u => fetch(u, {cache: 'no-cache'}).then(async r => r.ok && c.put(u, await clean(r))).catch(() => {})));
    await nextDays(7);
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) if (k.startsWith('bd-shell-') && k !== SHELL_CACHE) await caches.delete(k);
    await self.clients.claim();
  })());
});

// today and the days after it, so the Today page still opens tomorrow with no internet
async function nextDays(n) {
  const c = await caches.open('bd-site'), now = new Date();
  for (let i = 0; i < n; i++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + i);
    const u = '/data/day/' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0') + '.json';
    if (!(await caches.match(u))) await fetch(u).then(r => r.ok && c.put(u, r)).catch(() => {});
  }
}

self.addEventListener('message', e => { if (e.data === 'next-days') e.waitUntil(nextDays(7)); });

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  if (u.origin === location.origin) {
    if (u.pathname === '/sw.js') return;
    if (u.pathname.startsWith('/search/image/')) return;   // Search by photo's 60 MB model and numbers: never kept on the phone (website review, 28 Oct 2026)
    if (r.mode === 'navigate') return e.respondWith(page(r));
    if (/\.(jpe?g|png|webp|gif|svg|woff2?|ttf)$/i.test(u.pathname)) return e.respondWith(savedFirst(r, 'bd-site'));
    return e.respondWith(internetFirst(r, 'bd-site'));
  }
  if (r.url.startsWith(PHOTOS)) return e.respondWith(photo(r));
  if (u.hostname === 'fonts.googleapis.com') return e.respondWith(internetFirst(r, 'bd-site'));
  if (/^(fonts\.gstatic\.com|cdnjs\.cloudflare\.com)$/.test(u.hostname)) return e.respondWith(savedFirst(r, 'bd-site'));
});

// a copy with no "redirected" mark: Safari refuses to show a page whose saved answer came after a redirect
function clean(r) {
  if (!r.redirected) return r;
  return r.blob().then(b => new Response(b, {status: r.status, statusText: r.statusText, headers: r.headers}));
}

// keep a copy, but a copy that cannot be kept (a phone that is nearly full) never stops the page or photo showing
// (phone and tablet check, 29 Oct 2026)
async function keep(name, key, res) {
  try { await (await caches.open(name)).put(key, res.clone()); return true; } catch (x) { return false; }
}

function timeout(p, ms) {
  return new Promise((ok, no) => { const t = setTimeout(() => no(new Error('slow')), ms); p.then(v => { clearTimeout(t); ok(v); }, x => { clearTimeout(t); no(x); }); });
}

async function internetFirst(r, name) {
  const net = fetch(r).then(async res => {
    if (res.ok) await keep(name, r, res);
    return res;
  });
  try { return await timeout(net, WAIT); } catch (x) {
    const saved = await caches.match(r);
    if (saved) { net.catch(() => {}); return saved; }
    return net;   // nothing saved: keep waiting for the internet
  }
}

async function page(r) {
  const net = fetch(r).then(async res => {
    if (res.ok && !res.redirected) await keep('bd-site', r.url.split('#')[0], res);
    return res;
  });
  try { return await timeout(net, WAIT); } catch (x) {
    const u = new URL(r.url), alt = u.pathname.endsWith('/') ? u.pathname : u.pathname + '/';
    const saved = await caches.match(r, {ignoreSearch: true}) || await caches.match(alt, {ignoreSearch: true});
    if (saved) { net.catch(() => {}); return clean(saved); }
    try { return await net; } catch (y) {
      // a page never opened before: the friendly "no internet" page
      return (await caches.match('/offline/')) || new Response('No internet', {status: 503, headers: {'Content-Type': 'text/plain'}});
    }
  }
}

async function savedFirst(r, name) {
  const saved = await caches.match(r);
  if (saved) return saved;
  const res = await fetch(r);
  if (res.ok) keep(name, r, res);
  return res;
}

let corsOk = true;   // photos.bapas-diary.com lets the site keep real copies; if not, the browser's sealed copies
async function photo(r) {
  const saved = await caches.match(r.url);
  if (saved) return saved;
  try {
    let res;
    if (corsOk) res = await fetch(r.url, {mode: 'cors', credentials: 'omit'}).catch(() => null);
    if (!res) {
      res = await fetch(r.url, {mode: 'no-cors', credentials: 'omit'});
      corsOk = false;   // the internet is there but the photos do not allow real copies
    }
    if ((res.ok || res.type === 'opaque') && await keep('bd-photos', r.url, res))
      trim(await caches.open('bd-photos'), res.type === 'opaque' ? 150 : PHOTO_MAX);   // sealed copies take much more room in the browser's count
    return res;
  } catch (x) {
    return blank();
  }
}

let trimming = null;
function trim(c, max) {
  clearTimeout(trimming);
  trimming = setTimeout(async () => {
    const keys = await c.keys();   // oldest first
    for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
  }, 3000);
}

// a photo that was never saved, with no internet: soft paper with a small cloud, instead of a broken picture
function blank() {
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">' +
    '<stop offset="0" stop-color="#f6eedd"/><stop offset="1" stop-color="#e8dcc2"/></linearGradient></defs>' +
    '<rect width="400" height="500" fill="url(#g)"/><g fill="none" stroke="#c9b48a" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M150 290h108a38 38 0 0 0 4-76 58 58 0 0 0-112-12 40 40 0 0 0 0 88z"/><path d="M135 330l130-170"/></g></svg>';
  return new Response(svg, {headers: {'Content-Type': 'image/svg+xml', 'Cache-Control': 'no-store'}});
}
