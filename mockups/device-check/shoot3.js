// Website only, read only mockup: the live pages before and after the device check fixes, the fixes added in the browser
// only (nothing on the website changes). Never deploys, never touches the daily 2pm picture.
const { webkit, chromium, devices } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2] || 'shots3';
const SITE = 'https://bapas-diary.com';
fs.mkdirSync(OUT, { recursive: true });
const css = f => fs.readFileSync(__dirname + '/' + f, 'utf8');
const SMALL = css('fix-small.css'), SEARCH = css('fix-search.css'), TODAY = css('fix-today.css');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = {};
const vp = (w, h) => ({ viewport: { width: w, height: h }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: devices['iPad (gen 7)'].userAgent });
const RUNS = [
  ['iphone-se1-320', webkit, devices['iPhone SE'], [['today', '/', SMALL], ['search', '/search/#q=annakut&place=London', SMALL + SEARCH], ['calendar', '/calendar/', SMALL], ['years', '/through-the-years/', SMALL], ['legacy', '/then-and-now/', SMALL]]],
  ['android-320', chromium, devices['Galaxy S9+'], [['today', '/', SMALL], ['search', '/search/#q=annakut&place=London', SMALL + SEARCH]]],
  ['iphone-14', webkit, devices['iPhone 14'], [['today', '/', SMALL], ['search', '/search/#q=annakut&place=London', SMALL + SEARCH]]],
  ['ipad-mini-land-1024', webkit, vp(1024, 768), [['today', '/', TODAY]]],
  ['ipad-land-1080', webkit, devices['iPad (gen 7) landscape'], [['today', '/', TODAY]]],
  ['ipad-air-land-1112', webkit, vp(1112, 834), [['today', '/', TODAY]]],
  ['ipad-air-land-1180', webkit, vp(1180, 820), [['today', '/', TODAY]]],
];
(async () => {
  for (const [name, eng, dev, pages] of RUNS) {
    const b = await eng.launch(); const ctx = await b.newContext({ ...dev, locale: 'en-GB', timezoneId: 'Europe/London', serviceWorkers: 'block' });
    for (const [p, u, fix] of pages) {
      for (const when of ['before', 'after']) {
        const page = await ctx.newPage();
        try {
          await page.goto(SITE + u, { waitUntil: 'load', timeout: 45000 }); await sleep(4000);
          if (when === 'after') { await page.addStyleTag({ content: fix }); await sleep(800); }
          await page.screenshot({ path: `${OUT}/${name}__${p}__${when}.jpg`, type: 'jpeg', quality: 70 });
          if (p === 'search') { await page.evaluate(() => { const f = document.querySelector('.frow'); if (f) f.scrollIntoView({ block: 'start' }); scrollBy(0, -60); }); await sleep(600); await page.screenshot({ path: `${OUT}/${name}__${p}-filters__${when}.jpg`, type: 'jpeg', quality: 70 }); }
          log[`${name}__${p}__${when}`] = await page.evaluate(() => ({ W: innerWidth, scrollW: document.documentElement.scrollWidth,
            over: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e); return r.width > 0 && r.right > innerWidth + 1 && s.visibility !== 'hidden' && !e.closest('.cards,.board,.tape,svg,.ph-cal-wrap,.jrow,.ph-jrow'); }).slice(0, 10).map(e => e.tagName + '.' + (typeof e.className === 'string' ? e.className : '') + ' ' + Math.round(e.getBoundingClientRect().right)),
            ropeTop: (() => { const c = document.querySelector('.board'); return c ? Math.round(c.getBoundingClientRect().top + scrollY) : null; })(),
            overlaps: (() => { const q = s => document.querySelector(s); const a = [q('header .ss-launch'), q('.bapa-now'), q('header .remind'), q('.days, .daynav, nav.days'), q('h1')].filter(Boolean).map(e => [e.className || e.tagName, e.getBoundingClientRect()]); const o = []; for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) { const [n1, r1] = a[i], [n2, r2] = a[j]; if (r1.left < r2.right && r2.left < r1.right && r1.top < r2.bottom && r2.top < r1.bottom) o.push(n1 + ' x ' + n2); } return o; })() }));
        } catch (e) { log[`${name}__${p}__${when}`] = String(e).slice(0, 200); }
        await page.close(); await sleep(1200);
      }
    }
    await b.close();
  }
  fs.writeFileSync(`${OUT}/log.json`, JSON.stringify(log, null, 1));
})();
