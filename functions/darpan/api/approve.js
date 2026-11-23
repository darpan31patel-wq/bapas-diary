// Darpan's yes for the family group (Darpan, 22 Nov 2026: "when I see the picture in the preview window at 10, then I need an
// easier way for me to approve it for the family group"; 23 Nov 2026, asked what happens with no yes by 2pm: "no doesnt go out
// to family"). The phone page /darpan/ok/ writes it here. A special picture goes to the family group at 2pm only when he
// said yes for that day; the daily picture goes as always. Behind the /darpan/ password (functions/darpan/_middleware.js).
//   GET  /darpan/api/approve?date=YYYY-MM-DD       {date, approved, special, at}   (approved false when nothing is saved)
//   POST /darpan/api/approve  {date, approved, special}   special false = approved, but the special stays out today
// Kept in the KV store STUDIO_LOG under 'approve:<date>'; the 2pm send reads the open copy at /approved.json?date=...
const answer = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
const DATE = /^\d{4}-\d\d-\d\d$/;
const today = () => new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/London' });
const approvalOf = async (env, date) => {
  const v = env.STUDIO_LOG ? await env.STUDIO_LOG.get('approve:' + date, 'json').catch(() => null) : null;
  return { date, approved: !!(v && v.approved), special: !!(v && v.approved && v.special !== false), at: (v && v.at) || '' };
};

export async function onRequestGet({ request, env }) {
  const date = new URL(request.url).searchParams.get('date') || today();
  if (!DATE.test(date)) return answer({ error: 'date is YYYY-MM-DD' }, 400);
  return answer(Object.assign(await approvalOf(env, date), { store: !!env.STUDIO_LOG }));
}

export async function onRequestPost({ request, env }) {
  if (!env.STUDIO_LOG) return answer({ error: 'The approval store is not set up on the website.' }, 503);
  let e = {};
  try { e = await request.json(); } catch (x) { return answer({ error: 'not JSON' }, 400); }
  if (!DATE.test(e.date || '')) return answer({ error: 'date is YYYY-MM-DD' }, 400);
  const v = { approved: !!e.approved, special: e.special !== false, at: new Date().toISOString() };
  await env.STUDIO_LOG.put('approve:' + e.date, JSON.stringify(v), { expirationTtl: 60 * 24 * 3600 });
  return answer(Object.assign(await approvalOf(env, e.date), { ok: true }));
}
