// The Studio's copy of Darpan's special picture choices, readable without the password (collage builder note, 13 Nov
// 2026: "it will read the file from a Studio address instead"). Only his choices: no names, nothing private. The
// password gated writer is functions/darpan/api/special-days.js; the same file also goes to archive/special-days.json
// on main when the GitHub token is set.
export async function onRequestGet({ env }) {
  const v = env.STUDIO_LOG ? await env.STUDIO_LOG.get('special-days', 'json').catch(() => null) : null;
  const file = (v && v.file) || { about: 'No choices saved in the Studio yet.', add: [], off: [] };
  return new Response(JSON.stringify(file, null, 2) + '\n', { status: 200, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Saved-At': (v && v.at) || '' } });
}
