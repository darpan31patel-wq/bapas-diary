// node shoot.js <years|travels> <variant: now|a|b|c> <out.jpg> [steps json]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const S = path.join(__dirname, '..'), WEB = '/home/claude/web';
const [, , page, variant, out, stepsJson] = process.argv;
const steps = JSON.parse(stepsJson || '[]');
const URLS = { years: 'https://bapas-diary.com/through-the-years/', travels: 'https://bapas-diary.com/travels/' };
(async () => {
  const b = await chromium.launch();
  const c = await b.newContext({ viewport: { width: 390, height: 664 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true, serviceWorkers: 'block',
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' });
  await c.addInitScript(() => { try { localStorage.clear(); } catch (e) {} });
  // local fallbacks for things not in the recording
  await c.route(/bapas-diary\.com\/(travels\/photos|fonts)\//, r => {
    const f = path.join(WEB, 'live', new URL(r.request().url()).pathname);
    if (fs.existsSync(f)) return r.fulfill({ path: f }); return r.fallback();
  });
  await c.routeFromHAR(path.join(S, 'rec', page + '.har'), { notFound: 'abort' });
  if (variant !== 'now') {
    await c.route(URLS[page], async r => {
      let s = fs.readFileSync(path.join(S, 'rec', page + '.page.html'), 'utf8');
      for (const [a, b2] of (fs.existsSync(path.join(__dirname, `${page}.swap.json`)) ? JSON.parse(fs.readFileSync(path.join(__dirname, `${page}.swap.json`), 'utf8')) : [])) { if (!s.includes(a)) console.log('swap missing', a); s = s.replace(a, b2); }
      const css = fs.readFileSync(path.join(__dirname, `${page}.css`), 'utf8');
      const js = fs.existsSync(path.join(__dirname, `${page}.js`)) ? fs.readFileSync(path.join(__dirname, `${page}.js`), 'utf8') : '';
      const inj = `<style id="phone-redesign">${css}</style><script>document.documentElement.classList.add('pr-${variant}');</script>`;
      s = s.replace(/<\/head>|<nav class="site-menu/, m => inj + m);
      s = s.replace(/<\/body>|<\/html>/, m => `<script>${js}</script>` + m);
      r.fulfill({ body: s, contentType: 'text/html; charset=utf-8' });
    });
  }
  const p = await c.newPage();
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto(URLS[page], { waitUntil: 'load' }).catch(e => console.log(e.message));
  await p.waitForTimeout(2500);
  for (const st of steps) {
    if (st.click) await p.click(st.click, { timeout: 3000 }).catch(e => console.log('click', st.click, e.message.split('\n')[0]));
    if (st.eval) await p.evaluate(st.eval).catch(e => console.log('eval', e.message));
    await p.waitForTimeout(st.wait || 2500);
  }
  await p.screenshot({ path: out, quality: 85, type: 'jpeg' });
  await b.close();
})();
