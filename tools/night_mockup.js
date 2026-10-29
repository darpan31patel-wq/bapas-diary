// Mockup only (website, never the daily picture): screenshots of the live bapas-diary.com pages as they are now and
// with the gentle night mode added the way tools/web_night.py adds it, computer and phone, in the evening.
// Run by .github/workflows/night-mockup.yml.   node tools/night_mockup.js shots
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const out = process.argv[2] || 'shots';
const PAGES = [['today', '/', [0, 900, 2600]], ['calendar', '/calendar/', [0]], ['search', '/search/', [0, 1100]],
  ['search-words', '/search/#q=london', [0, 700]], ['travels', '/travels/', [0]], ['places', '/travels/places/', [0]],
  ['years', '/through-the-years/', [0]], ['legacy', '/then-and-now/', [0]], ['about', '/about/', [0, 900]]];
const CSS = path.join(__dirname, '..', 'site', 'night', 'night.css');
const dress = s => execFileSync('python3', ['-c',
  'import sys; sys.path.insert(0, "tools"); import web_night; sys.stdout.write(web_night.dress(sys.stdin.read(), ' +
  '\'<link rel="stylesheet" href="/night.css" id="site-night-css">\'))'], { input: s, encoding: 'utf8', maxBuffer: 1 << 28 });
(async () => {
  fs.mkdirSync(out + '/html', { recursive: true });
  const b = await chromium.launch();
  for (const [dev, opts] of [['computer', { viewport: { width: 1440, height: 900 } }],
                             ['phone', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }]]) {
    for (const look of ['now', 'night']) {
      const c = await b.newContext({ ...opts, serviceWorkers: 'block', timezoneId: 'Europe/London' });
      if (look === 'night') {
        await c.addInitScript(() => { const g = Date.prototype.getHours; Date.prototype.getHours = function () { return 21; }; });
        await c.route(/bapas-diary\.com\/night\.css/, r => r.fulfill({ path: CSS, contentType: 'text/css' }));
        await c.route(u => u.hostname === 'bapas-diary.com' && (u.pathname.endsWith('/') || u.pathname.endsWith('.html')), async r => {
          const res = await r.fetch();
          r.fulfill({ response: res, body: dress(await res.text()) });
        });
      }
      const p = await c.newPage();
      for (const [name, url, ys] of PAGES) {
        await p.goto('https://bapas-diary.com' + url, { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log(name, e.message));
        await p.waitForTimeout(5000);
        if (look === 'now' && dev === 'computer') fs.writeFileSync(`${out}/html/${name}.html`, await p.content());
        for (const [i, y] of ys.entries()) {
          if (y) { await p.evaluate(y => scrollTo(0, y), dev === 'phone' ? Math.round(y * 1.4) : y); await p.waitForTimeout(3000); }
          await p.screenshot({ path: `${out}/${name}-${i}-${dev}-${look}.jpg`, quality: 82 });
        }
        console.log(look, dev, name, await p.evaluate(() => document.documentElement.className + ' ' + document.documentElement.dataset.pg));
      }
      await c.close();
    }
  }
  await b.close();
})();
