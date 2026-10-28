// Who was with Bapa (Darpan, 26 Oct 2026: "search by people's names, do it"). Typing a person's name into the search
// bar, or asking "When did Bapa meet Narendra Modi?", gives a card with every day Bapa was with them, and the results
// become the photos of Bapa with them. The names are the swamis, leaders and devotees the baps.org captions name
// (data/people.json, from tools/search_people.py), with every spelling the captions use. A name typed a little
// differently still finds them (Tyagvallabh or Tyagavallabh, Bharwad or Bharvad, Narendrabhai or Narendra).
// No AI and nothing to pay for. Put inside the search page by tools/build_search.py, after site/search-ask.js, whose
// helpers (window.askKit) it uses; Ask the diary calls window.askPerson first.
(() => {
  const $ = id => document.getElementById(id);
  let PEOPLE = [];
  fetch('data/people.json').then(r => r.json()).then(list => {
    PEOPLE = list.map(([name, kind, spell, photos, days, first, last]) => {
      const stem = kind === 's' ? name.replace(/ Swami$/, '') : '';
      const keys = new Set(spell.map(sound));
      keys.add(sound(name));
      if (stem.length >= 8) keys.add(sound(stem));   // Viveksagar on its own finds Viveksagar Swami; short ones (Doctor) need the Swami
      const rx = new RegExp('(?:^|[^a-z])(?:' + spell.map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).sort((a, b) => b.length - a.length).join('|') + ')');
      return { name, kind, spell, photos, days, first, last, keys: [...keys], rx };
    });
    const dl = document.createElement('datalist');   // names offered as you type
    dl.id = 'people-list';
    dl.innerHTML = PEOPLE.map(p => `<option value="${p.name}">`).join('');
    document.body.appendChild(dl);
    $('q').setAttribute('list', 'people-list');
    if (window.search && $('q').value.trim()) search();
  }).catch(e => console.error(e));

  // the same spelling key as tools/search_people.py: Bharwad and Bharvad, Shree and Shri look alike
  function sound(s) {
    s = s.toLowerCase().replace(/[^a-z]/g, '');
    for (const [a, b] of [['w', 'v'], ['ph', 'f'], ['sh', 's'], ['kh', 'k'], ['gh', 'g'], ['th', 't'], ['dh', 'd'], ['bh', 'b'], ['ch', 'c'],
      ['jh', 'j'], ['ee', 'i'], ['oo', 'u'], ['aa', 'a'], ['y', 'i'], ['z', 'j'], ['q', 'k']]) s = s.split(a).join(b);
    return s.replace(/(.)\1+/g, '$1');
  }
  function dist(a, b) {   // letters to change, add or leave out to turn a into b
    if (Math.abs(a.length - b.length) > 2) return 9;
    let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      for (let j = 1; j <= b.length; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[b.length];
  }
  // the words around a name in a question
  const FILLER = /\b(when|where|what|which|who|whom|how|many|much|often|times?|did|does|do|was|were|is|are|has|have|had|bapa'?s?|swamishri|pramukh swami maharaj|mahant swami maharaj|maharaj|guru|meet|meets|met|meeting|see|saw|seen|with|and|together|show|tell|me|us|list|find|give|all|every|photos?|pictures?|pics?|darshan|of|the|a|an|in|on|at|to|for|by|from|ever|first|last|time|days?|years?|pujya|param|sadguru|shri|shree|sri|hh|his|holiness|honourable|hon|mr|mrs|dr|please)\b/g;
  function who(raw) {
    if (!PEOPLE.length) return null;
    const q = ' ' + raw.toLowerCase().replace(/[’`]/g, "'").replace(/[?!.,;:()"]/g, ' ') + ' ';
    const years = (q.match(/\b(19[5-9]\d|20[0-3]\d)\b/g) || []).map(Number);
    const rest = q.replace(/\b\d+\b/g, ' ').replace(FILLER, ' ').replace(/\s+/g, ' ').trim();
    const k = sound(rest);
    if (k.length < 5) return null;
    const allowed = k.length <= 6 ? 0 : k.length <= 10 ? 1 : 2;
    let best = null, bestD = 99;
    for (const p of PEOPLE) {
      let d = 99;
      for (const key of p.keys) { d = Math.min(d, dist(k, key)); if (!d) break; }
      if (d < bestD || (d === bestD && best && p.photos > best.photos)) { best = p; bestD = d; }
    }
    if (bestD > allowed) return null;
    return { p: best, years, how: /\bfirst\b|earliest/.test(q) ? 'first' : /\b(last|latest|most recent)\b/.test(q) ? 'last' : '' };
  }

  let cache = { p: null, n: -1, list: [] };
  function together(p) {   // every photo of Bapa with this person, and every On this day story that names them
    if (cache.p === p && cache.n === items.length) return cache.list;
    const list = items.filter(r => (r.kind === 'photo' ? r.b : r.kind === 'post') && p.rx.test(r.kind === 'photo' ? r.cap.toLowerCase() : r.hay));
    cache = { p, n: items.length, list };
    return list;
  }

  window.askPerson = function (raw) {
    const W = who(raw);
    if (!W || !window.askKit) return null;
    const { esc, t, gd, num, plural, range, fmt, guruOf, GURU, gurus, card } = window.askKit;
    const { p, years } = W;
    const inYears = r => !years.length || years.includes(+r.d.slice(0, 4));
    const all = together(p).filter(inYears), photos = all.filter(r => r.kind === 'photo');
    const keep = r => all.includes(r);
    const when = years.length ? ' in ' + years.join(', ') : '';
    if (!photos.length) return { html: card({ raw }, `The diary has no photos of Bapa with ${esc(p.name)}${when}.`, '',
      [years.length ? 'Try without the year.' : 'Try another spelling of the name.', '']), keep: () => false };
    // one row a day: where, what the caption says, and that day's first photo of them together
    const days = new Map();
    for (const r of photos) {
      const d = days.get(r.d) || { d: r.d, n: 0, r };
      d.n++;
      days.set(r.d, d);
    }
    let list = [...days.values()];
    if (W.how === 'last') list.reverse();
    const dates = list.map(x => x.d).sort(), span = range(dates[0], dates.at(-1));
    const per = { P: [], M: [] };
    for (const x of list) per[guruOf(x.d)].push(x.d);
    const say = ds => { ds = [...ds].sort(); return ds.length ? `${plural(ds.length, 'day')}, ${ds.length > 1 ? range(ds[0], ds.at(-1)) : fmt(ds[0])}` : ''; };
    const sayGu = ds => ds.length ? gd(`${ds.length} દિવસ`) : '';
    const where = r => r.g[2].split(',').map(c => c.trim()).find(c => c && !/^\d+$/.test(c)) || '';
    const row = x => {
      const r = x.r, small = `${PHOTOS}s/${r.g[3]}/${r.file}`;
      return `<div class="ask-row"><span class="yr">${x.d.slice(0, 4)}</span><span class="ask-cu who-cu" style="background-image:url('${small}')" role="img" aria-label="${esc(r.cap)}"></span>`
        + `<span class="tx"><b>${esc(where(r))}</b> <span class="when">${fmt(x.d)}</span><span class="c">${esc(r.cap)}</span></span>`
        + `<span class="who">${GURU[guruOf(x.d)]}<br><button type="button" class="ask-see who-see" data-day="${x.d}">${t(`See ${plural(x.n, 'photo')}`, gd(`${num(x.n)} ફોટા જુઓ`))}</button></span></div>`;
    };
    const limit = 8, first = list[0];
    const head = W.how === 'first' ? `Bapa first met ${esc(p.name)} on ${fmt(first.d)}, in ${esc(where(first.r))}.`
      : W.how === 'last' ? `Bapa last met ${esc(p.name)} on ${fmt(first.d)}, in ${esc(where(first.r))}.`
      : `Bapa was with ${esc(p.name)} on ${plural(list.length, 'day')}${list.length > 1 ? ', ' + span : ', ' + fmt(first.d)}${when}.`;
    const headGu = `બાપા સાથે ${esc(p.name)}: ${gd(`${list.length}`)} દિવસ${when ? gd(when.replace(' in ', ', ')) : ''}.`;
    const html = card({ raw }, head, headGu,
      [`Found by name in the photo captions. The ${plural(photos.length, 'photo')} of Bapa with ${esc(p.name)} are below.`,
        `ફોટાનાં વર્ણનમાં નામ પરથી. બાપા સાથેના ${gd(num(photos.length))} ફોટા નીચે છે.`],
      gurus({ P: say(per.P), M: say(per.M) }, { P: sayGu(per.P), M: sayGu(per.M) })
      + `<h3 class="ask-h">${t(list.length === 1 ? 'The day together' : 'Every day together', 'સાથેના દિવસો')}</h3><div class="ask-rows">${list.slice(0, limit).map(row).join('')}`
      + `<div class="ask-rest" hidden>${list.slice(limit).map(row).join('')}</div></div>`
      + (list.length > limit ? `<button type="button" class="ask-more">${t(`Show all ${list.length}`, gd(`બધાં ${list.length} જુઓ`))}</button>` : ''));
    return { html, keep, person: p };
  };

  // See photos: that day's photos of them together, in the results below
  document.addEventListener('click', e => {
    const s = e.target.closest('.who-see'); if (!s) return;
    e.stopPropagation();
    $('from').value = $('to').value = s.dataset.day;
    search();
    window.scrollTo({ top: $('years').offsetTop - 10, behavior: 'smooth' });
  }, true);

  const css = document.createElement('style');
  css.textContent = `.ask-cu.who-cu { background-size: cover; background-position: center 30%; }
#q::-webkit-calendar-picker-indicator { display: none !important; }`;   // no dropdown arrow from the name list
  document.head.appendChild(css);
})();
