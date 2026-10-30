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
if(navigator.serviceWorker)try{navigator.serviceWorker.register=()=>Promise.reject()}catch(e){}})();</script>''' % json.dumps(files)

# the videos for these days, by year
vids = json.load(open('data/youtube/days.json'))
V = {}
for date, lst in vids.items():
    if date[5:] in DAYS:
        V.setdefault(date[5:], {})[date[:4]] = [[v['id'], v['title']] for v in lst]
video = '''<style>
.slot .vid{display:inline-flex;align-items:center;gap:8px;margin-top:2px;padding:6px 13px 6px 7px;border:1px solid rgba(217,164,65,.6);border-radius:999px;
  background:rgba(0,0,0,.22);color:#ffe296;font:600 12.5px/1 Poppins,Arimo,sans-serif;letter-spacing:.04em;text-decoration:none;white-space:nowrap;transition:background .2s,border-color .2s}
.slot .vid:hover,.slot .vid:focus-visible{background:rgba(217,164,65,.22);border-color:#ffe296}
.slot .vid i{display:grid;place-items:center;width:20px;height:20px;border-radius:50%%;background:#d9a441}
.slot .vid i::before{content:"";margin-left:2px;border-left:7px solid #2a0d12;border-top:4.5px solid transparent;border-bottom:4.5px solid transparent}
.slot{text-align:center}
</style><script>
/* A gold "Watch the video" under each year's card when BAPS posted a video of that day on YouTube
   (data/youtube/days.json, matched by the date in each video's title). Opens the video on YouTube. */
const VIDEOS=%s;
function vid(slot,y){const d=(VIDEOS[DAY.date]||{})[y];if(!d)return;
  const a=document.createElement('a');a.className='vid';a.target='_blank';a.rel='noopener';
  a.href='https://www.youtube.com/watch?v='+d[0][0];a.title=d[0][1];
  a.innerHTML='<i aria-hidden="true"></i>Watch the video';
  slot.append(a);}
</script>''' % json.dumps(V)
html = html.replace('slot.append(el, cap); $(\'cards\').append(slot);', "slot.append(el, cap); vid(slot, y); $('cards').append(slot);", 1)
assert 'vid(slot, y)' in html
html = html.replace('<head>', '<head>' + shim, 1)
html = html.replace('</head>', video + '</head>', 1)
Path(out_path).write_text(html)
print(out_path, len(html) // 1024, 'KB;', {d: sorted(V.get(d, {})) for d in DAYS})
