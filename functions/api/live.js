// Is BAPS live on YouTube right now? For the Where Bapa is now card on Today (Darpan, 30 Oct 2026: "Whenever there is a
// live webcast happening on this channel, please display it in this box, and make a link"). Website only.
// A Cloudflare Pages Function, served at /api/live:
//   GET   {live: true, id, title}                      on air now
//         {live: false, next: {id, title, start}}      a webcast the channel has announced (start: seconds since 1970)
//         {live: false}                                nothing on air or announced
// It reads the channel's own public pages: /live is the stream's watch page while the channel is on air (or about to be,
// for a webcast announced soon), and the Live tab (/streams) lists every webcast it has announced, with its start time
// (Darpan, 30 Oct 2026: "also, show if there is an upcoming webcast as soon as the channel shows this"). No key or secret. The answer is kept a minute in Cloudflare's cache, so however many
// people have Today open, YouTube is asked at most about once a minute from each place.

const CHANNEL = 'UChbtzN0XrhPUjFg_RWp_Mhg';   // youtube.com/@bapslive
const KEEP = 60;                              // seconds an answer is kept

const answer = (body) => new Response(JSON.stringify(body), {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${KEEP}` },
});

const page = (path) => fetch(`https://www.youtube.com/channel/${CHANNEL}/${path}`, {
  headers: {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
    'Accept-Language': 'en-GB,en;q=0.9',
    Cookie: 'SOCS=CAI; CONSENT=YES+1',   // past the cookie question YouTube asks in Europe
  },
}).then((r) => (r.ok ? r.text() : ''));

const unjson = (s) => { try { return JSON.parse('"' + s + '"'); } catch (e) { return s; } };
const unhtml = (s) => s.replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');

async function look() {
  const now = Date.now() / 1000;
  const html = await page('live');
  // the stream's own page: its id from the player's details (the canonical link is not always there)
  const id = (html.match(/"videoDetails":\{"videoId":"([\w-]{11})"/) || html.match(/<link rel="canonical" href="https:\/\/www\.youtube\.com\/watch\?v=([\w-]{11})"/) || [])[1];
  const title = unhtml((html.match(/<meta name="title" content="([^"]*)"/) || [])[1] || '');
  if (id && /"isLive":true/.test(html) && !/"isUpcoming":true/.test(html)) return { live: true, id, title };
  if (id && /"isUpcoming":true/.test(html)) {
    const start = +((html.match(/"scheduledStartTime":"(\d+)"/) || [])[1] || 0)
      || Date.parse((html.match(/"startTimestamp":"([^"]+)"/) || [])[1] || '') / 1000 || 0;
    if (start) return { live: false, next: { id, title, start } };
  }
  // the Live tab: each announced webcast carries its start time; the soonest one still to come (or just due)
  const tab = await page('streams');
  let next = null;
  for (const m of tab.matchAll(/"upcomingEventData":\{"startTime":"(\d+)"/g)) {
    const start = +m[1];
    if (start < now - 3600 || (next && next.start <= start)) continue;
    const before = tab.slice(Math.max(0, m.index - 20000), m.index);
    const v = [...before.matchAll(/"videoRenderer":\{"videoId":"([\w-]{11})"/g)].pop();
    if (!v) continue;
    const t = before.slice(v.index).match(/"title":\{"runs":\[\{"text":"((?:[^"\\]|\\.)*)"/);
    next = { id: v[1], title: t ? unjson(t[1]) : '', start };
  }
  return next ? { live: false, next } : { live: false };
}

export async function onRequestGet({ request, waitUntil }) {
  const key = new URL('/api/live', request.url).toString();
  const kept = await caches.default.match(key);
  if (kept) return kept;
  let body;
  try { body = await look(); } catch (e) { body = { live: false }; }
  const res = answer(body);
  waitUntil(caches.default.put(key, res.clone()));
  return res;
}
