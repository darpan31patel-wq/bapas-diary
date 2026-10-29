// Mockup only (website, never the daily picture): records the live Today page and its Share this day choices on a
// computer and a phone sized screen, and saves a few of the ready share pictures, so Share a day can be shown to
// Darpan as it is now. Run by .github/workflows/dayshare-mockup.yml:   node mockups/dayshare/record.js out
const { chromium } = require('playwright');
const fs = require('fs');
const https = require('https');
const out = process.argv[2] || 'out';
const SITE = 'https://bapas-diary.com';
const wait = ms => new Promise(r => setTimeout(r, ms));
const get = (url, file) => new Promise(res => https.get(url, r => {
  if (r.statusCode !== 200) { console.log(url, r.statusCode); r.resume(); return res(); }
  const f = fs.createWriteStream(file); r.pipe(f); f.on('finish', () => { f.close(); res(); });
}).on('error', e => { console.log(url, e.message); res(); }));
const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true,
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' };
const computer = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 };
(async () => {
  fs.mkdirSync(out, { recursive: true });
  for (const d of ['10-29', '10-30', '11-01', '11-12', '04-16', '12-07']) {
    await get(`${SITE}/share/day/${d}.jpg`, `${out}/share-${d}.jpg`);
    await get(`${SITE}/share/day/${d}-wide.jpg`, `${out}/share-${d}-wide.jpg`);
  }
  await get(`${SITE}/day/10-29/`, `${out}/day-link-10-29.html`);
  const b = await chromium.launch();
  for (const [name, dev] of [['computer', computer], ['phone', phone]]) {
    const c = await b.newContext({ ...dev, serviceWorkers: 'block', recordHar: { path: `${out}/${name}.har`, content: 'embed' } });
    const p = await c.newPage();
    p.on('pageerror', e => console.log(name, 'ERR', e.message));
    await p.goto(SITE + '/#10-29', { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log(name, e.message));
    await wait(6000);
    await p.screenshot({ path: `${out}/${name}-top.jpg`, quality: 85 });
    fs.writeFileSync(`${out}/${name}.page.html`, await p.content());
    const info = await p.evaluate(() => {
      const r = s => { const e = document.querySelector(s); if (!e) return null; const b = e.getBoundingClientRect(); return { top: b.top + scrollY, left: b.left, w: b.width, h: b.height, hidden: !e.offsetParent }; };
      return { share: r('.bd-today-share'), controls: r('#controls'), pageH: document.documentElement.scrollHeight,
        shares: [...document.querySelectorAll('[data-share-day]')].map(e => e.className + ' | ' + e.textContent.trim()) };
    });
    console.log(name, JSON.stringify(info));
    const btn = p.locator('.bd-today-share').first();
    if (await btn.count()) {
      await btn.scrollIntoViewIfNeeded().catch(() => {}); await wait(1500);
      await p.screenshot({ path: `${out}/${name}-button.jpg`, quality: 85 });
      await btn.click({ timeout: 5000 }).catch(e => console.log(name, 'click', e.message.split('\n')[0]));
      await wait(3000);
      await p.screenshot({ path: `${out}/${name}-sheet.jpg`, quality: 85 });
    }
    await p.screenshot({ path: `${out}/${name}-full.jpg`, quality: 70, fullPage: true }).catch(e => console.log(e.message));
    await c.close();
  }
  await b.close();
})();
