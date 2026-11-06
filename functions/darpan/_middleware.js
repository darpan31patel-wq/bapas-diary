// Darpan's private corner of bapas-diary.com (Darpan, 4 Nov 2026: "an admin page on the website that only I have access
// to ... set a password for the page"). Website only: nothing here touches the daily 2pm picture.
//
// Every address under /darpan/ comes through here first. Nothing of the Studio is sent until the password is right:
//   no pass yet        the password page (and nothing else)
//   POST the password  right: a signed pass for this device, kept a year, then the page that was asked for
//                      wrong: a short wait, then the password page again
//   /darpan/logout     forgets the pass on this device
// The password is the Pages secret STUDIO_PASSWORD (the deploy copies it from the GitHub secret of the same name). It is
// never in the code. Changing it signs every device out. With no secret set, the page stays shut.

const COOKIE = 'bd_darpan';
const YEAR = 365 * 24 * 3600;
const enc = new TextEncoder();

async function keyFor(password) {
  const raw = await crypto.subtle.digest('SHA-256', enc.encode('bapas-diary darpan pass\n' + password));
  return crypto.subtle.importKey('raw', raw, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign', 'verify']);
}
const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
const unhex = (s) => new Uint8Array((s.match(/../g) || []).map((h) => parseInt(h, 16)));

async function makePass(key) {
  const until = String(Math.floor(Date.now() / 1000) + YEAR);
  return until + '.' + hex(await crypto.subtle.sign('HMAC', key, enc.encode(until)));
}
async function passOk(key, value) {
  const m = /^(\d{10})\.([0-9a-f]{64})$/.exec(value || '');
  if (!m || Number(m[1]) < Date.now() / 1000) return false;
  return crypto.subtle.verify('HMAC', key, unhex(m[2]), enc.encode(m[1]));   // constant time
}
// the same length and constant time, whatever is typed
async function samePassword(key, typed, password) {
  const a = await crypto.subtle.sign('HMAC', key, enc.encode(typed));
  return crypto.subtle.verify('HMAC', key, a, enc.encode(password));
}
function cookie(request, name) {
  for (const part of (request.headers.get('Cookie') || '').split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return v.join('=');
  }
  return '';
}

const PRIVATE = {
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
  'Cache-Control': 'private, no-store',
  'Referrer-Policy': 'no-referrer',
};

function lockPage(note, status = 200) {
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Bapa's Diary Studio</title>
<style>
:root{--maroon-deep:#2a0a12;--gold-hi:#ffe296;--gold-soft:#d9a441;--cream:#fff3dc;--mist:#d8c3a5}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 50% 0,#5a1626,var(--maroon-deep) 60%);color:var(--cream);font:16px/1.5 'Lora',Georgia,serif;min-height:100vh;display:grid;place-items:center;padding:24px 16px}
main{width:100%;max-width:380px;text-align:center}
h1{font:500 28px/1.2 'Lora',Georgia,serif;color:var(--gold-hi);margin:0 0 6px}
p{margin:0 0 22px;color:var(--mist)}
form{display:flex;flex-direction:column;gap:12px}
input{font:inherit;padding:12px 16px;border-radius:999px;border:1px solid rgba(217,164,65,.5);background:rgba(0,0,0,.3);color:var(--cream);text-align:center}
input:focus{outline:2px solid var(--gold-soft);outline-offset:2px}
button{font:700 12px 'Poppins',system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:#3d0e19;background:var(--gold-soft);border:0;border-radius:999px;padding:13px 18px;cursor:pointer}
.note{margin:16px 0 0;color:#ffb4a8;min-height:1.5em}
</style>
</head>
<body>
<main>
<h1>Bapa's Diary Studio</h1>
<p>Only for Darpan. Type your password to open it.</p>
<form method="post">
<input type="password" name="password" placeholder="Password" autocomplete="current-password" autofocus required>
<button type="submit">Open the Studio</button>
</form>
<p class="note">${note}</p>
</main>
</body>
</html>`;
  return new Response(html, { status, headers: { 'Content-Type': 'text/html; charset=utf-8', ...PRIVATE } });
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  const password = env.STUDIO_PASSWORD || '';
  if (!password) return lockPage('The Studio password has not been set up yet.', 503);
  const key = await keyFor(password);

  if (url.pathname === '/darpan/logout') {
    return new Response(null, { status: 303, headers: {
      Location: '/darpan/', ...PRIVATE,
      'Set-Cookie': `${COOKIE}=; Path=/darpan; Max-Age=0; HttpOnly; Secure; SameSite=Lax`,
    } });
  }

  const signedIn = await passOk(key, cookie(request, COOKIE));
  // a POST from a signed in device is the Studio itself (the changes log at /darpan/api/log), not a password try
  if (request.method === 'POST' && !signedIn) {
    const form = await request.formData().catch(() => null);
    const typed = String((form && form.get('password')) || '').slice(0, 200);
    if (!typed || !(await samePassword(key, typed, password))) {
      await new Promise((r) => setTimeout(r, 1500));   // slows anyone guessing
      return lockPage('That is not the password. Please try again.', 401);
    }
    return new Response(null, { status: 303, headers: {
      Location: url.pathname + url.search, ...PRIVATE,
      'Set-Cookie': `${COOKIE}=${await makePass(key)}; Path=/darpan; Max-Age=${YEAR}; HttpOnly; Secure; SameSite=Lax`,
    } });
  }

  if (!signedIn) return lockPage('');

  const res = await next();
  const out = new Response(res.body, res);
  for (const [k, v] of Object.entries(PRIVATE)) out.headers.set(k, v);
  return out;
}
