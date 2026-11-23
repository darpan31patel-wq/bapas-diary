// Ask Claude (Darpan, 23 Nov 2026: "could I add a Claude API key to the search bar on the website?", then "0.50p limit",
// "build it"). A question typed into the Search bar, like "Why did Bapa go to Neasden in 1995?", also gets a short answer
// in plain words written by Claude, from the diary only. A Cloudflare Pages Function at /api/ask:
//   POST /api/ask   {q: "the question", hints: "what the page already found", lang: "en" | "gu"}
//        answers    {answer: "..."}   or   {off: "why"} when it is not answering (then Search carries on as always)
// The key: the Pages secret ANTHROPIC_API_KEY (the deploy copies it from the GitHub secret of the same name). It is never
// in the page, so nobody can copy it.
// The cap: at most 50p a day (London day) in Claude charges, counted from what each answer really used, kept in the KV
// store bound as MISSED under "ask/" keys (missed.js reads only keys starting "2", feedback.js only "feedback/").
// When the day's 50p is spent, or the key is missing, the Search bar simply works as it always has.
// Same answers are kept for 12 hours (the questions under the bar are asked again and again, and cost nothing then).
// Each visitor can ask 25 questions a day (only a scrambled form of their address is kept, for one day), so one person
// can never use up everyone's 50p.

const MODEL = 'claude-haiku-5-5';          // the cheapest Claude: $0.10 a million words in, $0.50 out
const CAP_PENCE = 50;                      // Darpan: "0.50p limit" a day
const USD_TO_PENCE = 80;                   // a little above the real rate, so the cap is never passed
const PER_VISITOR = 25;
const PRICE = { in: 0.10, write: 0.125, read: 0.01, out: 0.50 };   // dollars a million tokens, Haiku 5.5

const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const clean = (s, n) => String(s || '').replace(/\s+/g, ' ').trim().slice(0, n);
const londonDay = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/London' }).format(new Date());
const hash = async s => [...new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)))]
  .slice(0, 12).map(b => b.toString(16).padStart(2, '0')).join('');
// channel names and links never reach the answer (Darpan's firm rule: the site never names where the posts came from)
const NO_LINKS = s => s.replace(/https?:\/\/\S+/g, '').replace(/\bt\.me\/\S*/gi, '');
const NO_NAME = new RegExp(['tele', 'gram'].join(''), 'gi');

// ---------- the diary, read once per worker ----------
let DIARY = null;
async function diary(request, env) {
  if (DIARY) return DIARY;
  const get = async path => {
    const url = new URL(path, request.url);
    const r = env.ASSETS ? await env.ASSETS.fetch(url) : await fetch(url);
    return r.ok ? r.json() : null;
  };
  const [stopsJson, stories] = await Promise.all([get('/search/data/stops.json'), get('/search/data/stories.json')]);
  const country = (stopsJson && stopsJson.country) || {};
  // every stop of Bapa's travels, 1999 to now: "from..to Place, Country (N photos)"
  const travels = ((stopsJson && stopsJson.stops) || []).map(s => {
    const [, place, from, to, n] = s;
    return `${from}${to && to !== from ? '..' + to : ''} ${place}${country[place] && country[place] !== place ? ', ' + country[place] : ''} (${n} photos)`;
  }).join('\n');
  const posts = (stories || []).map(s => {
    const text = NO_LINKS(String(s[2] || '')).replace(NO_NAME, '').replace(/\n{2,}/g, '\n').trim();
    return { d: s[0], p: s[1] || '', text, hay: (s[1] + ' ' + text).toLowerCase() };
  });
  DIARY = { travels, posts };
  return DIARY;
}

// ---------- the few On this day stories that fit the question ----------
const STOP = new Set(('the and for was were did does when where what which who whom how many much times time with from into '
  + 'that this there their they them his her him bapa bapas swami swamishri maharaj pramukh mahant param pujya guru '
  + 'tell show give list find about have has had been any some all can could would should please first last ever year years '
  + 'day days go went going come came visit visited are is our you your do it its in on of to at by an a').split(' '));
const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
function pick(posts, q, most = 10) {
  const low = q.toLowerCase();
  const words = [...new Set(low.replace(/[^a-z0-9઀-૿ ]/g, ' ').split(/\s+/).filter(w => w.length > 2 && !STOP.has(w) && !/^\d+$/.test(w)))];
  const years = (low.match(/\b(19[4-9]\d|20[0-3]\d)\b/g) || []);
  const month = MONTHS.findIndex(m => low.includes(m) || new RegExp(`\\b${m.slice(0, 3)}\\b`).test(low)) + 1;
  const dayN = month && (low.match(/\b([0-3]?\d)(st|nd|rd|th)?\b/) || [])[1];
  const scored = [];
  for (const s of posts) {
    let n = 0;
    for (const w of words) if (s.hay.includes(w)) n += w.length > 5 ? 3 : 2;
    if (years.length && years.includes(s.d.slice(0, 4))) n += 3;
    if (month && Number(s.d.slice(5, 7)) === month) n += 2;
    if (dayN && Number(s.d.slice(8, 10)) === Number(dayN)) n += 2;
    if (n > 2) scored.push([n, s]);
  }
  scored.sort((a, b) => b[0] - a[0] || (a[1].d < b[1].d ? -1 : 1));
  return scored.slice(0, most).map(([, s]) => `${s.d} ${s.p}\n${s.text.slice(0, 900)}`).join('\n\n');
}

const RULES = `You answer questions on Bapa's Diary (bapas-diary.com), a devotional diary of the vicharan of the BAPS gurus.
"Bapa" or "Swamishri" means Pramukh Swami Maharaj up to 12 August 2016, and Mahant Swami Maharaj from 13 August 2016.
Before 1971 the guru was Yogiji Maharaj.

How to answer:
- Use ONLY the diary facts below and in the message. Never add facts from anywhere else, and never guess dates or places.
- If the diary does not hold the answer, say so kindly in one sentence, and say what it does show that is closest.
- Two to four short, warm sentences in plain words, like a kind elder explaining to family. No lists, no headings, no markdown.
- Write dates as "7 December 2005". Use the guru's full name the first time.
- Never name any app, channel, website or link the facts came from. Call the posts "On this day".
- If asked anything not about Bapa, the gurus, BAPS or the diary, gently say you can only answer about Bapa's diary.

Bapa's travels in the diary, one stop a line (date or date range, place, photos that day or trip):
`;

export async function onRequestPost({ request, env }) {
  if (!env.ANTHROPIC_API_KEY) return answer({ off: 'no key yet' });
  let body = {};
  try { body = await request.json(); } catch (e) { return answer({ off: 'bad question' }, 400); }
  const q = clean(body.q, 200), hints = clean(body.hints, 1500), gu = body.lang === 'gu' || /[઀-૿]/.test(q);
  if (q.length < 4) return answer({ off: 'too short' });

  // the same question asked lately: the kept answer, free
  const cache = caches.default;
  const cacheKey = new Request(`https://bapas-diary.com/api/ask/kept/${await hash(q.toLowerCase() + '|' + gu + '|' + hints)}`);
  const kept = await cache.match(cacheKey).catch(() => null);
  if (kept) return answer(await kept.json());

  // the day's 50p, and this visitor's 25 questions
  const day = londonDay(), store = env.MISSED;
  const spendKey = `ask/spend/${day}`;
  const spent = store ? Number(await store.get(spendKey).catch(() => 0)) || 0 : 0;
  if (spent >= CAP_PENCE) return answer({ off: 'today is full' });
  const who = `ask/who/${day}/${await hash((request.headers.get('CF-Connecting-IP') || 'x') + day)}`;
  const asked = store ? Number(await store.get(who).catch(() => 0)) || 0 : 0;
  if (asked >= PER_VISITOR) return answer({ off: 'enough for today' });

  const { travels, posts } = await diary(request, env);
  const stories = pick(posts, q);
  const today = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  const user = `Today is ${today}.\n\nWhat the Search page already found for this question:\n${hints || '(nothing)'}\n\n`
    + `On this day posts that may fit:\n${stories || '(none found)'}\n\n`
    + `The question: ${q}\n\n${gu ? 'Answer in simple Gujarati.' : 'Answer in English.'}`;

  let r;
  try {
    r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'x-api-key': env.ANTHROPIC_API_KEY, 'anthropic-version': '2026-10-21', 'content-type': 'application/json' },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 700,
        output_config: { effort: 'low' },
        // the rules and the travels list are the same every time: kept by Anthropic for 5 minutes at a tenth of the price
        system: [{ type: 'text', text: RULES + travels, cache_control: { type: 'ephemeral' } }],
        messages: [{ role: 'user', content: user }],
      }),
    });
  } catch (e) { return answer({ off: 'Claude not reachable' }); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) return answer({ off: `Claude said ${r.status}` });

  // what it really cost, added to today's total
  const u = j.usage || {};
  const usd = ((u.input_tokens || 0) * PRICE.in + (u.cache_creation_input_tokens || 0) * PRICE.write
    + (u.cache_read_input_tokens || 0) * PRICE.read + (u.output_tokens || 0) * PRICE.out) / 1e6;
  if (store) {
    const pence = usd * USD_TO_PENCE;
    await Promise.all([
      store.put(spendKey, String(Math.round((spent + pence) * 10000) / 10000), { expirationTtl: 40 * 86400 }),
      store.put(who, String(asked + 1), { expirationTtl: 2 * 86400 }),
    ]).catch(() => {});
  }

  if (j.stop_reason === 'refusal') return answer({ off: 'not answered' });
  const text = (j.content || []).filter(b => b.type === 'text').map(b => b.text).join('').trim();
  const out = NO_LINKS(text).replace(NO_NAME, '').replace(/[*#_`]/g, '').replace(/[ \t]+/g, ' ').trim();
  if (!out) return answer({ off: 'no answer' });
  const result = { answer: out };
  await cache.put(cacheKey, new Response(JSON.stringify(result), { headers: { 'Cache-Control': 'max-age=43200' } })).catch(() => {});
  return answer(result);
}

// how much of today's 50p is used (for Darpan, and the page to know whether to ask at all)
export async function onRequestGet({ env }) {
  const spent = env.MISSED ? Number(await env.MISSED.get(`ask/spend/${londonDay()}`).catch(() => 0)) || 0 : 0;
  return answer({ on: !!env.ANTHROPIC_API_KEY && spent < CAP_PENCE, spentPence: Math.round(spent * 100) / 100, capPence: CAP_PENCE });
}
