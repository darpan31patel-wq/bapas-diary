// Searches that found nothing (Darpan, 31 Oct 2026: "when searches something that provides no searches, can we save
// those searches?"). A Cloudflare Pages Function at /api/missed:
//   POST /api/missed   {q: "the words", page: "search"}   kept, no answer body
//   GET  /api/missed?key=WORD                              {days: [[date, [[words, times], ...]], ...]} newest first
// Kept in a Cloudflare KV store bound as MISSED (the deploy binds it; see website-deploy.yml). Only the words typed,
// the day and the page: no names, no addresses, nothing about who searched. The list is read with the word kept as the
// MISSED_KEY secret, on bapas-diary.com/missed/. Without the store or the key, this does nothing and answers quietly.

const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const clean = (s) => String(s || '').replace(/\s+/g, ' ').trim().slice(0, 80);

export async function onRequestPost({ request, env }) {
  if (!env.MISSED) return new Response(null, { status: 204 });
  let body = {};
  try { body = await request.json(); } catch (e) { return new Response(null, { status: 204 }); }
  const q = clean(body.q), page = /^[a-z-]{1,20}$/.test(body.page || '') ? body.page : 'search';
  if (q.length < 2) return new Response(null, { status: 204 });
  const day = new Date().toISOString().slice(0, 10);
  const key = `${day}/${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
  await env.MISSED.put(key, JSON.stringify({ q, page }));   // kept for good (the diary keeps everything)
  return new Response(null, { status: 204 });
}

export async function onRequestGet({ request, env }) {
  const key = new URL(request.url).searchParams.get('key') || '';
  if (!env.MISSED) return answer({ error: 'no store yet' }, 503);
  if (!env.MISSED_KEY || key !== env.MISSED_KEY) return answer({ error: 'wrong word' }, 403);
  const days = {};
  let cursor;
  for (let n = 0; n < 20; n++) {   // up to 20,000 saved searches, newest days first below
    const page = await env.MISSED.list({ limit: 1000, cursor });
    for (const k of page.keys) {
      const day = k.name.slice(0, 10);
      const v = await env.MISSED.get(k.name, 'json').catch(() => null);
      if (!v || !v.q) continue;
      const d = days[day] = days[day] || {};
      const w = v.q.toLowerCase();
      d[w] = (d[w] || 0) + 1;
    }
    if (page.list_complete || !page.cursor) break;
    cursor = page.cursor;
  }
  const out = Object.keys(days).sort().reverse().map(day => [day, Object.entries(days[day]).sort((a, b) => b[1] - a[1])]);
  return answer({ days: out });
}
