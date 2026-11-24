// Has Darpan said yes to today's special picture for the family group? Read by the 2pm send (Darpan, 23 Nov 2026: with no
// yes by 2pm the special "doesnt go out to family"; the daily picture goes as always). Open to read, nothing private: only
// the day and yes or no. The password gated writer is functions/darpan/api/approve.js (the phone page /darpan/ok/).
//   GET /approved.json?date=YYYY-MM-DD   (no date = today in London)
//   ->  {date, approved, special, at}    special true = send the special picture(s) at 2pm; false = leave them out
const approvalOf = async (env, date) => {   // the same reading as functions/darpan/api/approve.js
  const v = env.STUDIO_LOG ? await env.STUDIO_LOG.get('approve:' + date, 'json').catch(() => null) : null;
  return { date, approved: !!(v && v.approved), special: !!(v && v.approved && v.special !== false), at: (v && v.at) || '' };
};
export async function onRequestGet({ request, env }) {
  const date = new URL(request.url).searchParams.get('date') || new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/London' });
  if (!/^\d{4}-\d\d-\d\d$/.test(date)) return new Response('{"error":"date is YYYY-MM-DD"}\n', { status: 400, headers: { 'Content-Type': 'application/json' } });
  return new Response(JSON.stringify(await approvalOf(env, date)) + '\n', { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
}
