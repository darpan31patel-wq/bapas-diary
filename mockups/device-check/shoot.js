// Website only, read only: opens the live bapas-diary.com pages on phone and tablet sizes (Safari engine for Apple,
// Chrome engine for Android) and saves screenshots plus notes (page wider than the screen, broken photos, errors,
// the page words) into the folder given. Never deploys, never touches the daily 2pm picture.
const { webkit, chromium, devices } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2] || 'shots';
const SITE = 'https://bapas-diary.com';
fs.mkdirSync(OUT, { recursive: true });

const D = (name, engine, d, land) => ({ name, engine, d: devices[land ? d + ' landscape' : d] || devices[(land ? d + ' landscape' : d).replace(' (3rd gen)', '')] });
const DEVICES = [
  D('iphone-se', 'webkit', 'iPhone SE (3rd gen)'),
  D('iphone-14', 'webkit', 'iPhone 14'),
  D('iphone-14-pro-max', 'webkit', 'iPhone 14 Pro Max'),
  D('android-pixel-7', 'chromium', 'Pixel 7'),
  D('android-small', 'chromium', 'Galaxy S9+'),
  D('ipad-mini', 'webkit', 'iPad Mini'),
  D('ipad-portrait', 'webkit', 'iPad (gen 7)'),
  D('ipad-landscape', 'webkit', 'iPad (gen 7)', true),
  D('ipad-pro-landscape', 'webkit', 'iPad Pro 11', true),
  D('android-tablet', 'chromium', 'Galaxy Tab S4'),
];
const only = process.env.ONLY ? process.env.ONLY.split(',') : null;
const PAGES = [
  ['today', '/'],
  ['calendar', '/calendar/'],
  ['search', '/search/'],
  ['search-chosen', '/search/#q=annakut&place=London'],
  ['travels', '/travels/'],
  ['places', '/travels/places/'],
  ['years', '/through-the-years/'],
  ['legacy', '/then-and-now/'],
  ['year', '/year/2025/'],
  ['about', '/about/'],
  ['favourites', '/favourites/'],
];
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function measure(page) {
  return page.evaluate(() => {
    const W = innerWidth, out = { W, H: innerHeight, scrollW: document.documentElement.scrollWidth, bodyW: document.body.scrollWidth, scrollH: document.documentElement.scrollHeight };
    const name = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\s+/).slice(0, 3).join('.') : '');
    const vis = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.05; };
    const clipped = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const s = getComputedStyle(p); if (/(hidden|clip|auto|scroll)/.test(s.overflowX)) { const r = p.getBoundingClientRect(); if (r.right <= W + 2 && r.left >= -2) return true; } } return false; };
    out.wide = [];
    for (const e of document.querySelectorAll('body *')) {
      const r = e.getBoundingClientRect();
      if (r.width < 2 || r.height < 2 || !vis(e)) continue;
      if ((r.right > W + 2 || r.left < -2) && !clipped(e)) out.wide.push({ el: name(e), left: Math.round(r.left), right: Math.round(r.right), text: (e.innerText || '').trim().slice(0, 60) });
      if (out.wide.length > 25) break;
    }
    out.broken = [...document.images].filter(i => i.complete && i.currentSrc && i.naturalWidth === 0).map(i => i.currentSrc).slice(0, 20);
    out.tinyText = [];
    const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n; (n = tw.nextNode()) && out.tinyText.length < 15;) {
      const t = n.textContent.trim(); if (!t || !n.parentElement || !vis(n.parentElement)) continue;
      const fs = parseFloat(getComputedStyle(n.parentElement).fontSize), r = n.parentElement.getBoundingClientRect();
      if (fs < 11 && r.width > 0 && r.top < innerHeight * 3) out.tinyText.push({ el: name(n.parentElement), px: fs, text: t.slice(0, 40) });
    }
    out.smallTaps = [...document.querySelectorAll('a,button,[role=button],select,input')].filter(e => { const r = e.getBoundingClientRect(); return vis(e) && r.width > 0 && r.top < innerHeight && r.bottom > 0 && (r.width < 28 || r.height < 28); }).slice(0, 15).map(e => { const r = e.getBoundingClientRect(); return { el: name(e), w: Math.round(r.width), h: Math.round(r.height), text: (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 30) }; });
    out.text = document.body.innerText;
    return out;
  });
}

async function scrollThrough(page) {
  await page.evaluate(async () => {
    const H = document.documentElement.scrollHeight, step = innerHeight * 0.9;
    for (let y = 0; y < Math.min(H, innerHeight * 8); y += step) { scrollTo(0, y); await new Promise(r => setTimeout(r, 250)); }
    scrollTo(0, 0);
  });
  await sleep(800);
}

async function shot(page, file, full) {
  const vp = page.viewportSize();
  if (!full) return page.screenshot({ path: file, type: 'jpeg', quality: 60 });
  const H = await page.evaluate(() => document.documentElement.scrollHeight);
  const h = Math.min(H, vp.height * 6);
  return page.screenshot({ path: file, type: 'jpeg', quality: 55, fullPage: true, clip: { x: 0, y: 0, width: vp.width, height: h } });
}

(async () => {
  const report = {};
  for (const dev of DEVICES) {
    if (only && !only.includes(dev.name)) continue;
    const browser = await (dev.engine === 'webkit' ? webkit : chromium).launch();
    const ctx = await browser.newContext({ ...dev.d, locale: 'en-GB', timezoneId: 'Europe/London' });
    for (const [pname, path] of PAGES) {
      const key = `${dev.name}__${pname}`, r = report[key] = { device: dev.name, engine: dev.engine, page: pname, errors: [], failed: [] };
      const page = await ctx.newPage();
      page.on('pageerror', e => r.errors.push('pageerror: ' + e.message.slice(0, 200)));
      page.on('console', m => { if (m.type() === 'error') r.errors.push('console: ' + m.text().slice(0, 200)); });
      page.on('response', res => { if (res.status() >= 400) r.failed.push(res.status() + ' ' + res.url().slice(0, 160)); });
      page.on('requestfailed', q => r.failed.push('failed ' + q.url().slice(0, 160) + ' ' + (q.failure() || {}).errorText));
      try {
        await page.goto(SITE + path, { waitUntil: 'load', timeout: 45000 });
        await sleep(3500);
        await shot(page, `${OUT}/${key}__top.jpg`);
        await scrollThrough(page);
        Object.assign(r, await measure(page));
        await shot(page, `${OUT}/${key}__full.jpg`, true);
        // things to tap
        if (pname === 'today') {
          const ss = await page.$('#screensaverButton');
          if (ss) { await ss.scrollIntoViewIfNeeded(); await ss.click(); await sleep(1200); await shot(page, `${OUT}/${key}__screensaver-box.jpg`);
            const ok = page.getByRole('button', { name: /^OK$/i }); if (await ok.count()) { await ok.first().click(); await sleep(9000); await shot(page, `${OUT}/${key}__screensaver.jpg`); } }
          await page.goto(SITE + path, { waitUntil: 'load', timeout: 45000 }); await sleep(3000);
          const sh = await page.$('[data-share-day]');
          if (sh) { await sh.scrollIntoViewIfNeeded(); await sh.click(); await sleep(1200); await shot(page, `${OUT}/${key}__share.jpg`); }
          await page.goto(SITE + path, { waitUntil: 'load', timeout: 45000 }); await sleep(3000);
          const ph = await page.$('main img, .rope img, img[data-fav], .card img');
          if (ph) { try { await ph.scrollIntoViewIfNeeded(); await ph.click({ timeout: 5000 }); await sleep(2500); await shot(page, `${OUT}/${key}__photo-open.jpg`); } catch (e) { r.errors.push('tap photo: ' + e.message.slice(0, 120)); } }
        }
        if (pname === 'calendar') {
          const opened = await page.evaluate(() => {
            const a = [...document.querySelectorAll('a[href]')].find(a => /\d{4}-\d{2}-\d{2}|#date=|\/day\//.test(a.getAttribute('href')) && a.getBoundingClientRect().height > 10);
            if (a) { a.scrollIntoView({ block: 'center' }); return true; } return false;
          });
          if (opened) {
            const a = await page.evaluateHandle(() => [...document.querySelectorAll('a[href]')].find(a => /\d{4}-\d{2}-\d{2}|#date=|\/day\//.test(a.getAttribute('href')) && a.getBoundingClientRect().height > 10));
            try { await a.asElement().click({ timeout: 5000 }); await sleep(2500); await shot(page, `${OUT}/${key}__tap1.jpg`);
              const card = await page.$('.ph-card:not([hidden])'); if (card) { await card.click({ timeout: 5000 }); await sleep(3000); }
              await shot(page, `${OUT}/${key}__daybox.jpg`);
              r.dayboxText = await page.evaluate(() => document.body.innerText.slice(0, 6000));
              await page.evaluate(() => { const b = [...document.querySelectorAll('*')].find(e => getComputedStyle(e).position === 'fixed' && e.scrollHeight > e.clientHeight + 50); if (b) b.scrollTop = b.scrollHeight / 2; });
              await sleep(1500); await shot(page, `${OUT}/${key}__daybox-mid.jpg`);
            } catch (e) { r.errors.push('tap day: ' + e.message.slice(0, 120)); }
          }
        }
      } catch (e) { r.errors.push('open: ' + e.message.slice(0, 200)); }
      await page.close();
      console.log(key, 'wide', (r.wide || []).length, 'broken', (r.broken || []).length, 'errors', r.errors.length, 'failed', r.failed.length);
    }
    await browser.close();
  }
  fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1));
})();
