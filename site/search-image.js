// Search by photo (Darpan, 26 Oct 2026: "upload an image, or paste an image, or a part of the image, and our system
// will try and find the same image"). A picture chosen, pasted or dropped onto the search bar is turned into numbers
// by a small open model (DINOv2, from Meta) right here in the visitor's browser, and those numbers are compared with
// the numbers of every photo in the diary (made once on GitHub by .github/workflows/website-image-search.yml).
// Nothing is sent anywhere and nothing costs anything to run. The model and the photo numbers (about 50 MB) are only
// fetched the first time someone searches by photo, then the browser keeps them.
// Put inside the search page by tools/build_search.py, after its own script, whose items and search() it uses.
(() => {
  const $ = id => document.getElementById(id);
  const ORT = new URL('image/', location.href).href;   // onnxruntime-web 1.20.1, kept with the model (no outside CDN)
  const SIDE = 224, MEAN = [0.485, 0.456, 0.406], STD = [0.229, 0.224, 0.225];
  const KEEP = 60;   // the closest photos shown, best first
  const isGu = () => document.documentElement.classList.contains('gu');
  const T = (en, gu) => isGu() ? gu : en;

  // ---------- the button in the search bar and the picture panel under it ----------
  const css = document.createElement('style');
  css.textContent = `
#pic-btn { font: 600 16px var(--serif); color: var(--maroon); background: var(--paper-hi); border: 1.5px solid var(--maroon); border-radius: 8px; padding: 9px 14px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
#pic-btn:hover, #pic-btn.on { background: var(--maroon); color: var(--paper-hi); }
#pic-btn svg { width: 20px; height: 20px; }
@media (max-width: 600px) { #pic-btn { padding: 9px 11px; } #pic-btn span { display: none; } #pic-btn svg { width: 24px; height: 24px; } }   /* phones: the camera alone, beside the search box */
#pic-panel { max-width: 920px; margin: 16px auto 4px; display: flex; gap: 18px; align-items: center; justify-content: center; flex-wrap: wrap; }
#pic-panel[hidden] { display: none; }
#pic-frame { position: relative; touch-action: none; cursor: crosshair; user-select: none; line-height: 0; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 10px rgba(59, 18, 25, .18); }
#pic-frame img { max-width: min(300px, 80vw); max-height: 200px; display: block; }
#pic-box { position: absolute; border: 2px solid #fff; outline: 2px solid var(--maroon); box-shadow: 0 0 0 999px rgba(30, 8, 12, .45); pointer-events: none; }
#pic-box[hidden] { display: none; }
#pic-side { max-width: 420px; text-align: center; text-wrap: balance; }
#pic-side p { margin: 0 0 8px; font: 17px/1.4 var(--serif); color: var(--ink); }
#pic-side .hint { color: var(--muted); font-style: italic; font-size: 15px; }
#pic-side .row { display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }
#pic-side button { font: italic 600 16px var(--serif); color: var(--maroon); background: none; border: 0; border-bottom: 1px solid var(--gold-soft); padding: 4px 2px; cursor: pointer; }
#pic-side button[hidden] { display: none; }
.bar.drop { outline: 3px dashed var(--maroon); outline-offset: -6px; }
.card .same { display: inline-block; font: 700 11px var(--sans, sans-serif); letter-spacing: .12em; text-transform: uppercase; color: #fff; background: var(--maroon); border-radius: 4px; padding: 3px 7px; margin-bottom: 4px; }`;
  document.head.appendChild(css);

  const icon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 8a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="13" r="4"/></svg>';
  $('q').insertAdjacentHTML('afterend', `<button id="pic-btn" type="button" title="Search with a photo: choose one, paste one, or drop one here" aria-label="Search by photo">${icon}<span>${T('Search by photo', 'ફોટાથી શોધો')}</span></button><input id="pic-file" type="file" accept="image/*" hidden>`);
  document.querySelector('.bar').insertAdjacentHTML('afterend', `<div id="pic-panel" class="wrap" hidden>
    <div id="pic-frame"><img id="pic-img" alt="Your picture"><div id="pic-box" hidden></div></div>
    <div id="pic-side"><p id="pic-msg"></p><p class="hint" id="pic-hint"></p>
      <div class="row"><button id="pic-see" type="button" hidden></button><button id="pic-whole" type="button" hidden></button><button id="pic-other" type="button"></button><button id="pic-close" type="button"></button></div></div></div>`);
  const btn = $('pic-btn'), file = $('pic-file'), panel = $('pic-panel'), img = $('pic-img'), box = $('pic-box'), frame = $('pic-frame');
  const words = () => {
    btn.querySelector('span').textContent = T('Search by photo', 'ફોટાથી શોધો');
    $('pic-hint').textContent = T('To find only part of it, draw a box over that part.', 'ફક્ત એક ભાગ શોધવા, તે ભાગ પર ચોરસ દોરો.');
    $('pic-whole').textContent = T('Use the whole picture', 'આખો ફોટો વાપરો');
    $('pic-other').textContent = T('Another picture', 'બીજો ફોટો');
    $('pic-see').textContent = T('See the photos ↓', 'ફોટા જુઓ ↓');
    $('pic-close').innerHTML = '&#x2715; ' + T('Close', 'બંધ કરો');
  };
  words();
  new MutationObserver(words).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  const say = s => { $('pic-msg').innerHTML = s; };

  // ---------- the model and the photo numbers, fetched the first time only ----------
  let ready = null, sess, meta, vecs, keys, lookup = null;
  function get() {
    if (ready) return ready;
    ready = (async () => {
      if (!window.ort) await new Promise((ok, bad) => { const s = document.createElement('script'); s.src = ORT + 'ort.min.js'; s.onload = ok; s.onerror = bad; document.head.appendChild(s); });
      ort.env.wasm.wasmPaths = ORT;
      meta = await (await fetch('image/meta.json')).json();
      const parts = [fetch('image/' + meta.model), ...meta.vecs.map(f => fetch('image/' + f)), fetch('image/keys.json')];
      let have = 0;
      const total = meta.bytes;
      const read = async r => {   // read while showing how much has come
        if (!r.ok) throw new Error(r.status);
        const rd = r.body.getReader(), chunks = [];
        for (;;) { const { done, value } = await rd.read(); if (done) break; chunks.push(value); have += value.length; say(T(`Getting ready, first time only: <b>${Math.min(99, Math.round(100 * have / total))}%</b>`, `પહેલી વાર તૈયાર થાય છે: <b>${Math.min(99, Math.round(100 * have / total))}%</b>`)); }
        return new Blob(chunks).arrayBuffer();
      };
      const bufs = await Promise.all((await Promise.all(parts)).map(read));
      sess = await ort.InferenceSession.create(bufs[0], { executionProviders: ['wasm'] });
      const all = new Uint8Array(meta.n * 96);
      let at = 0;
      for (const b of bufs.slice(1, -1)) { all.set(new Uint8Array(b), at); at += b.byteLength; }
      vecs = new Int32Array(all.buffer);   // 24 words of 32 yes/no answers per photo
      keys = JSON.parse(new TextDecoder().decode(bufs.at(-1)));
    })();
    ready.catch(() => { ready = null; });
    return ready;
  }

  // the picture (or the part in the box) as the model wants it: 224 x 224, colours scaled like the training photos
  function pixels(rect) {
    let src = img, sx = rect.x, sy = rect.y, sw = rect.w, sh = rect.h;
    // shrink by halves first, so a big phone photo is smoothed the way the photos on GitHub were
    while (sw > SIDE * 2 && sh > SIDE * 2) {
      const c = document.createElement('canvas'); c.width = Math.round(sw / 2); c.height = Math.round(sh / 2);
      const x = c.getContext('2d'); x.imageSmoothingQuality = 'high'; x.drawImage(src, sx, sy, sw, sh, 0, 0, c.width, c.height);
      src = c; sx = 0; sy = 0; sw = c.width; sh = c.height;
    }
    const c = document.createElement('canvas'); c.width = c.height = SIDE;
    const x = c.getContext('2d'); x.imageSmoothingQuality = 'high'; x.drawImage(src, sx, sy, sw, sh, 0, 0, SIDE, SIDE);
    const d = x.getImageData(0, 0, SIDE, SIDE).data, out = new Float32Array(3 * SIDE * SIDE), n = SIDE * SIDE;
    for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) out[k * n + i] = (d[i * 4 + k] / 255 - MEAN[k]) / STD[k];
    return out;
  }

  let pick = null, chosen = null, busy = 0;
  async function find(rect) {
    const job = ++busy;
    say(T('Looking…', 'શોધે છે…'));
    try { await get(); } catch (e) { console.error(e); say(T('Search by photo did not load. Check the internet and try again.', 'ફોટાથી શોધ લોડ ન થઈ. ઇન્ટરનેટ તપાસી ફરી પ્રયત્ન કરો.')); return; }
    if (job !== busy) return;
    const out = await sess.run({ [sess.inputNames[0]]: new ort.Tensor('float32', pixels(rect), [1, 3, SIDE, SIDE]) });
    if (job !== busy) return;
    // the model gives 257 lists of 384 numbers: the whole picture first, then its 256 parts. Like the photos on
    // GitHub (tools/image_index.py build), the picture becomes 768 yes/no answers: is each number of the whole
    // picture, and of the average of its parts, above the usual value? Photos with the most answers the same come first.
    const t = out[sess.outputNames[0]].data, F = 384, P = t.length / F - 1;
    const cls = Array.from(t.subarray(0, F)), avg = new Array(F).fill(0);
    for (let p = 1; p <= P; p++) for (let i = 0; i < F; i++) avg[i] += t[p * F + i] / P;
    const unit = v => { const l = Math.hypot(...v); return v.map(x => x / l); };
    const ans = [...unit(cls).map((v, i) => v > meta.mc[i]), ...unit(avg).map((v, i) => v > meta.mm[i])];
    const q = new Int32Array(24);   // packed the same way as numpy packbits: first answer in the highest bit of each byte
    const bytes = new Uint8Array(q.buffer);
    ans.forEach((v, i) => { if (v) bytes[i >> 3] |= 128 >> (i & 7); });
    const pop = x => { x -= (x >>> 1) & 0x55555555; x = (x & 0x33333333) + ((x >>> 2) & 0x33333333); return (((x + (x >>> 4)) & 0x0f0f0f0f) * 0x01010101) >>> 24; };
    const n = meta.n, score = new Uint16Array(n);
    for (let r = 0, o = 0; r < n; r++, o += 24) { let d = 0; for (let j = 0; j < 24; j++) d += pop(vecs[o + j] ^ q[j]); score[r] = 768 - d; }
    // the best KEEP, without sorting every photo: count how many photos have each score, then take from the top
    const hist = new Uint32Array(769);
    for (const v of score) hist[v]++;
    let bar = 768, got = 0;
    while (bar > 0 && got + hist[bar] < KEEP) got += hist[bar--];
    const best = [];
    for (let r = 0; r < n; r++) if (score[r] >= bar) best.push([r, score[r]]);
    best.sort((a, b) => b[1] - a[1]);
    chosen = best.slice(0, KEEP * 2).map(([r, s]) => [keys[r], s]);
    say(T('The closest photo is first, then the ones most like it.', 'સૌથી નજીકનો ફોટો પહેલો છે, પછી તેના જેવા ફોટા.'));
    $('pic-see').hidden = false;
    $('q').value = '';
    search();
  }
  // used by search() in the page: the photos picked by the picture, and their score (found again as more years load)
  function resolve() {
    if (!lookup || lookup.from !== items.length) { lookup = new Map(); lookup.from = items.length; for (const it of items) if (it.kind === 'photo') lookup.set(it.g[3] + '/' + it.file, it); }
    pick = new Map();
    for (const [k, s] of chosen) { const it = lookup.get(k); if (it) pick.set(it, s); }
    return pick;
  }
  window.picSearch = () => chosen ? resolve() : null;
  window.picSame = it => chosen && pick && pick.get(it) === chosen[0][1];

  // ---------- choosing, pasting, dropping, drawing a box ----------
  let natural = null;
  function open(blob) {
    if (!blob || !/^image\//.test(blob.type)) return;
    const url = URL.createObjectURL(blob);
    img.onload = () => {
      natural = { x: 0, y: 0, w: img.naturalWidth, h: img.naturalHeight };
      box.hidden = true; $('pic-whole').hidden = true; $('pic-see').hidden = true;
      panel.hidden = false; btn.classList.add('on');
      // a new picture is a fresh search: the words and filters are emptied (they can be picked again to narrow it)
      ['q', 'fest', 'place', 'act', 'year', 'month', 'day', 'from', 'to'].forEach(id => $(id) && ($(id).value = ''));
      find(natural);
    };
    img.src = url;
  }
  function close() {
    panel.hidden = true; btn.classList.remove('on'); pick = chosen = null; busy++;
    search();
  }
  window.picClose = () => { if (!panel.hidden) close(); };
  btn.addEventListener('click', () => { file.value = ''; file.click(); });
  $('pic-other').addEventListener('click', () => { file.value = ''; file.click(); });
  $('pic-close').addEventListener('click', close);
  $('pic-see').addEventListener('click', () => $('years').scrollIntoView({ behavior: 'smooth' }));   // the photos found, under the filters
  $('pic-whole').addEventListener('click', () => { box.hidden = true; $('pic-whole').hidden = true; find(natural); });
  file.addEventListener('change', () => open(file.files[0]));
  document.addEventListener('paste', e => {
    const f = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith('image/'));
    if (f) { e.preventDefault(); open(f.getAsFile()); }
  });
  const bar = document.querySelector('.bar');
  addEventListener('dragover', e => { if ([...e.dataTransfer.types].includes('Files')) { e.preventDefault(); bar.classList.add('drop'); } });
  addEventListener('dragleave', e => { if (!e.relatedTarget) bar.classList.remove('drop'); });
  addEventListener('drop', e => { bar.classList.remove('drop'); const f = [...e.dataTransfer.files].find(f => f.type.startsWith('image/')); if (f) { e.preventDefault(); open(f); } });

  let start = null;
  const at = e => { const r = img.getBoundingClientRect(); return { x: Math.min(Math.max(e.clientX - r.left, 0), r.width), y: Math.min(Math.max(e.clientY - r.top, 0), r.height), r }; };
  frame.addEventListener('pointerdown', e => { start = at(e); frame.setPointerCapture(e.pointerId); e.preventDefault(); });
  frame.addEventListener('pointermove', e => {
    if (!start) return;
    const p = at(e);
    Object.assign(box.style, { left: Math.min(start.x, p.x) + 'px', top: Math.min(start.y, p.y) + 'px', width: Math.abs(p.x - start.x) + 'px', height: Math.abs(p.y - start.y) + 'px' });
    box.hidden = false;
  });
  frame.addEventListener('pointerup', e => {
    if (!start) return;
    const p = at(e), k = img.naturalWidth / p.r.width;
    const w = Math.abs(p.x - start.x), h = Math.abs(p.y - start.y), x = Math.min(start.x, p.x), y = Math.min(start.y, p.y);
    start = null;
    if (w < 12 || h < 12) { box.hidden = true; return; }   // a tap, not a box
    $('pic-whole').hidden = false;
    find({ x: x * k, y: y * k, w: w * k, h: h * k });
  });
})();
