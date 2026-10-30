// Mockup of the undated photos in the live Search (Darpan, 30 Oct 2026). Run by .github/workflows/undated-mockup.yml:
// the live page with the change put in only inside this test browser (site/undated/search-swaps.json), its data and
// photos served from the files here. Nothing on the website changes.
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const SWAPS = JSON.parse(fs.readFileSync('site/undated/search-swaps.json', 'utf8'));
const LIST = fs.readFileSync('undated-search.json', 'utf8'), N = JSON.parse(LIST).p.length;
const sizes = [['laptop', 1440, 900, 1, false], ['phone', 390, 844, 3, true]];
(async () => {
  const b = await chromium.launch();
  for (const [sz, w, h, dpr, mob] of sizes) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr, isMobile: mob, hasTouch: mob, serviceWorkers: 'block', timezoneId: 'Europe/London' });
    const p = await ctx.newPage(); const hit = [];
    await p.route(/bapas-diary\.com\/search\/(index\.html)?(#.*)?$/, async r => {
      const res = await r.fetch(); let t = await res.text();
      for (const [o, n] of SWAPS) { hit.push(t.includes(o)); t = t.replace(o, n); }
      await r.fulfill({ response: res, body: t });
    });
    await p.route(/bapas-diary\.com\/search\/data\/about\.json/, async r => {
      const res = await r.fetch(); const j = await res.json(); j.undated = N;
      await r.fulfill({ response: res, body: JSON.stringify(j) });
    });
    await p.route(/bapas-diary\.com\/search\/data\/undated\.json/, r => r.fulfill({ status: 200, contentType: 'application/json', body: LIST }));
    await p.route(/photos\.bapas-diary\.com\/(s|m)\/undated\/(u\d+\.jpg)/, r => {
      const m = r.request().url().match(/\/(s|m)\/undated\/(u\d+\.jpg)/);
      const f = path.join('out', m[1], 'undated', m[2]);
      return fs.existsSync(f) ? r.fulfill({ status: 200, contentType: 'image/jpeg', body: fs.readFileSync(f) }) : r.fulfill({ status: 404 });
    });
    await p.goto('https://bapas-diary.com/search/', { waitUntil: 'networkidle', timeout: 120000 }).catch(() => {});
    await p.waitForTimeout(9000);
    console.log(sz, 'swaps', JSON.stringify(hit));
    const shot = async name => { await p.waitForTimeout(2500); await p.screenshot({ path: `undated-${sz}-${name}.jpg`, type: 'jpeg', quality: 80 }); };
    // 1. the top: the line under the title with the new count
    await p.evaluate(() => scrollTo(0, 0)); await shot('1-top');
    // 2. "No date" picked in the year list: every undated photo
    await p.selectOption('#year', 'none').catch(e => console.log('year', e.message));
    await p.evaluate(() => { const e = document.getElementById('count'); e && e.scrollIntoView({ block: 'start' }); scrollBy(0, -90); });
    console.log(sz, 'no date:', await p.evaluate(() => document.getElementById('count')?.textContent.trim()));
    await shot('2-no-date');
    // 3. a photo opened big
    await p.click('#cards [data-i]').catch(e => console.log('open', e.message));
    await shot('3-big');
    await p.keyboard.press('Escape').catch(() => {});
    // 4. a word: dated photos first, then the undated ones; the year bars end with "No date"
    await p.selectOption('#year', '').catch(() => {});
    await p.fill('#q', 'garland'); await p.waitForTimeout(1500);
    await p.evaluate(() => { const e = document.getElementById('years'); e && e.scrollIntoView({ block: 'start' }); scrollBy(0, -90); });
    console.log(sz, 'garland:', await p.evaluate(() => document.getElementById('count')?.textContent.trim()));
    await shot('4-word-bars');
    // 5. a word with "No date" picked: only the undated photos that have it
    await p.selectOption('#year', 'none').catch(() => {});
    await p.fill('#q', 'smiling'); await p.waitForTimeout(1500);
    await p.evaluate(() => { const e = document.getElementById('years'); e && e.scrollIntoView({ block: 'start' }); scrollBy(0, -90); });
    console.log(sz, 'smiling, no date:', await p.evaluate(() => document.getElementById('count')?.textContent.trim()));
    await shot('5-word-no-date');
    await ctx.close();
  }
  await b.close();
})();
