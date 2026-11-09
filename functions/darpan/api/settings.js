// The Studio's backup (Darpan, 9 Nov 2026: a new laptop, a cleared browser or a lost phone must lose nothing). Behind
// the /darpan/ password (functions/darpan/_middleware.js runs first), so only Darpan can read or write it.
//   POST /darpan/api/settings  {at, settings, dates, zoom, log}   this device's whole Studio memory, replaces the last
//   GET  /darpan/api/settings                                     the same back, {} when nothing is saved yet
// Kept in the Cloudflare KV store bound as STUDIO_LOG under one key. Without it the Studio keeps everything on the device only.
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const KEY = 'settings:backup';

export async function onRequestPost({ request, env }) {
  if (!env.STUDIO_LOG) return answer({ store: false }, 202);
  let e = {};
  try { e = await request.json(); } catch (x) { return answer({ error: 'not JSON' }, 400); }
  const body = JSON.stringify({
    at: /^\d{4}-\d\d-\d\dT[\d:.]+Z$/.test(e.at || '') ? e.at : new Date().toISOString(),
    settings: e.settings && typeof e.settings === 'object' ? e.settings : null,
    dates: e.dates && typeof e.dates === 'object' ? e.dates : null,
    zoom: typeof e.zoom === 'number' ? e.zoom : null,
    log: (Array.isArray(e.log) ? e.log : []).slice(0, 100),
  });
  if (body.length > 4e6) return answer({ error: 'too big' }, 413);
  await env.STUDIO_LOG.put(KEY, body);
  return answer({ ok: true });
}

export async function onRequestGet({ env }) {
  if (!env.STUDIO_LOG) return answer({ store: false });
  const v = await env.STUDIO_LOG.get(KEY, 'json').catch(() => null);
  return answer(v || {});
}
