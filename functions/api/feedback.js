// The feedback box at the bottom of About (Darpan, 4 Nov 2026: "I also want to add a feedback box to the bottom of
// 'about', and all those answers are seen in the missed page"). A Cloudflare Pages Function at /api/feedback:
//   POST /api/feedback   {message, name?, website?}   kept, answers {ok: true}
//   GET  /api/feedback?key=WORD                      {items: [{day, name, message}, ...]} newest first
// Kept in the same KV store as the searches that found nothing (binding MISSED), under keys starting "feedback/", so
// nothing new has to be set up. Read on bapas-diary.com/interaction/ with the same word (the MISSED_KEY secret).
// Only what the person typed and the day are kept: no email, no address, nothing about who sent it.

const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const clean = (s, n) => String(s || '').replace(/\r\n?/g, '\n').replace(/[ \t]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim().slice(0, n);

export async function onRequestPost({ request, env }) {
  let body = {};
  try { body = await request.json(); } catch (e) { return answer({ error: 'Sorry, something went wrong. Please try again.' }, 400); }
  if (body.website) return answer({ ok: true });   // the hidden box only robots fill in
  const message = clean(body.message, 2000), name = clean(body.name, 60).replace(/\n/g, ' ');
  if (message.length < 2) return answer({ error: 'Please write a few words first.' }, 400);
  if (!env.MISSED) return answer({ error: 'Sorry, the feedback box is not ready yet. Please email hello@bapas-diary.com.' }, 503);
  const now = new Date(), day = now.toISOString().slice(0, 10);
  const key = `feedback/${day}/${now.getTime()}-${Math.random().toString(36).slice(2, 7)}`;
  await env.MISSED.put(key, JSON.stringify({ message, name, page: 'about' }));   // kept for good
  return answer({ ok: true });
}

export async function onRequestGet({ request, env }) {
  const key = new URL(request.url).searchParams.get('key') || '';
  if (!env.MISSED) return answer({ error: 'no store yet' }, 503);
  if (!env.MISSED_KEY || key !== env.MISSED_KEY) return answer({ error: 'wrong word' }, 403);
  const items = [];
  let cursor;
  for (let n = 0; n < 10; n++) {
    const page = await env.MISSED.list({ prefix: 'feedback/', limit: 1000, cursor });
    for (const k of page.keys) {
      const v = await env.MISSED.get(k.name, 'json').catch(() => null);
      if (v && v.message) items.push({ at: Number(k.name.split('/')[2].split('-')[0]) || 0, day: k.name.slice(9, 19), name: v.name || '', message: v.message });
    }
    if (page.list_complete || !page.cursor) break;
    cursor = page.cursor;
  }
  items.sort((a, b) => b.at - a.at);
  return answer({ items });
}
