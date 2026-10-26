// The sign up for the weekly darshan email of bapas-diary.com (Darpan, 25 Oct 2026). Website only.
// A Cloudflare Pages Function, served at /api/weekly:
//   POST {email, lists}    sends the little "please confirm" email (nobody is signed up without tapping it);
//                          lists: "weekly" (Sunday email) and/or "daily" (the morning On this day reminder, 26 Oct 2026)
//   GET ?e=&l=&t=&s=       the Confirm button: adds the address to those lists (Resend segments)
// The only secret is RESEND_API_KEY (a Pages secret, put there by the website deploy from the GitHub secret).
// The confirm link is signed with it, so nothing needs storing here; Resend keeps the list and the one tap unsubscribe.

const FROM = "Bapa's Diary <hello@bapas-diary.com>";
const SEGMENTS = { weekly: 'Weekly darshan', daily: 'Daily darshan' };
const SITE = 'https://bapas-diary.com';
const DAYS = 7;   // a confirm link works for a week

const enc = new TextEncoder();
const b64 = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');

async function sign(env, text) {
  const key = await crypto.subtle.importKey('raw', enc.encode('weekly-darshan:' + env.RESEND_API_KEY),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return b64(await crypto.subtle.sign('HMAC', key, enc.encode(text)));
}

async function resend(env, path, body, method = 'POST') {
  const r = await fetch('https://api.resend.com' + path, {
    method, headers: { Authorization: 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  return { ok: r.ok, status: r.status, data };
}

async function segmentId(env, name) {
  const list = await resend(env, '/segments', undefined, 'GET');
  const found = (list.data.data || []).find((s) => s.name === name);
  if (found) return found.id;
  return (await resend(env, '/segments', { name })).data.id;
}
const pickLists = (v) => [...new Set(String(v || '').split(/[ ,]+/))].filter((k) => k in SEGMENTS).sort();

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const good = (email) => typeof email === 'string' && email.length <= 254 && /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$/.test(email);

function confirmEmail(link, lists) {
  const what = lists.length === 2 ? 'arrives each morning, and the week\'s darshan every Sunday'
    : lists[0] === 'daily' ? 'arrives every morning' : 'arrives every Sunday morning';
  const serif = "'EB Garamond', Georgia, 'Times New Roman', serif", sans = 'Arimo, Arial, Helvetica, sans-serif';
  return `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;background:#faf1de"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#faf1de"><tr><td align="center" style="padding:22px 8px 30px">
<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="width:100%;max-width:520px;background:#fffaf0">
<tr><td align="center" style="background:#5a1626;padding:24px 20px 20px"><div style="font:700 11px ${sans};letter-spacing:4px;text-transform:uppercase;color:#d9a441">Bapa's Diary</div>
<div style="font:600 30px/1.1 ${serif};color:#ffe296;padding-top:8px">Nearly there</div></td></tr>
<tr><td align="center" style="padding:24px 24px 28px;font:18px/1.5 ${serif};color:#2e1a14">Jay Swaminarayan 🙏🏽<br>Tap the button below and your darshan of Pramukh Swami Maharaj and Mahant Swami Maharaj ${what}.
<div style="padding:20px 0 16px"><a href="${link}" style="display:inline-block;font:700 14px ${sans};color:#3d0e19;background:#d9a441;padding:12px 22px;border-radius:999px;text-decoration:none">Yes, send me the darshan</a></div>
<div style="font:12px/1.5 ${sans};color:#7a5c48">Didn't ask for this? Just ignore this email and nothing more will come.</div></td></tr>
</table></td></tr></table></body></html>`;
}

function page(title, words) {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title} · Bapa's Diary</title><link rel="stylesheet" href="/menu.css"></head>
<body style="margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(120% 140% at 50% 0%,#5a1626,#3d0e19);color:#faf1de;font:18px/1.5 'EB Garamond',Georgia,serif;text-align:center">
<main style="max-width:30rem;padding:24px"><h1 style="font-weight:600;color:#ffe296;margin:0 0 10px">${title}</h1><p style="margin:0 0 22px">${words}</p>
<a href="/" style="display:inline-block;font:700 13px Arimo,Arial,sans-serif;letter-spacing:.06em;text-transform:uppercase;color:#3d0e19;background:#d9a441;padding:12px 20px;border-radius:8px;text-decoration:none">Today's darshan</a></main></body></html>`,
    { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

export async function onRequestPost({ request, env }) {
  let body = {};
  try { body = await request.json(); } catch { return json({ error: 'Please type your email again.' }, 400); }
  if (body.website) return json({ ok: true });   // the hidden box only robots fill in
  const email = String(body.email || '').trim().toLowerCase();
  if (!good(email)) return json({ error: 'That email does not look right. Please check it.' }, 400);
  const lists = pickLists(Array.isArray(body.lists) ? body.lists.join(',') : body.lists || 'weekly');
  if (!lists.length) return json({ error: 'Please tick at least one.' }, 400);
  const l = lists.join(','), t = String(Math.floor(Date.now() / 1000));
  const s = await sign(env, email + '|' + l + '|' + t);
  const link = `${SITE}/api/weekly?e=${encodeURIComponent(email)}&l=${l}&t=${t}&s=${s}`;
  const r = await resend(env, '/emails', { from: FROM, to: [email], subject: 'Please confirm your darshan emails', html: confirmEmail(link, lists) });
  if (!r.ok) return json({ error: 'Sorry, the email could not be sent just now. Please try again later.' }, 502);
  return json({ ok: true });
}

export async function onRequestGet({ request, env }) {
  const u = new URL(request.url);
  const email = (u.searchParams.get('e') || '').toLowerCase(), t = u.searchParams.get('t') || '', s = u.searchParams.get('s') || '';
  const lists = pickLists(u.searchParams.get('l')), l = lists.join(',');
  const fresh = Date.now() / 1000 - Number(t) < DAYS * 86400;
  if (!good(email) || !lists.length || !fresh || s !== await sign(env, email + '|' + l + '|' + t))
    return page('This link has run out', 'Please sign up again on the Today page and use the newest email we send.');
  const segs = [];
  for (const k of lists) segs.push(await segmentId(env, SEGMENTS[k]));
  let r = await resend(env, '/contacts', { email, unsubscribed: false, segments: segs.map((id) => ({ id })) });
  if (!r.ok) {   // already known (maybe left before, or adding the other list): sign them back up and add the lists
    await resend(env, '/contacts/' + encodeURIComponent(email), { unsubscribed: false }, 'PATCH');
    for (const id of segs) r = await resend(env, `/contacts/${encodeURIComponent(email)}/segments/${id}`, {});
  }
  if (!r.ok) return page('Something went wrong', 'Sorry, we could not finish signing you up. Please try again a little later.');
  const when = { daily: 'every morning at 7 am UK time', weekly: 'every Sunday at 10 am UK time' };
  return page('You are signed up 🙏🏽', 'Your darshan of Pramukh Swami Maharaj and Mahant Swami Maharaj arrives ' + lists.map((k) => when[k]).join(', and ') + '.');
}
