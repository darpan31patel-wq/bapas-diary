#!/usr/bin/env python3
"""Travels globe: look up villages on OpenStreetMap (Nominatim), politely, one a second.

    python3 tools/travels_geocode.py site/travels-lookup.txt travels-geo.json

Writes {name: [lon, lat, "what OpenStreetMap found"]} (or null when nothing was found). Website only."""
import json, sys, time, urllib.parse, urllib.request

out = {}
for line in open(sys.argv[1], encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    name, q = line.split('|', 1)
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 1})
    req = urllib.request.Request(url, headers={'User-Agent': 'bapas-diary travels globe (personal site)'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            hit = json.load(r)
    except Exception as e:
        hit = []
        print(name, 'error', e, flush=True)
    out[name] = [round(float(hit[0]['lon']), 4), round(float(hit[0]['lat']), 4), hit[0]['display_name']] if hit else None
    print(name, out[name], flush=True)
    time.sleep(1.2)
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False, indent=1)
