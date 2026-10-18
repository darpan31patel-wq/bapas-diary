// Bapa's Diary: read every vicharan page on baps.org for the given years, in Darpan's own Chrome.
// Paste into the console of a www.baps.org tab, then: CR.run(1999, 2026)   (CR.log shows progress)
// Saves one file per year to Downloads: bapas-diary-YYYY.json
// {year, pages: [{p: page path, t: page title, rows: [[album, file, caption], ...]}]}
// Gentle on the site: one page at a time with a pause between them. Resumes from localStorage if the tab reloads.
window.CR = (() => {
  const log = [], sleep = ms => new Promise(r => setTimeout(r, ms));
  const BASES = ['/vicharan.aspx', '/HH-Pramukh-Swami-Maharaj-Vicharan.aspx'];
  const GAP = 900;
  async function get(url, tries = 3) {
    for (let i = 0; i < tries; i++) {
      try {
        const r = await fetch(url, {credentials: 'include'});
        if (r.ok) return new DOMParser().parseFromString(await r.text(), 'text/html');
        log.push('  status ' + r.status + ' ' + url.split('?')[0]);
      } catch (e) { log.push('  error ' + e.message); }
      await sleep(5000 * (i + 1));
    }
    return null;
  }
  const links = (d, y) => [...new Set([...d.querySelectorAll('a')].map(a => (a.getAttribute('href') || '').replace(/^https?:\/\/(www\.)?baps\.org/i, '').split('?')[0].split('#')[0])
    .filter(h => new RegExp('^/?(Vicharan|photos)/' + y + '/[^/]+\\.aspx$', 'i').test(h)).map(h => h.replace(/^\/?/, '/')))];
  function rows(d) {
    const seen = new Set(), out = [];
    for (const im of d.querySelectorAll('img')) {
      const m = (im.getAttribute('src') || '').match(/GalleryImages\/(\d+)\/WebImages\/([^\/?#]+\.jpe?g)/i);
      if (!m || seen.has(m[1] + m[2])) continue;
      seen.add(m[1] + m[2]);
      out.push([m[1], m[2], (im.getAttribute('alt') || im.getAttribute('title') || '').replace(/\s+/g, ' ').trim()]);
    }
    return out;
  }
  function save(y, data) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(data)], {type: 'application/json'}));
    a.download = 'bapas-diary-' + y + '.json';
    document.body.appendChild(a); a.click(); a.remove();
  }
  async function year(y, months = [1,2,3,4,5,6,7,8,9,10,11,12]) {
    const queue = [], seen = new Set();
    for (const mn of months) for (const b of BASES) {
      const d = await get(b + '?yr=' + y + '&mn=' + mn); await sleep(GAP);
      if (d) for (const h of links(d, y)) if (!seen.has(h)) { seen.add(h); queue.push(h); }
    }
    log.push(y + ': ' + queue.length + ' pages to read');
    const pages = [];
    while (queue.length) {
      const h = queue.shift();
      const d = await get(h); await sleep(GAP);
      if (!d) { pages.push({p: h, t: '', rows: [], failed: true}); continue; }
      for (const l of links(d, y)) if (!seen.has(l) && /\/photos\//i.test(l)) { seen.add(l); queue.push(l); }   // old years: photos sit on gallery pages
      pages.push({p: h, t: (d.title || '').trim(), rows: rows(d)});
      CR.now = y + ' ' + pages.length + '/' + (pages.length + queue.length);
    }
    const n = pages.reduce((s, p) => s + p.rows.length, 0);
    log.push(y + ': done, ' + pages.length + ' pages, ' + n + ' photos, ' + pages.filter(p => p.failed).length + ' failed');
    return {year: y, read: new Date().toISOString(), pages};
  }
  async function run(from, to, months) {
    const done = JSON.parse(localStorage.getItem('bdCrawlDone') || '[]');
    for (let y = from; y <= to; y++) {
      if (done.includes(y)) { log.push(y + ': already saved'); continue; }
      try { save(y, await year(y, months)); done.push(y); localStorage.setItem('bdCrawlDone', JSON.stringify(done)); }
      catch (e) { log.push(y + ': stopped, ' + e.message); }
    }
    log.push('all done');
  }
  return {log, run, year, rows, links, save, reset: () => localStorage.removeItem('bdCrawlDone')};
})();
