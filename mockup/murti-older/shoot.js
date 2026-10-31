// The real Darshan tab on bapas-diary.com with the older days change (patched page and cal.js served in its place).
const { chromium } = require('playwright');
const fs = require('fs');
const page_html = fs.readFileSync(process.argv[2], 'utf8'), cal = fs.readFileSync(process.argv[3], 'utf8');
(async () => {
  const b = await chromium.launch();
  const shots = [['computer-diwali-2023', 1440, 900, '#2023-11-12', null], ['computer-by-colour', 1440, 900, '#2023-11-13', 'colour'],
                 ['phone-annakut-2024', 390, 844, '#2024-11-02', null], ['computer-first-day', 1440, 900, '#2022-09-10', null]];
  for (const [name, w, h, hash, view] of shots) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: w < 500 ? 2 : 1 });
    const p = await ctx.newPage();
    await p.route('https://bapas-diary.com/darshan/', r => r.fulfill({ contentType: 'text/html', body: page_html }));
    await p.route('https://bapas-diary.com/darshan/cal.js', r => r.fulfill({ contentType: 'application/javascript', body: cal }));
    await p.goto('https://bapas-diary.com/darshan/' + hash, { waitUntil: 'networkidle' });
    if (view) { await p.evaluate(v => { const b = [...document.querySelectorAll('button, a')].find(x => /colour/i.test(x.textContent)); b && b.click(); }, view); await p.waitForTimeout(2500); }
    await p.waitForTimeout(2500);
    await p.screenshot({ path: `mockup/murti-older/${name}.jpg`, type: 'jpeg', quality: 80, fullPage: !!view });
    console.log('shot', name, await p.evaluate(() => document.getElementById('k-date')?.textContent + ' | ' + document.getElementById('k-ind')?.textContent + ' | ' + document.getElementById('k-tags')?.textContent));
    await ctx.close();
  }
  await b.close();
})();
