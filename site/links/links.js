/* Every tab linked together (Darpan, 28 Oct 2026: "I want all the websites, all the tabs to be linked together
   somehow"). Website only: nothing here touches the daily 2pm picture. tools/web_links.py fills in the places and
   adds this file to the pages at deploy time.

   BDLinks({date, from, to, place, skip}) gives a row of gold buttons for one photo, day or stay, each opening the
   same day, trip or place on another tab (the same look and addresses as the Travels stops):
     Photos         /search/#date=YYYY-MM-DD, or #place=NAME&from=&to= for a stay
     On this day    /#YYYY-MM-DD, Today on that date, at that year
     Calendar       /calendar/#YYYY-MM-DD (that day glows), or #place=NAME&from=&to= (the whole stay glows)
     Travels        /travels/#YYYY-MM-DD, the journey at the stop for that day
     Places         /travels/places/#place=NAME, every visit to that place
     Then and now   /then-and-now/#slug, when that place has a pair
   skip names the page it is on: 'search', 'today', 'calendar', 'travels', 'places' or 'tn'. */
(() => {
  const PLACES = {{PLACES}};   // a place's name in lower case -> its name on the Travels map
  const TN = {{TN}};           // map name -> Then and now page
  const FIRST = '1999-01-01';  // the Calendar and Travels start in 1999
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const day = s => /^\d{4}-\d{2}-\d{2}$/.test(s || '') ? s : '';
  const key = s => s.toLowerCase().replace(/\(.*?\)/g, '').replace(/\bmt\.? /, 'mount ').replace(/\s+/g, ' ').trim();
  const KEYS = {};
  Object.entries(PLACES).forEach(([k, v]) => { KEYS[k] = v; KEYS[key(k)] = v; });
  // "Mayfair, Johannesburg" or "2004, Houston": the first part that is a place on the map
  function mapPlace(s) {
    if (!s) return '';
    const parts = String(s).split(',').map(x => x.trim()).filter(Boolean);
    for (const x of [String(s).trim(), ...parts]) { const k = KEYS[x.toLowerCase()] || KEYS[key(x)]; if (k) return k; }
    return '';
  }
  if (!document.getElementById('bd-go-css')) {
    const st = document.createElement('style'); st.id = 'bd-go-css';
    st.textContent = '.go-row{display:flex;flex-wrap:wrap;gap:6px 8px;justify-content:center;margin:10px 0 0}' +
      '.go-row.left{justify-content:flex-start}' +
      '.go{display:inline-block;padding:6px 13px;border:1px solid var(--go,#d9a441);border-radius:999px;color:var(--go,#d9a441);' +
      'background:none;font:600 11.5px/1.2 Poppins,Arimo,Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;' +
      'text-decoration:none;white-space:nowrap;-webkit-user-select:none;user-select:none}' +
      '.go:hover,.go:focus-visible{background:var(--go,#d9a441);color:var(--go-on,#2a0d14);outline:none}' +
      '@media (max-width:760px){.go-row{gap:6px}.go{padding:5px 11px;font-size:11px}}';
    document.head.append(st);
  }
  window.BDLinks = function ({date, from, to, place, skip, left} = {}) {
    date = day(date); from = day(from); to = day(to) || from;
    if (from && from === to && !date) { date = from; from = to = ''; }
    const at = date || from, p = mapPlace(place), raw = String(place || '').split(',')[0].trim();
    const stay = from && to && (p || raw) ? `place=${encodeURIComponent(p || raw)}&from=${from}&to=${to}` : '';
    const no = new Set([].concat(skip || []));
    const out = [];
    const add = (id, label, href) => { if (!no.has(id) && href) out.push(`<a class="go" href="${esc(href)}">${label} &rsaquo;</a>`); };
    add('search', 'Photos', stay ? '/search/#' + stay : at && '/search/#date=' + at);
    add('today', 'On this day', at && '/#' + at);
    add('calendar', 'Calendar', at >= FIRST && (stay ? '/calendar/#' + stay : '/calendar/#' + at));
    add('travels', 'Travels', at >= FIRST && '/travels/#' + at);
    add('places', 'Places', p && '/travels/places/#place=' + encodeURIComponent(p));
    add('tn', 'Then and now', p && TN[p] && '/then-and-now/#' + TN[p]);
    return out.length ? `<nav class="go-row${left ? ' left' : ''}" aria-label="See this on the other tabs">${out.join('')}</nav>` : '';
  };
  window.BDLinks.place = mapPlace;
})();
