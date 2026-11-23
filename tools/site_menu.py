"""Puts the tabs of every page's shared menu (nav.site-menu, see live/menu.css) in the site's one order, so pages
built by different threads always match. Website only; run by .github/workflows/website-deploy.yml on the built site.

    python3 tools/site_menu.py out
"""
import hashlib, os, re, sys

# Darpan, 24 Oct 2026: Calendar is the second tab. 26 Oct 2026: Then and now is its own tab ("make it its own thing",
# "yes then and now tab"), after Through the years; added here to every page's menu, so no page can miss it.
# 29 Oct 2026: the Darshan tab, the Neasden mandir's murti darshan day by day ("yes"), before About.
ORDER = ['/', '/calendar/', '/search/', '/travels/', '/through-the-years/', '/then-and-now/', '/darshan/', '/about/']
ADD = {'/then-and-now/': 'Legacy',   # Darpan, 28 Oct 2026: "change 'then and now' to 'legacy'"
       '/darshan/': 'Darshan'}
NAV = re.compile(r'(<nav class="site-menu[^"]*"[^>]*>)(.*?)(</nav>)', re.S)
TAB = re.compile(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>.*?</a>', re.S)
# Darpan, 26 Oct 2026: the tabs always stay at the top of the screen; scrolled down they go very faint but can still be
# clicked (live/menu.css, nav.site-menu.faint). Listens to every scroll, the page's own or a box inside it.
FAINT = ('<script id="menu-faint">(function(){var n=document.querySelector("nav.site-menu");if(!n)return;'
         'addEventListener("scroll",function(e){var t=e.target.nodeType===9?document.scrollingElement:e.target;'
         'if(t&&t.scrollHeight>innerHeight*.6)n.classList.toggle("faint",t.scrollTop>40)},{passive:true,capture:true})})()</script>')

# Darpan, 23 Nov 2026 ("throoughly test this, then we can go live yes", mockup 17 Nov): one gold ring glides between the
# tabs and stretches to fit each name (live/menu.css .tab-glide): to the tab under the mouse, back to the page's own tab
# when the mouse leaves, to a tab as it is tapped or reached with the keyboard. Phones: the highlight slides along the bar.
GLIDE = ('<script id="menu-glide">(function(){var n=document.querySelector("nav.site-menu");if(!n||!window.ResizeObserver)return;'
         'var g=document.createElement("span"),on=n.querySelector("a.on"),at=on,ph=matchMedia("(max-width: 760px)");'
         'g.className="tab-glide";g.setAttribute("aria-hidden","true");n.insertBefore(g,n.firstChild);'
         'function put(a,now){if(!a||!a.offsetWidth)a=on;if(!a||!a.offsetWidth){g.style.opacity=0;at=null;return}'
         'var N=n.getBoundingClientRect(),r=a.getBoundingClientRect(),x=r.left-N.left+n.scrollLeft,y=r.top-N.top,w=r.width,h=r.height;'
         'if(!ph.matches&&a!==on){var o=on&&on.offsetWidth?on.getBoundingClientRect().height:h+11;x-=13;w+=26;y+=(h-o)/2;h=o}'
         'if(now)g.classList.add("now");g.style.opacity="";g.style.width=w+"px";g.style.height=h+"px";g.style.transform="translate("+x+"px,"+y+"px)";'
         'if(now){g.offsetWidth;g.classList.remove("now")}at=a;n.classList.toggle("away",a!==on);'
         '[].forEach.call(n.querySelectorAll("a"),function(l){l.classList.toggle("lit",l===a&&a!==on)})}'
         'put(on,1);n.classList.add("glide");'
         'var ro=new ResizeObserver(function(){put(at,1)});ro.observe(n);[].forEach.call(n.querySelectorAll("a"),function(l){ro.observe(l)});'
         'n.addEventListener("pointerover",function(e){if(e.pointerType==="touch")return;var a=e.target.closest&&e.target.closest("a");if(a&&n.contains(a))put(a)});'
         'n.addEventListener("pointerleave",function(){put(on)});'
         'n.addEventListener("click",function(e){var a=e.target.closest&&e.target.closest("a");if(a)put(a)});'
         'n.addEventListener("focusin",function(e){if(e.target.tagName==="A")put(e.target)});'
         'n.addEventListener("focusout",function(){put(on)});'
         'addEventListener("pageshow",function(){put(on,1)})})()</script>')


def reorder(m):
    tabs = {href: a.group(0) for a in TAB.finditer(m.group(2)) for href in [a.group(1)]}
    for href, name in ADD.items():   # every page's tab says the same, whatever the page was built with
        if href in tabs:
            tabs[href] = re.sub(r'>.*?</a>$', f'>{name}</a>', tabs[href], flags=re.S)
    for href, name in ADD.items():
        tabs.setdefault(href, f'<a href="{href}">{name}</a>')
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
                if 'id="menu-glide"' not in t:
                    t = NAV.sub(lambda m: m.group(0) + GLIDE, t, count=1)
                if v:
                    t = re.sub(r'href="/menu\.css(\?v=[0-9a-f]+)?"', f'href="/menu.css?v={v}"', t)
                if t != s:
                    open(p, 'w', encoding='utf-8').write(t)
                    print('menu order:', os.path.relpath(p, root))


if __name__ == '__main__':
    main(sys.argv[1])
