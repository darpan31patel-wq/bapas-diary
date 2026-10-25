"""Month pack for the dashboard: python tools/dashboard_month_pack.py <poster branch checkout> 2024-02 <out>. Reads the poster branch's preview/poster/<month>/ photos (tools/poster.py pick_month for options A and B)."""
import calendar, datetime, json, os, re, sys
V = sys.argv[1]; month = sys.argv[2]; out = os.path.join(sys.argv[3], month)
sys.path[:0] = [V, os.path.join(V, 'tools')]
os.chdir(V)
import poster
from PIL import Image
y, m = map(int, month.split('-'))
pdir = os.path.join(V, 'preview', 'poster', month)
photos = json.load(open(os.path.join(pdir, 'photos.json'))); photos['dir'] = pdir
cal = json.load(open(os.path.join(V, 'calendar', 'baps-calendar.json')))
cal = cal.get('days', cal)
if isinstance(cal, list): cal = {c['date']: c for c in cal}
pa, pb = poster.pick_month(photos, .86, 'close'), poster.pick_month(photos, 1.0, 'act')
notes = poster.tg_notes(y, m)
os.makedirs(out, exist_ok=True)
nd = calendar.monthrange(y, m)[1]
first = cal[f'{y}-{m:02d}-01']
days, prev = [], None
for dn in range(1, nd + 1):
    info = cal[f'{y}-{m:02d}-{dn:02d}']
    tithi = info['indian_date'] if info['month'] != prev else info['indian_date'].split(' ', 1)[-1]
    prev = info['month']
    fest = [re.sub(r'\s*\(.*?\)', '', f['name']) for f in info['festivals']] + [n for n in info['notes'] if not poster.NOT_FESTIVAL.search(n)]
    fest = [f.rsplit(',', 1)[1].strip() if len(f) > 26 and ',' in f else f for f in fest]
    cands = []
    for x in photos['cands'].get(str(dn), []):
        im = Image.open(os.path.join(pdir, x['file'])).convert('RGB')
        s = min(1, 800 / max(im.size)); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        name = f'{dn:02d}-{len(cands)}.jpg'; im.save(os.path.join(out, name), quality=80)
        k = im.width / x['size'][0]
        cands.append(dict(img=name, w=im.width, h=im.height, face=[round(v * k, 1) for v in x['face']] if x.get('face') else None,
                          caption=poster.clean_caption(x.get('caption') or ''), place=re.sub(r',\s*(India|UAE)$', '', x.get('place') or ''),
                          special=bool(x.get('special')), unsure=bool(x.get('unsure')), url=x['url']))
    idx = lambda p: next((i for i, c in enumerate(cands) if p and c['url'] == p['url']), 0)
    days.append(dict(day=dn, sunday=datetime.date(y, m, dn).weekday() == 6, tithi=tithi, fest=fest[:2], story=notes.get(dn, ''),
                     cands=cands, pickA=idx(pa.get(dn)), pickB=idx(pb.get(dn)),
                     modeA=(pa.get(dn) or {}).get('mode', 'close'), modeB=(pb.get(dn) or {}).get('mode', 'frame')))
sub = f"{first['lunar_months'].replace('-', ' · ')}  ·  Vikram Samvat {first['vikram_samvat']}".upper()
json.dump(dict(month=month, title=f'{calendar.month_name[m]} {y}', subtitle='in Bapa’s Diary', subline=sub, days=days),
          open(os.path.join(out, 'pack.json'), 'w'), indent=1, ensure_ascii=False)
print(month, nd, 'days', sum(len(d['cands']) for d in days), 'photos')
