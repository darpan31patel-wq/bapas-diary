"""Reads every post of a public Telegram channel from its no-login web page t.me/s/<channel> into posts.json
(id, posted, photos, videos, files, forwarded_from, text, links, images), the same shape as telegram/posts.json.

    python tools/tg_fetch.py SatpurushInUKEurope telegram/satpurush/posts.json
"""
import json, os, re, sys, time, urllib.request
from html.parser import HTMLParser


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.posts, self.p, self.depth, self.text_at, self.a = [], None, 0, None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs); cls = (a.get('class') or '').split()
        if 'tgme_widget_message' in cls and a.get('data-post'):
            self.p = dict(id=int(a['data-post'].split('/')[1]), posted=None, photos=0, videos=0, files=0,
                          forwarded_from=None, text='', links=[], images=[])
            self.posts.append(self.p)
        if not self.p:
            return
        if tag == 'div' and 'tgme_widget_message_text' in cls and self.text_at is None:
            self.text_at = 0
        elif self.text_at is not None and tag not in ('br', 'img'):
            self.text_at += 1
        if tag == 'br' and self.text_at is not None:
            self.p['text'] += '\n'
        if tag == 'a' and self.text_at is not None and a.get('href'):
            self.p['links'].append(a['href'])
        if tag == 'time' and a.get('datetime') and not self.p['posted']:
            self.p['posted'] = a['datetime']
        if 'tgme_widget_message_photo_wrap' in cls:
            self.p['photos'] += 1
            m = re.search(r"url\('?\"?(.*?)'?\"?\)", a.get('style') or '')
            if m:
                self.p['images'].append(m[1])
        if 'tgme_widget_message_video_thumb' in cls:
            m = re.search(r"url\('?\"?(.*?)'?\"?\)", a.get('style') or '')
            if m:
                self.p.setdefault('stills', []).append(m[1])
        if {'tgme_widget_message_video_player', 'tgme_widget_message_roundvideo_player'} & set(cls):
            self.p['videos'] += 1
        if 'tgme_widget_message_document' in cls:
            self.p['files'] += 1
        if 'tgme_widget_message_forwarded_from_name' in cls:
            self.a = 'fwd'

    def handle_endtag(self, tag):
        if self.text_at is not None and tag not in ('br', 'img'):
            self.text_at -= 1
            if self.text_at < 0:
                self.text_at = None

    def handle_data(self, data):
        if self.p is None:
            return
        if self.a == 'fwd':
            self.p['forwarded_from'] = (self.p['forwarded_from'] or '') + data
            if data.strip():
                self.a = None
        if self.text_at is not None:
            self.p['text'] += data


def get(url):
    for n in range(5):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            return urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
        except Exception as e:
            print('retry', url, e); time.sleep(5 * (n + 1))
    raise SystemExit('cannot read ' + url)


def main(channel, out):
    posts, before = {}, None
    while True:
        pg = Page(); pg.feed(get(f'https://t.me/s/{channel}' + (f'?before={before}' if before else '')))
        if not pg.posts:
            break
        for p in pg.posts:
            posts[p['id']] = p
        low = min(p['id'] for p in pg.posts)
        if before and low >= before or low <= 1:
            break
        before = low
        print(len(posts), 'posts, down to', low, flush=True)
        time.sleep(0.5)
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    json.dump(sorted(posts.values(), key=lambda p: p['id']), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('saved', len(posts), 'posts to', out)


if __name__ == '__main__':
    main(*sys.argv[1:3])
