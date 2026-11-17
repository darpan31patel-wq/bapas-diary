// The Studio's changes log, read only, for the 2pm picture project's weekly learning script (its note, 17 Nov 2026:
// "If the Studio change log can be read by GitHub ... it can learn from swaps and crops too").
//   GET /api/studio-log           header X-Studio-Read-Key: the GitHub secret STUDIO_READ_KEY (the deploy copies it to Pages)
//   GET /api/studio-log?since=2026-11-10                    only entries at or after that day
// Answers {entries: [...]} newest first, the same entries as /darpan/api/log. Without the key set, or with a wrong key, nothing.
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' },
});
const enc = new TextEncoder();
async function same(a, b) {   // constant time, whatever is sent
  const k = await crypto.subtle.importKey('raw', enc.encode('bapas-diary studio log'), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const [x, y] = await Promise.all([crypto.subtle.sign('HMAC', k, enc.encode(a)), crypto.subtle.sign('HMAC', k, enc.encode(b))]);
  const p = new Uint8Array(x), q = new Uint8Array(y); let d = 0; for (let i = 0; i < p.length; i++) d |= p[i] ^ q[i]; return d === 0;
}

export async function onRequestGet({ request, env }) {
  const want = (env.STUDIO_READ_KEY || '').trim();
  const got = (request.headers.get('X-Studio-Read-Key') || '').trim();
  if (!want || !got || !(await same(got, want))) { await new Promise((r) => setTimeout(r, 1000)); return answer({ error: 'no' }, 401); }
  if (!env.STUDIO_LOG) return answer({ store: false, entries: [] });
  const since = /^\d{4}-\d\d-\d\d$/.test(new URL(request.url).searchParams.get('since') || '') ? new URL(request.url).searchParams.get('since') : '';
  const entries = [];
  let cursor;
  for (let n = 0; n < 5; n++) {
    const page = await env.STUDIO_LOG.list({ limit: 1000, cursor });
    for (const k of page.keys) { if (since && k.name < since) continue; const v = await env.STUDIO_LOG.get(k.name, 'json').catch(() => null); if (v) entries.push(v); }
    if (page.list_complete || !page.cursor) break;
    cursor = page.cursor;
  }
  entries.sort((a, b) => b.at.localeCompare(a.at));
  return answer({ store: true, entries });
}
