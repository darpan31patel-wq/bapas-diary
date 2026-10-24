"""Helps Google find bapas-diary.com, and puts the friendly page not found page in place (Darpan, 24 Oct 2026).

Website only: nothing here touches the daily 2pm picture. Runs in the deploy on the built site:

    python3 tools/web_seo.py --out out

  out/404.html      site/404.html: shown for any address that doesn't exist (Cloudflare Pages uses it by itself)
  out/robots.txt    every page may be read by search engines, with the address of the site map
  out/sitemap.xml   the top pages of the site
"""
import argparse, datetime, os, shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://bapas-diary.com'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    shutil.copy(os.path.join(HERE, 'site', '404.html'), os.path.join(a.out, '404.html'))
    pages = sorted(os.path.relpath(r, a.out).replace(os.sep, '/') for r, _, f in os.walk(a.out)
                   if 'index.html' in f and os.path.relpath(r, a.out).count(os.sep) == 0)
    today = datetime.date.today().isoformat()
    urls = ''.join(f'  <url><loc>{SITE}/{"" if p == "." else p + "/"}</loc><lastmod>{today}</lastmod></url>\n' for p in pages)
    with open(os.path.join(a.out, 'sitemap.xml'), 'w') as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    with open(os.path.join(a.out, 'robots.txt'), 'w') as f:
        f.write(f'User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n')
    print('sitemap:', ', '.join('/' if p == '.' else '/' + p + '/' for p in pages))


if __name__ == '__main__':
    main()
