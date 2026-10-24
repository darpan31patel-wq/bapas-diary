# Builds the private mockup of the sideways scrolling calendar (website only, never the daily picture).
# Uses photos saved by the poster thread (preview/poster/<month>/) and calendar/baps-calendar.json.
# Usage: python3 tools/calendar_mockup.py <folder with ph/<month>/>  -> <folder>/data.js, pasted into site/calendar-mockup.html at __DATA__
import json, base64, io, os, sys
from PIL import Image
S=sys.argv[1]; cal={d['date']:d for d in json.load(open('/home/claude/bapas-diary/calendar/baps-calendar.json'))['days']}
out={}
def enc(p, w):
    im=Image.open(p).convert('RGB'); im.thumbnail((w,w*2)); b=io.BytesIO(); im.save(b,'JPEG',quality=66,optimize=True)
    return 'data:image/jpeg;base64,'+base64.b64encode(b.getvalue()).decode()
for m in ('2010-01','2012-01'):
    pj=json.load(open(f'{S}/ph/{m}/photos.json')); days=[]
    y,mo=map(int,m.split('-'))
    import calendar as C
    for d in range(1,C.monthrange(y,mo)[1]+1):
        date=f'{m}-{d:02d}'; c=cal.get(date,{}); e={'d':d,'date':date,'wd':c.get('weekday',''),'ind':c.get('indian_date',''),'fest':[f['name'] for f in c.get('festivals',[])],'about':[f.get('about','') for f in c.get('festivals',[])],'sam':c.get('vikram_samvat',''),'notes':c.get('notes',[]),'ph':[]}
        for k in ('close','act'):
            r=pj.get(k,{}).get(str(d))
            if not r: continue
            p=f"{S}/ph/{m}/{r['file']}"
            if not os.path.exists(p): continue
            fx=r.get('face'); sz=r.get('size')
            pos='50% 30%'
            if fx and sz: pos=f"{round((fx[0]+fx[2]/2)/sz[0]*100)}% {round((fx[1]+fx[3]/2)/sz[1]*100)}%"
            e['place']=r.get('place','')
            ff=[round(fx[0]/sz[0],3),round(fx[1]/sz[1],3),round(fx[2]/sz[0],3),round(fx[3]/sz[1],3)] if fx and sz else None
            e['ph'].append({'f':ff,'ar':round(sz[0]/sz[1],3) if sz else None,'src':enc(p,600),'cap':r.get('caption',''),'pos':pos})
        days.append(e)
    out[m]={'places':pj['places'],'days':days}
s=json.dumps(out); print(len(s)/1e6,'MB')
open(f'{S}/data.js','w').write('const DATA='+s+';')
