"""Puts the tabs of every page's shared menu (nav.site-menu, see live/menu.css) in the site's one order, so pages
built by different threads always match. Website only; run by .github/workflows/website-deploy.yml on the built site.

    python3 tools/site_menu.py out
"""
import hashlib, os, re, sys

# Darpan, 24 Oct 2026: Calendar is the second tab.
ORDER = ['/', '/calendar/', '/search/', '/travels/', '/through-the-years/', '/about/']
NAV = re.compile(r'(<nav class="site-menu[^"]*"[^>]*>)(.*?)(</nav>)', re.S)
TAB = re.compile(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>.*?</a>', re.S)
# Darpan, 26 Oct 2026: the tabs always stay at the top of the screen; scrolled down they go very faint but can still be
# clicked (live/menu.css, nav.site-menu.faint). Listens to every scroll, the page's own or a box inside it.
FAINT = ('<script id="menu-faint">(function(){var n=document.querySelector("nav.site-menu");if(!n)return;'
         'addEventListener("scroll",function(e){var t=e.target.nodeType===9?document.scrollingElement:e.target;'
         'if(t&&t.scrollHeight>innerHeight*.6)n.classList.toggle("faint",t.scrollTop>40)},{passive:true,capture:true})})()</script>')


def reorder(m):
    tabs = {href: a.group(0) for a in TAB.finditer(m.group(2)) for href in [a.group(1)]}
    rest = [tabs[h] for h in tabs if h not in ORDER]
    return m.group(1) + ''.join([tabs[h] for h in ORDER if h in tabs] + rest) + m.group(3)


def main(root):
    # /menu.css?v=its own fingerprint, so a browser never keeps showing an old menu after a change (Darpan, 26 Oct 2026:
    # still saw the dark edge after it was removed)
    css = os.path.join(root, 'menu.css')
    v = hashlib.sha1(open(css, 'rb').read()).hexdigest()[:10] if os.path.isfile(css) else ''
    for d, _, files in os.walk(root):
        for f in files:
            if f.endswith('.html'):
                p = os.path.join(d, f)
                s = open(p, encoding='utf-8').read()
                t = NAV.sub(reorder, s)
                if 'id="menu-faint"' not in t:
                    t = NAV.sub(lambda m: m.group(0) + FAINT, t, count=1)
                if v:
                    t = re.sub(r'href="/menu\.css(\?v=[0-9a-f]+)?"', f'href="/menu.css?v={v}"', t)
                if t != s:
                    open(p, 'w', encoding='utf-8').write(t)
                    print('menu order:', os.path.relpath(p, root))


if __name__ == '__main__':
    main(sys.argv[1])
