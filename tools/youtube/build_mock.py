"""Mockup of the "Watch the video" link: the live Today page (mock/live, copied by youtube-today-copy.yml) made into
one self contained file, with the video link added under each year's card that has a BAPS video for that day."""
import base64, json, re, sys
from pathlib import Path

LIVE = Path('mock/live')
DAYS = ['10-29', '10-30', '10-31', '11-01']
out_path = sys.argv[1]
html = (LIVE / 'index.html').read_text()

def local(p):
    return LIVE / p.split('?')[0].lstrip('/')

def fonts(css):
    def put(m):
        f = local(m.group(1))
        if not f.exists():
            return m.group(0)
        return 'url(data:font/woff2;base64,' + base64.b64encode(f.read_bytes()).decode() + ')'
    return re.sub(r"url\(['\"]?(/[^)'\"]+\.woff2)['\"]?\)", put, css)

html = re.sub(r'<link rel="stylesheet" href="(/[^"]+)"[^>]*>', lambda m: '<style>' + fonts(local(m.group(1)).read_text()) + '</style>', html)
html = re.sub(r'<script src="(/[^"]+)"( defer)?></script>',
              lambda m: '<script>' + (f"addEventListener('DOMContentLoaded',()=>{{{local(m.group(1)).read_text()}\n}});" if m.group(2) else local(m.group(1)).read_text()) + '</script>', html)
html = re.sub(r'<link rel="(manifest|icon|apple-touch-icon)"[^>]*>', '', html)
html = fonts(html)   # the page's own @font-face rules

# what the page fetches, answered from inside the file
files = {f'/data/day/{d}.json': (LIVE / f'data/day/{d}.json').read_text() for d in DAYS}
for p in ['/gu/words.json', '/api/live', '/offline/files.json', '/data/calendar.json']:
    files[p] = local(p).read_text()
shim = '''<script>(()=>{const F=%s;const get=u=>{try{u=new URL(u,location.href).pathname}catch(e){};u=u.replace('/data/day/../','/data/');return F[u]};
const f0=window.fetch.bind(window);window.fetch=(u,o)=>{const t=get(typeof u==='string'?u:u.url);return t!=null?Promise.resolve(new Response(t,{status:200,headers:{'Content-Type':'application/json'}})):Promise.resolve(new Response('',{status:404}))};
const op=XMLHttpRequest.prototype.open,sd=XMLHttpRequest.prototype.send;XMLHttpRequest.prototype.open=function(m,u,...r){this._u=u;return op.call(this,m,'data:application/json,{}',...r)};
XMLHttpRequest.prototype.send=function(){const t=get(this._u);if(t!=null){Object.defineProperty(this,'status',{value:200});Object.defineProperty(this,'responseText',{value:t});return}return sd.call(this)};
if(navigator.serviceWorker)try{navigator.serviceWorker.register=()=>Promise.reject()}catch(e){}})();</script>'''

# the change itself, as in site/day.html: the same CSS and code, taken from there
day = Path('site/day.html').read_text()
css = day[day.index('.slot .vid{'):day.index('\n', day.index('.slot .vid i::before{')) + 1]
css += day[day.index('.yhead .vgo{'):day.index('\n', day.index('.go.vgo:hover i::before')) + 1]
helper = day[day.index('// a BAPS video of that day on YouTube'):day.index('// every photo of the day, year by year')]
for old, new in [
    ("slot.append(el, cap); $('cards').append(slot);", "slot.append(el, cap); $('cards').append(slot);\n  if (Y && Y.v) slot.insertAdjacentHTML('beforeend', watchVideo(Y.v, 'vid'));"),
    ("See more &rsaquo;</a></div>` +", "See more &rsaquo;</a>${Y && Y.v ? watchVideo(Y.v, 'go vgo') : ''}</div>` +"),
    ("trip: note ? Y.trip : null,", "trip: note ? Y.trip : null, v: !note && Y && Y.v,"),
    ("const {p, y, d, where, cal, trip, ti, more} = everyPhoto[vi];", "const {p, y, d, where, cal, trip, ti, more, v} = everyPhoto[vi];"),
    ("See more &rsaquo;</a></figcaption></figure>`;", "See more &rsaquo;</a>${v ? ' ' + watchVideo(v, 'go vgo') : ''}</figcaption></figure>`;"),
    ("// every photo of the day, year by year\n", helper + "// every photo of the day, year by year\n"),
]:
    assert html.count(old) == 1, old
    html = html.replace(old, new)
html = html.replace('</head>', '<style>' + css + '</style></head>', 1)
# the day files with their videos, as tools/web_videos.py writes them
vids = json.load(open('data/youtube/days.json'))
for d in DAYS:
    day_ = json.loads(files[f'/data/day/{d}.json'])
    for Y in day_['years']:
        v = vids.get(Y.get('d') or f"{Y['y']}-{day_['date']}")
        if v: Y['v'] = [[x['id'], x['title']] for x in v]
    files[f'/data/day/{d}.json'] = json.dumps(day_, ensure_ascii=False)
html = html.replace('<head>', '<head>' + shim % json.dumps(files), 1)
Path(out_path).write_text(html)
print(out_path, len(html) // 1024, 'KB')
