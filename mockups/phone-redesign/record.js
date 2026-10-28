// Mockup only (website, never the daily picture): records the live Through the years and Travels pages on an iPhone
// sized screen into HAR files, so the phone redesign can be tried on the real pages offline. Run by
// .github/workflows/phone-redesign-mockup.yml:   node mockups/phone-redesign/record.js out
const { chromium } = require('playwright');
const fs = require('fs');
const out = process.argv[2] || 'out';
const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true,
  userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1' };
const wait = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  for (const [name, url, act] of [
    ['years', '/through-the-years/', async p => {
      for (const y of ['2003', '2010', '2015']) { await p.click(`.yr[data-y="${y}"]`).catch(() => {}); await wait(2500); }
      await p.click('#tab-msm').catch(() => {}); await wait(3000);
      for (const y of ['2019', '2021', '2024']) { await p.click(`.yr[data-y="${y}"]`).catch(() => {}); await wait(2500); }
    }],
    ['travels', '/travels/', async p => { await wait(9000); }],
    ['places', '/travels/places/', async p => { await wait(5000); }],
  ]) {
    const c = await b.newContext({ ...phone, serviceWorkers: 'block', recordHar: { path: `${out}/${name}.har`, content: 'embed' } });
    const p = await c.newPage();
    await p.goto('https://bapas-diary.com' + url, { waitUntil: 'networkidle', timeout: 90000 }).catch(e => console.log(name, e.message));
    await wait(4000);
    await p.screenshot({ path: `${out}/${name}-now.jpg`, quality: 85 });
    fs.writeFileSync(`${out}/${name}.dom.html`, await p.content());
    await act(p);
    await p.screenshot({ path: `${out}/${name}-after.jpg`, quality: 85 });
    await c.close();
    console.log('recorded', name);
  }
  await b.close();
})();
