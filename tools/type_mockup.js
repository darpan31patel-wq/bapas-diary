// Mockup only (website, never the daily picture): screenshots of the live bapas-diary.com pages as they are now and
// with live/type.css added the way tools/web_type.py adds it, computer and phone. Run by .github/workflows/type-mockup.yml.
//   node tools/type_mockup.js shots
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const out = process.argv[2] || 'shots';
const PAGES = [['today', '/', [0, 1500]], ['calendar', '/calendar/', [0]], ['search', '/search/', [0, 1100]], ['travels', '/travels/', [0]],
  ['places', '/travels/places/', [0]], ['years', '/through-the-years/', [0]], ['legacy', '/then-and-now/', [0]], ['about', '/about/', [0, 900]]];
const LIVE = path.join(__dirname, '..', 'live');
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  for (const [dev, opts] of [['computer', { viewport: { width: 1440, height: 900 } }],
                             ['phone', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true }]]) {
    for (const look of ['now', 'new']) {
      const c = await b.newContext({ ...opts, serviceWorkers: 'block' });
      if (look === 'new') {
        await c.route(/bapas-diary\.com\/(type\.css|fonts\/(lora|poppins)-[^/?]+)/, r => {
          const f = path.join(LIVE, new URL(r.request().url()).pathname);
          r.fulfill({ path: f, contentType: f.endsWith('.css') ? 'text/css' : 'font/woff2' });
        });
        await c.route(u => u.hostname === 'bapas-diary.com' && (u.pathname.endsWith('/') || u.pathname.endsWith('.html')), async r => {
          const res = await r.fetch();
          let s = await res.text();
          const tag = '<link rel="stylesheet" href="/type.css" id="site-type">';
          s = s.includes('</head>') ? s.replace('</head>', tag + '</head>') : s.replace('<nav class="site-menu', tag + '<nav class="site-menu');
          r.fulfill({ response: res, body: s });
        });
      }
      const p = await c.newPage();
      for (const [name, url, ys] of PAGES) {
        await p.goto('https://bapas-diary.com' + url, { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log(name, e.message));
        await p.waitForTimeout(4000);
        for (const [i, y] of ys.entries()) {
          if (y) { await p.evaluate(y => scrollTo(0, y), dev === 'phone' ? Math.round(y * 1.4) : y); await p.waitForTimeout(2500); }
          await p.screenshot({ path: `${out}/${name}-${i}-${dev}-${look}.jpg`, quality: 80 });
        }
        console.log(look, dev, name);
      }
      await c.close();
    }
  }
  await b.close();
})();
