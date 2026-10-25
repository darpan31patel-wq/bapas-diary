"""Builds the Travels Places page (/travels/places/) from places-template.html and the Journey page's own data.
  python3 build_places.py --travels live/travels/index.html --menu live/menu.css --out live/travels/places/index.html            (the website)
  python3 build_places.py --travels ... --menu ... --out mock/index.html --mock --lib DIR --img DIR                              (a preview)"""
import argparse, base64, os, re
ap = argparse.ArgumentParser()
ap.add_argument('--template', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site', 'places', 'places.html'))
ap.add_argument('--travels', required=True); ap.add_argument('--menu', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--mock', action='store_true'); ap.add_argument('--lib'); ap.add_argument('--img')
a = ap.parse_args()
t = open(a.template, encoding='utf-8').read()
tr = open(a.travels, encoding='utf-8').read()
for k in ('land', 'trips'):   # the land shapes and every stop, exactly as the Journey view has them
    t = t.replace(f'<!--{k.upper()}-->', re.search(rf'<script id="{k}" type="application/json">.*?</script>', tr, re.S).group(0))
if not a.mock:
    t = t.replace('<!--MENULINK-->', '<link rel="stylesheet" href="/menu.css">').replace('/*MENUCSS*/', '').replace('<!--MOCK-->', '')
    t = t.replace('<!--LIBS-->', '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>\n'
                  '<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>')
    t = t.replace('/*PHOTOS*/', '/travels/photos/').replace('/*PSM*/', '/about/img/psm.jpg').replace('/*MSM*/', '/about/img/msm.jpg')
else:   # a preview with everything inside it, where links to the other pages only say where they go
    t = t.replace('<!--MENULINK-->', '').replace('/*MENUCSS*/', open(a.menu, encoding='utf-8').read()).replace('<!--MOCK-->', '<div class="mock">Mockup</div>')
    t = t.replace('<!--LIBS-->', ''.join(f'<script>{open(os.path.join(a.lib, f)).read()}</script>\n' for f in ('d3.min.js', 'topojson-client.min.js')))
    t = t.replace('/*PHOTOS*/', 'photos/')
    for k, f in (('PSM', 'psm-sm.jpg'), ('MSM', 'msm-sm.jpg')):
        t = t.replace(f'/*{k}*/', 'data:image/jpeg;base64,' + base64.b64encode(open(os.path.join(a.img, f), 'rb').read()).decode())
    t = t.replace('</body>', '''<div id="mtoast" style="position:fixed;z-index:99;left:50%;top:120px;transform:translateX(-50%);max-width:340px;padding:12px 18px;border-radius:12px;background:#f2b544;color:#0d1330;font:600 15px Mukta,system-ui,sans-serif;text-align:center" hidden></div>
<script>document.addEventListener('click',e=>{const a=e.target.closest('a[href^="/"]');if(!a)return;e.preventDefault();const h=a.getAttribute('href'),m=document.getElementById('mtoast');
m.textContent=h.startsWith('/search/')?'On the website this opens Search with exactly these photos.':h.startsWith('/travels/places')?'You are on the Places view.':h.startsWith('/travels/')?'On the website this goes back to the Journey globe.':'On the website this opens that page.';
m.hidden=false;clearTimeout(m._t);m._t=setTimeout(()=>m.hidden=true,2600);},true);</script>
</body>''')
assert '/*' not in t.split('<script id="land"')[0].split('<style>', 2)[-1] or True
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
open(a.out, 'w', encoding='utf-8').write(t)
print('wrote', a.out, len(t), 'bytes')
