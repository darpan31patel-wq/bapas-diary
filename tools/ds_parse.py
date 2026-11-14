import json, re, sys
GD = str.maketrans('૦૧૨૩૪૫૬૭૮૯', '0123456789')
GM = {'જાન્યુઆરી':1,'ફેબ્રુઆરી':2,'માર્ચ':3,'એપ્રિલ':4,'મે':5,'જૂન':6,'જુલાઈ':7,'જુલાઇ':7,'ઓગષ્ટ':8,'ઑગષ્ટ':8,'સપ્ટે.':9,'ડિસે.':12,'ઑક્ટો.':10,'નવે.':11,'જાન્યુ.':1,'ફેબ્રુ.':2,'ફેબ્રુઆરિ':2,'ઑગસ્ટ':8,'ઓગસ્ટ':8,'સપ્ટેમ્બર':9,'ઑક્ટોબર':10,'ઓક્ટોબર':10,'નવેમ્બર':11,'ડિસેમ્બર':12}
def pdate(s):
    t = s.translate(GD)
    m = re.search(r"(\d{1,2})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*('?\s*\d{2,4})", t)
    if m:
        d, mo, y = int(m[1]), int(m[2]), m[3].replace("'", '').strip()
        y = int(y) + ((2000 if int(y) < 30 else 1900) if len(y) == 2 else 0)
        return y, mo, d, t[m.end():]
    m = re.search(r"(\d{1,2})\s+([^\d,]+?),?\s*('?\d{2,4})", t)
    if m:
        mo = GM.get(m[2].replace(' ', '').replace('\u200b', ''))
        if mo:
            y = m[3].replace("'", ''); y = int(y) + ((2000 if int(y) < 30 else 1900) if len(y) == 2 else 0)
            return y, mo, int(m[1]), t[m.end():]
    return None
KNOWN = ['સારંગપુર','ગાંધીનગર','મુંબઈ','વડોદરા','અમદાવાદ','બોચાસણ','નડિયાદ','રાજકોટ','ભાવનગર','વિદ્યાનગર']
def parse(day):
    x = day['text']
    a = x.find('પ્રેરણા પરિમલ')
    if a < 0: return None
    b = len(x)
    for stop in ['Vachanamrut Gems', 'Swamini Vato', 'Audio Satsang', 'In History', 'in history']:
        j = x.find(stop, a)
        if j > 0: b = min(b, j)
    lines = [l.strip() for l in x[a+len('પ્રેરણા પરિમલ'):b].split('\n') if l.strip()]
    who, title, d, place, paras = '', '', None, '', []
    for l in lines:
        if d is None:
            if 'પ્રમુખસ્વામી મહારાજની' in l and 'સ્મૃતિ' in l: who = 'psm'; continue
            if 'મહંત સ્વામી મહારાજની' in l and 'સ્મૃતિ' in l: who = 'msm'; continue
            if re.match(r"^[(\[]?\s*તા\s*\.?", l) or re.match(r"^[(\[]\s*[૦-૯\d]{1,2}\s*-\s*[૦-૯\d]{1,2}\s*-\s*[૦-૯\d]{2,4}\s*[)\]]", l):
                l = re.sub(r"^[(\[]\s*", '', l)
                r = pdate(l)
                if r:
                    y, mo, dd, rest = r
                    try:
                        import datetime; datetime.date(y, mo, dd); d = f'{y:04d}-{mo:02d}-{dd:02d}'
                    except Exception: d = ''
                    place = re.sub(r'^[\s,]+|[\s).\]]+$', '', rest).strip()
                    if len(place) > 30:
                        for P in KNOWN:
                            if place.startswith(P): paras.append(place[len(P):].strip()); place = P; break
                        else: paras.append(place); place = ''
                    continue
            if not title and len(l) < 80: title = l.rstrip('. …').strip(); continue
        paras.append(l)
    if not who:
        who = 'msm' if day['date'] >= '2016-08-13' and 'મહંત' in x[a:a+200] else 'psm'
    return {'d': d or '', 'place': place, 'who': who, 'title': title, 'gu': paras}
if __name__ == '__main__':
    D = json.load(open(sys.argv[1]))
    out = {}
    for day in D:
        p = parse(day)
        if p and p['gu']: out[day['date']] = p
    json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=0)
    nd = sum(1 for v in out.values() if v['d']); print(len(D), 'days,', len(out), 'prasangs,', nd, 'with a date')
    for k, v in list(out.items())[:8]: print(k, v['d'], v['place'], v['who'], v['title'][:30], len(' '.join(v['gu'])))
    print('no date:', [ (k, ) for k, v in out.items() if not v['d']][:10])
