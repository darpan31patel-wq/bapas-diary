// Darshan Screensaver photo keeper.
// Each darshan photo is saved on the Mac after its first download (index.html saves only
// photos that loaded properly), and from then on it is shown straight from the Mac,
// with no waiting for the internet. Anything not saved yet simply comes from the mandir.
// On This Day photos (baps.org, or Bapa's Diary's copy on photos.bapas-diary.com) are saved here the first time they show, so the day's
// photos are downloaded once rather than every time round. The newest MEMORY_KEEP are kept.
// Bapa's Diary (29 Oct 2026): the darshan photos are the website's own copy on photos.bapas-diary.com/darshan/.
const PHOTO_CACHE = 'darshan-photos-v1';
const MEMORY_CACHE = 'on-this-day-photos-v1';
const MEMORY_KEEP = 120;  // about three days of On This Day photos
// Offline copy (21 Oct 2026: keep working if Cloudflare or the internet goes down).
// The page itself, its fonts and its lists are still fetched fresh every time, exactly as before,
// and a copy of each is kept on the Mac. Only when the internet doesn't answer is the kept copy shown.
const SITE_CACHE = 'darshan-site-v1';
const SITE_KEEP = 80;    // the page, fonts and lists
const WAIT_MS = 6000;     // how long to wait for the internet before using the kept copy

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  if (req.url.startsWith('https://photos.bapas-diary.com/darshan/') && req.destination === 'image') {   // Bapa's Diary's own copy of the mandir's photos
    e.respondWith(
      caches.open(PHOTO_CACHE)
        .then(cache => cache.match(req.url))
        .then(async hit => hit || fetch(req))
        .catch(() => fetch(req))
    );
  } else if ((req.url.startsWith('https://www.baps.org/Data/Sites/1/Media/') || req.url.startsWith('https://photos.bapas-diary.com/'))
             && req.mode === 'no-cors') {
    e.respondWith(keepMemory(req));
  } else if (req.url.startsWith(self.registration.scope) && !/[?&]v=\d/.test(req.url)
             && !req.url.includes('/backup/') && !req.url.includes('/changes')
             && req.destination !== 'image') {
    // (the self update check, ?v=, always goes straight to the internet; other photos have their own keepers)
    e.respondWith(freshOrKept(req));
  }
});

// The fresh copy from the internet when it answers; the copy kept on the Mac when it doesn't
async function freshOrKept(req) {
  let cache = null;
  try { cache = await caches.open(SITE_CACHE); } catch (e) {}
  const fresh = fetch(req).then(res => {
    if (res.ok && res.type === 'basic' && cache) cache.put(req.url, res.clone()).then(() => trim(cache)).catch(() => {});
    return res;
  });
  fresh.catch(() => {});
  const kept = () => cache ? cache.match(req.url).catch(() => null) : null;
  try {
    const res = await Promise.race([fresh, new Promise((_, no) => setTimeout(no, WAIT_MS))]);
    if (res.status < 500) return res;
    return (await kept()) || res;            // Cloudflare having a problem
  } catch (e) {
    return (await kept()) || fresh;          // no internet, or too slow
  }
}

async function trim(cache) {
  const keys = await cache.keys();   // oldest first; the page itself is saved again on every visit
  for (const k of keys.slice(0, Math.max(0, keys.length - SITE_KEEP))) await cache.delete(k);
}

async function keepMemory(req) {
  let cache = null;
  try {
    cache = await caches.open(MEMORY_CACHE);
    const hit = await cache.match(req.url);
    if (hit) return hit;
  } catch (e) {}
  const res = await fetch(req);
  // A photo that fails to show is taken out again by index.html
  if (cache && (res.ok || res.type === 'opaque')) {
    cache.put(req.url, res.clone()).then(() => tidy(cache)).catch(() => {});
  }
  return res;
}

async function tidy(cache) {
  const keys = await cache.keys();   // oldest first
  for (const k of keys.slice(0, Math.max(0, keys.length - MEMORY_KEEP))) await cache.delete(k);
}
