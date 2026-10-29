// Takes a JPEG of whole months on the live Calendar (bapas-diary.com/calendar/), computer size.
// Read only: opens the public page, changes nothing. Usage: node shoot.js OUTDIR 1999-11 2012-11 ...
const { chromium } = require('playwright');
const fs = require('fs');
const [out, ...months] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
(async () => {
  const browser = await chromium.launch();
  for (const k of months) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
    await page.goto(`https://bapas-diary.com/calendar/#${k}`, { waitUntil: 'networkidle', timeout: 120000 });
    // every day in full colour, as when the mouse is over it (look C fades the days away from the mouse)
    await page.addStyleTag({ content: '.card{--q:1!important}' });
    await page.mouse.move(5, 995);
    await page.waitForSelector(`.month[data-k="${k}"] .card`, { timeout: 60000 });
    await page.waitForFunction(k => {
      const mo = document.querySelector(`.month[data-k="${k}"]`);
      return [...mo.querySelectorAll('img')].every(i => i.complete);
    }, k, { timeout: 120000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(2500);
    const box = await page.evaluate(k => {
      const mo = document.querySelector(`.month[data-k="${k}"]`).getBoundingClientRect();
      const t = document.querySelector('header').getBoundingClientRect();
      return { x: mo.left - 28, y: t.top, width: mo.width + 56, height: mo.bottom + 18 - t.top };
    }, k);
    const [y, m] = k.split('-');
    await page.screenshot({ path: `${out}/calendar-${k}-${MONTHS[m - 1].toLowerCase()}-${y}.jpg`, type: 'jpeg', quality: 92, clip: box });
    console.log(k, JSON.stringify(box));
    await page.close();
  }
  await browser.close();
})();
