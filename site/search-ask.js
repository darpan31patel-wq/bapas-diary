// Ask the diary (Darpan, 25 Oct 2026: "go live, make it part of the search bar, the more extensive our search ability
// the better"). A question typed into the search bar, like "When did Bapa go to London?" or "Where was Bapa on Diwali
// 2005?", gets a short answer above the results, and the results become the photos with Bapa that answer it.
// No AI and nothing to pay for: the question is read here, in the page, for places (Bapa's travels, from the Travels
// page: data/stops.json), dates, months, years, festivals (the BAPS calendar), mandir days and what is in a photo.
// Put inside the search page by tools/build_search.py, after its own script, whose items, cal and search() it uses.
(() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
  const MON = MONTHS.map(m => m[0].toUpperCase() + m.slice(1));
  const GM = ['જાન્યુઆરી', 'ફેબ્રુઆરી', 'માર્ચ', 'એપ્રિલ', 'મે', 'જૂન', 'જુલાઈ', 'ઑગસ્ટ', 'સપ્ટેમ્બર', 'ઑક્ટોબર', 'નવેમ્બર', 'ડિસેમ્બર'];
  const PASSED = '2016-08-13';   // Pramukh Swami Maharaj until this day, Mahant Swami Maharaj from it
  const guruOf = d => d < PASSED ? 'P' : 'M';
  const GURU = { P: 'Pramukh Swami Maharaj', M: 'Mahant Swami Maharaj' };
  const GURU_GU = { P: 'પ્રમુખસ્વામી મહારાજ', M: 'મહંતસ્વામી મહારાજ' };
  const TODAY = new Date().toISOString().slice(0, 10);
  // the BAPS calendar in the diary starts in 2010. Before that, the main festivals' days are worked out from the Hindu
  // calendar (tools/old_festivals.py), checked against the BAPS calendar and the photo captions (Darpan, 26 Oct 2026)
  // worked out by tools/old_festivals.py: for each festival, MMDD for every year from 1940 to 2009
  const OLD_FEST_FROM = 1940, OLD_FEST = {
"Akhatrij": "0510042904180507042505140503042305110501042005080426051505050424051205020421051004280417050604260514050304230512043004190508042705150505042405130502042105090429041705060426051505030423051104300418050704270516050504240513050204200509042804180506042605150504042205110430041905070427",
"Annakut and Bestu Varash (New Year)": "1031102111091029101711051025111311011022111010311019110710271115110310231111110110211109102911161104102511131102102211101030101911061026111411041023111111011021110810281116110510251113110210231110103010191107102611141104102411111101102111081027111511051026111311021022111010291018",
"Bhagatji Maharaj's Birthday": "0323031303020321030902260317030603240314030303220311022803180308032503150305032403120301032003090226031603060325031403030322031102280318030703260315030503240313030103190309032803160306032503140302032103100228031803070326031603040323031203010319030903280317030603250314030303210310",
"Bhai Beej": "1101102211101031101911071027111411031023111111011020110810281116110410251113110210221110103011181106102611141104102311111101102111081028111511051025111311021023110910291117110610261114110410241111103110201108102711151105102611131102102211101029111711061027111411031024111210301020",
"Buddha Jayanti": "0521051105010519050805260515050505230512050205210509052805170506052405130503052205110430051905080526051505040523051205020521051005280517050605250513050305220512043005180507052605150504052405130501052005090528051605060525051405030522051104300518050705260516050405230513050205190509",
"Dev Diwali": "1114110311221112103111191109112811161105112411131101112111101129111811071126111511031122111212011119110911281117110511231113110211211110112911181106112511141104112211121201112011081127111611051123111311031122111011291118110711251114110411231111113011191108112611161105112411131102",
"Devshayani Ekadashi": "0715070507240714070207200709062907160706072507150704072207110630071807070627071607050724071307020720070906280717070607250715070407220710063007190707062707160706072307120701072007090629071807070725071407030722071006300719070907270716070507240712070107200710062907180707072507130702",
"Dhan Teras (Lakshmi Pujan)": "1028101811061026101411021022111010301019110710281016110310231111103110211109102910171105102510141101102211101031101911071027101611031023111111011021110910291018110410251112110210221110103010201106102610151103102311111101102111081028101711051024111211021023111010301019110710261015",
"Diwali": "1030102011081028101611041024111210311021110910301018110610261113110210221110103110191107102710161103102411121101102111091029101811051025111311031022111010311020110710271115110410241112110110221108102810181105102511131103102311101030101911071026111411041025111211011021110910281017",
"Ganesh Chaturthi": "0905082609140904082309100830091809060827091509050824091209010920090808280917090608260914090308230910083009180908082709150905082509110831091909090829091709060827091309020822091008300918090808280915090408240912083109190909083009170906082609130902082209100831091809070828091509030824",
"Gunatitanand Swami Diksha Day (Poshi Punam)": "01250113010201210110----0117010701260114010401230112----0119010801270116010501240113010101200109----0117010701260115010301220111----011801080127011701050124011301020120010901290118010701250114010301210111----011901080127011601050123011201020121010901290118010701250114010301220111",
"Gunatitanand Swami's Birthday (Sharad Punam)": "1015100410231012100110201010102910171006102510141002102110111030101910081026101510041023101210021020100910281017100510241014100310211011103010191007102610151005102310121031102110091027101710061024101410031022101010291018100710251015100510241012103110201009102710161006102510141003",
"Guru Purnima": "0719070807270717070607250714070307210710072907180707072607160705072207110701072007080727071707060724071307020721071007290718070807260715070407230711070107200709072707170706072407130702072107110729071807070726071407030722071207300720070907280716070507240713070207210711073007180707",
"Hanuman Jayanti": "0422041204010420040804270416040504230413040204210410033004180407042504140404042304110401041904080426041504050424041304020421041003290417040604250414040404230412033104190408042704150405042404140402042104100330041704060425041504030422041103310418040804270416040504240413040204200409",
"Holi": "0323031303020321030902260317030603240314030303220311022803180308032503150305032403120301032003090226031603060325031403030322031102280318030703260315030503240313030103190309032803160306032503140302032103100228031803070326031603040323031203010319030903280317030603250314030303210310",
"Independence Day": "0815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815081508150815",
"Jal Jhilani Ekadashi": "0912090109200910083009180907092509130903092209110831091909090927091509040923091309020921091008300917090609250914090309220912090109190908092609160904092309130903092109100830091709050924091409040922091109010919090709260915090509230913090209210909082909170906092409140904092309110831",
"Janmashtami": "0826081509030823081108300820090808280817090408240813083108210811082908190906082608140902082208120830082009080828081609040824081309010821081108300818090608250815090208230812083108200907082708160903082408140902082108110829081809050825081509030823081208310820090708270816090408240814",
"Kali Chaudash": "1029101911071027101511031023111110301020110810291017110410241112110110211109103010181106102610151102102311111031102011081028101711041024111211021021110910301019110610261113110310231111103110211107102710161104102411121102102211091029101811061025111311031024111110311020110810271016",
"Labh Pancham": "1104102411131102102211101030111711051026111411041023111111011119110710271115110510251113110211211109102911171106102611141104102411111031111911081027111511051026111311021120110910291116110610271114110310231111103011181107102811151105102511131101112011091029111711061027111511031023",
"Mahant Swami Maharaj's Jayanti": "0926091510030922091009290919100809270917100509240912100109201010092809181007092609141003092209110930091910080928091610040923091310010921101009290918100609250914100209220912100109191008092709161004092309131002092110100929091810060925091410030922091210010920100709260915100409230913",
"Mahavir Jayanti": "0420041003300418040604250414040304210411040104200408032804150405042304120402042104090330041704060424041404030422041103310419040803270415040504240412040204210410032904170406042504140403042204120331041804070328041504050424041304010420040903290416040604250415040304220411033104180407",
"Makar Sankranti (Uttarayan)": "0114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114011401140114",
"Prabodhini Ekadashi": "1110103011181108102811161105112411121101112011091029111711071126111411031121111010301118110811271116110511231112103111191109103011171106112511141102112111101031111811081127111611041122111211011120110910301118110611241113110311211111103111191107112611151104112211121102112111091029",
"Pramukh Swami Maharaj's Jayanti": "12071126121512041123121212021221120811271216120611241214120312221210112912181207112612151205----1212120112201209112712161206112612141203122212101128121712071127121512051224121211301219120811281216120611251214120212211210112912171207112712161204122312121201121912081128121712061125",
"Pramukh Varni Din": "0609053006180607052606130603052406110531052106080527061506040525061206020522061005290617060605260613060305240612053105200608052806150604052506130602052206100530061606060526061406030524061105310618060705280616060405250613060205210609052906170606052606140604052306110531061806070528",
"Pushpadolotsav (Dhuleti)": "0324031303030322031002270318030703250315030403230312030103190309032603160306032503130302032103100227031703070326031503040323031202290319030803270316030603250314030203210310032903170307032603150304032203110301031903080327031703050324031303020320031003290318030703260315030403220311",
"Raksha Bandhan": "0817080708260815080408230812083108190808082708170805082408140803082108100829081808070826081508050823081208300820080808270817080608240814080308210809082808180808082608150804082308110830081908090827081708060825081308020821081008280818080808260815080408220812083008190809082808160805",
"Ramnavmi": "0417040603260414040204200410033104180407032804160403032304110401041904090329041704050325041304020420041003310419040703270415040403230411040104200409032904170405032404120402042104100331041804070326041404030324041104010420040903280416040503250412040204210411033004180406032704140404",
"Rathyatra": "0707062607150704062207110701062007080628071707060624071307020622071006290619070806260714070306230711070106200709062707160705062407120702062207110629061807070626071407030623071207010620070906280715070506240713070206220710063007170706062607140703062307120701061907080627071607040624",
"Republic Day": "0126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126012601260126",
"Shivratri": "0306022302130304022202100301021803080225021403050223021203030220031002270216030702240213030402220211030102180308022602140306022302130302021903100227021603070225021403040221----02290217030802260216030602230212030202190310022702170307022502140304022003110228021803080226021503050222",
"Start of Navratri": "1002092210110930091810070926101510030923101210020920100809271016100509241013100309211010092909181006092610151004092310121001092010080927101610060924101310030922101009291017100709261015100409241011093009191008092710161006092510131002092110100928101710070927101510040923101209300919",
"Swaminarayan Jayanti (Hari Navmi)": "0417040603260414040204200410033104180407032804160403032304110401041904090329041704050325041304020420041003310419040703270415040403230411040104200409032904170405032404120402042104100331041804070326041404030324041104010420040903280416040503250412040204210411033004180406032704140404",
"Vaman Jayanti": "0912090209210911083009180908092609140903092209120901092009090928091609050924091309020921091108310918090709250915090309220912090209200909092709160905092409130903092109100830091809060925091509040922091209010920090809270916090609240913090309220910083009170907092509150904092309110831",
"Vasant Panchmi": "0213020101210209012901180206012702150203012302110131011902080128021602050125021202010121020901300119020601260214020301220210013101210208012802160205012402120201012202090130----02070126021302030123021001310121020901280215020401240211020101220210012902170206012602130202012302110131",
"Vijaya Dashmi": "1010092910181008092710161005102410121001102010090928101710071026101410021021101109301019100809281015100410231012100110201010092910171006102510141002102110111001101910081027101610041022101210021020101009291018100510241013100310211011100110191007102610151004102210121002102110090928",
"Yogi Jayanti": "0602052205110530051906070528051706040524051306010520060805290519060605260515060305220511053005200607052805170604052305130601052106090529051906060525051406020523051205310520060805270516060405240513060105220610052905180605052605140602052305130530052006070527051506030524051406010521"
};

  // ---------- Gujarati (the site's English / ગુજરાતી switch) ----------
  const root = document.documentElement;
  const isGu = () => root.classList.contains('gu');
  let W = null;
  const loadGu = () => W ? Promise.resolve() : fetch('/gu/words.json').then(r => r.json()).then(j => { W = j; }).catch(() => { W = {}; });
  const g = s => (W && W[s]) || s;
  const gd = s => s.replace(/[0-9]/g, d => '૦૧૨૩૪૫૬૭૮૯'[d]);
  new MutationObserver(() => { if (isGu() && !W) loadGu().then(() => window.search && search()); else if (window.search && last) search(); })
    .observe(root, { attributes: true, attributeFilter: ['class'] });

  // ---------- words ----------
  const num = n => n.toLocaleString('en-GB');
  const pd = s => s.split('-').map(Number);
  const fmt = (s, noYear) => { const [y, m, d] = pd(s); return `${d} ${MON[m - 1]}` + (noYear ? '' : ` ${y}`); };
  const fmtGu = (s, noYear) => { const [y, m, d] = pd(s); return gd(`${d} ${GM[m - 1]}` + (noYear ? '' : ` ${y}`)); };
  function range(a, b, f = fmt) {
    if (!b || a === b) return f(a);
    const [ay, am] = pd(a), [by, bm] = pd(b);
    if (f === fmt) {
      if (ay === by && am === bm) return `${pd(a)[2]} to ${fmt(b)}`;
      if (ay === by) return `${fmt(a, true)} to ${fmt(b)}`;
      return `${fmt(a)} to ${fmt(b)}`;
    }
    return `${ay === by ? fmtGu(a, true) : fmtGu(a)} થી ${fmtGu(b)}`;
  }
  const andList = (a, and = 'and') => a.length < 2 ? (a[0] || '') : a.slice(0, -1).join(', ') + ` ${and} ` + a[a.length - 1];
  const plural = (n, w, ws) => `${num(n)} ${n === 1 ? w : (ws || w + 's')}`;
  const iso = (y, m, d) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

  // ---------- what the diary knows ----------
  let STOPS = [], PLACES = [], COUNTRY = {}, FEST_DAYS = null, ready = false;
  fetch('data/stops.json').then(r => r.json()).then(d => {
    STOPS = d.stops.map(([y, p, a, b, n, cap, pic]) => ({ y, p, a, b, n, cap, pic }));
    COUNTRY = d.country;
    PLACES = [...new Set(STOPS.map(s => s.p))].sort((a, b) => b.length - a.length);
    ready = true;
    if (window.search && last) search();
  }).catch(e => console.error(e));
  const nonIndia = () => [...new Set(Object.values(COUNTRY))].filter(c => c !== 'India');
  const REGIONS = {
    africa: ['Kenya', 'Tanzania', 'Uganda', 'South Africa', 'Botswana', 'Zambia', 'Malawi', 'Egypt'], 'east africa': ['Kenya', 'Tanzania', 'Uganda'],
    europe: ['UK', 'France', 'Portugal'], america: ['USA', 'Canada'], 'north america': ['USA', 'Canada'], usa: ['USA'], 'united states': ['USA'],
    uk: ['UK'], england: ['UK'], britain: ['UK'], 'united kingdom': ['UK'], australia: ['Australia'], 'new zealand': ['New Zealand'],
    canada: ['Canada'], india: ['India'], 'middle east': ['UAE', 'Oman', 'Kuwait', 'Bahrain', 'Israel'], gulf: ['UAE', 'Oman', 'Kuwait', 'Bahrain'],
    asia: ['Thailand', 'Singapore', 'Hong Kong', 'Indonesia'], 'far east': ['Thailand', 'Singapore', 'Hong Kong', 'Indonesia'],
    abroad: null, overseas: null, 'outside india': null, 'foreign countries': null,
  };
  const regionCountries = r => REGIONS[r] || (r in REGIONS ? nonIndia() : [Object.values(COUNTRY).find(c => c.toLowerCase() === r)]);
  const ALIAS = { neasden: 'London', 'mt abu': 'Mount Abu', vadodara: 'Atladara (Vadodara)', baroda: 'Atladara (Vadodara)', atladara: 'Atladara (Vadodara)',
    delhi: 'New Delhi', 'new jersey': 'Robbinsville', nj: 'Robbinsville', bombay: 'Mumbai', calcutta: 'Kolkata', madras: 'Chennai', bangalore: 'Bengaluru',
    'dar es salaam': 'Dar-es-Salaam', amdavad: 'Ahmedabad', ahmadabad: 'Ahmedabad', 'new york city': 'New York', nyc: 'New York', 'la': 'Los Angeles',
    'washington dc': 'Washington', leicester: 'Leicester', johannesburg: 'Johannesburg', joburg: 'Johannesburg' };

  const FEST = [
    [/\bdev diwali\b/, 'Dev Diwali'], [/\bdiwali\b|\bdeepavali\b|\bdivali\b/, 'Diwali'],
    [/annakut|new year|bestu/, 'Annakut and Bestu Varash (New Year)'],
    [/janmasht?ami|krishna jayanti/, 'Janmashtami'], [/guru ?purnima|guru ?punam/, 'Guru Purnima'],
    [/dhuleti|fuldol|pushpadol/, 'Pushpadolotsav (Dhuleti)'], [/\bholi\b/, 'Holi'],
    [/ram ?navm?i/, 'Ramnavmi'], [/swaminarayan jayanti|hari ?navm?i|hari jayanti/, 'Swaminarayan Jayanti (Hari Navmi)'],
    [/pramukh swami( maharaj)?'?s? (jayanti|birthday|janma)|pramukh jayanti/, "Pramukh Swami Maharaj's Jayanti"],
    [/mahant swami( maharaj)?'?s? (jayanti|birthday|janma)|mahant jayanti/, "Mahant Swami Maharaj's Jayanti"],
    [/yogi(ji)?( maharaj)?'?s? (jayanti|birthday)|yogi jayanti/, 'Yogi Jayanti'], [/bhagatji/, "Bhagatji Maharaj's Birthday"],
    [/shastriji/, 'Shastriji Maharaj Smruti Parva'], [/sharad pu(r?n|nam)|gunatitanand swami'?s? (birthday|jayanti)/, "Gunatitanand Swami's Birthday (Sharad Punam)"],
    [/poshi pun/, 'Gunatitanand Swami Diksha Day (Poshi Punam)'],
    [/navratri/, 'Start of Navratri'], [/dussehra|dasara|dashera|vijaya? dash/, 'Vijaya Dashmi'], [/uttarayan|sankranti/, 'Makar Sankranti (Uttarayan)'],
    [/vasant panch/, 'Vasant Panchmi'], [/raksha ?bandhan|rakhi/, 'Raksha Bandhan'], [/ganesh/, 'Ganesh Chaturthi'], [/shivratri/, 'Shivratri'],
    [/dhan ?teras/, 'Dhan Teras (Lakshmi Pujan)'], [/kali chaud/, 'Kali Chaudash'], [/bhai b[ei]+j/, 'Bhai Beej'], [/labh pancham/, 'Labh Pancham'],
    [/rath ?yatra/, 'Rathyatra'], [/akha ?trij|akhatrij/, 'Akhatrij'], [/hanuman jayanti/, 'Hanuman Jayanti'], [/varni din/, 'Pramukh Varni Din'],
    [/prabodhini/, 'Prabodhini Ekadashi'], [/devshayani|devpodhi/, 'Devshayani Ekadashi'], [/independence day/, 'Independence Day'], [/republic day/, 'Republic Day'],
  ];
  function festDays() {
    if (FEST_DAYS) return FEST_DAYS;
    const f = {};
    for (const [d, c] of Object.entries(cal)) for (const x of c.list) (f[x] = f[x] || []).push(d);
    for (const [x, days] of Object.entries(OLD_FEST)) for (let i = 0; i < days.length; i += 4) {
      const d = `${OLD_FEST_FROM + i / 4}-${days.slice(i, i + 2)}-${days.slice(i + 2, i + 4)}`;
      if (days[i] !== '-' && !cal[d]) (f[x] = f[x] || []).push(d);
    }
    for (const k in f) f[k].sort();
    if (Object.keys(cal).length) FEST_DAYS = f;
    return f;
  }

  // the festivals on a day before the BAPS calendar starts (for the plain search and the Festival list too)
  let OLD_ON = null;
  window.festOn = d => {
    if (cal[d]) return [];
    if (!OLD_ON) { OLD_ON = {}; for (const [x, days] of Object.entries(festDays())) for (const e of days) if (!cal[e]) (OLD_ON[e] = OLD_ON[e] || []).push(x); }
    return OLD_ON[d] || [];
  };

  // ---------- forgiving spellings (Darpan, 26 Oct 2026) ----------
  // Gujarati words are written in English many ways: Diwali or Divali, Swamishri or Swamishree, Pratishtha or Pratistha.
  // Each word gets a sound key (w is v, bh is b, sh is s, ee is i, double letters single), and a looser one that also
  // drops the a's (Ramnavami, Ramnavmi). A word searched for also finds the other spellings with its key that are in
  // the diary; a word the diary does not have at all finds the nearest one that it does (one letter off).
  const SAME = { salangpur: 'sarangpur', vartal: 'vadtal', junagarh: 'junagadh', gadhpur: 'gadhada', deepavali: 'diwali', dipavali: 'diwali',
    deepawali: 'diwali', dipawali: 'diwali', dussera: 'dussehra', dashehra: 'dussehra', dasera: 'dussehra', dashera: 'dussehra', dasara: 'dussehra',
    amdavad: 'ahmedabad', ahmadabad: 'ahmedabad', bombay: 'mumbai', baroda: 'vadodara', calcutta: 'kolkata', madras: 'chennai', bangalore: 'bengaluru',
    poonam: 'punam', poornima: 'purnima', purnam: 'punam', idol: 'murti', murthi: 'murti', moorti: 'murti' };
  const strong = w => w.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/x/g, 'ks').replace(/w/g, 'v').replace(/ph/g, 'f')
    .replace(/q/g, 'k').replace(/z/g, 'j').replace(/([bdgkjtcs])h/g, '$1').replace(/ee/g, 'i').replace(/oo/g, 'u').replace(/(.)\1+/g, '$1');
  const loose = w => { const k = strong(w); return (k[0] || '') + k.slice(1).replace(/a/g, '').replace(/(.)\1+/g, '$1'); };
  function near1(a, b) {   // true when a and b differ by one letter (added, dropped, changed, or two swapped)
    if (Math.abs(a.length - b.length) > 1 || a === b) return false;
    let i = 0; while (i < a.length && a[i] === b[i]) i++;
    if (a.length === b.length) return a.slice(i + 1) === b.slice(i + 1) || (a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2));
    return a.length > b.length ? a.slice(i + 1) === b.slice(i) : a.slice(i) === b.slice(i + 1);
  }
  // every word in the diary, with how often it is used (built once, when everything has loaded)
  let VOCAB = null, BY_STRONG = null, BY_LOOSE = null;
  function vocab() {
    if (VOCAB || loaded < total) return VOCAB;
    const n = new Map();
    const addAll = t => { for (const w of t.match(/[a-z]{3,}/g) || []) n.set(w, (n.get(w) || 0) + 1); };
    for (const r of items) addAll(r.hay);
    for (const c of Object.values(cal)) addAll([c.indian, c.fest, c.about, c.notes].join(' ').toLowerCase());
    for (const x of Object.keys(OLD_FEST)) addAll(x.toLowerCase());
    VOCAB = n; BY_STRONG = new Map(); BY_LOOSE = new Map();
    for (const w of n.keys()) {
      const a = strong(w), b = loose(w);
      (BY_STRONG.get(a) || BY_STRONG.set(a, []).get(a)).push(w);
      (BY_LOOSE.get(b) || BY_LOOSE.set(b, []).get(b)).push(w);
    }
    return VOCAB;
  }
  const uses = w => { let n = 0; for (const [v, c] of VOCAB) if (v.startsWith(w)) n += c; return n; };
  // the spellings to look for, for one searched word: [the word itself, then other spellings in the diary]
  function spellings(w) {
    w = w.toLowerCase();
    const out = [w], same = SAME[w];
    if (same) out.push(same);
    if (w.length < 4 || !/^[a-z]+$/.test(w) || !vocab()) return out;
    const add = list => { for (const v of list || []) if (!out.some(o => v.includes(o))) out.push(v); };
    // the same sound: always (Diwali, Divali); with the a's dropped too when the word itself is rare (Ramnavami, Ramnavmi)
    const ks = strong(w), kl = loose(w), n = uses(w);
    const close = (k, x) => w.length <= 5 ? k === x : k.startsWith(x) && k.length - x.length < 3;   // short words: the same sound only
    for (const [k, list] of BY_STRONG) if (close(k, ks)) add(list.filter(v => v.length >= w.length - 1));
    if (n < 20 && kl.length >= 3) for (const [k, list] of BY_LOOSE) if (close(k, kl)) add(list.filter(v => v.length >= w.length - 1));
    // not in the diary at all: the nearest words that are, one letter off (Sarangpor, Sarangpur)
    if (!n && out.length === 1 && w.length >= 5) {
      const hit = [...VOCAB].filter(([v]) => near1(loose(v), kl) || near1(v, w)).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([v]) => v);
      add(hit);
    }
    return out.slice(0, 12);
  }
  // for the plain search: each word's spellings, and a line to say what else was looked for
  window.spellWords = want => {
    const alts = want.map(w => /\s/.test(w) ? [w] : spellings(w));
    // the line names the main other spellings only (the most used ones), not every slip of the keyboard
    const extra = alts.flatMap(a => a.slice(1)).filter((v, i, a) => a.indexOf(v) === i).sort((a, b) => (VOCAB ? uses(b) - uses(a) : 0)).filter((v, i) => !i || !VOCAB || uses(v) >= 5);
    const missing = alts.filter((a, i) => a.length > 1 && !uses(want[i].toLowerCase()) && VOCAB).map(a => a[0]);
    const cap = v => v[0].toUpperCase() + v.slice(1);
    const note = !extra.length ? '' : missing.length ? `Nothing spelt “${esc(missing.join(' '))}”, so showing ${andList(extra.slice(0, 3).map(cap))}.`
      : `Other spellings found too: ${andList(extra.slice(0, 3).map(cap))}.`;
    return { alts, flat: alts.flat(), note };
  };
  // for a question: a misspelt place, festival or thing becomes the diary's own word, so "salangpur" and
  // "janmastami" are read as Sarangpur and Janmashtami
  const FEST_WORDS = ['diwali', 'annakut', 'janmashtami', 'navratri', 'dussehra', 'uttarayan', 'sankranti', 'shivratri', 'ramnavmi', 'rathyatra', 'raksha',
    'bandhan', 'purnima', 'punam', 'holi', 'dhuleti', 'fuldol', 'pushpadolotsav', 'jayanti', 'ekadashi', 'prabodhini', 'devshayani', 'akhatrij', 'vasant',
    'panchmi', 'bhagatji', 'shastriji', 'gunatitanand', 'pramukh', 'mahant', 'yogiji', 'hanuman', 'ganesh', 'teras', 'chaudash', 'beej', 'labh', 'pancham',
    'bestu', 'sharad', 'poshi', 'varni', 'independence', 'republic', 'swaminarayan', 'mandir', 'pratishtha', 'shilanyas', 'patotsav', 'swamishri', 'bapa',
    'akshardham', 'darshan', 'murti', 'birthday', 'janmashtmi'];
  let CANON = null;
  function canonWords() {
    if (CANON && CANON.n === PLACES.length) return CANON;
    const words = new Set([...FEST_WORDS, ...Object.keys(THINGS), ...Object.keys(ALIAS), ...Object.keys(REGIONS)].flatMap(w => w.split(' ')));
    for (const p of PLACES) for (const w of p.toLowerCase().replace(/[()]/g, '').split(/[\s-]+/)) words.add(w);
    CANON = { n: PLACES.length, strong: new Map(), loose: new Map(), list: [...words].filter(w => w.length >= 4) };
    for (const w of CANON.list) { CANON.strong.set(strong(w), w); CANON.loose.set(loose(w), w); }
    return CANON;
  }
  const PLAIN = /^(when|where|what|which|went|visit\w*|travel\w*|photos?|pictures?|times?|many|often|first|last|year|years|days?|there|about|from|with|have|this|that|show|tell|find|give|could|would|ever|been|going|come|came|celebrat\w*|during|stay\w*|spent|place|places)$/;
  function spellQuestion(q) {
    const C = canonWords();
    return q.replace(/[a-z]{4,}/g, w => {
      if (SAME[w]) return SAME[w];
      if (PLAIN.test(w) || C.list.includes(w)) return w;
      const k = C.strong.get(strong(w)) || C.loose.get(loose(w));
      if (k) return k;
      if (w.length >= 6) { const n = C.list.find(c => c.length >= 6 && (near1(c, w) || near1(loose(c), loose(w)))); if (n) return n; }
      return w;
    });
  }

  // what is in a photo (the Action list and the captions); several ways of saying each
  const THINGS = { smiling: /smil/, laughing: /laugh/, children: /child|kids?\b|balaks?\b|balikas?\b|youth/, garland: /garland|\bhaar\b/, blessing: /bless|ashirwad/,
    flowers: /flower/, 'red flowers': /red flower/, 'pink flowers': /pink flower/, roses: /\broses?\b/, marigold: /marigold/, petals: /petal/,
    dance: /danc/, music: /music|kirtan|bhajan|sing/, food: /\bfood|eating|\beat\b|prasad|thal\b/, sweets: /sweet/, arti: /\ba+rti\b/,
    procession: /procession|nagar yatra|rally/, 'folded hands': /folded hands|namaste|joined hands/, writing: /\bwrit/, reading: /\bread/,
    car: /\bcars?\b|vehicle/, elephant: /elephant/, peacock: /peacock/, fireworks: /firework/, sunset: /sunset|evening sky/, 'blue sky': /blue sky|\bsky\b/,
    umbrella: /umbrella/, yagna: /yagna|yagya|yajna/, puja: /\bpuja\b|pooja/, 'close up': /close ?up|portrait/, speaking: /speak|discourse|pravachan|blessing words|address/,
    'meeting people': /meet/, saints: /\bsaints?\b|sadhus?\b|swamis\b/, crowd: /crowd|devotees|thousands/, murti: /\bmurtis?\b|thakorji/, stage: /\bstage\b/,
    mandir: /\bmandirs?\b|temple/, 'red carpet': /red carpet/, garden: /garden/, trees: /\btrees?\b/, chariot: /chariot|rath\b/, flags: /\bflags?\b/,
    dignitaries: /dignitar|minister|president|mayor|leader/, statue: /statue/, dome: /\bdomes?\b|shikhar/, 'mandir at night': /at night|night/,
    annakut: /annakut/, plane: /plane|airport|flight/, boat: /\bboat|ship/, horse: /\bhorses?\b/, cow: /\bcows?\b|gaushala/, wheelchair: null };
  delete THINGS.wheelchair;

  const GU_WORDS = { 'ક્યારે': 'when', 'ક્યાં': 'where', 'ક્યા': 'where', 'બાપા': 'bapa', 'ગયા': 'go to', 'પધાર્યા': 'go to', 'દિવાળી': 'diwali',
    'ફોટા': 'photos', 'કેટલી વાર': 'how many times', 'પહેલી વાર': 'first time', 'છેલ્લી વાર': 'last time', 'સ્વામીશ્રી': 'bapa', 'જન્મજયંતી': 'jayanti',
    'પ્રમુખસ્વામી': 'pramukh swami', 'મહંતસ્વામી': 'mahant swami', 'મૂર્તિપ્રતિષ્ઠા': 'murti pratishtha', 'જન્માષ્ટમી': 'janmashtami',
    'ગુરુપૂર્ણિમા': 'guru purnima', 'અન્નકૂટ': 'annakut', 'હોળી': 'holi', 'આફ્રિકા': 'africa', 'અમેરિકા': 'america', 'માં': ' in ' };
  const QWORDS = /^(when|where|what|which|who|whom|how|did|does|do|was|were|is|are|has|have|had|show|tell|list|find|give|can|could|in which|on which)\b/;

  // ---------- reading a question ----------
  function read(raw) {
    let q = ' ' + raw.normalize('NFC').replace(/[૦-૯]/g, c => '૦૧૨૩૪૫૬૭૮૯'.indexOf(c)) + ' ';
    const gujarati = /[઀-૿]/.test(q);
    if (gujarati && W) for (const [en, gu] of Object.entries(W)) if (gu.length > 1 && PLACES.includes(en) && q.includes(gu)) q = q.split(gu).join(' ' + en + ' ');
    if (gujarati) for (const [gu, en] of Object.entries(GU_WORDS)) q = q.split(gu).join(' ' + en + ' ');
    q = q.toLowerCase().replace(/[’`]/g, "'").replace(/[?!.,;:()"]/g, ' ').replace(/\s+/g, ' ');
    q = spellQuestion(q);
    const Q = { raw, q, gujarati, years: [], places: [], region: '', fest: '', dates: [], day: '', month: 0, guru: '', things: [], mandir: '' };
    let rest = q;
    const cut = rx => { rest = rest.replace(rx, ' '); };
    for (const [rx, f] of FEST) if (rx.test(rest)) { Q.fest = f; cut(rx); break; }
    if (!Q.fest) for (const f of Object.keys(festDays())) if (f.length > 4 && rest.includes(' ' + f.toLowerCase() + ' ')) { Q.fest = f; cut(f.toLowerCase()); break; }
    // dates: 14 march 2005, march 14 2005, 14/3/2005, 2005-03-14
    const M = '(' + MONTHS.map(m => m.slice(0, 3) + '(?:' + m.slice(3) + ')?').join('|') + ')';
    const mi = s => MONTHS.findIndex(x => x.startsWith(s.slice(0, 3))) + 1;
    const md = (mo, d) => `${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    let m;
    if ((m = rest.match(/\b(\d{4})-(\d{1,2})-(\d{1,2})\b/))) { Q.dates.push(iso(+m[1], +m[2], +m[3])); cut(m[0]); }
    else if ((m = rest.match(/\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b/))) { Q.dates.push(iso(+m[3], +m[2], +m[1])); cut(m[0]); }
    else if ((m = rest.match(new RegExp('\\b(\\d{1,2})(?:st|nd|rd|th)? (?:of )?' + M + '\\b(?: (\\d{4}))?')))) {
      if (m[3]) Q.dates.push(iso(+m[3], mi(m[2]), +m[1])); else Q.day = md(mi(m[2]), +m[1]); cut(m[0]);
    } else if ((m = rest.match(new RegExp('\\b' + M + ' (\\d{1,2})(?:st|nd|rd|th)?\\b(?: (\\d{4}))?')))) {
      if (m[3]) Q.dates.push(iso(+m[3], mi(m[1]), +m[2])); else Q.day = md(mi(m[1]), +m[2]); cut(m[0]);
    }
    if (!Q.dates.length && !Q.day && /\b(today|on this day|this day)\b/.test(rest)) { Q.day = TODAY.slice(5); cut(/\b(today|on this day|this day)\b/); }
    if (!Q.dates.length && !Q.day && /\byesterday\b/.test(rest)) { Q.day = new Date(Date.now() - 864e5).toISOString().slice(5, 10); cut(/\byesterday\b/); }
    if ((m = rest.match(new RegExp('\\b' + M + '\\b')))) { Q.month = mi(m[1]); cut(m[0]); }
    if ((m = rest.match(/\b(?:between|from) (\d{4}) (?:and|to|till|until) (\d{4})\b/))) { for (let y = +m[1]; y <= +m[2]; y++) Q.years.push(y); cut(m[0]); }
    if ((m = rest.match(/\b(?:since|after) (\d{4})\b/))) { for (let y = +m[1]; y <= +TODAY.slice(0, 4); y++) Q.years.push(y); cut(m[0]); }
    if ((m = rest.match(/\bbefore (\d{4})\b/))) { for (let y = 1999; y < +m[1]; y++) Q.years.push(y); cut(m[0]); }
    if ((m = rest.match(/\b(?:in )?the (\d{3})0s\b/))) { for (let y = +(m[1] + '0'); y <= +(m[1] + '9'); y++) Q.years.push(y); cut(m[0]); }
    for (const y of rest.match(/\b(19[5-9]\d|20[0-3]\d)\b/g) || []) Q.years.push(+y);
    if (/\bthis year\b/.test(rest)) Q.years.push(+TODAY.slice(0, 4));
    if (/\blast year\b/.test(rest)) Q.years.push(+TODAY.slice(0, 4) - 1);
    Q.years = [...new Set(Q.years)].sort();
    if (/mandir|murti ?prati?sh?th?a|pratishtha|prathistha|shilanyas|foundation stone|patotsav|inaugurat|consecrat/.test(rest))
      Q.mandir = /shilanyas|foundation stone/.test(rest) ? 's' : /patotsav|anniversary/.test(rest) ? 't' : 'p';
    for (const [a, p] of Object.entries(ALIAS)) { const rx = new RegExp('\\b' + a + '\\b'); if (rx.test(rest)) { Q.places.push(p); cut(rx); } }
    rest = rest.replace(/[()]/g, '');
    for (const p of PLACES) {
      const rx = new RegExp('\\b' + p.toLowerCase().replace(/[()]/g, '').replace(/-/g, '[- ]') + '\\b');
      if (rx.test(rest)) { Q.places.push(p); cut(rx); }
    }
    Q.places = [...new Set(Q.places)];
    if (!Q.places.length) for (const r of [...Object.keys(REGIONS), ...new Set(Object.values(COUNTRY).map(c => c.toLowerCase()))].sort((a, b) => b.length - a.length))
      if (new RegExp('\\b' + r + '\\b').test(rest)) { Q.region = r; cut(new RegExp('\\b' + r + '\\b')); break; }
    if (/pramukh/.test(rest)) Q.guru = 'P'; else if (/mahant/.test(rest)) Q.guru = 'M';
    for (const [t, rx] of Object.entries(THINGS)) if (rx.test(rest)) Q.things.push(t);
    if (Q.things.includes('red flowers') || Q.things.includes('pink flowers')) Q.things = Q.things.filter(t => t !== 'flowers');
    if (Q.mandir) Q.things = Q.things.filter(t => t !== 'mandir');
    Q.how = /how many|how often|number of|count/.test(q) ? 'count' : /\bfirst\b|earliest/.test(q) ? 'first' : /\b(last|latest|most recent|recently)\b/.test(q) ? 'last' : '';
    Q.rest = rest.replace(/\b(when|where|what|which|who|did|does|do|was|is|were|are|has|have|had|bapa'?s?|swamishri|swami|maharaj|pramukh|mahant|guru|go|went|gone|going|come|came|visit|visited|visits|visiting|travel\w*|to|in|on|the|a|an|of|for|and|with|me|show|tell|list|find|give|photos?|pictures?|pics?|darshan|times?|how|many|often|number|count|first|last|latest|earliest|time|celebrate\w*|be|there|he|his|him|during|year|years|day|days|at|did|can|could|you|i|see|all|any|some|ever|about|from|by|it|its|this|that|my|our|please|place|places|mandir|stay\w*|spend|spent|doing|happen\w*)\b/g, ' ').replace(/\b\d+\b/g, ' ').replace(/\s+/g, ' ').trim();
    Q.isQuestion = gujarati || /\?/.test(raw) || QWORDS.test(q.trim()) || /\bbapa\b|swamishri|pramukh swami|mahant swami/.test(q)
      || ((Q.places.length || Q.region) && (Q.years.length || Q.month || Q.mandir || Q.how)) || (Q.mandir && Q.years.length) || (Q.fest && Q.years.length) || Q.dates.length > 0 || !!Q.day;
    // only a name ("Swamishri", "Bapa"): an ordinary search for the word, not a question
    if (!/\?/.test(raw) && !gujarati && !QWORDS.test(q.trim()) && !Q.rest && !Q.fest && !Q.dates.length && !Q.day && !Q.places.length && !Q.region && !Q.years.length
      && !Q.month && !Q.things.length && !Q.mandir) Q.isQuestion = false;
    return Q;
  }

  // ---------- the diary's own numbers ----------
  let dayCache = null, dayCacheN = -1;
  function bapaDays() {   // date -> photos with Bapa that day
    if (dayCacheN === items.length) return dayCache;
    dayCache = {};
    for (const r of items) if (r.kind === 'photo' && r.b && r.g[0] && !r.g[1]) dayCache[r.d] = (dayCache[r.d] || 0) + 1;
    dayCacheN = items.length;
    return dayCache;
  }
  const stopOn = d => STOPS.find(s => s.a <= d && d <= s.b);
  const near = d => { let before = null, after = null; for (const s of STOPS) { if (s.b < d) before = s; else if (s.a > d && !after) after = s; } return { before, after }; };
  const placesIn = Q => Q.places.length ? Q.places : Q.region ? PLACES.filter(p => regionCountries(Q.region).includes(COUNTRY[p] || 'India')) : [];
  const nameOf = Q => Q.places.length ? andList(Q.places) : Q.region.replace(/\b\w/g, c => c.toUpperCase()).replace(/\bUsa\b/, 'USA').replace(/\bUk\b/, 'UK');
  const placeHit = (r, places) => {
    if (r.kind === 'photo') return places.some(p => r.city === p || r.g[2].toLowerCase().split(',').some(c => c.trim().startsWith(p.toLowerCase())));
    return places.some(p => ((r.place || '') + ' ' + (r.text || '')).includes(p));
  };
  // a photo from an album with a range of dates (a long stay) counts for every day of it
  const covers = (r, d) => r.d === d || (r.kind === 'photo' && !!r.g[1] && r.g[0] <= d && d <= r.g[1]);
  const coversAny = (r, set) => set.has(r.d) || (r.kind === 'photo' && !!r.g[1] && [...set].some(d => r.g[0] <= d && d <= r.g[1]));
  const bapaOnly = r => r.kind !== 'photo' || r.b;   // Bapa's questions show photos with Bapa in them

  // ---------- the answer card ----------
  const PORTRAIT = { P: '/about/img/psm.jpg', M: '/about/img/msm.jpg' };
  function gurus(vals, valsGu) {
    return `<div class="ask-gurus">${['P', 'M'].map(k => `<div class="ask-guru${vals[k] ? '' : ' dim'}"><img src="${PORTRAIT[k]}" alt="${GURU[k]}"><div><div class="n">${GURU[k]}</div><div class="v">${t(vals[k] || 'Not in this answer', (valsGu || {})[k] || (vals[k] ? '' : 'આ જવાબમાં નથી'))}</div></div></div>`).join('')}</div>`;
  }
  // English and Gujarati side by side: the Gujarati switch shows one or the other
  const t = (en, gu) => gu ? `<span class="ask-en">${en}</span><span class="ask-gu" translate="no">${gu}</span>` : en;
  function closeUp(s) {
    if (!s.pic) return `<span class="ask-cu" aria-hidden="true"></span>`;
    const [c, r, rows] = s.pic;
    return `<span class="ask-cu" role="img" aria-label="Bapa in ${esc(s.p)}" style="background-image:url(/travels/photos/${s.y}.jpg);background-size:800% ${rows * 100}%;background-position:${c / 7 * 100}% ${rows > 1 ? r / (rows - 1) * 100 : 0}%"></span>`;
  }
  function rows(list, label, labelGu, limit = 8) {
    const row = s => `<div class="ask-row"><span class="yr">${s.y}</span>${closeUp(s)}<span class="tx"><b>${esc(s.p)}</b> <span class="when">${range(s.a, s.b)}</span><span class="c">${esc(s.cap || '')}</span></span><span class="who">${GURU[guruOf(s.a)]}<br><button type="button" class="ask-see" data-place="${esc(s.p)}" data-from="${s.a}" data-to="${s.b}">${s.n ? t(`See ${plural(s.n, 'photo')}`, gd(`${num(s.n)} ફોટા જુઓ`)) : t('See that day', 'તે દિવસ જુઓ')}</button></span></div>`;
    const more = list.length > limit ? `<button type="button" class="ask-more">${t(`Show all ${list.length}`, gd(`બધાં ${list.length} જુઓ`))}</button>` : '';
    return `<h3 class="ask-h">${t(label, labelGu)}</h3><div class="ask-rows">${list.slice(0, limit).map(row).join('')}<div class="ask-rest" hidden>${list.slice(limit).map(row).join('')}</div></div>${more}`;
  }
  const below = n => `<p class="ask-below">${t(n ? `The ${plural(n, 'photo')} with Bapa are below.` : 'The photos are below.', 'ફોટા નીચે છે.')}</p>`;
  function card(Q, en, gu, sub, body) {
    return `<div class="ask-q">${t('You asked', 'આપે પૂછ્યું')} <b>${esc(Q.raw)}</b></div><p class="ask-a">${t(en, gu)}</p>${sub ? `<p class="ask-sub">${t(sub[0], sub[1])}</p>` : ''}${body || ''}`;
  }
  const P_GU = p => g(p);
  const inGu = p => `${g(p)}માં`;

  // ---------- answers: each gives the card, and which results answer it ----------
  function answer(Q) {
    const P = placesIn(Q);
    if (Q.mandir && P.length) return mandirAnswer(Q, P);
    if (Q.fest) return festAnswer(Q, P);
    if (Q.dates.length) return dateAnswer(Q, Q.dates[0]);
    if (Q.day) return dayAnswer(Q, P);
    if (Q.things.length) return thingsAnswer(Q, P);
    if (P.length) return placeAnswer(Q, P);
    if (Q.years.length) return periodAnswer(Q);
    if (Q.mandir) return { html: '', keep: r => (r.m || '').includes(Q.mandir) && bapaOnly(r) };
    return wordsAnswer(Q, P);
  }

  function placeAnswer(Q, P) {
    let list = STOPS.filter(s => P.includes(s.p));
    const name = nameOf(Q);
    if (Q.years.length) list = list.filter(s => Q.years.some(y => +s.a.slice(0, 4) <= y && y <= +s.b.slice(0, 4)));
    if (Q.month) list = list.filter(s => Q.years.length ? true : (+s.a.slice(5, 7) <= Q.month && Q.month <= +s.b.slice(5, 7)) || s.a.slice(0, 4) !== s.b.slice(0, 4));
    if (Q.guru) list = list.filter(s => guruOf(s.a) === Q.guru);
    const who = Q.guru ? GURU[Q.guru] : 'Bapa', whoGu = Q.guru ? GURU_GU[Q.guru] : 'બાપા';
    if (!list.length) return { html: card(Q, `The diary has no visit by ${who} to ${esc(name)}${Q.years.length ? ' in ' + andList(Q.years.map(String)) : ''}.`,
      `ડાયરીમાં ${whoGu}ની ${esc(P_GU(name))}ની કોઈ મુલાકાત નથી.`, ['Try another year, or the full name of the place.', '']), keep: () => false };
    const years = [...new Set(list.map(s => s.y))];
    const total = list.reduce((n, s) => n + s.n, 0);
    const by = { P: list.filter(s => guruOf(s.a) === 'P'), M: list.filter(s => guruOf(s.a) === 'M') };
    const span = l => { const ys = [...new Set(l.map(s => String(s.y)))]; return ys.length > 3 ? `${ys[0]} to ${ys.at(-1)}` : andList(ys); };
    const gv = k => by[k].length ? `${plural(by[k].length, 'visit')}, ${span(by[k])}` : '';
    const gvGu = k => by[k].length ? gd(`${by[k].length} મુલાકાત, ${span(by[k]).replace(' to ', ' થી ').replace(' and ', ' અને ')}`) : '';
    const seen = [...new Set(list.map(s => s.p))];
    let en, gu, order = list;
    if (Q.how === 'count') { en = `${who} went to ${esc(name)} ${plural(list.length, 'time')}, in ${plural(years.length, 'different year')}.`; gu = gd(`${whoGu} ${esc(P_GU(name))} ${list.length} વાર પધાર્યા, ${years.length} જુદાં જુદાં વર્ષોમાં.`); }
    else if (Q.how === 'first') { const s = list[0]; en = `The first time was ${range(s.a, s.b)}, in ${esc(s.p)}.`; gu = `પહેલી વાર ${range(s.a, s.b, fmtGu)} દરમિયાન ${esc(inGu(s.p))}.`; }
    else if (Q.how === 'last') { const s = list.at(-1); en = `The last time was ${range(s.a, s.b)}, in ${esc(s.p)}.`; gu = `છેલ્લી વાર ${range(s.a, s.b, fmtGu)} દરમિયાન ${esc(inGu(s.p))}.`; order = list.slice().reverse(); }
    else { en = `${who} went to ${esc(name)} in ${andList(years.map(String))}.`; gu = gd(`${whoGu} ${esc(P_GU(name))} ${andList(years.map(String), 'અને')}માં પધાર્યા.`); }
    const sub = `${plural(list.length, 'visit')} with ${num(total)} photos of Bapa` + (Q.region ? `, at ${plural(seen.length, 'place')}: ${andList(seen.slice(0, 8))}${seen.length > 8 ? ' and more' : ''}.` : '.');
    const subGu = gd(`${list.length} મુલાકાત, બાપાના ${num(total)} ફોટા.`);
    return { html: card(Q, en, gu, [sub, subGu], gurus({ P: gv('P'), M: gv('M') }, { P: gvGu('P'), M: gvGu('M') }) + rows(order, 'Every visit', 'દરેક મુલાકાત') + below(total)),
      keep: r => bapaOnly(r) && list.some(s => s.a <= r.d && r.d <= s.b) && placeHit(r, P) };
  }

  function whereOn(d) {
    const s = stopOn(d);
    if (s) return { s, ok: true };
    const n = near(d);
    return { ...n, ok: false };
  }

  function dateAnswer(Q, d, label, labelGu) {
    const w = whereOn(d), k = guruOf(d), n = bapaDays()[d] || 0, fests = (cal[d] || {}).list || [];
    const named = label || fmt(d), namedGu = labelGu || fmtGu(d);
    let en, gu, sub = '', subGu = '';
    const early = !w.ok && !w.before && w.after && d.slice(0, 4) < w.after.a.slice(0, 4);   // before the photos begin
    if (w.ok) {
      en = `On ${named}, ${GURU[k]} was in ${esc(w.s.p)}.`; gu = `${namedGu}ના દિવસે ${GURU_GU[k]} ${esc(inGu(w.s.p))} હતા.`;
      sub = (n ? `The diary has ${plural(n, 'photo')} of Bapa that day. ` : '') + (w.s.a === w.s.b ? '' : `He was in ${esc(w.s.p)} from ${range(w.s.a, w.s.b)}.`);
    } else {
      en = `The diary has no photos of ${GURU[k]} on ${named}.`; gu = `${namedGu}ના દિવસના ${GURU_GU[k]}ના ફોટા ડાયરીમાં નથી.`;
      const bits = [];
      if (early) bits.push(`The photos in the diary start in ${w.after.a.slice(0, 4)}. Any On this day stories from that day are below`);
      else {
        if (w.before) bits.push(`On ${fmt(w.before.b)} He was in ${esc(w.before.p)}`);
        if (w.after) bits.push(`${bits.length ? 'on' : 'On'} ${fmt(w.after.a)} He was in ${esc(w.after.p)}`);
      }
      sub = bits.length ? andList(bits) + '.' : '';
    }
    if (fests.length && !label) sub += ` BAPS calendar: ${esc(andList(fests))}.`;
    const vals = { P: '', M: '' }, valsGu = { P: '', M: '' };
    vals[k] = w.ok ? `In ${esc(w.s.p)} that day` : 'No photos that day'; valsGu[k] = w.ok ? `તે દિવસે ${esc(inGu(w.s.p))}` : 'તે દિવસના ફોટા નથી';
    const list = w.ok ? [w.s] : early ? [] : [w.before, w.after].filter(Boolean);
    return { html: card(Q, en, gu, [sub.trim(), subGu], gurus(vals, valsGu) + (list.length ? rows(list, w.ok ? 'Where He was' : 'The nearest days in the diary', w.ok ? 'તેઓ ક્યાં હતા' : 'ડાયરીના નજીકના દિવસો') : '') + below(n)),
      keep: r => covers(r, d) && bapaOnly(r) };
  }

  function festAnswer(Q, P) {
    let ds = festDays()[Q.fest] || [];
    const fGu = g(Q.fest);
    if (Q.years.length) {
      const hit = ds.filter(d => Q.years.includes(+d.slice(0, 4)));
      if (hit.length === 1) return dateAnswer(Q, hit[0], `${Q.fest} ${hit[0].slice(0, 4)} (${fmt(hit[0], true)})`, gd(`${fGu} ${hit[0].slice(0, 4)} (${fmtGu(hit[0], true)})`));
      if (!hit.length) return { html: card(Q, `The diary does not have the date of ${esc(Q.fest)} in ${andList(Q.years.map(String))}.`, '',
        [`The BAPS calendar in the diary runs from 2010 to 2027, and the main festivals are worked out back to ${OLD_FEST_FROM}.`, '']), keep: () => false };
      ds = hit;
    }
    ds = ds.filter(d => d <= TODAY);
    let found = ds.map(d => ({ d, w: whereOn(d) })).filter(x => x.w.ok);
    if (P.length) found = found.filter(x => P.includes(x.w.s.p));
    if (Q.guru) found = found.filter(x => guruOf(x.d) === Q.guru);
    if (!found.length) return { html: card(Q, `The diary has no photos of Bapa on ${esc(Q.fest)}${P.length ? ' in ' + esc(nameOf(Q)) : ''}.`, '', null), keep: () => false };
    const where = {};
    found.forEach(x => (where[x.w.s.p] = where[x.w.s.p] || []).push(x.d));
    const top = Object.entries(where).sort((a, b) => b[1].length - a[1].length);
    const nY = new Set(found.map(x => x.d.slice(0, 4))).size;
    const en = `Bapa celebrated ${esc(Q.fest)} in ${plural(top.length, 'place')} over ${plural(nY, 'year')}${top[0][1].length > 1 ? `, most often in ${esc(top[0][0])} (${top[0][1].length} times)` : ''}.`;
    const gu = gd(`બાપાએ ${esc(fGu)} ${nY} વર્ષ ${top.length} સ્થળોએ ઊજવી${top[0][1].length > 1 ? `, સૌથી વધુ ${esc(inGu(top[0][0]))} (${top[0][1].length} વાર)` : ''}.`);
    const by = k => found.filter(x => guruOf(x.d) === k);
    const most = l => Object.entries(l.reduce((o, x) => (o[x.w.s.p] = (o[x.w.s.p] || 0) + 1, o), {})).sort((a, b) => b[1] - a[1])[0][0];
    const gv = k => by(k).length ? `${plural(by(k).length, 'year')}, mostly in ${esc(most(by(k)))}` : '';
    const gvGu = k => by(k).length ? gd(`${by(k).length} વર્ષ, મોટા ભાગે ${esc(inGu(most(by(k))))}`) : '';
    const days = bapaDays();
    const list = found.slice().reverse().map(x => ({ ...x.w.s, a: x.d, b: x.d, n: days[x.d] || 0, cap: `${Q.fest}, ${fmt(x.d)}` }));
    const dates = new Set(found.map(x => x.d));
    const early = found.some(x => !cal[x.d]);
    return { html: card(Q, en, gu, [`Every year from the BAPS calendar${early ? ' (before 2010, worked out from the Hindu calendar)' : ''}, with where Bapa was that day.`, 'BAPS કેલેન્ડરનું દરેક વર્ષ, અને તે દિવસે બાપા ક્યાં હતા.'],
      gurus({ P: gv('P'), M: gv('M') }, { P: gvGu('P'), M: gvGu('M') }) + rows(list, `${Q.fest}, year by year`, `${fGu}, વર્ષે વર્ષે`) + below(list.reduce((n, s) => n + s.n, 0))),
      keep: r => coversAny(r, dates) && bapaOnly(r) };
  }

  function dayAnswer(Q, P) {
    const md = Q.day, days = bapaDays();
    let ds = Object.keys(days).filter(d => d.slice(5) === md && (!Q.years.length || Q.years.includes(+d.slice(0, 4)))).sort();
    if (Q.years.length === 1 && ds.length <= 1) return dateAnswer(Q, `${Q.years[0]}-${md}`);
    let found = ds.map(d => ({ d, w: whereOn(d) })).filter(x => x.w.ok);
    if (P.length) found = found.filter(x => P.includes(x.w.s.p));
    const label = fmt('2000-' + md, true), labelGu = fmtGu('2000-' + md, true);
    if (!found.length) return { html: card(Q, `The diary has no photos of Bapa on ${label}.`, `${labelGu}ના બાપાના ફોટા ડાયરીમાં નથી.`, null), keep: () => false };
    const list = found.slice().reverse().map(x => ({ ...x.w.s, a: x.d, b: x.d, n: days[x.d], cap: ((cal[x.d] || {}).list || []).join(', ') || x.w.s.cap }));
    const total = list.reduce((n, s) => n + s.n, 0), by = k => found.filter(x => guruOf(x.d) === k).length;
    const y0 = found[0].d.slice(0, 4), y1 = found.at(-1).d.slice(0, 4);
    const dates = new Set(found.map(x => x.d));
    return { html: card(Q, `Bapa's darshan on ${label} is in the diary ${plural(found.length, 'time')}, from ${y0} to ${y1}.`,
      gd(`${labelGu}નાં બાપાનાં દર્શન ડાયરીમાં ${found.length} વાર છે, ${y0} થી ${y1}.`), [`${num(total)} photos across the years. Here is where He was each time.`, ''],
      gurus({ P: by('P') ? plural(by('P'), 'year') : '', M: by('M') ? plural(by('M'), 'year') : '' }, { P: by('P') ? gd(`${by('P')} વર્ષ`) : '', M: by('M') ? gd(`${by('M')} વર્ષ`) : '' }) +
      rows(list, `${label}, year by year`, `${labelGu}, વર્ષે વર્ષે`) + below(total)),
      keep: r => coversAny(r, dates) && bapaOnly(r) };
  }

  function periodAnswer(Q) {
    const ys = Q.years.map(String), mm = Q.month ? String(Q.month).padStart(2, '0') : '';
    let list = STOPS.filter(s => ys.some(y => s.a.slice(0, 4) <= y && y <= s.b.slice(0, 4)));
    if (mm) list = list.filter(s => ys.some(y => s.a.slice(0, 7) <= `${y}-${mm}` && `${y}-${mm}` <= s.b.slice(0, 7)));
    if (Q.guru) list = list.filter(s => guruOf(s.a) === Q.guru);
    const when = (Q.month ? MON[Q.month - 1] + ' ' : '') + (ys.length > 3 ? `${ys[0]} to ${ys.at(-1)}` : andList(ys));
    const whenGu = gd((Q.month ? GM[Q.month - 1] + ' ' : '') + (ys.length > 3 ? `${ys[0]} થી ${ys.at(-1)}` : andList(ys, 'અને')));
    if (!list.length) return { html: card(Q, `The diary has no travels for ${when}.`, `${whenGu} માટે ડાયરીમાં કોઈ વિચરણ નથી.`, ['The photos run from 1999 to today.', '']), keep: () => false };
    const places = [...new Set(list.map(s => s.p))], countries = [...new Set(places.map(p => COUNTRY[p] || 'India'))];
    const en = Q.month ? `In ${when}, Bapa was in ${andList(places.slice(0, 6))}${places.length > 6 ? ` and ${places.length - 6} more places` : ''}.`
      : `In ${when}, Bapa went to ${plural(places.length, 'place')} in ${plural(countries.length, 'country', 'countries')}.`;
    const gu = Q.month ? `${whenGu}માં બાપા ${places.slice(0, 6).map(g).join(', ')}${places.length > 6 ? gd(` અને બીજાં ${places.length - 6} સ્થળોએ`) : ''} હતા.`
      : gd(`${whenGu}માં બાપા ${countries.length} દેશોમાં ${places.length} સ્થળોએ પધાર્યા.`);
    const total = list.reduce((n, s) => n + s.n, 0);
    const by = k => new Set(list.filter(s => guruOf(s.a) === k).map(s => s.p)).size;
    return { html: card(Q, en, gu, Q.month ? null : [`${andList(countries)}.`, countries.map(g).join(', ')],
      gurus({ P: by('P') ? plural(by('P'), 'place') : '', M: by('M') ? plural(by('M'), 'place') : '' }, { P: by('P') ? gd(`${by('P')} સ્થળો`) : '', M: by('M') ? gd(`${by('M')} સ્થળો`) : '' }) +
      rows(list, 'His travels, in order', 'તેમનું વિચરણ, ક્રમવાર', 10) + below(0)),
      keep: r => bapaOnly(r) && ys.includes(r.d.slice(0, 4)) && (!mm || r.d.slice(5, 7) === mm) && (!Q.guru || guruOf(r.d) === Q.guru) };
  }

  function mandirAnswer(Q, P) {
    const kinds = { p: ['murti pratishtha', 'મૂર્તિપ્રતિષ્ઠા'], s: ['foundation stone', 'શિલાન્યાસ'], t: ['patotsav', 'પાટોત્સવ'] };
    const days = {};
    for (const r of items) if (r.kind === 'photo' && (r.m || '').includes(Q.mandir) && placeHit(r, P) && (!Q.years.length || Q.years.includes(+r.d.slice(0, 4)))) {
      const e = days[r.d] = days[r.d] || { n: 0, cap: '', p: r.city };
      e.n += r.b ? 1 : 0;
      if (!e.cap || (r.cap.length > 40 && r.cap.length < e.cap.length)) e.cap = r.cap;
    }
    const name = esc(nameOf(Q)), [k, kGu] = kinds[Q.mandir];
    const ds = Object.keys(days).sort();
    if (!ds.length) return { html: card(Q, `The diary has no ${k} day in ${name}.`, `ડાયરીમાં ${esc(P_GU(nameOf(Q)))}માં ${kGu}નો કોઈ દિવસ નથી.`,
      ['Mandirs opened before 1999 are older than the photos in the diary.', '']), keep: () => false };
    const list = ds.map(d => { const s = stopOn(d); return { y: +d.slice(0, 4), p: days[d].p, a: d, b: d, n: days[d].n, cap: days[d].cap, pic: s && s.p === days[d].p ? s.pic : 0, there: !!(s && P.includes(s.p)) }; });
    if (list.every(x => x.pic)) list.forEach(x => { x.y = +x.a.slice(0, 4); });
    const first = list[0];
    const by = gk => list.filter(x => x.there && guruOf(x.a) === gk).length;
    const en = first.there ? `${GURU[guruOf(first.a)]} performed the ${k} in ${esc(first.p)} on ${fmt(first.a)}.` : `The first ${k} in ${esc(first.p)} in the diary was on ${fmt(first.a)}.`;
    const gu = first.there ? `${GURU_GU[guruOf(first.a)]}એ ${fmtGu(first.a)}ના રોજ ${esc(inGu(first.p))} ${kGu} કરી.` : `ડાયરીમાં ${esc(inGu(first.p))} પહેલી ${kGu} ${fmtGu(first.a)}ના રોજ.`;
    const set = new Set(ds);
    return { html: card(Q, en, gu, list.length > 1 ? [`The diary has ${plural(list.length, k + ' day')} in ${name}, listed below.`, ''] : null,
      gurus({ P: by('P') ? plural(by('P'), 'day') : '', M: by('M') ? plural(by('M'), 'day') : '' }, { P: by('P') ? gd(`${by('P')} દિવસ`) : '', M: by('M') ? gd(`${by('M')} દિવસ`) : '' }) +
      rows(list, `Every ${k} day`, `${kGu}ના બધા દિવસો`) + below(0)),
      keep: r => set.has(r.d) && placeHit(r, P) && bapaOnly(r) };
  }

  function thingsAnswer(Q, P) {
    const rx = Q.things.map(x => THINGS[x]);
    const has = r => r.kind === 'photo' && Q.things.every((x, i) => (r.tags && r.tags.split(', ').includes(x)) || rx[i].test(r.hay));
    const keep = r => bapaOnly(r) && has(r) && (!Q.years.length || Q.years.includes(+r.d.slice(0, 4))) && (!Q.month || +r.d.slice(5, 7) === Q.month)
      && (!P.length || placeHit(r, P)) && (!Q.guru || guruOf(r.d) === Q.guru) && (!Q.rest || Q.rest.split(' ').every(w => THINGS_WORD.test(w) || r.hay.includes(w)));
    const what = andList(Q.things), whatGu = andList(Q.things.map(g), 'અને');
    const extra = `${Q.years.length ? ', ' + andList(Q.years.map(String)) : ''}${P.length ? ', in ' + esc(nameOf(Q)) : ''}`;
    return { html: card(Q, `Darshan of Bapa: ${esc(what)}${extra}.`, `બાપાનાં દર્શન: ${esc(whatGu)}${gd(Q.years.length ? ', ' + Q.years.join(', ') : '')}${P.length ? ', ' + esc(P_GU(nameOf(Q))) : ''}.`,
      ['Found from the words in each caption and what is in each photo. The photos are below.', 'દરેક ફોટાના શબ્દો અને તેમાં શું છે તે પરથી. ફોટા નીચે છે.']), keep };
  }
  const THINGS_WORD = new RegExp(Object.values(THINGS).map(r => r.source).join('|'));

  // not a question the diary can answer exactly: search for the words that are left, with any year or place it found
  function wordsAnswer(Q, P) {
    const words = Q.rest.split(' ').filter(w => w.length > 1).map(w => w.replace(/(ies)$/, 'y').replace(/([^s])s$/, '$1'));
    const alts = words.map(spellings);
    const keep = r => bapaOnly(r) && alts.every(a => a.some(w => r.hay.includes(w) || calHay(r.d).includes(w))) && (!Q.years.length || Q.years.includes(+r.d.slice(0, 4)))
      && (!Q.month || +r.d.slice(5, 7) === Q.month) && (!P.length || placeHit(r, P)) && (!Q.guru || guruOf(r.d) === Q.guru);
    const html = card(Q, words.length ? `Here is everything in the diary with “${esc(words.join(' '))}”.` : 'Ask about a place, a year, a date, a festival or what is in a photo.',
      words.length ? `ડાયરીમાં “${esc(words.join(' '))}” સાથેનું બધું.` : 'સ્થળ, વર્ષ, તારીખ, તહેવાર કે ફોટામાં શું છે તે વિશે પૂછો.',
      ['For example: “Where was Bapa on Janmashtami 2019?” or “How many times did Bapa go to Nairobi?”', '']);
    return { html, keep: words.length || Q.years.length || P.length ? keep : () => false };
  }
  const calHay = d => { const c = cal[d]; return c ? [c.indian, c.fest, c.about, c.notes].join(' ').toLowerCase() : festOn(d).join(' ').toLowerCase(); };

  // ---------- the search bar ----------
  let last = '', wasAsking = false;
  const box = () => $('answer');
  window.askDiary = function (text) {
    const raw = (text || '').trim();
    last = raw;
    if (!raw || !ready || !items.length) { if (box()) box().hidden = true; return null; }
    if (/[઀-૿]/.test(raw) && !W) loadGu().then(() => { if (last === raw) search(); });
    const Q = read(raw);
    if (!Q.isQuestion) { box().hidden = true; wasAsking = false; return null; }
    // a new question starts from everything: the year the page opened on (or filters left from a word search) would hide its answer
    if (!wasAsking) ['fest', 'place', 'act', 'mandir', 'year', 'month', 'day', 'from', 'to'].forEach(id => $(id).value = '');
    if (!wasAsking) linkPlace = '';
    wasAsking = true;
    const A = answer(Q);
    box().innerHTML = A.html;
    box().hidden = !A.html;
    return A;
  };
  // questions to try, under the search bar
  // six, in two even rows of three (Darpan, 25 Oct 2026)
  const ASK = ['When did Bapa go to London?', 'Where was Bapa on Diwali 2005?', 'How many times did Bapa go to Africa?', 'Where was Bapa on 7 December?',
    'Where did Bapa go in March 2026?', 'Where was Bapa on Janmashtami?'];
  if ($('c-ask')) {
    $('c-ask').innerHTML = ASK.map(x => `<button type="button" data-ask="${esc(x)}">${esc(x)}</button>`).join('');
    $('c-ask').addEventListener('click', e => {
      const b = e.target.closest('[data-ask]'); if (!b) return;
      e.stopPropagation();
      ['fest', 'place', 'act', 'mandir', 'year', 'month', 'day', 'from', 'to'].forEach(id => $(id).value = '');
      linkPlace = '';
      $('q').value = b.dataset.ask; search();
      $('answer').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }
  // inside the answer: Show all, and See these photos (that visit, in the normal search)
  document.addEventListener('click', e => {
    const m = e.target.closest('.ask-more');
    if (m) { m.previousElementSibling.querySelector('.ask-rest').hidden = false; m.remove(); return; }
    const s = e.target.closest('.ask-see'); if (!s) return;
    ['q', 'fest', 'place', 'act', 'mandir', 'year', 'month', 'day'].forEach(id => $(id).value = '');
    linkPlace = s.dataset.place; placeOption(s.dataset.place);
    $('from').value = s.dataset.from; $('to').value = s.dataset.to;
    search();
    window.scrollTo({ top: $('years').offsetTop - 10, behavior: 'smooth' });
  });

  const css = document.createElement('style');
  css.textContent = `
.can .ask-chips button { font-style: italic; font-weight: 500; }
.status .spelt { flex-basis: 100%; font-size: 15px; color: var(--gold-deep); }
.answer-card { margin-top: 18px; background: linear-gradient(var(--ivory-top), var(--paper-hi)); border: 1px solid var(--ivory-edge); border-radius: 10px;
  padding: 22px clamp(16px, 4vw, 34px) 18px; box-shadow: 0 10px 26px -16px rgba(59, 18, 25, .45); scroll-margin-top: 90px; }
.ask-q { font: 700 11px/1.5 var(--sans); letter-spacing: .18em; text-transform: uppercase; color: var(--gold-deep); }
.ask-q b { color: var(--maroon); }
.ask-a { margin: 8px 0 0; font: 600 clamp(23px, 3.6vw, 30px)/1.25 var(--serif); color: var(--maroon); text-wrap: balance; }
.ask-sub { margin: 8px 0 0; font: italic 500 18px/1.45 var(--serif); color: var(--muted); text-wrap: pretty; }
.ask-gurus { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 18px; }
.ask-guru { display: flex; align-items: center; gap: 12px; min-width: 0; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper-hi); }
.ask-guru img { width: 54px; height: 54px; flex: none; border-radius: 50%; object-fit: cover; box-shadow: 0 0 0 2px var(--gold); }
.ask-guru .n { font: 700 10px/1.3 var(--sans); letter-spacing: .14em; text-transform: uppercase; color: var(--gold-deep); }
.ask-guru .v { font: 500 17px/1.3 var(--serif); color: var(--ink); }
.ask-guru.dim .v { color: var(--muted); font-style: italic; }
.ask-h { display: flex; align-items: center; gap: 12px; margin: 22px 0 6px; font: 700 11px var(--sans); letter-spacing: .2em; text-transform: uppercase; color: var(--gold-deep); }
.ask-h::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.ask-row { display: grid; grid-template-columns: 46px 60px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 8px 0; border-top: 1px solid var(--line); }
.ask-rows > .ask-row:first-child { border-top: 0; }
.ask-row .yr { font: 700 14px var(--sans); color: var(--maroon); font-variant-numeric: tabular-nums; }
.ask-cu { width: 60px; height: 60px; border-radius: 6px; background-color: var(--ivory-bot); background-repeat: no-repeat; box-shadow: 0 0 0 1px var(--ivory-edge); }
.ask-row .tx { min-width: 0; font: 500 17px/1.3 var(--serif); color: var(--ink); }
.ask-row .tx b { color: var(--maroon); }
.ask-row .c { display: block; font-style: italic; font-size: 15px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ask-row .who { text-align: right; font: 600 10.5px/1.6 var(--sans); letter-spacing: .06em; color: var(--muted); }
.ask-see, .ask-more { font: 700 10.5px var(--sans); letter-spacing: .12em; text-transform: uppercase; color: var(--maroon); background: none; border: 0; border-bottom: 1px solid var(--gold-soft); padding: 2px 0; cursor: pointer; }
.ask-more { margin-top: 8px; }
.ask-see:hover, .ask-more:hover { color: var(--gold-deep); }
.ask-below { margin: 16px 0 0; text-align: center; font: italic 500 17px var(--serif); color: var(--muted); }
.ask-gu { display: none; }
:root.gu .ask-gu { display: inline; }
:root.gu .ask-en { display: none; }
@media (max-width: 600px) {
  .ask-gurus { grid-template-columns: 1fr; }
  .ask-row { grid-template-columns: 40px 50px minmax(0, 1fr); gap: 10px; }
  .ask-cu { width: 50px; height: 50px; }
  .ask-row .who { grid-column: 3; text-align: left; }
}`;
  document.head.appendChild(css);
})();
