// Website only (Darpan, 25 Oct 2026: "I want captions and photos" together, daily at 8pm UK). Run in a www.baps.org tab of
// Darpan's own Chrome by the daily helper (README.md here). Reads only the vicharan day pages that are new, plus the last few
// days again (baps.org adds photos to a day later), one page at a time with a pause, exactly like a person reading them.
// It never tries to get past baps.org's Cloudflare check: if a page doesn't load it is skipped and tried again tomorrow.
//   await CAP.run(['/Vicharan/2026/21-October-2026-32045.aspx', ...pages already saved], 3)  -> list of pages to save
//   CAP.part(0)  -> {page, title, rows: [[album, file, caption], ...], hash}   one page
//   CAP.short(0) -> the same page written short (numbered files as runs, a caption repeated in a row as [n, caption]),
//                   90 captions at a time: CAP.short(0, 90) gives the next ones (capsTotal says how many there are)
window.CAP = (() => {
  const GAP = 3000, sleep = ms => new Promise(r => setTimeout(r, ms));
  const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = (h * 33 + s.charCodeAt(i)) >>> 0; return h.toString(16); };
  async function get(url) {
    for (let i = 0; i < 2; i++) {
      try {
        const r = await fetch(url, {credentials: 'include'});
        if (r.ok) return new DOMParser().parseFromString(await r.text(), 'text/html');
      } catch (e) {}
      await sleep(10000);
    }
    return null;
  }
  function rows(d) {
    const seen = new Set(), out = [];
    for (const im of d.querySelectorAll('img')) {
      const m = (im.getAttribute('src') || '').match(/GalleryImages\/(\d+)\/WebImages\/([^\/?#]+\.jpe?g)/i);
      if (!m || seen.has(m[1] + m[2])) continue;
      seen.add(m[1] + m[2]);
      let c = im.getAttribute('alt') || im.getAttribute('title') || '';
      if (c.includes('<')) c = new DOMParser().parseFromString(c, 'text/html').body.textContent;   // a link to the day's photo album
      out.push([m[1], m[2], c.replace(/\s+/g, ' ').trim()]);
    }
    return out;
  }
  const out = [];
  async function run(known, again = 3) {
    out.length = 0;
    const t = new Date(), months = [[t.getFullYear(), t.getMonth() + 1]];
    if (t.getDate() <= 7) { const p = new Date(t.getFullYear(), t.getMonth() - 1, 1); months.unshift([p.getFullYear(), p.getMonth() + 1]); }
    const pages = [];
    for (const [y, mn] of months) {
      const d = await get('/vicharan.aspx?yr=' + y + '&mn=' + mn); await sleep(GAP);
      if (!d) return {error: 'the month list did not load (try again tomorrow)'};
      for (const a of d.querySelectorAll('a')) {
        const h = (a.getAttribute('href') || '').replace(/^https?:\/\/(www\.)?baps\.org/i, '').split(/[?#]/)[0];
        if (/^\/Vicharan\/\d{4}\/[^\/]+\.aspx$/i.test(h) && !pages.includes(h)) pages.push(h);
      }
    }
    const recent = pages.slice(-again), todo = pages.filter(p => !known.includes(p) || recent.includes(p));
    for (const p of todo) {
      const d = await get(p); await sleep(GAP);
      if (!d) continue;
      const r = rows(d), title = (d.title || '').trim();
      if (r.length) out.push({page: p, title, rows: r, hash: hash(JSON.stringify(r))});
      // the day's own photo albums (a festival, a nagar yatra), linked from the day page: same date and place
      const albums = new Set();
      for (const a of d.querySelectorAll('a, img')) {
        const html = a.tagName === 'IMG' ? (a.getAttribute('alt') || '') : '<a href="' + (a.getAttribute('href') || '') + '">';
        for (const m of html.matchAll(/href="(?:https?:\/\/(?:www\.)?baps\.org)?(\/Photos\/\d{4}\/[^"?#]+\.aspx)/gi)) albums.add(m[1]);
      }
      for (const al of albums) {
        if (known.includes(al) && !recent.includes(p)) continue;
        const g = await get(al); await sleep(GAP);
        const gr = g ? rows(g) : [];
        if (gr.length) out.push({page: al, day: p, title, rows: gr, hash: hash(JSON.stringify(gr))});
      }
    }
    return out.map((x, i) => ({part: i, page: x.page, photos: x.rows.length}));
  }
  function compact(i) {
    const x = out[i], files = [];
    let run = null;
    for (const [al, f] of x.rows) {
      const m = f.match(/^(.*_)(\d+)(_[^_]+\.jpe?g|\.jpe?g)$/i);
      if (run && m && al === run.al && m[1] === run.pre && m[3] === run.suf && +m[2] === run.to + 1 && m[2].length === run.w) { run.to++; continue; }
      run = m ? {al, pre: m[1], suf: m[3], from: +m[2], to: +m[2], w: m[2].length} : null;
      files.push(run || {al, f});
    }
    return {page: x.page, day: x.day, title: x.title, hash: x.hash, caps: x.rows.map(r => r[2]),
            files: files.map(r => r.f ? r.al + ' ' + r.f : r.al + ' ' + r.pre + '[' + r.from + '-' + r.to + '/' + r.w + ']' + r.suf)};
  }
  function short(i, from = 0) {
    const x = compact(i), caps = [];
    for (const c of x.caps) {
      const l = caps[caps.length - 1];
      if (Array.isArray(l) && l[1] === c) l[0]++; else if (l === c) caps[caps.length - 1] = [2, c]; else caps.push(c);
    }
    return {...x, caps: caps.slice(from, from + 90), capsFrom: from, capsTotal: caps.length};
  }
  return {run, part: i => out[i], compact, short, hash};
})();
