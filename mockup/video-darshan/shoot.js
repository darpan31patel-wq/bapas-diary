// Mockup shots of the Video Darshan links ON the real bapas-diary.com pages (Darpan, 31 Oct 2026). Never deployed.
// The live pages are loaded as they are; only the pages this change touches are swapped for the live page with the
// change applied (pages/), and /data/videos/ and /data/fest/ come from this build (tools/web_videos.py).
const { chromium } = require('playwright');
const fs = require('fs');
const PAGES = { '/search/': 'pages/search.html', '/photos/': 'pages/photos.html', '/travels/': 'pages/travels.html', '/travels/places/': 'pages/places.html' };
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const b = await chromium.launch();
  fs.mkdirSync('shots', { recursive: true });
  for (const [dev, vp, mobile] of [['computer', { width: 1440, height: 900 }, false], ['phone', { width: 390, height: 844 }, true]]) {
    async function open(path, opts = {}) {
      const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile, serviceWorkers: 'block' });
      await ctx.route('**/*', async r => {
        const u = new URL(r.request().url());
        if (u.hostname !== 'bapas-diary.com') return r.continue();
        if (PAGES[u.pathname] && fs.existsSync(PAGES[u.pathname])) return r.fulfill({ body: fs.readFileSync(PAGES[u.pathname]), contentType: 'text/html; charset=utf-8' });
        let m = u.pathname.match(/^\/data\/videos\/(.+)$/);
        if (m) return fs.existsSync('vids/' + m[1]) ? r.fulfill({ path: 'vids/' + m[1], contentType: 'application/json' }) : r.fulfill({ status: 404, body: '' });
        m = u.pathname.match(/^\/data\/fest\/(.+)$/);
        if (m && fs.existsSync('fest/' + m[1])) return r.fulfill({ path: 'fest/' + m[1], contentType: 'application/json' });
        if (u.pathname === '/api/live' && opts.live) return r.fulfill({ body: JSON.stringify({ live: true, id: 'EeYqMau_lXk', title: 'Live webcast' }), contentType: 'application/json' });
        return r.continue();
      });
      const p = await ctx.newPage();
      if (opts.clock) await p.clock.install({ time: new Date(opts.clock) });
      await p.goto('https://bapas-diary.com' + path, { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log('goto', path, e.message));
      await wait(opts.wait || 3000);
      return p;
    }
    const shot = async (p, name, full) => { await p.screenshot({ path: `shots/${name}-${dev}.jpg`, quality: 82, type: 'jpeg', fullPage: !!full }); console.log('shot', name, dev); };
    const tryit = async (name, f) => { try { await f(); } catch (e) { console.log('FAILED', name, dev, e.message); } };

    await tryit('search', async () => {
      const p = await open('/search/#date=2017-10-19', { wait: 6000 });
      const c = p.locator('[data-i]').filter({ hasText: /Swami|Swamishri/ }); await (await c.count() ? c.nth(1) : p.locator('[data-i]').first()).click(); await wait(3000); await shot(p, '1-search-big-photo');
    });
    await tryit('calendar', async () => {
      const p = await open('/calendar/#2017-10', { wait: 6000 });
      const c = p.locator('a.card[href*="2017-10-19"]');
      if (await c.count()) { await c.first().click(); await wait(5000); } else { await p.goto('https://bapas-diary.com/photos/#date=2017-10-19'); await wait(5000); }
      await shot(p, '2-calendar-day');
    });
    await tryit('photos', async () => { const p = await open('/photos/#date=2025-10-20', { wait: 5000 }); await shot(p, '2b-calendar-day-diwali-2025'); });
    for (const [k, when] of [['diwali', '2026-11-08T09:00:00Z'], ['annakut', '2026-11-10T09:00:00Z']])
      await tryit(k, async () => { const p = await open('/', { clock: when, wait: 8000 }); await shot(p, `3-today-${k}`);
        await p.evaluate(() => { const v = [...document.querySelectorAll('a.vid')].pop(); if (v) v.scrollIntoView({ block: 'center' }); }); await wait(2500); await shot(p, `3-today-${k}-video`); });
    await tryit('travels', async () => { const p = await open('/travels/', { wait: 8000 }); await p.locator('.yr[data-y="2017"]').first().click(); await wait(6000); await shot(p, '4-travels-journey'); });
    await tryit('places', async () => {
      const p = await open('/travels/places/#place=Gondal', { wait: 8000 });
      await p.evaluate(() => { const v = document.querySelector('.vv a'); if (v) v.closest('.visit').scrollIntoView({ block: 'center' }); }); await wait(2000);
      await shot(p, '4b-travels-places-gondal');
    });
    await tryit('latest', async () => { const p = await open('/search/#latest', { wait: 7000 }); await p.evaluate(() => document.getElementById('count').scrollIntoView({ block: 'center' })); await wait(1500); await shot(p, '5-latest-vicharan'); });
    await tryit('latest-live', async () => { const p = await open('/search/#latest', { wait: 7000, live: true }); await p.evaluate(() => document.getElementById('count').scrollIntoView({ block: 'center' })); await wait(1500); await shot(p, '5b-latest-vicharan-with-live-webcast'); });
    for (const e of ['daily', 'email']) await tryit(e, async () => {
      if (!fs.existsSync(`weekly/${e}.html`)) return;
      const ctx = await b.newContext({ viewport: mobile ? vp : { width: 760, height: 1000 }, deviceScaleFactor: mobile ? 2 : 1 });
      const p = await ctx.newPage(); await p.goto('file://' + process.cwd() + `/weekly/${e}.html`); await wait(4000);
      await shot(p, e === 'daily' ? '6-email-8am' : '6b-email-sunday', true);
    });
  }
  await b.close();
})();
