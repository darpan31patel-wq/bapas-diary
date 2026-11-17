// The Studio's special picture remake, asked by the website itself (Darpan, 17 Nov 2026: "The special picture builder
// isn't building ... So make it work"). With the Pages secret STUDIO_GITHUB_TOKEN (the deploy copies the GitHub secret of
// that name) the Studio needs no GitHub key on each computer: it asks here, and this asks GitHub to run the Collage
// builder's remake (studio.yml, input special) and reads how the run is going. Behind the /darpan/ password
// (functions/darpan/_middleware.js runs first). Only these few GitHub addresses pass; nothing else can be asked.
//   GET  /darpan/api/remake                 {server: true | false}   is the website able to ask by itself
//   GET  /darpan/api/remake?p=<path>        GitHub's answer for one of the read paths below
//   POST /darpan/api/remake  {date}         starts the remake for that date (YYYY-MM-DD) on main; answers GitHub's status
const REPO = 'https://api.github.com/repos/darpan31patel-wq/bapas-diary';
const answer = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
});
const ghHeaders = (token) => Object.assign({ Accept: 'application/vnd.github+json', 'User-Agent': 'bapas-diary-studio', 'X-GitHub-Api-Version': '2022-11-28' },
  token ? { Authorization: 'Bearer ' + token } : {});
const READS = [
  /^\/actions\/workflows\/studio\.yml\/runs\?event=workflow_dispatch&per_page=\d{1,2}$/,
  /^\/actions\/runs\/\d{1,20}$/,
  /^\/actions\/runs\/\d{1,20}\/jobs$/,
  /^\/contents\/packs\/special\/(\d{4}-\d\d-\d\d\/pack|remake)\.json\?ref=studio$/,
];

export async function onRequestGet({ request, env }) {
  const token = env.STUDIO_GITHUB_TOKEN || '';
  const p = new URL(request.url).searchParams.get('p');
  if (!p) return answer({ server: !!token });
  if (!READS.some((re) => re.test(p))) return answer({ error: 'not allowed' }, 400);
  const raw = p.startsWith('/contents/');
  const r = await fetch(REPO + p, { headers: Object.assign(ghHeaders(token), raw ? { Accept: 'application/vnd.github.raw+json' } : {}) });
  return new Response(r.body, { status: r.status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
}

export async function onRequestPost({ request, env }) {
  const token = env.STUDIO_GITHUB_TOKEN || '';
  if (!token) return answer({ error: 'no token', server: false }, 503);
  let e = {};
  try { e = await request.json(); } catch (x) { return answer({ error: 'not JSON' }, 400); }
  const date = String(e.date || '');
  if (!/^\d{4}-\d\d-\d\d$/.test(date)) return answer({ error: 'date' }, 400);
  const r = await fetch(REPO + '/actions/workflows/studio.yml/dispatches', {
    method: 'POST', headers: Object.assign(ghHeaders(token), { 'Content-Type': 'application/json' }),
    body: JSON.stringify({ ref: 'main', inputs: { special: date } }),
  });
  return answer({ status: r.status }, r.status === 204 ? 200 : r.status);
}
