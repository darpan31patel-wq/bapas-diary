// Video moments (Darpan, 31 Oct 2026: "yes moments"): the chapters of one BAPS video on YouTube, so a Video Darshan
// link can open the video straight at the Arti, the Puja or the blessings. A Cloudflare Pages Function at /api/chapters:
//   GET /api/chapters?v=YOUTUBE_ID   {ch: [[seconds, "Arti"], ...]}   (an empty list when the video has none)
// It reads the video's own public watch page: YouTube's chapters, or else the times written in the description
// ("0:00 Puja", "12:30 Arti"). No key or secret. A video's chapters hardly ever change, so each answer is kept a week
// in Cloudflare's cache, and YouTube is asked about each video only once a week, only when someone looks at it.

const KEEP = 7 * 86400;

const answer = (body, keep = KEEP) => new Response(JSON.stringify(body), {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${keep}` },
});

const unjson = (s) => { try { return JSON.parse('"' + s + '"'); } catch (e) { return s; } };
const secs = (t) => t.split(':').reduce((a, n) => a * 60 + +n, 0);

export function chaptersOf(html) {
  // YouTube's own chapters (the ones that show on the video's progress bar)
  const own = [];
  for (const m of html.matchAll(/"chapterRenderer":\{"title":\{"simpleText":"((?:[^"\\]|\\.)*)"\},"timeRangeStartMillis":(\d+)/g)) {
    const at = Math.round(+m[2] / 1000), name = unjson(m[1]).trim();
    if (name && !own.some(c => c[0] === at)) own.push([at, name]);
  }
  if (own.length > 1) return own;
  // the times written in the description, one to a line
  const d = unjson((html.match(/"shortDescription":"((?:[^"\\]|\\.)*)"/) || [])[1] || '');
  const list = [];
  for (const line of d.split('\n')) {
    const m = line.match(/^\s*[-•▶►*]?\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*[-–—:|.)]?\s*(.{2,80}?)\s*$/)
      || line.match(/^\s*(.{2,80}?)\s*[-–—:|]\s*\(?((?:\d{1,2}:)?\d{1,2}:\d{2})\)?\s*$/);
    if (!m) continue;
    const [t, name] = /\d:\d\d/.test(m[1]) ? [m[1], m[2]] : [m[2], m[1]];
    if (!list.some(c => c[0] === secs(t))) list.push([secs(t), name.replace(/^[-–—:|.\s]+/, '')]);
  }
  return list.length > 1 ? list.sort((a, b) => a[0] - b[0]) : [];
}

export async function onRequestGet({ request, waitUntil }) {
  const id = new URL(request.url).searchParams.get('v') || '';
  if (!/^[\w-]{11}$/.test(id)) return answer({ ch: [] }, 3600);
  const key = new URL('/api/chapters?v=' + id, request.url).toString();
  const kept = await caches.default.match(key);
  if (kept) return kept;
  let body = { ch: [] }, keep = KEEP;
  try {
    const r = await fetch('https://www.youtube.com/watch?v=' + id, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36',
        'Accept-Language': 'en-GB,en;q=0.9',
        Cookie: 'SOCS=CAI; CONSENT=YES+1',
      },
    });
    const html = r.ok ? await r.text() : '';
    if (!html.includes('"videoDetails"')) keep = 3600;   // YouTube said no this time: ask again in an hour
    body = { ch: chaptersOf(html) };
  } catch (e) { keep = 600; }
  const res = answer(body, keep);
  waitUntil(caches.default.put(key, res.clone()));
  return res;
}
