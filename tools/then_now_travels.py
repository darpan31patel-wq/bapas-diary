#!/usr/bin/env python3
"""Put a "Then and now" link on the Travels story card (Darpan typed '1 and 2 happy go live', 25 Oct 2026): when the
card shows a place that has a Then and now pair, a small gold link opens /then-and-now/#slug.

    python3 tools/then_now_travels.py TRAVELS.html '{"Surat": "surat", ...}'

The place list is what tools/build_then_now.py prints. Edits TRAVELS.html in place and can be run again (it replaces
its own earlier link). Works on both the Travels mockup template and travels-live.html. Website only.
"""
import json, re, sys

path, places = sys.argv[1], json.loads(sys.argv[2])
s = open(path).read()
s = re.sub(r'\n/\* then and now \*/.*?/\* end then and now \*/', '', s, flags=re.S)
s = re.sub(r'\n  <a class="tn" id="tn"[^\n]*</a>', '', s)
s = re.sub(r"\n    // then and now\n.*?// end then and now", '', s, flags=re.S)
css = ('\n/* then and now */\n.tn { display: inline-block; margin-top: 10px; padding: 7px 14px; border: 1px solid var(--gold); border-radius: 999px;'
       ' color: var(--gold); font-size: 13px; letter-spacing: .08em; text-transform: uppercase; text-decoration: none; -webkit-user-select: none; user-select: none; }\n'
       '.tn:hover, .tn:focus-visible { background: var(--gold); color: var(--night); outline: none; }\n'
       '@media (max-width: 760px) { .tn { margin-top: 6px; padding: 5px 12px; font-size: 12px; } }\n/* end then and now */')
s = s.replace('</style>', css + '\n</style>', 1)
s = s.replace('  <div class="cap" id="cap"></div>',
              '  <div class="cap" id="cap"></div>\n  <a class="tn" id="tn" href="/then-and-now/" hidden>Then and now &rsaquo;</a>', 1)
js = ("\n    // then and now\n    const TN = " + json.dumps(places) + ", tn = TN[tgt.name];\n"
      "    $('tn').hidden = st.flying || !tn; if (tn) $('tn').href = '/then-and-now/#' + tn;\n    // end then and now")
anchor = "    $('cap').textContent = st.flying"
assert anchor in s and 'id="tn"' in s
s = s.replace(anchor, js.lstrip('\n') + '\n' + anchor, 1)
open(path, 'w').write(s)
print('ok', path)
