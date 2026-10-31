# Do the BAPS videos have chapters or timestamps in their descriptions? (Video moments, Darpan 31 Oct 2026: "yes moments")
for id in "$@"; do
  curl -s -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36' -H 'Accept-Language: en-GB' -b 'SOCS=CAI; CONSENT=YES+1' "https://www.youtube.com/watch?v=$id" > p.html
  python3 - "$id" <<'P'
import re, sys, json
h = open('p.html', encoding='utf-8', errors='ignore').read()
m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', h)
d = json.loads('"' + m.group(1) + '"') if m else ''
t = re.search(r'<meta name="title" content="([^"]*)"', h)
stamps = re.findall(r'(?m)^\s*\(?(?:\d{1,2}:)?\d{1,2}:\d{2}', d)
print(f"== {sys.argv[1]} title={t.group(1) if t else '?'} | descr={len(d)} chars | chapterRenderer={h.count('chapterRenderer')} | timestamps={len(stamps)} | videoDetails={h.count('videoDetails')} | consent={h.count('consent.youtube')}")
print('   ' + d[:300].replace('\n', ' / '))
P
done
