// The Studio's changes log (Darpan, 4 Nov 2026: remember what he changed on the picture and why). Behind the /darpan/
// password (functions/darpan/_middleware.js runs first), so only Darpan, and Claude in his own browser, can read or add.
//   POST /darpan/api/log  {at, kind, for, how, where, changes: [...], why}   kept for good
//   GET  /darpan/api/log                                                     {entries: [...]} newest first
// Kept in the Cloudflare KV store bound as STUDIO_LOG. Without it the Studio keeps the log on the device only.
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const s = (v, n) => String(v ?? '').slice(0, n);

export async function onRequestPost({ request, env }) {
  if (!env.STUDIO_LOG) return answer({ store: false }, 202);
  let e = {};
  try { e = await request.json(); } catch (x) { return answer({ error: 'not JSON' }, 400); }
  const at = /^\d{4}-\d\d-\d\dT[\d:.]+Z$/.test(e.at || '') ? e.at : new Date().toISOString();
  const clean = {
    at, kind: e.kind === 'month' ? 'month' : 'day', for: s(e.for, 10), how: s(e.how, 60), where: s(e.where, 200),
    changes: (Array.isArray(e.changes) ? e.changes : []).slice(0, 80).map((c) => s(c, 300)), why: s(e.why, 2000),
  };
  await env.STUDIO_LOG.put(at, JSON.stringify(clean));
  return answer({ ok: true });
}

export async function onRequestGet({ env }) {
  if (!env.STUDIO_LOG) return answer({ store: false, entries: [] });
  const entries = [];
  let cursor;
  for (let n = 0; n < 5; n++) {
    const page = await env.STUDIO_LOG.list({ limit: 1000, cursor });
    for (const k of page.keys) { const v = await env.STUDIO_LOG.get(k.name, 'json').catch(() => null); if (v) entries.push(v); }
    if (page.list_complete || !page.cursor) break;
    cursor = page.cursor;
  }
  entries.sort((a, b) => b.at.localeCompare(a.at));
  return answer({ store: true, entries });
}
