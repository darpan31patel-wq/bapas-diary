// Is BAPS live on YouTube right now? For the Where Bapa is now card on Today (Darpan, 30 Oct 2026: "Whenever there is a
// live webcast happening on this channel, please display it in this box, and make a link"). Website only.
// A Cloudflare Pages Function, served at /api/live:
//   GET   {live: false}  or  {live: true, id, title}
// It reads the channel's own public /live page, which is the stream's watch page while the channel is on air and the
// channel's home page when it is not. No key or secret. The answer is kept a minute in Cloudflare's cache, so however many
// people have Today open, YouTube is asked at most about once a minute from each place.

const CHANNEL = 'UChbtzN0XrhPUjFg_RWp_Mhg';   // youtube.com/@bapslive
const KEEP = 60;                              // seconds an answer is kept

const answer = (body) => new Response(JSON.stringify(body), {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${KEEP}` },
});

async function look() {
  const r = await fetch(`https://www.youtube.com/channel/${CHANNEL}/live`, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
      'Accept-Language': 'en-GB,en;q=0.9',
      Cookie: 'SOCS=CAI; CONSENT=YES+1',   // past the cookie question YouTube asks in Europe
    },
  });
  if (!r.ok) return { live: false };
  const html = await r.text();
  // on air: the page is the stream itself, playing now (an upcoming stream also has a watch page, but is not live yet)
  const id = (html.match(/<link rel="canonical" href="https:\/\/www\.youtube\.com\/watch\?v=([\w-]{11})"/) || [])[1];
  if (!id || !/"isLive":true/.test(html) || /"isUpcoming":true/.test(html)) return { live: false };
  const title = ((html.match(/<meta name="title" content="([^"]*)"/) || [])[1] || '')
    .replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
  return { live: true, id, title };
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
