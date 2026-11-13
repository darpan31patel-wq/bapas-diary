// Darpan's own choice of special pictures (collage builder note, 13 Nov 2026): which story, News article, year or photos
// become the day's special picture, and which days get none. The 2pm picture project reads one small file,
// archive/special-days.json on main, at its morning run (about 5am UK). Behind the /darpan/ password
// (functions/darpan/_middleware.js runs first), so only Darpan can read or change it here.
//   GET  /darpan/api/special-days          {file: {about, add, off}, source: 'github' | 'studio' | 'none', at}
//   POST /darpan/api/special-days  {add, off}   replaces the two lists, keeps the "about" line, answers {ok, source, at}
// Where it goes: with the Pages secret STUDIO_GITHUB_TOKEN (a GitHub token for bapas-diary with Contents read and write;
// the deploy copies the GitHub secret of that name) the file is written to main; a copy is always kept in the KV store
// STUDIO_LOG under 'special-days' and served openly at /special-days.json (functions/special-days.json.js), so the
// 2pm picture project can read it from a Studio address when no token is set. Nothing else in the repository is touched.
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const s = (v, n) => String(v ?? '').slice(0, n);
const GH = 'https://api.github.com/repos/darpan31patel-wq/bapas-diary/contents/archive/special-days.json';
const ABOUT = "Darpan's own choice of special pictures (13 Nov 2026). add: each choice gets its own special picture on its day, 'MM-DD' every year or 'YYYY-MM-DD' that day only. kind story (ref = the story's date or channel link), news (ref = the News article's path), year (year = that year's photos of the day), photos (photos = addresses, with year, place, headline, story). off: days with no special picture at all.";
const KEY = 'special-days';
const DAY = /^(\d{4}-)?\d\d-\d\d$/;

const ghHeaders = (token) => ({ Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'User-Agent': 'bapas-diary-studio', 'X-GitHub-Api-Version': '2022-11-28' });

async function fromGitHub(token) {
  const r = await fetch(GH + '?ref=main', { headers: ghHeaders(token) });
  if (r.status === 404) return { file: null, sha: null };
  if (!r.ok) throw new Error('GitHub said ' + r.status);
  const j = await r.json();
  const text = new TextDecoder().decode(Uint8Array.from(atob((j.content || '').replace(/\n/g, '')), (c) => c.charCodeAt(0)));
  return { file: JSON.parse(text), sha: j.sha };
}

function clean(e) {
  if (!e || !DAY.test(e.day || '') || !['story', 'news', 'year', 'photos'].includes(e.kind)) return null;
  const out = { day: e.day, kind: e.kind };
  if (e.kind === 'story' || e.kind === 'news') { out.ref = s(e.ref, 300); if (!out.ref) return null; }
  if (e.kind === 'year' || e.kind === 'photos') { out.year = Number(e.year) || 0; if (!out.year) return null; }
  for (const f of ['note', 'headline', 'place']) if (e[f]) out[f] = s(e[f], f === 'headline' ? 300 : 200);
  if (e.story) out.story = s(e.story, 6000);
  if (Array.isArray(e.photos) && e.photos.length) out.photos = e.photos.slice(0, 40).map((p) => s(p, 400)).filter(Boolean);
  if (e.kind === 'photos' && !(out.photos || []).length) return null;
  return out;
}

export async function onRequestGet({ env }) {
  const token = env.STUDIO_GITHUB_TOKEN || '';
  if (token) {
    try { const { file } = await fromGitHub(token); if (file) return answer({ file, source: 'github' }); } catch (x) { /* falls back to the copy */ }
  }
  const v = env.STUDIO_LOG ? await env.STUDIO_LOG.get(KEY, 'json').catch(() => null) : null;
  if (v && v.file) return answer({ file: v.file, source: 'studio', at: v.at });
  return answer({ file: { about: ABOUT, add: [], off: [] }, source: 'none' });
}

export async function onRequestPost({ request, env }) {
  let e = {};
  try { e = await request.json(); } catch (x) { return answer({ error: 'not JSON' }, 400); }
  const add = (Array.isArray(e.add) ? e.add : []).slice(0, 400).map(clean).filter(Boolean);
  const off = [...new Set((Array.isArray(e.off) ? e.off : []).slice(0, 400).map((d) => s(d, 10)).filter((d) => DAY.test(d)))];
  const token = env.STUDIO_GITHUB_TOKEN || '';
  const at = new Date().toISOString();
  let about = ABOUT, sha = null, source = 'studio';
  if (token) {
    try { const got = await fromGitHub(token); sha = got.sha; if (got.file && got.file.about) about = got.file.about; }
    catch (x) { return answer({ error: 'GitHub could not be read: ' + x.message }, 502); }
  }
  const file = { about, add, off };
  if (env.STUDIO_LOG) await env.STUDIO_LOG.put(KEY, JSON.stringify({ at, file }));
  else if (!token) return answer({ error: 'nowhere to keep it: no store and no GitHub token' }, 503);
  if (token) {
    const body = {
      message: `Studio: Darpan's special picture choices (${at.slice(0, 16).replace('T', ' ')} UTC)`,
      content: btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify(file, null, 2) + '\n'))),
      branch: 'main', ...(sha ? { sha } : {}),
    };
    const r = await fetch(GH, { method: 'PUT', headers: { ...ghHeaders(token), 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) return answer({ ok: false, source: 'studio', at, error: 'kept in the Studio, but GitHub said ' + r.status + (r.status === 403 || r.status === 404 ? ' (the token needs Contents: Read and write on bapas-diary)' : '') });
    source = 'github';
  }
  return answer({ ok: true, source, at, add: add.length, off: off.length });
}
