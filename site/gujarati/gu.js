/* bapas-diary.com in Gujarati: the English / ગુજરાતી switch (Darpan, 25 Oct 2026: "a button that shows the whole
   website in Gujarati"). Added to the <head> of every page by tools/web_gujarati.py at deploy time. Website only:
   nothing here touches the daily 2pm picture.
   The pages themselves stay as they are, in English. When Gujarati is chosen, this script swaps the words on the
   screen for their Gujarati ones from /gu/words.json (menus, buttons, dates, places, the BAPS calendar, photo
   captions and On this day lines), including words the pages add later and words drawn on the globe. Anything with
   no Gujarati yet stays in English, whole, never half and half. The choice is remembered on this phone or computer
   (localStorage bapas-diary-lang); a link ending in ?lang=gu opens in Gujarati too. */
(() => {
  const KEY = 'bapas-diary-lang', root = document.documentElement;
  const store = {
    get: () => { try { return localStorage.getItem(KEY); } catch (e) { return null; } },
    set: v => { try { localStorage.setItem(KEY, v); } catch (e) {} },
  };
  const asked = new URLSearchParams(location.search).get('lang');
  if (asked === 'gu' || asked === 'en') store.set(asked);
  let on = store.get() === 'gu';

  /* ---------- the words ---------- */
  let W = null;                                   // English -> Gujarati, from /gu/words.json
  const DIG = '૦૧૨૩૪૫૬૭૮૯';
  const digits = s => s.replace(/[0-9]/g, d => DIG[d]);
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const GM = ['જાન્યુઆરી', 'ફેબ્રુઆરી', 'માર્ચ', 'એપ્રિલ', 'મે', 'જૂન', 'જુલાઈ', 'ઑગસ્ટ', 'સપ્ટેમ્બર', 'ઑક્ટોબર', 'નવેમ્બર', 'ડિસેમ્બર'];
  const GMS = ['જાન્યુ', 'ફેબ્રુ', 'માર્ચ', 'એપ્રિલ', 'મે', 'જૂન', 'જુલાઈ', 'ઑગ', 'સપ્ટે', 'ઑક્ટો', 'નવે', 'ડિસે'];
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const GD = ['રવિવાર', 'સોમવાર', 'મંગળવાર', 'બુધવાર', 'ગુરુવાર', 'શુક્રવાર', 'શનિવાર'];
  const GDS = ['રવિ', 'સોમ', 'મંગળ', 'બુધ', 'ગુરુ', 'શુક્ર', 'શનિ'];
  // single words that may sit anywhere inside a date or a short label
  const T = {to: 'થી', of: '/', and: 'અને', today: 'આજ સુધી', TH: '', ST: '', ND: '', RD: ''};
  MONTHS.forEach((m, i) => {
    T[m] = T[m.toUpperCase()] = GM[i];
    T[m.slice(0, 3)] = T[m.slice(0, 3).toUpperCase()] = GMS[i];
    if (m === 'September') T.Sept = GMS[i];
  });
  DAYS.forEach((d, i) => { T[d] = T[d.toUpperCase()] = GD[i]; T[d.slice(0, 3)] = T[d.slice(0, 3).toUpperCase()] = GDS[i]; });
  const word = s => (W && W[s]) || null;
  // "Ahmedabad" -> "અમદાવાદમાં" (in Ahmedabad)
  const inPlace = p => { const g = tr(p); return g === p ? null : g + 'માં'; };

  // whole sentences built by the pages, English pattern -> Gujarati
  const P = [
    [/^(\d[\d,]*) years and (\d[\d,]*) photos from this day\. Each card fades through all of its year's photos\. Tap a card to see them all\.$/,
      m => `આ દિવસનાં ${m[1]} વર્ષ અને ${m[2]} ફોટા. દરેક કાર્ડમાં તે વર્ષના બધા ફોટા વારાફરતી આવે છે. બધા જોવા કાર્ડ પર ટૅપ કરો.`],
    [/^(\d+) years remembered on this day\.$/, m => `આ દિવસનાં ${m[1]} વર્ષની સ્મૃતિ.`],
    [/^In (\d{4}) this date is$/, m => `${m[1]}માં આ તારીખે`],
    [/^Every photo from (.+)$/, m => `${tr(m[1])}ના બધા ફોટા`],
    [/^(\d[\d,]*) photos?, year by year$/, m => `${m[1]} ફોટા, વર્ષ પ્રમાણે`],
    [/^From the same trip, (.+)$/, m => `એ જ વિચરણમાંથી, ${tr(m[1])}`],
    [/^From these days, (.+)$/, m => `આ દિવસોમાંથી, ${tr(m[1])}`],
    [/^(\d+), (.+): see all (\d+) photos$/, m => `${m[1]}, ${tr(m[2])}: બધા ${m[3]} ફોટા જુઓ`],
    [/^(\d[\d,]*) of (\d[\d,]*)$/, m => `${m[1]} / ${m[2]}`],
    [/^Bapa was in (.+?), (\d.*)$/, m => inPlace(m[1]) && `બાપા ${inPlace(m[1])} હતા, ${tr(m[2])}`],
    [/^Bapa was in (.+)$/, m => inPlace(m[1]) && `બાપા ${inPlace(m[1])} હતા`],
    [/^(.+)\. Open this day's photos$/, m => `${tr(m[1])}. આ દિવસના ફોટા ખોલો`],
    [/^Go to (\d{4})$/, m => `${m[1]} પર જાઓ`],
    [/^Bapa aged (\d+)$/, m => `બાપાની ઉંમર ${m[1]} વર્ષ`],
    [/^See all (\d[\d,]*) photos from this day$/, m => `આ દિવસના બધા ${m[1]} ફોટા જુઓ`],
    [/^Day (\d+) of (\d+) with a close darshan$/, m => `નજીકનાં દર્શનનો દિવસ ${m[1]} / ${m[2]}`],
    [/^(Pramukh Swami Maharaj|Mahant Swami Maharaj) on (.+)$/, m => `${tr(m[2])}ના રોજ ${tr(m[1])}`],
    [/^(\d+) a second$/, m => `સેકન્ડમાં ${m[1]}`],
    [/^A smruti of Bapa for (.+?) 🙏🏽$/, m => `${tr(m[1])} ની બાપાની સ્મૃતિ 🙏🏽`],
    [/^A smruti of Bapa for (.+?)\. Open His diary to see where He was\.$/, m => `${tr(m[1])} ની બાપાની સ્મૃતિ. તેઓ ક્યાં હતા તે જોવા તેમની ડાયરી ખોલો.`],
    [/^The picture of (.+)$/, m => `${tr(m[1])} નો ફોટો`],
    [/^(.+) in Bapa's Diary$/, m => `બાપાની ડાયરીમાં ${tr(m[1])}`],
    [/^Darshan on (.+)$/, m => `${tr(m[1])}નાં દર્શન`],
    [/^The link may be old or mistyped\. But Bapa has darshan waiting for you, from (.+) through the years\.$/,
      m => `લિંક જૂની કે ખોટી હશે. પણ વર્ષોવર્ષના ${tr(m[1])}નાં બાપાનાં દર્શન તમારી રાહ જુએ છે.`],
    [/^My favourite darshans of Bapa, (\d+) darshans? 🙏🏽$/, m => `બાપાનાં મારાં મનપસંદ ${m[1]} દર્શન 🙏🏽`],
    [/^(\d+) darshans?, chosen with love\. Tap a heart to keep any of them for yourself\.$/, m => `પ્રેમથી પસંદ કરેલાં ${m[1]} દર્શન. તમારે સાચવવું હોય તે પર હૃદય દબાવો.`],
    [/^(\d+) darshans?, kept on this phone or computer\.$/, m => `${m[1]} દર્શન, આ ફોન કે કમ્પ્યુટરમાં સચવાયાં.`],
    [/^Every vicharan photo on baps\.org from (\d+) to (\d+) \(([\d,]+) photos\), ([\d,]+) On this day stories and the BAPS calendar for ([\d,]+) days, all mixed together by date\.$/,
      m => `baps.org પરના ${m[1]} થી ${m[2]} સુધીના વિચરણના બધા ફોટા (${m[3]} ફોટા), આ દિવસના ${m[4]} પ્રસંગો અને ${m[5]} દિવસનું બી.એ.પી.એસ. કેલેન્ડર, બધું તારીખ પ્રમાણે સાથે.`],
    [/^Every vicharan photo on baps\.org from (\d+) to (\d+)$/, m => `baps.org પરના ${m[1]} થી ${m[2]} સુધીના વિચરણના બધા ફોટા`],   // Search intro (25 Oct, calmer look)
    [/^(Every vicharan photo .+ all mixed together by date\.) Search for words, or pick a year, month, day or range of dates\.$/,
      m => tr(m[1]) !== m[1] && `${tr(m[1])} શબ્દો શોધો, કે વર્ષ, મહિનો, દિવસ કે તારીખો પસંદ કરો.`],
    [/^(.+) \((.+)\)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} (${N(m[2])})`],
    [/^›\s+(.+)$/, m => tr(m[1]) !== m[1] && `› ${tr(m[1])}`],   // a page name after the menu arrow
    // Travels Places, Then and now, and the offline version (25 Oct)
    [/^([\d,]+) (visits?|days?|photos?|places?|countries|country)$/, m => `${m[1]} ${{visit: 'મુલાકાત', visits: 'મુલાકાતો', day: 'દિવસ', days: 'દિવસ', photo: 'ફોટો', photos: 'ફોટા', place: 'સ્થળ', places: 'સ્થળો', country: 'દેશ', countries: 'દેશો'}[m[2]]}`],
    [/^See all ([\d,]+) photos from (.+)$/, m => N(m[2]) && `${N(m[2])}ના બધા ${m[1]} ફોટા જુઓ`],
    [/^([\d,]+) places in ([\d,]+) countries, (\d{4}) to (\d{4})\. Tap a gold dot on the globe, or find a place by name\.$/,
      m => `${m[2]} દેશોમાં ${m[1]} સ્થળો, ${m[3]}થી ${m[4]}. ગ્લોબ પર સોનેરી ટપકું દબાવો, કે નામથી સ્થળ શોધો.`],
    [/^Tap below to also keep the next (\d+) days of darshan with their photos, all of Search, Travels and\s+Bapa through the years\. It needs about (\d+) MB, so WiFi is best\.$/,
      m => `નીચે દબાવો તો આવતા ${m[1]} દિવસનાં દર્શન તેમના ફોટા સાથે, આખું શોધો, વિચરણ અને વર્ષોવર્ષ પણ સચવાઈ જશે. આશરે ${m[2]} MB જોઈશે, એટલે WiFi સારું.`],
    [/^on (\d+) (\w+)\. It tops itself up each day you have internet\.(?: Using about (\d+) MB\.)?$/,
      m => T[m[2]] && `${m[1]} ${T[m[2]]}ના રોજ. જે દિવસે ઇન્ટરનેટ હોય તે દિવસે તે જાતે નવું ઉમેરે છે.${m[3] ? ` આશરે ${m[3]} MB વપરાય છે.` : ''}`],
    [/^Saving ([\d,]+) of ([\d,]+)…$/, m => `${m[2]}માંથી ${m[1]} સચવાયા…`],
    [/^Vikram Samvat (\d+)$/, m => `વિક્રમ સંવત ${m[1]}`],
    [/^V\.S\. (\d+)$/, m => `વિ.સં. ${m[1]}`],
    [/^(.+)'s Birthday$/, m => tr(m[1]) !== m[1] && `${tr(m[1])} પ્રાગટ્ય દિન`],
    [/^(.+) \(([\d,]+)\)$/, m => tr(m[1]) !== m[1] && `${tr(m[1])} (${m[2]})`],
    [/^(Pramukh Swami Maharaj|Mahant Swami Maharaj|Swamishri|Yogiji Maharaj) in (.+?): (.+)$/, m => N(m[3]) && inPlace(m[2]) && `${tr(m[1])} ${inPlace(m[2])}: ${N(m[3])}`],
    // photo captions: who + what is happening (people.tsv, doing.tsv)
    [/^(.+?) doing (samip )?darshan of (?:the )?(.+)$/, m => N(m[1]) && N(m[3]) && `${N(m[1])} ${N(m[3])}નાં ${m[2] ? 'સમીપ ' : ''}દર્શન કરે છે`],
    [/^(.+?) doing (.+?)'s puja darshan$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં પૂજાદર્શન કરે છે`],
    [/^(.+?) (?:engrossed|engaged) in (?:the )?darshan of (?:the )?(.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં દર્શનમાં લીન`],
    [/^(.+?) (?:engrossed|engaged) in (?:the )?(.+?)'s darshan$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં દર્શનમાં લીન`],
    [/^(.+?) (?:on his way for|arrives for) (.+?)'s darshan$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં દર્શને પધારે છે`],
    [/^(.+?) offers? thal to (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ને થાળ ધરાવે છે`],
    [/^Thal is offered to (.+)$/, m => N(m[1]) && `${N(m[1])}ને થાળ ધરાવાય છે`],
    [/^(.+?) offers? a flower to (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ને પુષ્પ અર્પે છે`],
    [/^(.+?) places? a flower at the feet of (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં ચરણોમાં પુષ્પ મૂકે છે`],
    [/^(.+?) performs? (?:the )?abhishek of (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નો અભિષેક કરે છે`],
    [/^(.+?) performs? (?:the )?pujan of (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નું પૂજન કરે છે`],
    [/^(.+?) touches his eyes after (?:reverently |reverentially )?touching the holy (?:charanarvind|charnarvind|feet) of (.+)$/,
      m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં ચરણારવિંદનો સ્પર્શ કરી નેત્રે અડાડે છે`],
    [/^(.+?) (?:reverently |reverentially )?touches (?:the )?holy (?:charanarvind|charnarvind|feet) of (.+)$/,
      m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નાં ચરણારવિંદનો સ્પર્શ કરે છે`],
    [/^(.+?) blesses (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ને આશીર્વાદ આપે છે`],
    [/^(.+?) honou?rs? (.+?) with (?:a )?garlands?( and (?:a )?shawl)?$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ને હાર${m[3] ? ' અને શાલ' : ''} પહેરાવે છે`],
    [/^(.+?) welcomes? (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}નું સ્વાગત કરે છે`],
    [/^(.+?) visits (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ની મુલાકાત લે છે`],
    [/^(.+?) arrives (?:at|in) (.+)$/, m => N(m[1]) && inPlace(m[2]) && `${N(m[1])} ${inPlace(m[2])} પધારે છે`],
    [/^(.+?) in conversation with (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])} સાથે વાતચીત કરે છે`],
    [/^(.+?)'s (morning |daily |evening )?puja$/, m => N(m[1]) && `${N(m[1])}ની ${{'morning ': 'પ્રાતઃ', 'daily ': 'નિત્ય', 'evening ': 'સાયં '}[m[2]] || ''}પૂજા`],
    [/^(.+?) with (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])} સાથે`],
    [/^(?:A )?skit presentations? (?:by|of) (.+?)(?: before Swamishri| in front of Swamishri)?$/i, m => N(m[1]) && `${N(m[1])} દ્વારા સંવાદની રજૂઆત`],
    [/^(Annakut|Thal|Flowers?|Chandan garments) (?:is |are )?offered to (.+)$/, m => N(m[2]) &&
      `${N(m[2])}ને ધરાવેલ${{Annakut: 'ો અન્નકૂટ', Thal: 'ો થાળ', Flower: 'ું પુષ્પ', Flowers: 'ાં પુષ્પો', 'Chandan garments': 'ા ચંદનના વાઘા'}[m[1]]}`],
    [/^(.+?) (?:adorned|decorated) (?:in|with) (?:chandan garments|sandalwood paste|chandan)(?: \((?:chandan|sandalwood paste)\))?$/, m => N(m[1]) && `ચંદનના શણગારમાં ${N(m[1])}`],
    [/^(.+?) - Chandan adornment$/, m => N(m[1]) && `ચંદનના શણગારમાં ${N(m[1])}`],
    [/^(?:A colou?rful )?Nagar ?yatra (?:\(procession\) )?(?:of the murtis )?(?:took place )?(?:through|on|in) the streets of (.+?)\.?$/i, m => N(m[1]) && `${N(m[1])}ની શેરીઓમાં નગરયાત્રા`],
    [/^(.+?) (?:addresses|delivers a discourse to) the (.+)$/, m => N(m[1]) && N(m[2]) && `${N(m[1])} ${N(m[2])}ને સંબોધે છે`],
    [/^(.+?) delivers a discourse$/, m => N(m[1]) && `${N(m[1])} પ્રવચન કરે છે`],
    // a gathering at a place: "Evening sabha at Neasden Mandir"
    [/^(.+) (?:at|in) (.+)$/, m => short(m[1]) && N(m[1]) && inPlace(m[2]) && `${inPlace(m[2])} ${N(m[1])}`],
    [/^(.+) from (.+)$/, m => short(m[1]) && N(m[1]) && N(m[2]) && `${N(m[2])}થી ${N(m[1])}`],
  ];
  const short = s => s.split(' ').length <= 5;
  // a name in Gujarati, or null
  function N(s) { const g = tr(s); return g !== s && !/[A-Za-z]/.test(g) ? g : null; }
  // who + what: "Swamishri" + "~performs his daily puja"
  function doing(s) {
    for (let i = s.indexOf(' '); i > 0; i = s.indexOf(' ', i + 1)) {
      const v = word('~' + s.slice(i + 1));
      if (!v) continue;
      const who = N(s.slice(0, i));
      if (who) return v[0] === '+' ? who + v.slice(1) : who + ' ' + v;
    }
    return null;
  }

  // English -> Gujarati, or null when some of it has no Gujarati yet
  function gu(s) {
    if (!/[A-Za-z]/.test(s)) return digits(s);
    const w = word(s) || word(s.replace(/\s+/g, ' ')) || (s.length < 60 && word(s.toLowerCase().replace(/^./, c => c.toUpperCase())));
    if (w) return digits(w);
    for (const [re, f] of P) { const m = s.match(re); if (m) { const g = f(m); if (g) return digits(g); } }
    const d = doing(s); if (d) return digits(d);
    // the Bapa pages say what Bapa does without his name ('Performs his daily puja', the On this day picture's captions)
    const v = /^[A-Z][a-z]/.test(s) && word('~' + s[0].toLowerCase() + s.slice(1));
    if (v) return digits(v[0] === '+' ? v.slice(1) : v);
    const more = s.match(/^(.+?)[.\s]*For more photos.*$/i);   // a leftover link line from baps.org
    if (more) return gu(more[1]);
    const end = s.match(/^([\s\S]*?)([\s,.;:-]+)$/);    // "Shri Swaminarayan Mandir," and the like
    if (end && /[A-Za-z]/.test(end[1])) { const g = gu(end[1]); return g === null ? null : g + end[2]; }
    // several things joined together: translate each part
    for (const sep of [' · ', '; ', ', ', ' / ', '/', ' & ', ' and ', ' - ', ' – ', ': ']) {
      if (s.includes(sep)) {
        const parts = s.split(sep).map(x => x.trim() ? gu(x.trim()) : '');
        if (parts.every(x => x !== null)) return parts.join(sep === ' and ' ? ' અને ' : sep === ' & ' ? ' અને ' : sep);
      }
    }
    // dates and short labels, word by word: only when every word is known
    if (s.split(' ').length > 8) return null;
    const toks = s.split(/(\s+|[.,()‹›…–-])/);
    let ok = true;
    const out = toks.map(t => {
      if (!/[A-Za-z]/.test(t)) return t;
      const m = t.match(/^(\d+)(st|nd|rd|th|ST|ND|RD|TH)$/);
      if (m) return m[1];
      if (t in T) return T[t];
      const w = word(t) || word(t.toLowerCase()) || word(t[0].toUpperCase() + t.slice(1)); if (w) return w;
      ok = false; return t;
    });
    return ok ? digits(out.join('').replace(/(\S)થી/g, '$1 થી')) : null;
  }
  const cache = new Map();
  function tr(s) {
    if (!s || !/\S/.test(s)) return s;
    if (cache.has(s)) return cache.get(s);
    const m = s.match(/^(\s*)([\s\S]*?)(\s*)$/);
    let g = gu(m[2]);
    g = g === null ? s : m[1] + g + m[3];
    if (cache.size > 20000) cache.clear();
    cache.set(s, g);
    return g;
  }

  /* ---------- swapping the words on the page ---------- */
  const ATTRS = ['title', 'aria-label', 'placeholder', 'alt'];
  const SKIP = /^(SCRIPT|STYLE|TEXTAREA|CODE|PRE|NOSCRIPT|TEMPLATE)$/;
  const done = new WeakMap();                     // text node -> the Gujarati we put there
  const touched = new Set();                      // [node, attribute or null, English] to put back for English
  const skip = el => !el || SKIP.test(el.nodeName) || (el.closest && el.closest('[translate="no"], .gu-switch, [contenteditable]'));
  function text(n) {
    const v = n.nodeValue;
    if (done.get(n) === v || !/[A-Za-z0-9]/.test(v)) return;
    const p = n.parentNode;
    if (!p || p.nodeType !== 1 || skip(p)) return;
    const g = tr(v);
    done.set(n, g);
    if (g !== v) { touched.add([n, null, v]); n.nodeValue = g; }
  }
  function attrs(el) {
    if (skip(el)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (!v || !/[A-Za-z0-9]/.test(v) || el['gu_' + a] === v) continue;
      const g = tr(v);
      el['gu_' + a] = g;
      if (g !== v) { touched.add([el, a, v]); el.setAttribute(a, g); }
    }
  }
  function walk(node) {
    if (node.nodeType === 3) return text(node);
    if (node.nodeType !== 1 && node.nodeType !== 9) return;
    if (node.nodeType === 1) { if (skip(node)) return; attrs(node); }
    const w = document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: x => x.nodeType === 1 && skip(x) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
    });
    let x; while ((x = w.nextNode())) x.nodeType === 3 ? text(x) : attrs(x);
  }
  const watcher = new MutationObserver(list => {
    if (!on || !W) return;
    for (const r of list) {
      if (r.type === 'characterData') text(r.target);
      else if (r.type === 'attributes') attrs(r.target);
      else r.addedNodes.forEach(walk);
    }
  });
  function translateAll() {
    walk(document.documentElement);
    watcher.observe(document.documentElement, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
    redraw();
  }
  function putBack() {
    watcher.disconnect();
    touched.forEach(([n, a, v]) => { if (a) { n.setAttribute(a, v); n['gu_' + a] = null; } else { n.nodeValue = v; done.delete(n); } });
    touched.clear();
    redraw();
  }
  // pages that draw on a canvas (the globe, Through the years) draw again in the new language
  const redraw = () => requestAnimationFrame(() => dispatchEvent(new Event('resize')));
  const C = window.CanvasRenderingContext2D && CanvasRenderingContext2D.prototype;
  if (C) ['fillText', 'strokeText', 'measureText'].forEach(f => {
    const orig = C[f];
    C[f] = function (t, ...rest) { return orig.call(this, on && W && typeof t === 'string' ? tr(t) : t, ...rest); };
  });

  /* ---------- the look in Gujarati ---------- */
  const css = document.createElement('style');
  // only the website's own web fonts: naming an installed font here (Arial, Georgia) would hide it
  const serif = ['EB Garamond', 'Diary Garamond', 'Cormorant Garamond', 'Cinzel', 'Lora', 'Marcellus'];
  const sans = ['Arimo', 'Diary Arimo', 'Mukta'];
  const GU = 'unicode-range: U+0951-0952, U+0964-0965, U+0A80-0AFF, U+200C-200D, U+20B9, U+25CC, U+A830-A839; font-display: swap;';
  // the Gujarati letters join each English font family, one face per weight so every weight finds them
  const face = (f, src, w, st) => `@font-face { font-family: '${f}'; src: url(/gu/fonts/${src}.woff2) format('woff2'); font-weight: ${w}; font-style: ${st}; ${GU} }`;
  const faces = [];
  for (let w = 100; w <= 900; w += 100) for (const st of ['normal', 'italic']) {
    serif.forEach(f => faces.push(face(f, 'rasa', w, st)));
    sans.forEach(f => faces.push(face(f, w < 600 ? 'mukta-vaani-400' : 'mukta-vaani-700', w, st)));
  }
  css.textContent = faces.join('\n') +
    `@font-face { font-family: 'Gujarati Serif'; src: url(/gu/fonts/rasa.woff2) format('woff2'); font-weight: 300 900; ${GU} }
     html.gu-wait body { opacity: 0 !important; }
     html.gu body { transition: opacity .25s; }
     /* Gujarati letters join up; spacing them apart, the way the English capitals are, breaks them */
     html.gu body *:not(.gu-switch):not(.gu-switch *) { letter-spacing: normal !important; }
     html.gu .site-menu a { font-size: 14px; }
     @media (max-width: 760px) { html.gu nav.site-menu a[href="/through-the-years/"]::after { content: 'વર્ષો'; } }
     @media (max-width: 760px) { html.gu .site-menu a { font-size: inherit; } }
     .gu-switch { all: unset; box-sizing: border-box; flex: none; display: inline-flex; align-items: stretch; height: 26px; margin-left: 6px;
       border: 1px solid rgba(217, 164, 65, .7); border-radius: 999px; overflow: hidden; cursor: pointer; align-self: center;
       font: 600 12px/1 Arimo, Arial, sans-serif; color: #d9a441; background: rgba(0, 0, 0, .18); }
     .gu-switch span { display: flex; align-items: center; padding: 0 9px; letter-spacing: .04em; transition: background .2s, color .2s; }
     .gu-switch .g { font: 600 14px/1 'Gujarati Serif', serif; padding-bottom: 2px; }
     .gu-switch [aria-current] { background: #d9a441; color: #2a0d12; }
     .gu-switch:hover { border-color: #ffe296; }
     .gu-switch:focus-visible { outline: 2px solid #ffe296; outline-offset: 2px; }
     .site-menu .gu-switch { margin-bottom: -2px; }
     .ph-top .gu-switch { height: 34px; margin: 0 10px 0 auto; font-size: 14px; }
     .ph-top .gu-switch .g { font-size: 17px; }
     .ph-top .gu-switch span { padding: 0 12px; }`;
  (document.head || root).appendChild(css);

  /* ---------- the switch ---------- */
  function button() {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'gu-switch'; b.setAttribute('translate', 'no');
    b.setAttribute('aria-label', 'Language / ભાષા');
    b.innerHTML = '<span class="e" lang="en">EN</span><span class="g" lang="gu">ગુજરાતી</span>';
    b.onclick = () => choose(!on);
    return b;
  }
  function showChoice() {
    document.querySelectorAll('.gu-switch').forEach(b => {
      b.querySelector('.e').toggleAttribute('aria-current', !on);
      b.querySelector('.g').toggleAttribute('aria-current', on);
      b.title = on ? 'Read in English' : 'ગુજરાતીમાં વાંચો';
    });
  }
  function place() {
    const narrow = matchMedia('(max-width: 760px)').matches;
    const spot = narrow ? document.querySelector('.ph-top') : document.querySelector('nav.site-menu');
    if (!spot || spot.querySelector('.gu-switch')) return !!spot;
    if (narrow) { const about = spot.querySelector('.ph-about'); about ? about.before(button()) : spot.append(button()); }
    else spot.append(button());
    showChoice();
    return true;
  }
  // the phone strip at the top is added by phone.js after the page loads, so keep looking for a little while
  function placeSoon() {
    if (place()) return;
    const o = new MutationObserver(() => { if (place()) o.disconnect(); });
    o.observe(document.documentElement, {childList: true, subtree: true});
    setTimeout(() => o.disconnect(), 8000);
  }

  let loading = null;
  function load() {
    return loading = loading || (W ? Promise.resolve() : fetch('/gu/words.json').then(r => r.json()).then(j => { W = j; }).catch(() => { W = W || {}; }));
  }
  // when the page opens in Gujarati, the words are fetched before the page draws anything (the globe and
  // Through the years draw their words once, straight away), so nothing shows in English first
  function loadNow() {
    try {
      const x = new XMLHttpRequest();
      x.open('GET', '/gu/words.json', false); x.send();
      if (x.status === 200) W = JSON.parse(x.responseText);
    } catch (e) {}
  }
  function choose(g) {
    on = g; store.set(g ? 'gu' : 'en'); showChoice();
    root.lang = g ? 'gu' : 'en'; root.classList.toggle('gu', g);
    if (g) load().then(() => { if (on) translateAll(); }); else putBack();
  }

  if (on) {
    root.lang = 'gu'; root.classList.add('gu', 'gu-wait');
    const show = () => root.classList.remove('gu-wait');
    setTimeout(show, 2500);                       // never leave the page hidden
    loadNow();
    if (W) watcher.observe(document.documentElement, {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS});
    const go = () => load().then(() => { translateAll(); show(); });
    document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', go) : go();
  }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', placeSoon) : placeSoon();
  window.BapaGujarati = {tr: s => (on && W ? tr(s) : s), on: () => on, check: list => load().then(() => list.map(tr))};   // check: for testing the words
})();
