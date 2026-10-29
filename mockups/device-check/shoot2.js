// Website only, read only: second look. Why some pages fail in the Chrome engine, the Calendar day box on phones and
// tablets, a tapped Today photo, and the smallest phones. Never deploys, never touches the daily 2pm picture.
const { webkit, chromium, devices } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2] || 'shots2';
const SITE = 'https://bapas-diary.com';
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = {};
const jpg = (page, f, full) => page.screenshot({ path: `${OUT}/${f}.jpg`, type: 'jpeg', quality: 60, fullPage: !!full });
function watch(page, k) {
  const r = log[k] = log[k] || [];
  page.on('pageerror', e => r.push('pageerror: ' + e.message.slice(0, 200)));
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') r.push(m.type() + ': ' + m.text().slice(0, 200)); });
  page.on('requestfailed', q => r.push('failed ' + q.url().slice(0, 120) + ' ' + (q.failure() || {}).errorText));
  page.on('response', res => { if (res.status() >= 400) r.push(res.status() + ' ' + res.url().slice(0, 120)); });
}

(async () => {
  // A. the Chrome engine: straight answers from the site, then with and without the offline helper (service worker)
  const cb = await chromium.launch();
  const plain = await cb.newContext({ ...devices['Pixel 7'] });
  for (const u of ['/year/2025/', '/year/', '/search/data/about.json', '/search/data/2010.json', '/then-and-now/more.json', '/sw.js', '/search/']) {
    try { const res = await plain.request.get(SITE + u, { maxRedirects: 0 }); const b = await res.body();
      log['A-headers ' + u] = [res.status(), b.length, JSON.stringify(res.headers())]; } catch (e) { log['A-headers ' + u] = [String(e).slice(0, 200)]; }
  }
  for (const sw of ['block', 'allow']) {
    const ctx = await cb.newContext({ ...devices['Pixel 7'], serviceWorkers: sw });
    ctx.on('serviceworker', w => { (log['A-sw-' + sw] = log['A-sw-' + sw] || []).push('sw started ' + w.url()); });
    for (const [n, u] of [['today', '/'], ['search', '/search/#q=annakut&place=London'], ['year', '/year/2025/'], ['legacy', '/then-and-now/'], ['about', '/about/']]) {
      const page = await ctx.newPage(); const k = `A-${sw}-${n}`; watch(page, k);
      try { await page.goto(SITE + u, { waitUntil: 'load', timeout: 45000 }); await sleep(6000);
        log[k].push('estimate ' + JSON.stringify(await page.evaluate(() => navigator.storage && navigator.storage.estimate())));
        log[k].push('sw controller ' + await page.evaluate(() => !!(navigator.serviceWorker && navigator.serviceWorker.controller)));
        log[k].push('text ' + (await page.evaluate(() => document.body.innerText)).slice(0, 400).replace(/\s+/g, ' '));
        await jpg(page, k);
      } catch (e) { log[k].push('open: ' + e.message.slice(0, 200)); }
      await page.close(); await sleep(1500);
    }
    await ctx.close();
  }
  await cb.close();

  // B. Calendar day box, Today photo tapped, and the smallest phones
  const runs = [['iphone-14', webkit, devices['iPhone 14']], ['ipad-portrait', webkit, devices['iPad (gen 7)']], ['ipad-landscape', webkit, devices['iPad (gen 7) landscape']], ['pixel-7', chromium, devices['Pixel 7']], ['iphone-se1-320', webkit, devices['iPhone SE']]];
  for (const [name, eng, dev] of runs) {
    const b = await eng.launch(); const ctx = await b.newContext({ ...dev, locale: 'en-GB', timezoneId: 'Europe/London', serviceWorkers: 'block' });
    let page = await ctx.newPage(); watch(page, 'B-' + name);
    try {
      await page.goto(SITE + '/calendar/', { waitUntil: 'load', timeout: 45000 }); await sleep(4000);
      const phone = await page.$('.ph-day');
      if (phone) {
        const cells = await page.$$('.ph-day');
        let target = null;
        for (const c of cells) { const t = await c.evaluate(e => e.textContent.trim() + '|' + (e.style.backgroundImage || e.querySelector('img') ? 'p' : '')); if (/^27\|p/.test(t) || /^27/.test(t)) { const box = await c.boundingBox(); if (box && box.y > 0 && box.y < dev.viewport.height) { target = c; } } }
        target = target || cells[0];
        await target.click(); await sleep(2000); await jpg(page, `B-${name}-cal-tap`);
        const card = await page.$('.ph-card:not([hidden])'); if (card) { await card.click(); await sleep(3500); }
      } else {
        const a = await page.evaluateHandle(() => [...document.querySelectorAll('a[href]')].find(a => /2026-10-27/.test(a.getAttribute('href'))));
        if (a.asElement()) { await a.asElement().scrollIntoViewIfNeeded(); await a.asElement().click(); await sleep(3500); }
      }
      await jpg(page, `B-${name}-daybox`);
      for (let i = 1; i <= 3; i++) {
        await page.evaluate(i => { const b = [...document.querySelectorAll('*')].filter(e => { const s = getComputedStyle(e); return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 50 && e.getBoundingClientRect().height > 200; }).pop(); if (b) b.scrollTop = b.clientHeight * 0.85 * i; else scrollTo(0, innerHeight * 0.85 * i); }, i);
        await sleep(1500); await jpg(page, `B-${name}-daybox-${i}`);
      }
      log['B-' + name + '-daybox-text'] = [(await page.evaluate(() => document.body.innerText)).slice(0, 5000)];
    } catch (e) { log['B-' + name].push('calendar: ' + e.message.slice(0, 200)); }
    try {
      await page.goto(SITE + '/', { waitUntil: 'load', timeout: 45000 }); await sleep(4000);
      const pt = await page.evaluate(() => { const im = [...document.images].find(i => i.naturalWidth > 100 && i.getBoundingClientRect().top > 200 && !i.closest('header,nav,.bd-now,.ss-launch')); if (!im) return null; im.scrollIntoView({ block: 'center' }); const r = im.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, src: im.currentSrc }; });
      await sleep(800);
      if (pt) { const r = await page.evaluate(() => { const im = [...document.images].find(i => i.naturalWidth > 100 && i.getBoundingClientRect().top > 0 && !i.closest('header,nav,.bd-now,.ss-launch')); const b = im.getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; });
        await page.mouse.click(r.x, r.y); await sleep(3000); await jpg(page, `B-${name}-today-photo`); }
      for (const [n, u] of [['today', '/'], ['search', '/search/#q=annakut&place=London'], ['travels', '/travels/'], ['years', '/through-the-years/'], ['year', '/year/2025/'], ['about', '/about/']]) {
        if (name !== 'iphone-se1-320' && n !== 'today') continue;
        await page.goto(SITE + u, { waitUntil: 'load', timeout: 45000 }); await sleep(3500); await jpg(page, `B-${name}-${n}`);
        log[`B-${name}-${n}-width`] = [await page.evaluate(() => [innerWidth, document.documentElement.scrollWidth, [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 2; }).slice(0, 8).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)).join(' ; ')])];
        await sleep(1000);
      }
    } catch (e) { log['B-' + name].push('today: ' + e.message.slice(0, 200)); }
    await b.close();
  }
  fs.writeFileSync(`${OUT}/log.json`, JSON.stringify(log, null, 1));
})();
