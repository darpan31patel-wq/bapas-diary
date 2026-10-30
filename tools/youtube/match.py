"""Pair each playlist video with the diary day(s) in its title."""
import re,json,glob,collections,datetime as dt
M={m:i+1 for i,m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
def dates(t):
    out=[]
    # "4 Oct 2026" / "23-24 Oct 2026"
    for m in re.finditer(r"(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})",t):
        mo=M.get(m.group(3)[:3].lower())
        if mo: out.append((int(m.group(4)),mo,int(m.group(1)),int(m.group(2) or m.group(1))))
    # "October 13-14, 2023"
    for m in re.finditer(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?,?\s+(\d{4})",t):
        mo=M.get(m.group(1)[:3].lower())
        if mo: out.append((int(m.group(4)),mo,int(m.group(2)),int(m.group(3) or m.group(2))))
    days=set()
    for y,mo,a,b in out:
        for d in range(a,b+1 if b>=a else a+1):
            try: days.add(dt.date(y,mo,d))
            except ValueError: pass
    return days
vids={}
undated=[]
for l in open("data/youtube/flat.tsv"):
    vid,t,dur=l.rstrip("\n").split("\t")
    if t=="NA": continue
    ds=dates(t)
    if ds:
        for d in ds: vids.setdefault(d,[]).append((vid,t,dur))
    else: undated.append(t)
out={d.isoformat():[{"id":v,"title":t,"secs":int(s) if s.isdigit() else None} for v,t,s in x] for d,x in sorted(vids.items())}
json.dump(out,open("data/youtube/days.json","w"),ensure_ascii=False,indent=0)
json.dump(undated,open("data/youtube/undated.json","w"),ensure_ascii=False,indent=1)
print(len(out),"days,",len(undated),"undated")
