"""Where is Bapa now, on the Today page of bapas-diary.com (Darpan, 29 Oct 2026: "Where is Bapa now: a small map on Today
showing Bapa's current town from his schedule. YES").

A small card in the Today header: a little map with a gold dot on the town Bapa is staying in, the dates of the stay,
what is on there today (the schedule's own times, local to the town) and where he goes next. No buttons or links.
On computers it sits in the empty space to the right of the date, so the ropes stay where they are; on tablets and
phones it is a slim strip under the Screensaver button.

Website only: nothing here touches the daily 2pm picture. Runs in the deploy after web_screensaver.py, which writes the
schedule it reads:

    python3 tools/web_bapa_now.py --out out

  reads  out/screensaver/data/schedule.json   the stays and each day's events (Bapa's Diary's read of the BAPS page)
         out/travels/index.html               the land outline and the towns' places on the map (the Travels globe's own)
  writes out/index.html                       the card, its look, its map of each stay from yesterday on, and the few
                                              lines that pick today's stay on the visitor's own phone or computer
"""
import argparse, datetime, json, math, os, re, sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 150, 150        # the map's size on the page
SPAN = 10.0            # degrees of longitude across the map: all of Gujarat's coast shows, so the town is easy to place


def land_rings(topo):
    """The Travels globe's land outline, as rings of [lon, lat]."""
    sx, sy = topo['transform']['scale']
    tx, ty = topo['transform']['translate']
    arcs = []
    for arc in topo['arcs']:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ids):
        out = []
        for i in ids:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(a[1:] if out else a)
        return out
    rings = []
    for g in topo['objects']['land']['geometries']:
        polys = g['arcs'] if g['type'] == 'MultiPolygon' else [g['arcs']]
        for poly in polys:
            rings.extend(ring(r) for r in poly)
    return rings


def clip(ring, x0, y0, x1, y1):
    """Sutherland-Hodgman: the part of a ring inside the box."""
    def cut(pts, inside, meet):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(meet(q, p))
                out.append(p)
            elif inside(q):
                out.append(meet(q, p))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)
    pts = ring
    for inside, meet in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                         (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        if not pts:
            break
        pts = cut(pts, inside, meet)
    return pts


def town_map(ll, rings):
    """A square map centred on the town: its box in lon/lat and the land as one SVG path."""
    lon, lat = ll
    k = math.cos(math.radians(lat))          # so the coast keeps its shape away from the equator
    half_x = SPAN / 2
    half_y = SPAN / 2 * k * H / W
    box = [round(lon - half_x, 4), round(lat + half_y, 4), round(lon + half_x, 4), round(lat - half_y, 4)]
    m = 0.4                                   # a little beyond the edges, so the outline never shows a seam
    d = []
    for r in rings:
        xs = [p[0] for p in r]; ys = [p[1] for p in r]
        if max(xs) < box[0] - m or min(xs) > box[2] + m or max(ys) < box[3] - m or min(ys) > box[1] + m:
            continue
        c = clip(r, box[0] - m, box[3] - m, box[2] + m, box[1] + m)
        pts, last = [], None
        for x, y in c:
            p = (round((x - box[0]) / (box[2] - box[0]) * W, 1), round((box[1] - y) / (box[1] - box[3]) * H, 1))
            if p != last:
                pts.append(p); last = p
        if len(pts) > 2:
            d.append('M' + 'L'.join(f'{x:g},{y:g}' for x, y in pts) + 'Z')
    return box, ''.join(d)


def city(place):
    return place.split(',')[0].strip()


CSS = r'''<style>
/* Where is Bapa now (Darpan, 29 Oct 2026): a small card in the Today header, its map and its words; no buttons */
.bapa-now{display:flex;align-items:center;gap:14px;max-width:440px;margin:clamp(16px,2.2vw,24px) auto 0;padding:10px 16px 10px 10px;text-align:left;
  background:rgba(0,0,0,.22);border:1px solid rgba(217,164,65,.38);border-radius:14px;box-shadow:0 8px 20px rgba(0,0,0,.25)}
.bapa-now svg{flex:none;width:96px;height:96px;border-radius:10px;background:radial-gradient(circle at 50% 45%,#3a0f19,#1c070c);border:1px solid rgba(217,164,65,.25)}
.bapa-now .land{fill:rgba(217,164,65,.34);stroke:rgba(255,226,150,.7);stroke-width:.7;stroke-linejoin:round}
.bapa-now .route{fill:none;stroke:#d9a441;stroke-width:1.2;stroke-dasharray:2 3;stroke-linecap:round;opacity:.85}
.bapa-now .next{fill:#1c070c;stroke:#d9a441;stroke-width:1.4}
.bapa-now .here{fill:#ffe296;stroke:#7a3a10;stroke-width:1}
.bapa-now .glow{fill:none;stroke:#ffe296;stroke-width:1.5;transform-box:fill-box;transform-origin:center;animation:bn-ring 3.2s ease-out infinite}
@keyframes bn-ring{from{transform:scale(.6);opacity:.9}to{transform:scale(2.6);opacity:0}}
@media (prefers-reduced-motion:reduce){.bapa-now .glow{animation:none;opacity:.5}}
.bapa-now .bn-words{min-width:0}
.bapa-now .bn-lbl{font:700 10px/1.2 var(--sans);letter-spacing:.2em;text-transform:uppercase;color:var(--gold-soft)}
.bapa-now .bn-town{margin-top:3px;font:700 26px/1.05 var(--serif);color:var(--gold-hi)}
.bapa-now .bn-town small{font:700 10.5px/1 var(--sans);letter-spacing:.16em;text-transform:uppercase;color:var(--gold-soft);margin-left:8px;vertical-align:4px}
.bapa-now .bn-dates{margin-top:3px;font:500 15px/1.3 var(--serif);color:var(--cream)}
.bapa-now .bn-today,.bapa-now .bn-next{margin-top:3px;font:500 14px/1.3 var(--serif);color:var(--mist);text-wrap:balance}
.bapa-now .bn-today b,.bapa-now .bn-next b{font-weight:700;color:var(--cream)}
/* computers: in the empty space to the right of the date, level with the day buttons, so nothing below it moves */
@media (min-width:1180px){
  header{position:relative}
  .bapa-now{position:absolute;right:0;top:-48px;margin:0;width:clamp(330px,28vw,420px);max-width:none;padding:12px 18px 12px 12px;gap:16px}
  .bapa-now svg{width:clamp(110px,9vw,136px);height:clamp(110px,9vw,136px)}
  .bapa-now .bn-town{font-size:clamp(26px,2.2vw,32px)}
  .bapa-now .bn-next{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
}
/* and the email and Screensaver buttons move into the empty space on the left, the same height as the card, so the
   header is one row shorter and the ropes start higher (Darpan, 29 Oct 2026: "ropes as high up on the page as possible") */
@media (min-width:1180px){
  header .ss-launch,header .remind{position:absolute;left:0;margin:0;width:clamp(300px,25vw,400px);display:flex;flex-direction:column;align-items:center}
  header .ss-launch{top:-44px}
  header .remind{top:30px;z-index:5}
  header .remind form{margin-top:10px;padding:14px;background:#2a0a12;border:1px solid rgba(217,164,65,.38);border-radius:14px;box-shadow:0 10px 24px rgba(0,0,0,.45)}
  .board{margin-top:6px}
}
@media (min-width:1180px) and (max-width:1359px){
  .bapa-now{width:300px;padding:10px 14px 10px 10px;gap:12px}
  .bapa-now svg{width:100px;height:100px}
  .bapa-now .bn-town{font-size:25px}
  .bapa-now .bn-dates{font-size:14px}
  .bapa-now .bn-today,.bapa-now .bn-next{font-size:13px}
}
/* phones: one short strip, so the ropes stay close: the map, the town and its dates on one line, and today's event */
@media (max-width:600px){.bapa-now{margin-top:14px;padding:8px 12px 8px 8px;gap:10px}.bapa-now svg{width:64px;height:64px;border-radius:8px}
  .bapa-now .bn-lbl{font-size:9px}.bapa-now .bn-town{font-size:20px}.bapa-now .bn-town small{display:none}
  .bapa-now .bn-dates{display:inline;font-size:13.5px}.bapa-now .bn-town{display:inline;margin-right:8px}
  .bapa-now .bn-today{font-size:13px;margin-top:2px}.bapa-now .bn-next{display:none}}
</style>
'''

HTML = '''<div class="bapa-now" id="bapaNow" hidden aria-live="polite">
  <svg viewBox="0 0 150 150" role="img" aria-label="Map"><path class="land"/><path class="route"/><circle class="next" r="4"/><circle class="glow" r="6"/><circle class="here" r="5.5"/></svg>
  <div class="bn-words"><div class="bn-lbl">Where Bapa is now</div><div class="bn-town"></div><div class="bn-dates"></div><div class="bn-today"></div><div class="bn-next"></div></div>
</div>
'''

JS = r'''<script>
// Where is Bapa now: the stay for today on this phone or computer, picked from the schedule baked in at the last build
(() => {
  const S = JSON.parse(document.getElementById('bapaNowData').textContent);
  const el = document.getElementById('bapaNow'), q = s => el.querySelector(s);
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const dayIn = tz => new Intl.DateTimeFormat('en-CA', {timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
  const minsIn = tz => { const [h, m] = new Intl.DateTimeFormat('en-GB', {timeZone: tz, hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).format(new Date()).split(':'); return +h * 60 + +m; };
  const nice = d => `${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1]}`, short = d => `${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1].slice(0, 3)}`;
  const clock = t => { const [h, m] = t.split(':').map(Number); return `${(h + 11) % 12 + 1}.${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`; };
  const at = (map, ll) => [(ll[0] - map.box[0]) / (map.box[2] - map.box[0]) * 150, (map.box[1] - ll[1]) / (map.box[1] - map.box[3]) * 150];
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  function draw() {
    const stays = S.stays;
    const i = stays.findIndex(s => { const d = dayIn(s.tz); return s.from <= d && d <= s.to; });
    if (i < 0) { el.hidden = true; return; }
    let s = stays[i], n = stays[i + 1];
    const today = dayIn(s.tz);
    // a day two stays share is the travel day: the new town counts once that day has its first event there
    if (n && n.from === today && today === s.to) {
      const ev = S.days[today] || [], now = minsIn(n.tz);
      if (ev.some(e => /aagman|swagat/i.test(e.what) && e.from.split(':')[0] * 60 + +e.from.split(':')[1] <= now)) { s = n; n = stays[i + 2]; }
    }
    const map = S.maps[s.city];
    q('.bn-town').innerHTML = `${esc(s.city)}<small>${esc(s.country)}</small>`;
    q('.bn-dates').textContent = `${nice(s.from)} to ${nice(s.to)}`;
    // today's events there, in the town's own time: the one on now, else the next one, else tomorrow's first
    const mins = minsIn(s.tz), when = s.tz === 'Asia/Kolkata' ? 'IST' : s.tz === 'Europe/London' ? 'UK time' : 'local time';
    const ev = (S.days[today] || []).filter(e => e.what);
    const m = e => +e.from.slice(0, 2) * 60 + +e.from.slice(3), end = e => +e.to.slice(0, 2) * 60 + +e.to.slice(3);
    const on = ev.find(e => m(e) <= mins && mins < end(e)), next = ev.find(e => m(e) > mins);
    const line = (head, e) => `<b>${head}:</b> <span>${esc(e.what)}</span>, <span>${clock(e.from).slice(-2) === clock(e.to).slice(-2) ? clock(e.from).slice(0, -3) : clock(e.from)} to ${clock(e.to)} ${when}</span>`;
    q('.bn-today').innerHTML = on ? line('Now', on) : next ? line(m(next) >= 720 ? 'This evening' : 'Today', next) : '';
    q('.bn-today').hidden = !(on || next);
    q('.bn-next').innerHTML = n ? `<b>Next:</b> <span>${esc(n.city)}</span>, <span>${n.from.slice(0, 7) === n.to.slice(0, 7) ? +n.from.slice(8) : short(n.from)} to ${short(n.to)}</span>` : '';
    q('.bn-next').hidden = !n;
    // the map: the town in the middle, a dotted line towards the next town when it is on the map
    const svg = q('svg');
    if (!map) { svg.style.display = 'none'; el.hidden = false; return; }
    svg.style.display = '';
    q('.land').setAttribute('d', map.d);
    const [x, y] = at(map, map.ll);
    ['.here', '.glow'].forEach(c => { q(c).setAttribute('cx', x); q(c).setAttribute('cy', y); });
    const nm = n && S.maps[n.city];
    const [nx, ny] = nm ? at(map, nm.ll) : [-99, -99];
    const shows = nm && nx > 8 && nx < 142 && ny > 8 && ny < 142;
    q('.next').style.display = shows ? '' : 'none';
    q('.route').setAttribute('d', shows ? `M${x},${y}L${nx},${ny}` : '');
    if (shows) { q('.next').setAttribute('cx', nx); q('.next').setAttribute('cy', ny); }
    svg.setAttribute('aria-label', `Map with ${s.city} marked` + (shows ? `, and ${n.city} next` : ''));
    el.hidden = false;
  }
  draw();
  setInterval(draw, 60000);   // the event line moves on through the day, and the stay at midnight
})();
</script>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='the finished site folder')
    a = ap.parse_args()
    sched_p = os.path.join(a.out, 'screensaver', 'data', 'schedule.json')
    if not os.path.exists(sched_p):
        sched_p = os.path.join(HERE, 'site', 'screensaver', 'data', 'schedule.json')
    sched = json.load(open(sched_p, encoding='utf-8'))
    trav_p = os.path.join(a.out, 'travels', 'index.html')
    if not os.path.exists(trav_p):
        trav_p = os.path.join(HERE, 'live', 'travels', 'index.html')
    trav = open(trav_p, encoding='utf-8').read()
    places = json.loads(re.search(r'id="trips"[^>]*>(.*?)</script>', trav, re.S).group(1))['places']
    rings = land_rings(json.loads(re.search(r'id="land"[^>]*>(.*?)</script>', trav, re.S).group(1)))

    since = str(datetime.datetime.now(ZoneInfo('Europe/London')).date() - datetime.timedelta(days=1))
    stays, maps = [], {}
    for s in sched.get('stays', []):
        if s['to'] < since:
            continue
        c = city(s['place'])
        stays.append({'city': c, 'country': s['place'].split(',')[-1].strip(), 'tz': s['tz'], 'from': s['from'], 'to': s['to']})
        p = places.get(c)
        if p and c not in maps:
            box, d = town_map(p['ll'], rings)
            maps[c] = {'ll': p['ll'], 'box': box, 'd': d}
    days = {k: v for k, v in sched.get('days', {}).items() if k >= since}
    data = {'stays': stays, 'days': days, 'maps': maps}
    missing = [s['city'] for s in stays if s['city'] not in maps]
    print(f"where is Bapa now: {len(stays)} stays from {since}, {len(maps)} maps" + (f", no map for {missing}" if missing else ''))

    p = os.path.join(a.out, 'index.html')
    s = open(p, encoding='utf-8').read()
    if 'id="bapaNow"' in s:
        return
    assert s.count('</header>') == 1, 'the Today page has no header'
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    s = s.replace('</header>', CSS + HTML + '</header>', 1)
    s = s.replace('</body>', f'<script type="application/json" id="bapaNowData">{blob}</script>\n{JS}</body>', 1) if '</body>' in s \
        else s + f'<script type="application/json" id="bapaNowData">{blob}</script>\n{JS}'
    open(p, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    main()
