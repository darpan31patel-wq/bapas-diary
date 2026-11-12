// Website only (Darpan, 9 Nov 2026: "WANT CAPTIONS AND ARTICLES", "MAKE IT HAPPEN RIGHT NOW"). Run in the same www.baps.org
// tab as captions_chrome.js, after it. Reads the News list newest first and every article not saved yet, one page at a
// time with a pause, like a person reading. baps.org now has two kinds of News pages: the old /News/YYYY/...-NNNNN.aspx
// ones and the new /<region>/news/<name> ones (its new site, with galleries at .../gallery). Never gets past a check page:
// anything that doesn't load is skipped and tried again the next night.
//   await NEWS.run(<news_merge_daily.py --known>, 15)  -> list of articles read (15 = most News list pages to look at;
//                   NEWS.run(known, 20, false) reads all 20 pages without stopping at the first page already saved)
//   NEWS.show(0, 5) writes articles 0 to 4 as plain text into the tab, for get_page_text; news_merge_daily.py --text reads it
window.NEWS = (() => {
  const GAP = 3000, sleep = ms => new Promise(r => setTimeout(r, ms));
  const hash = s => { let h = 5381; for (let i = 0; i < s.length; i++) h = (h * 33 + s.charCodeAt(i)) >>> 0; return h.toString(16); };
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  async function get(url) {
    for (let i = 0; i < 2; i++) {
      try {
        const r = await fetch(url, {credentials: 'include'});
        if (r.ok) { const t = await r.text(); if (!/Just a moment|cf-challenge/i.test(t.slice(0, 3000))) return t; return null; }
      } catch (e) {}
      await sleep(10000);
    }
    return null;
  }
  const html = t => new DOMParser().parseFromString(t, 'text/html');
  const local = h => (h || '').replace(/^https?:\/\/(www\.)?baps\.org/i, '').split(/[?#]/)[0];
  const isArticle = h => /^\/[a-z0-9-]+\/news\/[^\/]+$/i.test(h) || /^\/News\/\d{4}\/[^\/]+\.aspx$/i.test(h);
  function list(d) {
    const out = [], seen = new Set();
    for (const a of d.querySelectorAll('a')) {
      const h = local(a.getAttribute('href'));
      if (!isArticle(h) || seen.has(h)) continue;
      seen.add(h);
      let c = a;
      for (let i = 0; i < 5 && c.parentElement && clean(c.textContent).length < 40; i++) c = c.parentElement;
      const m = clean(c.textContent).match(/([A-Za-z][^,]{0,60}), (\d{1,2} [A-Z][a-z]{2} \d{4})/);
      out.push({p: h, listed: m ? m[2] : '', where: m ? m[1].split(' ').slice(-3).join(' ') : ''});
    }
    return out;
  }
  function words(d) {    // the article's own words, in order, without the menu, footer and "Recent News"
    d.querySelectorAll('script, style, noscript, svg, header, footer, nav').forEach(x => x.remove());
    const els = [...d.body.querySelectorAll('h1, h2, h3, h4, p, li, blockquote, figcaption')].filter(e => !e.querySelector('h1, h2, h3, h4, p, li'));
    const lines = [];
    for (const e of els) {
      const t = clean(e.textContent);
      if (!t || t === 'Loading') continue;
      if (/^(Recent News|Related News)$/i.test(t)) break;
      if (lines[lines.length - 1] !== t) lines.push(t);
    }
    return lines;
  }
  function flight(t) {
    let s = '';
    for (const m of t.matchAll(/self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)/g)) { try { s += JSON.parse(m[1]); } catch (e) {} }
    return s;
  }
  function gallery(t) {     // the new site's gallery: photo addresses and captions (baps.org leaves most captions empty)
    const f = flight(t), i = f.indexOf('"postGallery"'), j = f.indexOf('"items":', i);
    if (i < 0 || j < 0) return [];
    let k = j + 8, dep = 0;
    for (; k < f.length; k++) { const c = f[k]; if (c === '[') dep++; else if (c === ']') { dep--; if (!dep) break; } }
    try { return JSON.parse(f.slice(j + 8, k + 1)).map(x => [decodeURIComponent((x.src || '').replace(/^https?:\/\/[^\/]+\//, '')).split('?')[0], clean(x.caption)]); }
    catch (e) { return []; }
  }
  // known: paths of new site articles already saved, and the numbers (31981) of old /News/ pages already saved
  const saved = (known, p) => known.includes(p) || known.includes((p.match(/-(\d+)\.aspx$/i) || [])[1]);
  const out = [];
  async function run(known, pages = 15, stop = true) {
    out.length = 0;
    const todo = [];
    for (let p = 1; p <= pages; p++) {
      const t = await get('/news?yr=-1&pagenumber=' + p); await sleep(GAP);
      if (!t) return {error: 'the News list did not load (try again tomorrow)', read: out.length};
      const L = list(html(t)), fresh = L.filter(x => !saved(known, x.p) && !todo.some(y => y.p === x.p));
      todo.push(...fresh);
      if (stop && !fresh.length && p > 1) break;     // a whole page already saved: everything older is saved too
    }
    for (const x of todo) {
      const t = await get(x.p); await sleep(GAP);
      if (!t) continue;
      const lines = words(html(t)), a = {p: x.p, listed: x.listed, where: x.where, lines, photos: []};
      if (/\/news\//.test(x.p) && !/^\/News\//.test(x.p)) {
        const g = await get(x.p + '/gallery'); await sleep(GAP);
        a.photos = g ? gallery(g) : [];
      }
      out.push(a);
    }
    return out.map((a, i) => ({i, p: a.p, listed: a.listed, lines: a.lines.length, photos: a.photos.length}));
  }
  // Plain text for get_page_text (it carries far more than the javascript tool's answer), a few articles at a time:
  // "@@@ path", "L listed date", "H hash", "N photos captions", "P photo folder", "S file names" (numbered files written
  // as runs, name_[1-174/3]), "T " + each line of words. news_merge_daily.py --text checks every hash.
  const stem = src => src.split('/').pop().replace(/\.(jpe?g|png|webp)$/i, '').replace(/_(display|thumb|original)-\d+$/i, '');
  function runs(stems) {
    const o = []; let r = null;
    for (const s of stems) {
      const m = s.match(/^(.*?)(\d+)(\D*)$/);
      if (r && m && m[1] === r.pre && m[3] === r.suf && +m[2] === r.to + 1 && m[2].length === r.w) { r.to++; continue; }
      r = m ? {pre: m[1], suf: m[3], from: +m[2], to: +m[2], w: m[2].length} : null;
      o.push(r || s);
    }
    return o.map(x => typeof x === 'string' ? x : (x.from === x.to ? x.pre + String(x.from).padStart(x.w, '0') + x.suf : x.pre + '[' + x.from + '-' + x.to + '/' + x.w + ']' + x.suf));
  }
  // "F" carries each photo's exact file name on static.wn.baps-apps.org, in the same order as the names: the part after
  // the name is "_display-<number>.JPG", written short as the number's step from the one before (and the ending only
  // when it changes). A photo in another folder is written whole after "!".
  function files(sorted, dir) {
    let n = 0, ext = null;
    return sorted.map(src => {
      const st = stem(src), d = src.slice(0, src.lastIndexOf('/') + 1), tail = src.slice(d.length + st.length), m = tail.match(/^_display-(\d+)(\.\w+)$/);
      if (d !== dir || !m || !src.slice(d.length).startsWith(st)) return '!' + encodeURI(src);
      const t = String(+m[1] - n) + (m[2] === ext ? '' : m[2]);
      n = +m[1]; ext = m[2];
      return t;
    });
  }
  function text(from = 0, to = out.length) {
    const s = [];
    for (let i = from; i < to && out[i]; i++) {
      const a = out[i];
      const sorted = a.photos.map(p => p[0]).sort((x, y) => stem(x) < stem(y) ? -1 : stem(x) > stem(y) ? 1 : 0);
      let r = runs(sorted.map(stem));
      if (r.join('\n').length > 2500) r = [];      // too many to pass on: the photo count and folder are still saved
      const caps = a.photos.filter(p => p[1]).length, first = (a.photos.find(p => !/^vi\//.test(p[0])) || a.photos[0] || [''])[0], dir = first.slice(0, first.lastIndexOf('/') + 1);   // not a YouTube thumbnail's folder
      const f = r.length ? files(sorted, dir) : [];
      s.push('@@@ ' + a.p, 'L ' + a.listed, 'H ' + hash(JSON.stringify(f.length ? [a.lines, r, dir, f] : [a.lines, r, dir])), 'N ' + a.photos.length + ' ' + caps, 'P ' + dir);
      if (a.refresh) s.push('R 1');
      for (const x of r) s.push('S ' + x);
      if (f.length) s.push('F ' + f.join(' '));
      for (const l of a.lines) s.push('T ' + l);
    }
    return s.join('\n');
  }
  function show(from, to) {          // NEWS.show(0, 5), then get_page_text, then NEWS.show(5, 10) ... (about 10,000 letters each)
    const s = text(from, to);
    document.title = 'News read';
    document.body.innerHTML = '';
    const el = document.createElement('article');
    el.style.whiteSpace = 'pre-wrap';
    el.textContent = s;
    document.body.appendChild(el);
    return s.length;
  }
  // Articles saved before the exact file names were kept (News archive thread, 12 Nov 2026): read only their gallery
  // pages again, gently, so the "F" names can be added. NEWS.refresh([paths from news_merge_daily.py --refresh]).
  async function refresh(paths) {
    out.length = 0;
    for (const p of paths) {
      const g = await get(p + '/gallery'); await sleep(GAP);
      if (g) out.push({p, listed: '', lines: [], photos: gallery(g), refresh: true});
    }
    return out.map((a, i) => ({i, p: a.p, photos: a.photos.length}));
  }
  return {run, refresh, text, show, part: i => out[i], hash};
})();
