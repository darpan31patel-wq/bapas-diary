"""Bapa's Diary style kit: every colour, the two fonts and the footer line in one place, so the daily picture, the
special pictures and the month posters all match (Darpan, 17 Nov 2026, idea 2: 'keep a style kit in one file').

Change a colour here and every picture follows. Only two fonts are used anywhere: EB Garamond (titles, years, words)
and Arimo bold (town names in spaced capitals) (idea 1: 'no more than two fonts')."""
import os

from PIL import ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- colours
MAROON = (96, 20, 32)                 # the year on a card, maroon text on ivory
MAROON_GLOW, MAROON_OUT = (66, 16, 28), (22, 5, 10)   # the background: lighter in the middle, darker at the edges
MAROON_EDGE = (18, 4, 8)              # the dark end of a thin gold rule
GOLD, GOLD_SOFT = (255, 207, 107), (217, 164, 65)
GOLD_TOP, GOLD_BOTTOM = (255, 226, 150), (206, 152, 64)   # the gold gradient of every title
FOOTER_GOLD = (226, 184, 104)         # the footer line and quiet gold words
CREAM = (240, 214, 160)               # the spaced capital line under a title, light gold words
IVORY_TOP, IVORY_BOTTOM, IVORY_EDGE = (248, 242, 228), (234, 223, 200), (196, 178, 146)   # the ivory card frames
IVORY_TEXT = (250, 241, 222)          # story words on maroon
PLACE = (88, 34, 34)                  # the town on a card
JALI_COLOUR = (160, 84, 74)           # the faint carved lattice near the edges
LAMP = (132, 74, 34)                  # the soft lamp light behind the title

# ---------------------------------------------------------------- the footer line
FOOTER = 'Darpan’s Smruti Project'

# ---------------------------------------------------------------- the two fonts
SERIF, SANS = 'eb-garamond', 'arimo'


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name + '.woff2'), max(8, round(size)))


def serif(size, weight=700):   # EB Garamond 500, 600 or 700
    return font(f'eb-garamond-latin-{weight}-normal', size)


def sans(size):                # Arimo bold, for town names in spaced capitals
    return font('arimo-latin-700-normal', size)
