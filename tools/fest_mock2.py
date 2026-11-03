"""Test only (never ship): the special picture for every festival, from the photos Claude picked by eye for each year
(preview/fest/picks.json: Bapa and the festival itself both clearly in the photo), one big special card in the middle,
and each festival's own dress. Darpan, 30 Oct 2026: 'There must be pictures with Bapa and fireworks... do this for all
the festivals. Do a special card. Make all the festivals and the pictures relevant to that event.'

python tools/fest_mock2.py out_folder [festival ...]"""
import datetime, json, math, os, random, re, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import make_hero as make
import fest_food
from make_hero import W, H, px

FEST = os.path.join(ROOT, 'preview', 'fest')
NAMES = {'diwali': 'Diwali', 'annakut': 'Annakut', 'janmashtami': 'Janmashtami', 'fuldol': 'Fuldol', 'gurupurnima': 'Guru Purnima',
         'harinom': 'Swaminarayan Jayanti', 'vasant': 'Vasant Panchami', 'rathyatra': 'Rathyatra', 'raksha': 'Raksha Bandhan',
         'psm': 'Pramukh Swami Maharaj Jayanti', 'msm': 'Mahant Swami Maharaj Jayanti'}
DAY = {'diwali': '2026-11-08', 'annakut': '2026-11-10', 'janmashtami': '2027-08-25', 'fuldol': '2027-03-23', 'gurupurnima': '2027-07-18',
       'harinom': '2027-04-15', 'vasant': '2027-02-11', 'rathyatra': '2027-07-05', 'raksha': '2027-08-17', 'psm': '2026-12-07', 'msm': '2027-09-13'}
MARIGOLD, ROSES, JASMINE = [(255, 159, 28), (255, 190, 40), (240, 120, 20)], [(224, 36, 94), (255, 143, 171), (255, 213, 106)], [(255, 252, 240), (245, 240, 220)]
DRESS = {   # night/top tint, glow colour, sky, rope, foot picture
    'diwali': dict(top=(10, 8, 26), glow=(150, 80, 20), sky=('fireworks',), rope=('bulbs',), foot='diya', diyas=True),
    'annakut': dict(glow=(190, 100, 20), rope=('sweets',), foot=None),   # light touch: laddus on the marigold cord, a full thali on each card
    'janmashtami': dict(top=(8, 12, 40), glow=(60, 90, 180), sky=('stars',), rope=('beads', [(31, 122, 140), (27, 63, 122), (80, 170, 90)]), foot='matki'),
    'fuldol': dict(glow=(170, 40, 90), sky=('puffs', [(255, 61, 127), (255, 212, 0), (53, 199, 89), (61, 183, 255), (255, 138, 26), (176, 92, 255)]),
                   rope=('beads', [(255, 61, 127), (255, 212, 0), (53, 199, 89), (61, 183, 255), (255, 138, 26)]), foot='gulal'),
    'gurupurnima': dict(top=(14, 14, 34), glow=(120, 110, 70), sky=('moon',), rope=('beads', JASMINE), foot='lotus'),
    'harinom': dict(glow=(190, 100, 20), sky=('petals', ROSES), rope=('beads', MARIGOLD), foot='kalash'),
    'vasant': dict(glow=(200, 170, 0), sky=('petals', [(255, 212, 0), (255, 232, 102)]), rope=('beads', [(255, 212, 0), (255, 232, 102)]), foot='flowers'),
    'rathyatra': dict(glow=(150, 50, 30), sky=None, rope=('flags', [(192, 38, 45), (255, 176, 32), (46, 125, 50), (21, 101, 192), (255, 243, 214)]), foot='wheel'),
    'raksha': dict(glow=(170, 40, 60), sky=('petals', [(255, 213, 106), (255, 143, 171)]), rope=('thread',), foot='rakhi'),
    'psm': dict(glow=(190, 100, 20), sky=('petals', ROSES), rope=('beads', ROSES), foot='garland'),
    'msm': dict(glow=(190, 100, 20), sky=('petals', ROSES), rope=('beads', ROSES), foot='garland'),
}
# card words where the archive's caption says nothing of the festival, or the same words come again
SAY = {
    ('diwali', 1990): 'Diwali puja darshan', ('diwali', 1997): 'Diwali darshan', ('diwali', 1998): 'Diwali morning puja',
    ('diwali', 2005): 'Diwali darshan', ('diwali', 2009): 'Diwali darshan with Thakorji', ('diwali', 2017): 'Watches the Diwali fireworks from the mandir',
    ('diwali', 2024): 'Watches the Diwali fireworks', ('diwali', 2025): 'Watches the fireworks after the arti',
    ('diwali', 2008): 'Sanctifies the account books on Chopda Pujan', ('diwali', 2013): 'Chopda Pujan arti', ('diwali', 2015): 'Performs the Chopda Pujan arti',
    ('annakut', 1990): 'Annakut utsav', ('annakut', 1997): 'Annakut on New Year’s Day', ('annakut', 1998): 'Annakut utsav',
    ('annakut', 2001): 'Observes the annakut items', ('annakut', 2004): 'Annakut arti of Thakorji', ('annakut', 2005): 'Performs the annakut arti',
    ('annakut', 2006): 'Annakut arti', ('annakut', 2008): 'Arti before the annakut', ('annakut', 2009): 'New Year annakut arti',
    ('annakut', 2010): 'Annakut arti in the Akshar Deri', ('annakut', 2012): 'Arti of the annakut', ('annakut', 2013): 'Annakut arti with Thakorji',
    ('annakut', 2014): 'Performs arti of the annakut', ('annakut', 2018): 'New Year’s Day annakut arti',
    ('annakut', 2019): 'Offers thal to Thakorji', ('annakut', 2020): 'Offers thal to the Guru Parampara', ('annakut', 2021): 'Offers the annakut thal',
    ('annakut', 2022): 'Offers thal to Pramukh Swami Maharaj', ('annakut', 2023): 'Offers the New Year thal', ('annakut', 2024): 'Offers thal on New Year’s Day',
    ('annakut', 2025): 'Offers the annakut to Thakorji',
    ('janmashtami', 1990): 'Janmashtami celebration', ('janmashtami', 1991): 'Janmashtami utsav', ('janmashtami', 2013): 'Krishna in a hindolo',
    ('janmashtami', 2007): 'Rocks Thakorji’s hindolo', ('janmashtami', 2009): 'Swings Thakorji', ('janmashtami', 2012): 'Swings Thakorji in a hindolo',
    ('janmashtami', 2014): 'Swings the hindolo', ('janmashtami', 2015): 'Swings Thakorji in the cradle', ('janmashtami', 2016): 'Swings Thakorji at midnight',
    ('janmashtami', 2017): 'Swings Harikrishna Maharaj', ('janmashtami', 2018): 'Rocks the decorated hindolo', ('janmashtami', 2019): 'Swings Thakorji on the hindolo',
    ('janmashtami', 2021): 'Swings Thakorji and Gunatitanand Swami', ('janmashtami', 2022): 'Krishna janmotsav arti', ('janmashtami', 2024): 'Swings the golden hindolo',
    ('janmashtami', 2025): 'Janmotsav arti', ('janmashtami', 2026): 'Swings the cradle',
    ('fuldol', 2003): 'Pushpadolotsav colours', ('fuldol', 2008): 'Showers colours on Thakorji', ('fuldol', 2009): 'Colours for Thakorji first',
    ('fuldol', 2010): 'First colours for Thakorji', ('fuldol', 2012): 'Sprays colours on Thakorji', ('fuldol', 2014): 'Sprays colours from the stage',
    ('fuldol', 2016): 'Showers colours on everyone', ('fuldol', 2020): 'Saffron water for Thakorji', ('fuldol', 2021): 'Sprays saffron water on Thakorji',
    ('fuldol', 2022): 'Saffron colours for Thakorji', ('fuldol', 2023): 'Saffron water for Akshar Purushottam Maharaj', ('fuldol', 2024): 'Plays colours with Thakorji',
    ('gurupurnima', 1977): 'Guru Purnima', ('gurupurnima', 2004): 'Senior saints garland Bapa', ('gurupurnima', 2008): 'Senior sadhus honour him',
    ('gurupurnima', 2010): 'Sadhus offer garlands', ('gurupurnima', 2011): 'Honoured with a shawl and garland', ('gurupurnima', 2013): 'Garlanded by the sadhus',
    ('gurupurnima', 2014): 'Darshan of Shastriji Maharaj on Guru Purnima', ('gurupurnima', 2015): 'Guru Purnima garlands', ('gurupurnima', 2018): 'Honoured by senior sadhus',
    ('gurupurnima', 2019): 'Viveksagar Swami offers a garland', ('gurupurnima', 2020): 'Guru pujan with a garland', ('gurupurnima', 2022): 'Honoured with a garland',
    ('gurupurnima', 2024): 'Guru pujan by Tyagvallabh Swami', ('gurupurnima', 2025): 'Guru pujan', ('gurupurnima', 2026): 'Anandswarup Swami offers a garland',
    ('harinom', 2003): 'Shriji Maharaj’s birthday arti', ('harinom', 2004): 'Pujan of Harikrishna Maharaj', ('harinom', 2007): 'Janmotsav arti of Thakorji',
    ('harinom', 2010): 'Performs the janmotsav arti', ('harinom', 2011): 'Midnight janmotsav arti', ('harinom', 2012): 'Swings Ghanshyam in the hindolo',
    ('harinom', 2014): 'Swings Thakorji', ('harinom', 2015): 'Swings the decorated hindolo', ('harinom', 2016): 'Swings Thakorji on Hari Nom',
    ('harinom', 2019): 'Swings Harikrishna Maharaj', ('harinom', 2020): 'Rocks the hindolo', ('harinom', 2021): 'Janmotsav arti for baby Ghanshyam',
    ('harinom', 2022): 'Sings ‘Dharma gher anand bhayo’', ('harinom', 2023): 'Swings Ghanshyam singing ‘Jay bolo Ghanshyamki’',
    ('harinom', 2024): 'Swings Thakorji in the golden hindolo', ('harinom', 2025): 'Swings Harikrishna Maharaj and Gunatitanand Swami', ('harinom', 2026): 'Swings Ghanshyam Maharaj',
    ('vasant', 2018): 'Reads the Shikshapatri', ('vasant', 2022): 'Reads the Shikshapatri on its birthday', ('vasant', 2015): 'Annakut for Shastriji Maharaj’s birthday',
    ('vasant', 2017): 'Vasant Panchami assembly', ('vasant', 2021): 'Vasant Panchami morning arti',
    ('rathyatra', 2000): 'Becomes the charioteer', ('rathyatra', 2009): 'Rathyatra celebration', ('rathyatra', 2011): 'Drives Thakorji’s chariot',
    ('rathyatra', 2012): 'Drives the chariot of Harikrishna Maharaj', ('rathyatra', 2014): 'Arrives in a lit rath at night', ('rathyatra', 2015): 'With Thakorji in his chariot',
    ('rathyatra', 2016): 'Darshan of Thakorji in his rath', ('rathyatra', 2017): 'Steers Thakorji’s chariot', ('rathyatra', 2018): 'Drives Thakorji’s rath',
    ('rathyatra', 2019): 'Pulls the chariot with the sadhus', ('rathyatra', 2020): 'Rathyatra arti', ('rathyatra', 2021): 'Rides in the Rathyatra',
    ('rathyatra', 2023): 'In the Rathyatra procession', ('rathyatra', 2025): 'Steers the rath of Thakorji',
    ('raksha', 1994): 'Raksha Bandhan utsav', ('raksha', 2011): 'Sanctifies rakhis for devotees', ('raksha', 2012): 'Ishwarcharan Swami ties a rakhi on his wrist',
    ('raksha', 2014): 'A nadachhadi tied on his wrist', ('raksha', 2015): 'Waves a chhadi of rakhis', ('raksha', 2017): 'Offers a rakhi to Thakorji',
    ('raksha', 2018): 'Atmaswarup Swami ties a rakhi', ('raksha', 2021): 'Blesses the rakhis', ('raksha', 2023): 'Ties a rakhi on Tyagvallabh Swami’s wrist',
    ('raksha', 2025): 'Yagnasetu Swami ties a nadachhadi', ('raksha', 2026): 'The sacred thread ceremony',
    ('msm', 2016): 'Honoured with an ‘84’ shawl', ('msm', 2017): 'A garland made of paghs', ('msm', 2018): 'Birthday garland', ('msm', 2019): 'Priyavrat Swami offers a garland',
    ('msm', 2020): 'His 87th birthday', ('msm', 2021): 'Birthday garlands', ('msm', 2022): 'Honoured with a birthday shawl', ('msm', 2023): 'Receives a birthday present',
    ('msm', 2024): 'Kothari Swami offers a garland', ('msm', 2025): 'A garland and a chhadi', ('msm', 2026): 'Lights the candles on his birthday cake',
    ('psm', 1999): 'Birthday garland', ('psm', 2000): 'His 80th birthday', ('psm', 2003): 'Garlanded on his birthday', ('psm', 2005): 'Kolkata devotees garland him',
    ('psm', 2007): '‘In the Joy of Others’ birthday', ('psm', 2009): 'Sadhus’ birthday garlands', ('psm', 2010): 'Kothari Swami offers a garland',
    ('psm', 2011): 'Birthday garland from the sadhus', ('psm', 2012): 'His 92nd birthday', ('psm', 2013): 'His 93rd birthday', ('psm', 2014): 'His 94th birthday',
    ('psm', 2015): 'His 95th birthday', ('psm', 2017): 'Ishwarcharan Swami offers a garland', ('psm', 2018): 'Tyagvallabh Swami offers a garland',
    ('psm', 2019): 'Viveksagar Swami offers a garland', ('psm', 2021): 'A heart shaped garland', ('psm', 2022): 'Kothari Swami offers a garland',
    ('psm', 2023): 'Garlanded on Pramukh Swami Maharaj’s birthday', ('psm', 2024): 'Senior swamis offer a garland', ('psm', 2025): 'Birthday garland',
    ('annakut', 1998): 'Annakut celebration', ('diwali', 2005): 'Blesses everyone on Diwali day', ('diwali', 2015): 'Performs the Chopda Pujan rituals',
    ('diwali', 2004): 'Writes blessings in the account books', ('diwali', 2012): 'Holds a Diwali lamp',
    ('janmashtami', 2003): 'Rocks Thakorji with the sadhus', ('janmashtami', 2008): 'Rocks Thakorji in a decorated hindolo', ('janmashtami', 2002): 'Janmashtami arti',
    ('janmashtami', 2001): 'Blesses the Janmashtami assembly', ('janmashtami', 2023): 'Swings Shri Krishna in a hindolo', ('janmashtami', 2020): 'Shri Krishna janmotsav arti',
    ('fuldol', 2002): 'Sprays colours on the sadhus', ('fuldol', 2004): 'Colours for Harikrishna Maharaj', ('fuldol', 2006): 'Showers colours with a water jet',
    ('fuldol', 2007): 'Showers colours on the bhaktas', ('fuldol', 2013): 'Holds up the colours', ('fuldol', 2019): 'Sprays saffron water on the sadhus',
    ('gurupurnima', 2005): 'Garlanded on Guru Purnima', ('gurupurnima', 2006): 'Children offer flowers', ('gurupurnima', 2017): 'Swamis garland Bapa',
    ('gurupurnima', 2012): 'Honoured with garlands and flowers', ('gurupurnima', 2000): 'Blesses everyone on Guru Purnima', ('gurupurnima', 2009): 'Blesses the Guru Purnima assembly',
    ('harinom', 2017): 'Abhishek of Harikrishna Maharaj',
    ('vasant', 2004): 'Darshan in Shastriji Maharaj’s room', ('vasant', 2006): 'Shastriji Maharaj’s 141st birthday', ('vasant', 2007): 'Pradakshina in Shastriji Maharaj’s room',
    ('vasant', 2009): 'A new sinhasan for Shastriji Maharaj', ('vasant', 2010): 'Prays in Shastriji Maharaj’s room', ('vasant', 2012): 'With the murti of Shastriji Maharaj',
    ('vasant', 2013): 'Shastriji Maharaj’s life story', ('vasant', 2016): 'Darshan of Shastriji Maharaj', ('vasant', 2019): 'Touches Shastriji Maharaj’s blanket',
    ('vasant', 2020): 'Pujan of Shastriji Maharaj', ('vasant', 2024): 'Darshan of Shastriji Maharaj’s murti',
    ('rathyatra', 2005): 'Rathyatra with Harikrishna Maharaj', ('rathyatra', 2013): 'Joins the Rathyatra', ('rathyatra', 2022): 'Rathyatra rituals', ('rathyatra', 2024): 'Rathyatra pujan',
    ('raksha', 2012): 'A rakhi tied on his wrist', ('raksha', 2023): 'Ties a rakhi on a swami’s wrist',
    ('psm', 2022): 'Kothari Swami’s birthday garland', ('psm', 2025): 'Garlanded on the birthday', ('psm', 2023): 'Garlanded on Bapa’s birthday',
}


# ------------------------------------------------------------------ drawing the festival's things

def hi(size, draw):
    """Draw at 4x on a clear square and shrink, so small pictures stay smooth."""
    s = size * 4
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw(im, ImageDraw.Draw(im), s)
    return im.resize((size, size), Image.LANCZOS)


def glow(im, s, cx, cy, r, col, a=140):
    g = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (a,))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(s * .07)))


def diya(im, d, s):
    glow(im, s, s * .5, s * .3, s * .3, (255, 170, 40))
    d.polygon([(s * .5, s * .06), (s * .6, s * .3), (s * .6, s * .42), (s * .5, s * .5), (s * .4, s * .42), (s * .4, s * .3)], fill=(255, 150, 30))
    d.polygon([(s * .5, s * .18), (s * .555, s * .34), (s * .5, s * .46), (s * .445, s * .34)], fill=(255, 238, 150))
    d.chord((s * .08, s * .22, s * .92, s * .92), 0, 180, fill=(170, 70, 30))
    d.chord((s * .14, s * .34, s * .86, s * .84), 0, 180, fill=(205, 100, 40))
    d.ellipse((s * .08, s * .5, s * .92, s * .64), fill=(150, 55, 25))
    d.ellipse((s * .14, s * .52, s * .86, s * .6), fill=(110, 40, 20))
    d.line((s * .2, s * .72, s * .8, s * .72), fill=(255, 210, 120), width=s // 40)


def thal(im, d, s):
    d.ellipse((s * .04, s * .7, s * .96, s * .92), fill=(214, 160, 50), outline=(140, 90, 20), width=s // 60)
    d.ellipse((s * .14, s * .72, s * .86, s * .84), fill=(240, 205, 110))
    for x, y in [(.3, .66), (.5, .66), (.7, .66), (.4, .5), (.6, .5), (.5, .34)]:
        r = s * .1
        d.ellipse((s * x - r, s * y - r, s * x + r, s * y + r), fill=(245, 150, 30), outline=(190, 100, 15), width=s // 80)
    d.polygon([(s * .78, s * .74), (s * .98, s * .62), (s * .9, s * .78)], fill=(63, 138, 46))


# Annakut (Darpan 31 Oct 2026: every Annakut design must be Indian food): laddu, jalebi, kaju katli, gulab jamun, samosa, puri, a full thali
def laddu(im, d, s):
    d.ellipse((s * .12, s * .12, s * .88, s * .88), fill=(240, 150, 30), outline=(190, 105, 15), width=max(1, s // 40))
    rnd = random.Random(s)
    for _ in range(40):
        x, y, r = rnd.uniform(.25, .75) * s, rnd.uniform(.25, .75) * s, s * .025
        d.ellipse((x - r, y - r, x + r, y + r), fill=rnd.choice([(255, 190, 70), (205, 115, 20)]))
    d.ellipse((s * .26, s * .22, s * .44, s * .36), fill=(255, 205, 110))


def jalebi(im, d, s):
    pts = [(s * .5 + math.cos(t) * s * .045 * t, s * .5 + math.sin(t) * s * .045 * t) for t in [i / 8 for i in range(4, 82)]]
    d.line(pts, fill=(200, 95, 10), width=max(2, s // 9), joint='curve')
    d.line(pts, fill=(255, 160, 30), width=max(1, s // 14), joint='curve')
    d.line(pts, fill=(255, 205, 100), width=max(1, s // 40), joint='curve')


def katli(im, d, s):
    d.polygon([(s * .5, s * .12), (s * .9, s * .5), (s * .5, s * .88), (s * .1, s * .5)], fill=(236, 222, 196), outline=(190, 170, 140))
    d.polygon([(s * .5, s * .26), (s * .74, s * .5), (s * .5, s * .74), (s * .26, s * .5)], fill=(225, 228, 232))


def jamun(im, d, s):
    d.ellipse((s * .14, s * .2, s * .86, s * .86), fill=(95, 35, 15), outline=(60, 20, 8))
    d.ellipse((s * .3, s * .3, s * .5, s * .45), fill=(170, 85, 40))


def samosa(im, d, s):
    d.polygon([(s * .5, s * .1), (s * .92, s * .86), (s * .08, s * .86)], fill=(214, 150, 60), outline=(150, 95, 30))
    d.polygon([(s * .5, s * .1), (s * .6, s * .86), (s * .08, s * .86)], fill=(232, 175, 80))
    for x in (.35, .55, .7):
        d.ellipse((s * x - s * .02, s * .6, s * x + s * .02, s * .64), fill=(150, 95, 30))


def puri(im, d, s):
    d.ellipse((s * .08, s * .22, s * .92, s * .82), fill=(225, 160, 60), outline=(170, 105, 30), width=max(1, s // 40))
    d.ellipse((s * .22, s * .3, s * .7, s * .6), fill=(245, 195, 100))


SWEETS = [laddu, jalebi, katli, jamun, samosa, puri]


def laddus(im, d, s):
    fest_food.pyramid(im, s * .5, s * .78, s * .085, 4, (240, 150, 30), [(255, 195, 80), (200, 110, 20)], 1)


def thali(im, d, s):
    """A full steel thali: dal, shaak, kadhi and kheer in katoris, rice, puris and a laddu."""
    d.ellipse((s * .02, s * .2, s * .98, s * .98), fill=(176, 182, 190), outline=(120, 126, 134), width=max(1, s // 50))
    d.ellipse((s * .08, s * .26, s * .92, s * .92), fill=(214, 218, 224))
    for x, y, c in [(.3, .4, (240, 190, 40)), (.52, .36, (95, 140, 40)), (.74, .44, (250, 230, 160)), (.76, .68, (245, 240, 225))]:
        r = s * .11
        d.ellipse((s * x - r, s * y - r, s * x + r, s * y + r), fill=(160, 166, 174))
        d.ellipse((s * x - r * .8, s * y - r * .8, s * x + r * .8, s * y + r * .8), fill=c)
    d.ellipse((s * .2, s * .56, s * .5, s * .84), fill=(250, 250, 244))   # rice
    for x, y in [(.52, .7), (.58, .78)]:
        d.ellipse((s * x - s * .09, s * y - s * .07, s * x + s * .09, s * y + s * .07), fill=(225, 160, 60), outline=(170, 105, 30))
    r = s * .07
    d.ellipse((s * .3 - r, s * .7 - r - s * .02, s * .3 + r, s * .7 + r - s * .02), fill=(240, 150, 30))


def matki(im, d, s):
    d.ellipse((s * .14, s * .36, s * .86, s * .96), fill=(176, 80, 36))
    d.ellipse((s * .2, s * .42, s * .5, s * .62), fill=(205, 110, 60))
    d.arc((s * .2, s * .5, s * .8, s * .82), 20, 160, fill=(255, 210, 122), width=s // 30)
    d.rectangle((s * .3, s * .26, s * .7, s * .42), fill=(150, 64, 28))
    d.ellipse((s * .24, s * .2, s * .76, s * .34), fill=(255, 250, 235))
    d.pieslice((s * .3, s * .02, s * .7, s * .36), 180, 360, fill=(255, 253, 243))


def gulal(im, d, s):
    d.ellipse((s * .02, s * .66, s * .98, s * .9), fill=(214, 160, 50), outline=(140, 90, 20), width=s // 60)
    for x, c in [(.24, (255, 61, 127)), (.5, (255, 212, 0)), (.76, (53, 199, 89))]:
        d.pieslice((s * (x - .18), s * .42, s * (x + .18), s * .98), 180, 360, fill=c)
    for x, y, c in [(.2, .3, (255, 61, 127)), (.5, .18, (255, 212, 0)), (.8, .28, (53, 199, 89))]:
        r = s * .05
        d.ellipse((s * x - r, s * y - r, s * x + r, s * y + r), fill=c + (150,))


def lotus(im, d, s):
    d.ellipse((s * .14, s * .82, s * .86, s * .94), fill=(63, 138, 46))
    d.polygon([(s * .5, s * .1), (s * .64, s * .5), (s * .5, s * .84), (s * .36, s * .5)], fill=(248, 165, 194))
    d.polygon([(s * .5, s * .84), (s * .16, s * .3), (s * .36, s * .6)], fill=(240, 98, 146))
    d.polygon([(s * .5, s * .84), (s * .84, s * .3), (s * .64, s * .6)], fill=(240, 98, 146))
    d.polygon([(s * .5, s * .86), (s * .02, s * .62), (s * .3, s * .8)], fill=(236, 64, 122))
    d.polygon([(s * .5, s * .86), (s * .98, s * .62), (s * .7, s * .8)], fill=(236, 64, 122))


def kalash(im, d, s):
    for a in (-60, -25, 25, 60):
        x = s * .5 + s * .3 * math.sin(math.radians(a)); y = s * .2 - s * .1 * math.cos(math.radians(a))
        d.ellipse((x - s * .1, y - s * .04, x + s * .1, y + s * .04), fill=(63, 138, 46))
    d.ellipse((s * .38, s * .04, s * .62, s * .3), fill=(138, 90, 43))
    d.rectangle((s * .32, s * .28, s * .68, s * .36), fill=(214, 160, 50))
    d.ellipse((s * .16, s * .34, s * .84, s * .96), fill=(214, 160, 50), outline=(140, 90, 20), width=s // 60)
    d.arc((s * .18, s * .5, s * .82, s * .78), 20, 160, fill=(192, 38, 45), width=s // 18)


def flowers(im, d, s):
    for x, y in [(.22, .6), (.5, .4), (.78, .6)]:
        for k in range(6):
            a = k / 6 * 2 * math.pi; r = s * .08
            cx, cy = s * x + math.cos(a) * s * .1, s * y + math.sin(a) * s * .1
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 212, 0))
        r = s * .07
        d.ellipse((s * x - r, s * y - r, s * x + r, s * y + r), fill=(240, 138, 0))
    d.arc((s * .1, s * .7, s * .9, s * 1.1), 200, 340, fill=(63, 138, 46), width=s // 30)


def wheel(im, d, s):
    c, r = s * .5, s * .42
    for k in range(8):
        a = k / 8 * 2 * math.pi
        d.line((c, c, c + math.cos(a) * r, c + math.sin(a) * r), fill=(138, 58, 18), width=s // 22)
    d.ellipse((c - r, c - r, c + r, c + r), outline=(138, 58, 18), width=s // 9)
    d.ellipse((c - r * .86, c - r * .86, c + r * .86, c + r * .86), outline=(230, 180, 80), width=s // 40)
    d.ellipse((c - s * .1, c - s * .1, c + s * .1, c + s * .1), fill=(214, 160, 50), outline=(138, 58, 18), width=s // 50)


def rakhi(im, d, s):
    d.arc((-s * .1, s * .3, s * 1.1, s * .9), 200, 340, fill=(208, 31, 60), width=s // 20)
    for k in range(10):
        a = k / 10 * 2 * math.pi; r = s * .09
        cx, cy = s * .5 + math.cos(a) * s * .24, s * .5 + math.sin(a) * s * .24
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 176, 32) if k % 2 else (255, 213, 106))
    d.ellipse((s * .32, s * .32, s * .68, s * .68), fill=(208, 31, 60))
    d.ellipse((s * .42, s * .42, s * .58, s * .58), fill=(214, 160, 50))


def garland(im, d, s):
    for k in range(20):
        a = k / 20 * 2 * math.pi; r = s * .07
        cx, cy = s * .5 + math.cos(a) * s * .34, s * .44 + math.sin(a) * s * .3
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(224, 36, 94) if k % 2 else (255, 143, 171))
    d.line((s * .5, s * .74, s * .5, s * .9), fill=(255, 213, 106), width=s // 30)
    d.ellipse((s * .44, s * .86, s * .56, s * .98), fill=(255, 213, 106))


PICS = dict(diya=diya, thal=thal, matki=matki, gulal=gulal, lotus=lotus, kalash=kalash, flowers=flowers, wheel=wheel, rakhi=rakhi, garland=garland, thali=thali, laddus=laddus)


def burst(d, cx, cy, R, col, rnd):
    n = rnd.randint(22, 30)
    for i in range(n):
        a = i / n * 2 * math.pi + rnd.uniform(-.05, .05); rr = R * rnd.uniform(.82, 1.05)
        for k in range(9):
            f = (k + 1) / 9
            x, y = cx + math.cos(a) * rr * f, cy + math.sin(a) * rr * f + R * .12 * f * f
            s = px(1.2 + 2.6 * f)
            d.ellipse((x - s, y - s, x + s, y + s), fill=col + (int(60 + 190 * f),))


def sky(img, spec, rnd):
    if not spec:
        return img
    kind = spec[0]
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    corners = [(.06, .1, 120), (.17, .06, 80), (.94, .1, 125), (.83, .06, 78), (.035, .45, 70), (.965, .5, 72), (.03, .85, 60), (.97, .88, 60)]
    if kind == 'fireworks':
        cols = [(255, 205, 90), (255, 120, 170), (120, 220, 255), (255, 150, 60), (190, 255, 140)]
        spots = corners[:6] + [(.26, .07, 55), (.74, .07, 55), (.1, .3, 60), (.9, .3, 60), (.05, .68, 62), (.95, .7, 62), (.025, .92, 45), (.975, .92, 45), (.12, .12, 40), (.88, .13, 40)]
        for i, (fx, fy, r) in enumerate(spots):   # Darpan 31 Oct 2026: more fireworks in the background
            burst(d, W * fx, H * fy, px(r), cols[i % len(cols)], rnd)
    elif kind == 'stars':
        for _ in range(420):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H) ** 1.4 / H ** .4
            r = px(rnd.choice((1, 1.2, 1.6, 2.4)))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 230, rnd.randint(120, 255)))
    elif kind == 'moon':
        for _ in range(260):
            x, y = rnd.uniform(0, W), rnd.uniform(0, H) ** 1.5 / H ** .5
            r = px(rnd.choice((1, 1.2, 1.8)))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 235, rnd.randint(100, 220)))
        for cx in (W * .07, W * .93):
            r = px(70)
            d.ellipse((cx - r * 2.2, H * .1 - r * 2.2, cx + r * 2.2, H * .1 + r * 2.2), fill=(255, 245, 210, 40))
            d.ellipse((cx - r, H * .1 - r, cx + r, H * .1 + r), fill=(255, 248, 225, 245))
            d.ellipse((cx - r * .3, H * .1 - r * .4, cx - r * .05, H * .1 - r * .15), fill=(235, 228, 200, 200))
    elif kind == 'petals':
        for _ in range(300):
            x = rnd.choice((rnd.uniform(0, W * .2), rnd.uniform(W * .8, W), rnd.uniform(0, W)))
            y = rnd.uniform(0, H)
            c = rnd.choice(spec[1]); r = px(rnd.uniform(5, 10)); a = rnd.uniform(0, math.pi)
            pts = [(x + math.cos(a + t) * r * (1 if k % 2 == 0 else .45), y + math.sin(a + t) * r * (1 if k % 2 == 0 else .45))
                   for k, t in enumerate((0, math.pi / 2, math.pi, 3 * math.pi / 2))]
            d.polygon(pts, fill=c + (rnd.randint(150, 230),))
    elif kind == 'sweets':
        icons = [hi(round(px(z)), f) for f in SWEETS for z in (26, 32)]
        layer = layer.convert('RGBA')
        for _ in range(36):   # a light scatter in the side margins only, so the photos stay the thing you see
            x = rnd.choice((rnd.uniform(0, W * .025), rnd.uniform(W * .975, W)))
            y = rnd.uniform(H * .05, H * .95)
            ic = rnd.choice(icons).rotate(rnd.uniform(0, 360), expand=True)
            ic.putalpha(ic.getchannel('A').point(lambda v: v * .7))
            layer.alpha_composite(ic, (int(x - ic.width / 2) % W, int(y - ic.height / 2) % H))
        d = ImageDraw.Draw(layer)
    elif kind == 'puffs':
        for i, (fx, fy, r) in enumerate(corners):
            for k in range(5):
                c = spec[1][(i + k) % len(spec[1])]
                x, y, rr = W * fx + px(rnd.uniform(-70, 70)), H * fy + px(rnd.uniform(-50, 50)), px(r * rnd.uniform(.6, 1.1))
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=c + (120,))
        layer = layer.filter(ImageFilter.GaussianBlur(px(18)))
    out = img.convert('RGBA')
    if kind in ('fireworks', 'moon'):
        g = layer.filter(ImageFilter.GaussianBlur(px(10)))
        out.alpha_composite(g); out.alpha_composite(g)
    out.alpha_composite(layer)
    return out.convert('RGB')


def background_for(k):
    spec = DRESS[k]

    def bg():
        img = BASE_BG()
        a = np.asarray(img).astype(np.float32)
        hh, ww = a.shape[:2]
        yy = np.linspace(0, 1, hh)[:, None, None]; xx = np.linspace(0, 1, ww)[None, :, None]
        if spec.get('top'):   # night: dark at the top fading into the maroon by the middle
            t = np.clip(1 - yy / .7, 0, 1) ** 1.2
            a = a * (1 - t * .85) + np.array(spec['top']) * t * .85
        g = np.clip(1 - np.hypot((xx - .5) / .6, (yy - 1.05) / .34), 0, 1) ** 1.5
        a = a + np.array(spec['glow']) * g * .55
        img = Image.fromarray(a.clip(0, 255).astype('uint8'))
        img = sky(img, spec.get('sky'), random.Random(k))
        if spec.get('diyas'):   # a row of lit diyas along the bottom edge, either side of the footer line (Darpan 31 Oct 2026)
            img = img.convert('RGBA')
            s_ = round(px(34)); ic = hi(s_, diya)
            x = px(30)
            while x < W - px(30):
                if x < W * .27 or x > W * .73:
                    img.alpha_composite(ic, (int(x), int(H - s_ - px(8))))
                x += px(58)
            img = img.convert('RGB')
        return img
    return bg


def rope_for(k):
    kind = DRESS[k]['rope']

    def go(img, pts, w=None):
        if kind[0] == 'thread':   # a red and gold rakhi thread with a rakhi now and then
            d = ImageDraw.Draw(img)
            ww = round(px(7))
            d.line(pts, fill=(150, 20, 40), width=ww + 2); d.line(pts, fill=(208, 31, 60), width=ww)
            d.line([(x, y - ww * .2) for x, y in pts], fill=(255, 200, 90), width=max(1, ww // 4))
            r = hi(round(px(46)), rakhi)
            for x, y in pts[::max(1, round(px(300) / 4))]:
                img.paste(r, (int(x - r.width / 2), int(y - r.height / 2)), r)
            return
        PLAIN_ROPE(img, pts, w)
        layer = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        step = px({'bulbs': 46, 'beads': 20, 'flags': 64, 'sweets': 20}[kind[0]])
        marks, acc, i = [], 0, 0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            acc += math.hypot(x1 - x0, y1 - y0)
            if acc >= step:
                acc = 0; marks.append((x1, y1, i)); i += 1
        if kind[0] == 'bulbs':
            cols = [(255, 70, 60), (255, 190, 40), (90, 220, 110), (80, 170, 255), (255, 110, 200)]
            for x, y, i in marks:
                r = px(13); c = cols[i % len(cols)]
                d.ellipse((x - r, y + px(4) - r, x + r, y + px(4) + r), fill=c + (150,))
            out = img.convert('RGBA'); out.alpha_composite(layer.filter(ImageFilter.GaussianBlur(px(9))))
            d = ImageDraw.Draw(out)
            for x, y, i in marks:
                c = cols[i % len(cols)]; r = px(6.5)
                d.rectangle((x - px(3), y, x + px(3), y + px(5)), fill=(60, 50, 40))
                d.ellipse((x - r, y + px(4), x + r, y + px(4) + 2.4 * r), fill=c)
            img.paste(out.convert('RGB'))
        elif kind[0] == 'beads':
            d = ImageDraw.Draw(img)
            for x, y, i in marks:
                c = kind[1][i % len(kind[1])]; r = px(9)
                d.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=tuple(max(0, v - 60) for v in c))
                d.ellipse((x - r * .5, y - r * .6, x - r * .05, y - r * .15), fill=tuple(min(255, v + 60) for v in c))
        elif kind[0] == 'sweets':
            d = ImageDraw.Draw(img)
            icons = [fest_food.ball(round(px(13)), (240, 150, 30), [(255, 195, 80), (200, 110, 20)], 3)]
            for x, y, i in marks:
                if i % 6 == 0:
                    ic = icons[0]
                    img.paste(ic, (int(x - ic.width / 2), int(y + px(2))), ic)
                else:
                    c = MARIGOLD[i % len(MARIGOLD)]; r = px(8)
                    d.ellipse((x - r, y - r, x + r, y + r), fill=c, outline=tuple(max(0, v - 60) for v in c))
        elif kind[0] == 'flags':
            d = ImageDraw.Draw(img)
            for x, y, i in marks:
                c = kind[1][i % len(kind[1])]
                d.polygon([(x - px(16), y), (x + px(16), y), (x, y + px(34))], fill=c, outline=(80, 40, 20))
    return go


def dressed(k, make_card):
    """The usual card, then its band redrawn: the festival's little picture at each foot corner, year and town between."""
    draw = PICS.get(DRESS[k].get('foot'))

    def go(self, x, num=None):
        card = make_card(self, x, num)
        B, PW, PH, BB, CW, CH = self.B, self.PW, self.PH, self.BB, self.CW, self.CH
        d = ImageDraw.Draw(card)
        for j in range(B + PH + 1, CH - 1):
            t = j / CH
            d.line((1, j, CW - 2, j), fill=tuple(round(a + (b - a) * t) for a, b in zip(make.IVORY_TOP, make.IVORY_BOTTOM)) + (255,))
        s = round(min(BB * .9, PW * .16)) if draw else 0
        if draw:
            pic = hi(s, draw)
            y = round(B + PH + (BB - s) / 2)
            card.alpha_composite(pic, (round(B * .6), y)); card.alpha_composite(pic, (CW - s - round(B * .6), y))
        yf, yt = make.garamond(min(PW * .15, BB * .62), 700), str(x['y'])
        pl = make.place(x).upper()
        pf, track = make.arimo_bold(min(PW * .06, BB * .25)), PW * .012
        room = CW - 2 * (s + B) - (d.textlength(yt, font=yf) + PW * .035)
        while pf.size > 8 and make.spaced(d, pl, pf, track) > room:
            pf = make.arimo_bold(pf.size - 1)
        yh = -d.textbbox((0, 0), yt, font=yf, anchor='ls')[1]
        ph = -d.textbbox((0, 0), 'A', font=pf, anchor='ls')[1] if pl else 0
        yw, pw_ = d.textlength(yt, font=yf), make.spaced(d, pl, pf, track)
        sp = PW * .035 if pl else 0
        x0 = (CW - (yw + sp + pw_)) / 2
        base = B + PH + BB / 2 + yh / 2
        d.text((x0, base), yt, font=yf, fill=make.YEAR_C2, anchor='ls')
        make.draw_spaced(d, x0 + yw + sp, base - (yh - ph) / 2 - pf.getmetrics()[0], pl, pf, track, make.PLACE_C2)
        return card
    return go


# ------------------------------------------------------------------ the photos

CROP = {('diwali', 1990): 'whole', ('diwali', 2008): 'whole'}   # the lamps and the lit deri must stay in the frame
ORIG_TRIM = make.trim_bars
make.trim_bars = lambda im, face: (im, face) if getattr(im, 'notrim', False) else ORIG_TRIM(im, face)
FACE = {('diwali', 2025): (140, 280, 90, 120), ('diwali', 2020): (810, 140, 120, 160)}   # side views the face finder misses (x, y, w, h in the photo)


SAY.update({   # 31 Oct 2026 picks: Diwali lamps and fireworks, Annakut with the whole spread of food
    ('diwali', 1990): 'Diwali puja darshan', ('diwali', 2006): 'Morning puja among Diwali divas', ('diwali', 2013): 'Performs the Diwali arti',
    ('diwali', 2017): 'Lights a divo', ('diwali', 2019): 'Blesses the mandir account books', ('diwali', 2020): 'Lights divas for Diwali',
    ('diwali', 2022): 'Lights a Diwali lamp', ('diwali', 2023): 'Lights a lamp on Diwali', ('diwali', 2018): 'Lights the lamp in the Akshar Deri',
    ('annakut', 1990): 'Annakut utsav', ('annakut', 2001): 'Sees the annakut being made', ('annakut', 2004): 'Annakut arti of Thakorji', ('annakut', 2005): 'Performs the annakut arti',
    ('annakut', 2006): 'Arti before a grand annakut', ('annakut', 2008): 'Arti of the New Year annakut',
    ('annakut', 2009): 'New Year annakut arti', ('annakut', 2010): 'Annakut arti in the Akshar Deri', ('annakut', 2012): 'Arti of the annakut',
    ('annakut', 2013): 'The New Year annakut before him', ('annakut', 2014): 'Darshan of the annakut', ('annakut', 2015): 'Engrossed in the annakut darshan',
    ('annakut', 2017): 'Arti before the London annakut', ('annakut', 2018): 'New Year’s Day annakut arti', ('annakut', 2019): 'Arti of the Gondal annakut',
    ('annakut', 2020): 'Annakut arti for Thakorji', ('annakut', 2021): 'Arti before the annakut', ('annakut', 2022): 'Annakut arti with the sadhus',
    ('annakut', 2023): 'Annakut arti on New Year’s Day', ('annakut', 2024): 'Waves the annakut arti', ('annakut', 2025): 'Arti of the grand annakut',
})

SAY.update({   # 31 Oct 2026, Darpan: Diwali = lights and fireworks with Bapa, as many years as possible
    ('diwali', 1990): 'Diwali morning puja', ('diwali', 1997): 'Morning puja under Diwali lights', ('diwali', 1998): 'Diwali puja darshan',
    ('diwali', 2004): 'Arti on Diwali day', ('diwali', 2005): 'Arti with a coconut and sugarcane divo', ('diwali', 2006): 'Morning puja among Diwali divas',
    ('diwali', 2008): 'Darshan in the lit Akshar Deri', ('diwali', 2009): 'Divas at the Yogi Smruti Mandir', ('diwali', 2010): 'Arrives at the Akshar Deri on Diwali night',
    ('diwali', 2013): 'Performs the Diwali arti', ('diwali', 2014): 'Lakshmi Pujan on Dhan Teras', ('diwali', 2015): 'Performs the Lakshmi Pujan',
    ('diwali', 2017): 'Lights a divo', ('diwali', 2019): 'Fireworks welcome Bapa', ('diwali', 2020): 'Lights divas for Diwali',
})
SAY.update({   # 3 Nov 2026: the eight years the website list had missed (found with the Diwali week thread)
    ('diwali', 1999): 'Sanctifies the account books', ('diwali', 2000): 'Before a swastik of divas', ('diwali', 2001): 'Diwali morning puja',
    ('diwali', 2002): 'Diwali blessings under the lamps', ('diwali', 2003): 'Arti on New Year’s Day', ('diwali', 2007): 'Darshan at the decorated Akshar Deri',
    ('diwali', 2016): 'His first Diwali arti as guru', ('diwali', 2021): 'Evening arti among the Diwali lights',
})
TOWN = {('diwali', 2019): 'Rajkot'}   # the photo's own town when it is from a nearby day

def tidy_town(t):
    t = re.sub(r'\s*\(.*?\)', '', (t or '').split(',')[0]).strip()
    return '' if re.fullmatch(r'(india|uk|usa|kenya|canada|australia)', t, re.I) else t


def photos_for(k):
    cands = json.load(open(os.path.join(FEST, 'cands.json')))[k]
    picks = json.load(open(os.path.join(FEST, 'picks.json')))[k]
    out = []
    for y in cands['years']:
        l = picks['p'].get(str(y['y']))
        h2 = picks.get('hero2')   # a second big card (Annakut: New Year blessings), taking that year's place
        if h2 and y['y'] == h2[0]:
            l = h2[1]
        if not l:
            continue
        x = y['c'][ord(l) - 97]
        path = os.path.join(FEST, 'img', f"{x['a']}-{x['f'].split('/')[-1]}")
        if not os.path.exists(path):
            print('  missing', k, y['y'], path); continue
        im = Image.open(path).convert('RGB'); iw, ih = im.size
        im.notrim = (k, y['y']) in FACE   # night photos: the dark sky is not a black bar to cut away
        box = x.get('box')
        if (k, y['y']) in FACE:
            face = FACE[(k, y['y'])]
        elif box:
            face = (box[2] * iw, box[3] * ih, box[4] * iw, box[5] * ih)
        else:
            face = make.bapa_face(im, y['d'])[0] or make.bapa_face(im, y['d'], need=.38)[0]
        c = x['c']
        c = 'Swamishri ' + c if c[:1].islower() else c
        say = SAY.get((k, y['y']))
        p = dict(y=y['y'], d=y['d'], im=im, face=face, c=c, town=TOWN.get((k, y['y'])) or tidy_town(y.get('place')), crop=CROP.get((k, y['y']), 'frame'), hero=y['y'] == picks['hero'] or bool(h2 and y['y'] == h2[0]))
        p['cap'] = say or ORIG_CAPTION(p)
        out.append(p)
    seen = {}
    for p in out:   # never the same words twice on one picture
        if p['cap'] in seen:
            print(f"  same words: {k} {p['y']} and {seen[p['cap']]}: {p['cap']}")
        seen[p['cap']] = p['y']
    return out


def main():
    dest = sys.argv[1]
    os.makedirs(dest, exist_ok=True)
    keys = sys.argv[2:] or list(NAMES)
    global BASE_BG, PLAIN_ROPE, ORIG_CAPTION
    BASE_BG, PLAIN_ROPE, ORIG_CAPTION, base_make = make.background, make.rope, make.caption, make.WideCard.make
    make.place = lambda x: x.get('town', '')
    make.hero_sharp = lambda im: True
    make.hero_of = lambda photos: [x for x in photos if x.get('hero')] or None
    make.ANNIVERSARY = ()
    for k in keys:
        make.caption = ORIG_CAPTION
        photos = photos_for(k)
        make.caption = lambda x: x.get('cap', '')
        make.background, make.rope = background_for(k), rope_for(k)
        make.WideCard.make = dressed(k, base_make)
        day = datetime.date.fromisoformat(DAY[k])
        name = NAMES[k]
        line = f'One darshan from each {name}, {photos[0]["y"]} to {photos[-1]["y"]}, each year on its own day'
        img = make.compose_wide(photos, day, seed=k, style='W2', title=f'Every {name}', cal=(line, ''))
        if k == 'annakut':   # Darpan 31 Oct 2026: stacked food in the free corners beside the bottom row
            row = make.ROWS[-1]
            room = row['x0'] - px(40)
            if room > px(120):
                w = round(room); h = round(min(row['CH'] * 1.15, w * 1.45))
                for i, cx in enumerate((row['x0'] / 2, W - row['x0'] / 2)):
                    disp = fest_food.display(w, h, seed=i)
                    img = img.convert('RGBA'); img.alpha_composite(disp, (int(cx - w / 2), int(row['y'] + row['CH'] - h)))
        img.convert('RGB').save(os.path.join(dest, f'every-{k}.jpg'), quality=90)
        print(k, len(photos), 'years, special cards', [x['y'] for x in photos if x.get('hero')])


if __name__ == '__main__':
    main()
