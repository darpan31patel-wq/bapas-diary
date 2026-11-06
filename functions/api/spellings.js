// Did you mean, learned (Darpan, 4 Nov 2026: "when a search finds nothing, the site suggests the closest place or word
// from the diary, and misspellings people keep making get learned from the Interaction page so next time they just work").
// A Cloudflare Pages Function at /api/spellings, kept in the same KV store as the missed searches (bound as MISSED), under
// the one key "spell/learned" (the missed list only reads keys starting "2", so it never sees this one):
//   POST /api/spellings {q: "sarngpur", fix: "sarangpur"}   someone tapped "Did you mean Sarangpur?" after "sarngpur"
//   GET  /api/spellings                                      {learned: {sarngpur: "sarangpur", ...}}  tapped 2 or more times
//   GET  /api/spellings?key=WORD                             {all: [[q, fix, times, lastDay], ...]}   for /interaction/
//   POST /api/spellings {key: WORD, forget: "sarngpur"}      Darpan takes one off from /interaction/
// The search page only ever uses a learned spelling for a word the diary does not have at all, and only when it is close
// to the diary word (site/search-ask.js checks both), so a made up entry can never hide real photos.

const KEY = 'spell/learned', LEARN_AT = 2;
const answer = (body, status = 200, cache = 'no-store') => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': cache },
});
const word = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
// how many letters apart two words are (added, dropped, changed, or two swapped)
function apart(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) {
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
  }
  return d[a.length][b.length];
}
const load = async env => (await env.MISSED.get(KEY, 'json').catch(() => null)) || {};

export async function onRequestPost({ request, env }) {
  if (!env.MISSED) return new Response(null, { status: 204 });
  let body = {};
  try { body = await request.json(); } catch (e) { return new Response(null, { status: 204 }); }
  const all = await load(env);
  if (body.forget !== undefined) {
    if (!env.MISSED_KEY || body.key !== env.MISSED_KEY) return answer({ error: 'wrong word' }, 403);
    delete all[word(body.forget)];
    await env.MISSED.put(KEY, JSON.stringify(all));
    return answer({ ok: true });
  }
  const q = word(body.q).replace(/[^a-z ]/g, ''), fix = word(body.fix).replace(/[^a-z ]/g, '');
  // only real slips: letters only, a few letters long, and close to the diary's word
  if (q.length < 3 || q.length > 40 || !fix || q === fix || apart(q.replace(/ /g, ''), fix.replace(/ /g, '')) > Math.max(2, Math.ceil(fix.length / 3)))
    return new Response(null, { status: 204 });
  const was = all[q] && all[q][0] === fix ? all[q] : [fix, 0, ''];
  all[q] = [fix, was[1] + 1, new Date().toISOString().slice(0, 10)];
  await env.MISSED.put(KEY, JSON.stringify(all));
  return new Response(null, { status: 204 });
}

export async function onRequestGet({ request, env }) {
  if (!env.MISSED) return answer({ learned: {} }, 200, 'public, max-age=600');
  const key = new URL(request.url).searchParams.get('key');
  const all = await load(env);
  if (key !== null) {
    if (!env.MISSED_KEY || key !== env.MISSED_KEY) return answer({ error: 'wrong word' }, 403);
    return answer({ learnAt: LEARN_AT, all: Object.entries(all).map(([q, [fix, n, day]]) => [q, fix, n, day]).sort((a, b) => b[2] - a[2] || (b[3] > a[3] ? 1 : -1)) });
  }
  const learned = {};
  for (const [q, [fix, n]] of Object.entries(all)) if (n >= LEARN_AT) learned[q] = fix;
  return answer({ learned }, 200, 'public, max-age=600');
}
