// Website only, read only mockup: Darpan's four picks from the phone and tablet check (30 Oct 2026), shown on the LIVE pages
// with the same changes made to the page in the robot's browser only. Never deploys, never touches the daily 2pm picture.
const { webkit, chromium, devices } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2] || 'shots4';
const SITE = 'https://bapas-diary.com';
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = {};
const swap = (t, a, b, k) => { if (!t.includes(a)) { (log.miss = log.miss || []).push(k); return t; } return t.split(a).join(b); };
const MORBI = ['2026-10-20', '2026-11-03'];   // the schedule's Morbi stay, a travel day counting for the town he arrives in

const DAYBOX = t => {
  t = swap(t, '.day h2 .ti {', '.day h2.solo { justify-content: center; border-bottom: 0; padding-bottom: 0; margin-top: -4px; }\n.day h2.solo:empty { display: none; }\n.day h2 .ti {', 'box css');
  t = swap(t, 'data.p.forEach(([gi, file, cap]) => {', 'data.p.forEach(([gi, file, cap, tags, bapa]) => {', 'box p');
  t = swap(t, '(byDay[d] = byDay[d] || []).push({ g, file, cap, d });', '(byDay[d] = byDay[d] || []).push({ g, file, cap, d, bapa: bapa ? 1 : 0 });', 'box push');
  t = swap(t, 'const keys = Object.keys(byDay).sort();', 'Object.values(byDay).forEach(list => list.sort((a, b) => b.bapa - a.bapa));\n  const keys = Object.keys(byDay).sort();', 'box sort');
  t = swap(t, "s.innerHTML = `<h2>${WD[dt(k).getUTCDay()]}", "s.innerHTML = from === to ? '<h2 class=\"solo\"></h2>' : `<h2>${WD[dt(k).getUTCDay()]}", 'box h2');
  return t;
};
const CAL = t => {
  t = swap(t, 'if(cur&&p===lastP&&cur.fut===fut){', 'if(cur&&p===lastP&&(cur.fut===fut||fut)){', 'cal chips');
  t = swap(t, 'if (cur && p === lastP && cur.fut === fut) {', 'if (cur && p === lastP && (cur.fut === fut || fut)) {', 'phone chips');
  t = swap(t, '</style>', '@media (hover:none) and (pointer:coarse) and (min-width:761px){.fest{font-size:calc(clamp(7.5px,1.15vh,10px) * var(--z) * 1.3);letter-spacing:.04em}.strip{font-size:calc(clamp(7px,1.05vh,9.5px) * var(--z) * 1.3);letter-spacing:.04em}.tday{font-size:calc(clamp(7px,1.05vh,9px) * var(--z) * 1.2)}}</style>', 'cal css');
  return t;
};
const CALJSON = j => {   // the stay's days up to today take the schedule's town (what web_calendar.py now does)
  for (const [m, days] of Object.entries(j.m || {})) days.forEach((row, i) => {
    const d = `${m}-${String(i + 1).padStart(2, '0')}`;
    if (d >= MORBI[0] && d <= MORBI[1] && row.length > 3) row[3] = 'Morbi';
  });
  return j;
};
const TODAY = t => {
  t = swap(t, "    const map = S.maps[s.city];\n", "    const prev = d => new Date(Date.parse(d + 'T12:00:00Z') - 864e5).toISOString().slice(0, 10);\n    const upto = x => { const after = stays[stays.indexOf(x) + 1]; return after && after.from === x.to && today < x.to ? prev(x.to) : x.to; };\n    const map = S.maps[s.city];\n", 'today upto');
  t = swap(t, "${nice(s.from)} to ${nice(s.to)}", "${nice(s.from)} to ${nice(upto(s))}", 'today dates');
  t = swap(t, "${n.from.slice(0, 7) === n.to.slice(0, 7) ? +n.from.slice(8) : short(n.from)} to ${short(n.to)}", "${n.from.slice(0, 7) === upto(n).slice(0, 7) ? +n.from.slice(8) : short(n.from)} to ${short(upto(n))}", 'today next');
  return t;
};

async function fixRoutes(ctx) {
  await ctx.route(/bapas-diary\.com\/(photos\/|calendar\/|$|\?|#)/, async route => {
    const res = await route.fetch(); let t = await res.text(); const u = route.request().url();
    if (/\/photos\//.test(u)) t = DAYBOX(t); else if (/\/calendar\//.test(u)) t = CAL(t); else t = TODAY(t);
    const h = { ...res.headers() }; delete h['content-length']; delete h['content-encoding']; route.fulfill({ status: res.status(), headers: h, body: t });
  });
  await ctx.route(/\/phone\.js|\/phone\/phone\.js/, async route => { const res = await route.fetch(); route.fulfill({ response: res, body: CAL(await res.text()) }); });
  await ctx.route(/calendar\.json/, async route => { const res = await route.fetch(); route.fulfill({ response: res, body: JSON.stringify(CALJSON(await res.json())) }); });
}

const RUNS = [['iphone-14', webkit, devices['iPhone 14']], ['ipad-landscape', webkit, devices['iPad (gen 7) landscape']], ['ipad-portrait', webkit, devices['iPad (gen 7)']]];
(async () => {
  for (const [name, eng, dev] of RUNS) {
    for (const when of ['before', 'after']) {
      const b = await eng.launch(); const ctx = await b.newContext({ ...dev, locale: 'en-GB', timezoneId: 'Europe/London', serviceWorkers: 'block' });
      if (when === 'after') await fixRoutes(ctx);
      const page = await ctx.newPage();
      const k = `${name}__${when}`;
      try {
        await page.goto(SITE + '/', { waitUntil: 'load', timeout: 45000 }); await sleep(3500);
        const card = await page.$('.bapa-now'); if (card) { await card.scrollIntoViewIfNeeded(); await card.screenshot({ path: `${OUT}/${k}__now.jpg`, type: 'jpeg', quality: 75 }); }
        log[k + ' now'] = await page.evaluate(() => (document.querySelector('.bapa-now') || {}).innerText || '');
        await page.goto(SITE + '/calendar/', { waitUntil: 'load', timeout: 45000 }); await sleep(5000);
        await page.screenshot({ path: `${OUT}/${k}__calendar.jpg`, type: 'jpeg', quality: 70 });
        log[k + ' stays'] = await page.evaluate(() => [...document.querySelectorAll('.place, .ph-stay')].map(e => e.innerText.replace(/\s+/g, ' ')).filter(t => /Morbi|Gondal|Ahmedabad/.test(t)).slice(-6));
        log[k + ' fest px'] = await page.evaluate(() => [...document.querySelectorAll('.fest, .strip')].slice(0, 5).map(e => getComputedStyle(e).fontSize));
        const p2 = await ctx.newPage();
        await p2.goto(SITE + '/photos/#date=2026-10-27&place=Morbi', { waitUntil: 'load', timeout: 45000 }); await sleep(5000);
        await p2.screenshot({ path: `${OUT}/${k}__daybox.jpg`, type: 'jpeg', quality: 70 });
        log[k + ' daybox'] = await p2.evaluate(() => document.body.innerText.slice(0, 400));
      } catch (e) { log[k] = String(e).slice(0, 300); }
      await b.close(); await sleep(1000);
    }
  }
  fs.writeFileSync(`${OUT}/log.json`, JSON.stringify(log, null, 1));
})();
