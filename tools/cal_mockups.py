"""Mockups only (Darpan, 24 Oct 2026): ten ways the BAPS calendar could show in the daily picture, drawn offline from
the photos saved by the calmock workflow (preview/cal/<date>-photos/).  python tools/cal_mockups.py OUTDIR"""
import datetime, json, os, re, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make
from make import px, garamond, W, GOLD, CAPTION_GOLD

HERE = make.HERE
CAL = {x['date']: x for x in json.load(open(os.path.join(HERE, 'calendar', 'baps-calendar.json'), encoding='utf-8'))['days']}
TIDY = {'Annakut and Bestu Varash': 'Annakut', 'Dhan Teras/Lakshmi Pujan': 'Dhan Teras', 'Vijaya Dashmi': 'Dussehra',
        'Vijaya Dashami': 'Dussehra', 'Dhan Trayodashi': 'Dhan Teras', "Aksharbrahma Gunatitanand Swami's Birthday": 'Gunatitanand Swami Jayanti',
        "Aksharbrahma Gunatitanand Swami's Birthday, Sharad Punam": 'Sharad Punam', 'Bhai Bij': 'Bhai Beej'}


def fest(date):
    x = CAL.get(date)
    return TIDY.get(x['festivals'][0]['name'], x['festivals'][0]['name']) if x and x['festivals'] else ''


def tithi(date):   # 'Aso Vad Chaudas/Amas' reads as the first tithi of the day
    x = CAL.get(date)
    return re.sub(r'/\w+', '', x['indian_date']) if x else ''


def load(name):
    folder = os.path.join(HERE, 'preview', 'cal', f'{name}-photos')
    ps = json.load(open(os.path.join(folder, 'photos.json')))
    for i, x in enumerate(ps):
        x['im'] = Image.open(os.path.join(folder, f'{i:02d}.jpg')).convert('RGB')
        if x.get('face') is not None:
            x['face'] = tuple(x['face'])
    return ps


def card_date(x, day):
    d = (x.get('fest') or x.get('d') or '')[:10]
    return d if re.fullmatch(r'\d{4}-\d\d-\d\d', d) else f'{x["y"]}-{day:%m-%d}'


ORIG_MAKE = make.WideCard.make


def with_tags(style):
    """Draw a small label on the photo of every card that carries x['_tag']."""
    def mk(self, x, num=None):
        card = ORIG_MAKE(self, x, num)
        t = x.get('_tag')
        if not t:
            return card
        d = ImageDraw.Draw(card)
        f = garamond(self.PW * .085, 700)
        tw = d.textlength(t, font=f)
        h, pad = f.size * 1.35, self.PW * .03
        x0, y0 = self.B + self.PW * .03, self.B + self.PW * .03
        if style == 'ribbon':   # gold tab, maroon letters
            box = (x0, y0, x0 + tw + 2 * pad, y0 + h)
            d.rounded_rectangle(box, radius=h / 2, fill=(236, 192, 104), outline=(150, 100, 40), width=max(1, round(px(1))))
            d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), t, font=f, fill=(96, 20, 32), anchor='mm')
        else:              # maroon tab, gold letters
            box = (x0, y0, x0 + tw + 2 * pad, y0 + h)
            d.rounded_rectangle(box, radius=self.PW * .012, fill=(96, 20, 32, 235), outline=(236, 192, 104), width=max(1, round(px(1.5))))
            d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), t, font=f, fill=GOLD, anchor='mm')
        return card
    return mk


def line_under_title(img, text, y=138, size=27, colour=CAPTION_GOLD, track=5):
    dr = ImageDraw.Draw(img)
    f = garamond(px(size), 600)
    t = text.upper()
    tw = make.spaced(dr, t, f, px(track))
    x0 = (W - tw) / 2
    make.draw_spaced(dr, x0, px(y) - f.getmetrics()[0], t, f, px(track), colour)
    mid = px(y) - f.size * .33
    make.diamond(dr, x0 - px(22), mid, px(4), GOLD); make.diamond(dr, x0 + tw + px(22), mid, px(4), GOLD)


def corner(img, text, right=False, y=None):
    dr = ImageDraw.Draw(img)
    f = garamond(px(24), 500)
    y = y or make.H - px(15)
    dr.text((W - px(30) if right else px(30), y), text, font=f, fill=(226, 184, 104), anchor='rs' if right else 'ls')


def draw(ps, day, title_day=None, tags=None, mode=None, foot=None, title=None):
    for x in ps:
        x.pop('_tag', None)
        if tags:
            t = fest(card_date(x, day))
            if t:
                x['_tag'] = t
    make.WideCard.make = with_tags(mode) if tags else ORIG_MAKE
    was, real = make.FOOTER, make.header_one
    if foot:
        make.FOOTER = f'{foot}   ·   {was}'
    if title:
        make.header_one = lambda img, t, sub: real(img, title, sub)
    img = make.compose(ps, title_day or day, seed=f'{day:%m-%d}', style='W2')
    make.WideCard.make, make.FOOTER, make.header_one = ORIG_MAKE, was, real
    return img


def main(out):
    os.makedirs(out, exist_ok=True)
    today = datetime.date(2026, 10, 24)
    p24 = load('2026-10-24')
    t24 = f'{tithi(str(today))}, Vikram Samvat {CAL[str(today)]["vikram_samvat"]}'
    made = []

    def save(img, n, name):
        f = os.path.join(out, f'{n:02d}-{name}.png'); img.save(f, optimize=True)
        img.convert('RGB').resize((2796, 1290), Image.LANCZOS).save(f[:-4] + '.jpg', quality=90); made.append(f)

    save(draw(p24, today, foot=t24), 1, 'indian-date-in-footer')

    img = draw(p24, today); corner(img, t24); save(img, 2, 'indian-date-in-corner')

    save(draw(p24, today, tags=True, mode='ribbon'), 3, 'festival-tag-gold')

    save(draw(p24, today, tags=True, mode='maroon'), 4, 'festival-tag-maroon')

    keep = [dict(x) for x in p24]
    for x in keep:
        t = fest(card_date(x, today))
        if t:
            x['p'] = f'{t}, {make.place(x)}' if make.place(x) else t
    img = make.compose(keep, today, seed='10-24', style='W2'); save(img, 5, 'festival-in-year-line')

    tom = today + datetime.timedelta(days=1)
    img = draw(p24, today); corner(img, f'Tomorrow: Sharad Punam, {fest(str(tom))}', right=True, y=make.H - px(15)); save(img, 6, 'tomorrow-line')

    save(draw(p24, today, tags=True, mode='ribbon', foot=t24), 7, 'date-line-and-tags')

    diwali = datetime.date(2026, 11, 8)
    p08 = load('2026-11-08')
    save(draw(p08, diwali, tags=True, mode='ribbon', title='Diwali, 8 November', foot=tithi(str(diwali))), 8, 'festival-day-8-november')

    pdw = load('diwali')
    for x in pdw:
        dd = datetime.date.fromisoformat(x['fest'])
        x['p'] = f'{dd.day} {dd:%b}'
    save(draw(pdw, diwali, title='Every Diwali', foot=f'One darshan from each Diwali, {pdw[0]["y"]} to {pdw[-1]["y"]}'), 9, 'diwali-through-the-years')

    ek = datetime.date(2026, 11, 5)
    p05 = load('2026-11-05')
    save(draw(p05, ek, tags=True, mode='maroon', foot=f'Rama Ekadashi (fast), Vagh Baras, {tithi(str(ek))}'), 10, 'ekadashi-day-5-november')
    print('\n'.join(made))


if __name__ == '__main__':
    main(sys.argv[1])
