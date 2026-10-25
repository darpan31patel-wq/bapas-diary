"""Darpan's rules for choosing photos of Bapa, for the website (bapas-diary.com) only.

A copy of the rules in make.py, the On this day picture builder, as it was on 25 Oct 2026 (Darpan, 25 Oct 2026: the
website's Bapa pages should choose photos of Bapa the same way). It is a copy on purpose: the website never imports or
changes anything in the daily 2pm picture chain, so a change there can't break the website and the other way round.
Only the parts that judge a single photo are here: the face check, face quality, and the caption rules. What make.py
does for one picture a day (the last 7 days, the collage layout) stays there.
"""
import glob, os, re

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(HERE, 'models')
PSM_UNTIL = '2016-08-13'   # Pramukh Swami Maharaj before this date, Mahant Swami Maharaj after
SAME_PERSON = .5           # cosine similarity; strangers and murtis score below .35
_MODELS = {}


def models():
    """The face finder (YuNet), the face matcher (SFace) and Bapa's two face fingerprints, loaded once per process."""
    if not _MODELS:
        import json
        _MODELS['detect'] = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320), .6, .3, 5000)
        _MODELS['recognise'] = cv2.FaceRecognizerSF.create(os.path.join(MODELS, 'face_recognition_sface_2021dec.onnx'), '')
        _MODELS['bapa'] = {k: np.array(v) for k, v in json.load(open(os.path.join(MODELS, 'bapa-faces.json'))).items()}
    return _MODELS


def bapa_face(im, when):
    """As make.bapa_face, with need=0: Bapa's best matching face as ((x, y, w, h), similarity, front, faces found),
    the box in im's own pixels, or (None, 0, 0, faces) when the photo has no face at all."""
    m = models()
    small = im.copy(); small.thumbnail((1280, 1280))
    k = im.width / small.width
    bgr = cv2.cvtColor(np.array(small), cv2.COLOR_RGB2BGR)
    ref = m['bapa']['psm' if when < PSM_UNTIL else 'msm']
    best, best_sim, front = None, 0, 0
    m['detect'].setInputSize((bgr.shape[1], bgr.shape[0]))
    faces = m['detect'].detect(bgr)[1]
    for f in faces if faces is not None else []:
        e = m['recognise'].feature(m['recognise'].alignCrop(bgr, f))[0]
        sim = float(ref @ (e / np.linalg.norm(e)))
        if sim > best_sim:
            best, best_sim, front = tuple(float(v) * k for v in f[:4]), sim, front_view(f)
    return best, best_sim, front, 0 if faces is None else len(faces)


def front_view(f):
    """0 to 1 from the detector's landmarks: the eyes are far apart on a face seen from the front and
    close together on a profile, and the nose sits between them when he looks at the camera."""
    x, y, w, h, rx, ry, lx, ly, nx, ny = [float(v) for v in f[:10]]
    eyes = abs(lx - rx) / max(w, 1)                                 # about .45 face on, under .2 side on
    centred = 1 - min(1, abs(nx - (lx + rx) / 2) / max(abs(lx - rx) / 2, 1))
    return max(0, min(1, (eyes - .18) / .25)) * (.5 + .5 * centred)


def frame_keep(iw, ih, fa):
    """How much of the photo (0 to 1) a frame of aspect fa (width / height) keeps when it fills the frame."""
    return min(1, (ih * fa) / iw) if iw / ih > fa else min(1, (iw / fa) / ih)


# From here on, copied from make.py unchanged.

DOING = re.compile(r'arti|puja|pujan|bless|greet|shower|lights?\b|sanctif|plays?|walk|pradakshina|parikrama|reads?|offer|appl|'
                   r'address|discourse|mala|meets?|inaugurat|pratishtha|ritual|perform|bows|thal|sprinkl|writ|garland|honou?r|'
                   r'welcom|darshan|meditat|pray|arriv|visit|abhishek|lamp|tilak', re.I)
JUST_A_FACE = re.compile(r'divine|jovial|\bmood\b|^\s*(HH|Param Pujya)?\s*(Pramukh|Mahant) Swami( Maharaj)?\s*$', re.I)
# a one-off moment worth keeping as a wide shot even if Bapa comes out small in it (Darpan, 18 Oct 2026: "if it's special keep it")
SPECIAL = re.compile(r'pratishtha|inaugurat|annakut|diwali|new year|janm|jayanti|diksha|abhishek|bhumi|foundation|shilanyas|'
                     r'mahotsav|celebrat|festival|procession|rath|yagna|mahapuja|chopda|rangoli|dandiya|\braas\b|\bras\b|'
                     r'instrument|surando|drum|president|prime minister|governor|congress|minister|mayor|ambassador|'
                     r'pilgrim|on foot|airport|farewell|departs|flag|cake|balloon|boat|horse|elephant|tractor|'
                     r'cricket|football|plant|tree|cow|children|balaks?\b|kids?\b', re.I)
RARE_DAYS = 120       # a caption word seen on fewer days of the year than this marks a special moment (Darpan, 20 Oct 2026: something you don't see normally)
WORD_DAYS = {}        # word -> number of days of the year (archive/vicharan) whose captions use it, built on first use
CAPTION_STOP = {'the', 'a', 'an', 'of', 'to', 'and', 'in', 'on', 'at', 'with', 'by', 'for', 'his', 'her', 'their', 'all', 'during', 'from', 'as',
                'is', 'are', 'was', 'were', 'this', 'that', 'into', 'onto', 'over', 'under', 'after', 'before', 'while', 'he', 'him', 'its', 'it',
                'hh', 'param', 'pujya', 'pramukh', 'mahant', 'swami', 'swamishri', 'maharaj', 'bapa', 'shri', 'be', 'upon', 'new', 'day'}


def caption_words(c):
    return [w.strip("'-") for w in re.findall(r"[a-z][a-z\-']+", (c or '').lower()) if w.strip("'-") and w.strip("'-") not in CAPTION_STOP]


def word_days():
    if not WORD_DAYS:
        days = {}
        for f in sorted(glob.glob(os.path.join(HERE, 'archive', 'vicharan', '*.txt'))):
            d = os.path.basename(f)[:5]
            for line in open(f, encoding='utf-8'):
                if line.startswith('#') or '|' not in line:
                    continue
                for w in set(caption_words(line.rstrip('\n').split('|', 1)[1])):
                    days.setdefault(w, set()).add(d)
        WORD_DAYS.update({w: len(v) for w, v in days.items()} or {'': 0})
    return WORD_DAYS


def rare_caption(c):
    """True when the caption has a word that turns up on few days of the year ('expounds', 'dandiya', 'Jitatmanand'),
    so it tells of something not seen most days; 'Meditates in his daily puja' is all everyday words."""
    ws = caption_words(c)
    return bool(ws) and min(word_days().get(w, 0) for w in ws) < RARE_DAYS


def is_special(c):
    """A special moment: a festival, pratishtha, visitor (SPECIAL) or rare words, and never an everyday line."""
    c = re.sub(r'\s+', ' ', c or '').strip()
    return bool(c) and (western(c) or not EVERYDAY.search(c) and not JUST_A_FACE.search(c) and bool(SPECIAL.search(c) or rare_caption(c)))



ACTION_KEEP = .72     # an action shot must keep at least this much of the photo inside the frame, or what Bapa does gets cut off
SIDE_FRONT, SIDE_LOSS = .3, 2.5   # a face less front on than this (front_view) is a side profile, and loses up to this much as an action shot
CLOSE_MIN_FACE = 64   # pixels: a face smaller than this can't be blown up into a close darshan
SHARP_MIN, BRIGHT_MIN = 40, 70   # a face blurrier (Laplacian variance at 160px) or darker (mean luminance) than this can't be a close darshan (Darpan, 20 Oct 2026: 2009 was a dark blurry video still)


def face_quality(im, face):
    """(sharpness, brightness) of the face: how crisp it is at a fixed 160px size, and how light."""
    if not face:
        return 0, 0
    fx, fy, fw, fh = [int(v) for v in face]
    crop = im.crop((max(0, fx), max(0, fy), min(im.width, fx + fw), min(im.height, fy + fh))).convert('L')
    if crop.width < 8 or crop.height < 8:
        return 0, 0
    crop = crop.resize((160, round(160 * crop.height / crop.width)), Image.LANCZOS)
    g = np.asarray(crop, np.float32)
    lap = cv2.Laplacian(g, cv2.CV_32F)
    return float(lap.var()), float(g.mean())


STOP = {'the', 'a', 'an', 'of', 'to', 'and', 'in', 'on', 'at', 'with', 'by', 'for', 'his', 'all', 'bapa', 'during'}


def album(u):
    """The baps.org album a photo comes from ('.../GalleryImages/2776/WebImages/P1010081f.jpg' -> '2776'), None for others."""
    m = re.search(r'/GalleryImages/(\d+)/', u or '')
    return m and m.group(1)


def caption_key(c):
    """Rough word stems of a caption, so 'Greets all with folded hands' and 'Greeting all with folded hands' match."""
    words = re.findall(r"[a-z]+", c.lower())
    return {w[:5] for w in words if w not in STOP}


COMMON_VERBS = {'bless', 'perfo', 'readi', 'reads', 'greet', 'engag', 'engro', 'has', 'visit', 'arriv', 'disco',
                'medit', 'turns', 'plays', 'appli', 'offer', 'durin', 'start', 'daily', 'morni', 'eveni'}


def same_caption(a, b):
    """Near repeats count too: 'Reads the Shikshapatri' inside 'Reads the Shikshapatri and Satsang Diksha',
    'In a divine mood' inside 'In a divine, jovial mood', 'Blesses all' beside 'Blesses the assembly'."""
    if not (a and b):
        return False
    if 'mood' in a and 'mood' in b:   # 'In a divine mood', 'In a happy mood', 'In a jovial mood' are one caption (Darpan, 20 Oct 2026)
        return True
    j = len(a & b) / len(a | b)
    small, big = sorted((a, b), key=len)
    shared_things = (a & b) - COMMON_VERBS     # 'tilak' in 'applies a tilak at start of daily puja' and '... on his forehead'
    return (j >= .7 or (small <= big and (len(small) >= 2 or j >= .5))
            or (len(a & b) >= 2 and shared_things and j >= .3))



NAME = r"(?:(?:H\.?\s?H\.?|Param Pujya|P\.?\s?P\.?)\s+)?(?:Pramukh Swami(?: Maharaj)?|Mahant Swami(?: Maharaj)?|Swamishri|Bapa)"


OTHERS = r"(?:(?:Pujya|Sadguru|Shri|Param Pujya)\s+)*[A-Z][\w\-]*(?:\s+[A-Z][\w\-]*)*(?:\s+Swami)?|(?i:(?:Senior\s+)?(?:swamis|sadhus|devotees|bhaktas|children|youths|kishores|students|volunteers|karyakars|sadhaks)(?:,? (?:and|parshads|sadhaks|swamis|devotees|bhaktas)+)*)(?:\s+from\s+[\w ,]+?)?|An?\s+\w+(?:\s+from\s+[\w ,]+?)?"
ABOUT_BAPA = [   # captions about someone else and Bapa, turned round so they say what Bapa does
    (rf"^({OTHERS}) (?:honou?rs?|garlands?) Swamishri(?: with (?:a|an) ([\w ,\-]+))?$", lambda m: f"Receives {('a ' + m.group(2)) if m.group(2) else 'a garland'} from {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:greets?|welcomes?) Swamishri.*$", lambda m: f"Greets {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:presents?|offers?) (?:a |an )?[\w ,\-]*?(?:and|to) hono?u?rs? Swamishri.*$", lambda m: f"Honoured by {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) hono?u?rs? Swamishri.*$", lambda m: f"Honoured by {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) sings? (thal|kirtans?|dhun|bhajans?)$", lambda m: f"Listens to {lower_group(m.group(1))} sing {m.group(2)}"),
    (rf"^({OTHERS}) (?:offers?|presents?) (?:a |an )?prayers? (?:to|before) Swamishri$", lambda m: f"Listens to a prayer from {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) (?:prays?) before Swamishri$", lambda m: f"Listens to a prayer from {m.group(1)}"),
    (rf"^({OTHERS}) (?:doing|engrossed in|in) (?:the )?(?:unique )?(?:darshan of Swamishri|Swamishri's (?:puja )?darshan|Swamishri's puja)$", lambda m: f"Gives darshan to {lower_group(m.group(1))}"),
    (rf"^({OTHERS}) recites? (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Listens to {lower_group(m.group(1))} recite {m.group(2)}"),
    (rf"^({OTHERS}) sings? (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Listens to {lower_group(m.group(1))} sing {m.group(2)}"),
    (rf"^({OTHERS}) (plays?|sings?|swings?) (.+?) with Swamishri$", lambda m: f"{re.sub('s$', '', m.group(2)).capitalize()}s {m.group(3)} with {m.group(1)}"),
    (rf"^({OTHERS}) (?:performs?|presents?|recites?|sings?) (.+?) (?:before|in) Swamishri(?:'s [\w ]+)?$", lambda m: f"Watches {lower_group(m.group(1))} perform {m.group(2)}"),
]


def lower_group(g):
    """'Swamis' or 'A devotee' read in lower case mid sentence; names ('Pujya Kothari Swami') stay as they are."""
    return g[0].lower() + g[1:] if re.match(r'(?i)(senior |an? )?(swamis|sadhus|devotees|bhaktas|children|youths|kishores|students|volunteers|karyakars|sadhaks|devotee|bhakta|youth|child|swami|sadhak)\b', g) else g


def about_bapa(c):
    """'Pujya Kothari Swami plays dandiya with Swamishri' becomes 'Plays dandiya with Pujya Kothari Swami'."""
    for pat, fix in ABOUT_BAPA:
        m = re.match(pat, c)
        if m:
            return fix(m)
    return c


def bapa_is_subject(c):
    """False when the caption is about someone else ('Swamis sing kirtans in Swamishri's puja')."""
    c = about_bapa(re.sub(r'\s+', ' ', c or '').strip())
    return not re.search(r"\bSwamishri\b|Bapa\b", c) or bool(re.match(rf'^{NAME}', c)) or c[:1].islower()


MONTH = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?'
JUNK = re.compile(r'click here|to view|please|https?:|read more|watch (the )?video|\bvideo\b.*\bhere\b', re.I)
def tidy(c):
    """Small clean ups of the website's caption: the date (it is always this day), 'the the', Mr and Mrs."""
    c = re.sub(rf'[\s,]*(?:on |dated )?\b\d{{1,2}}(?:st|nd|rd|th)? {MONTH}(?: \d{{4}})?\s*$', '', c)   # 'Doing mala, 18 Oct 2016'
    c = re.sub(rf'[\s,]*(?:on |dated )?\b{MONTH} \d{{1,2}}(?:st|nd|rd|th)?(?:,? \d{{4}})?\s*$', '', c)   # 'on October 18, 2016'
    c = re.sub(r'\b(the|a|an|of|to|in|on|and) \1\b', r'\1', c, flags=re.I)
    c = re.sub(r'\b(?:Mr|Mrs|Ms|Dr)\.? (?=[A-Z])', '', c)
    c = re.sub(r'\b([Dd])evotee(s?)\b', lambda m: ('B' if m.group(1) == 'D' else 'b') + 'hakta' + m.group(2), c)   # satsang word (Darpan, 18 Oct 2026)
    c = re.sub(r', (?:Shri|Smt\.?|Dr\.?|Mr\.?|Mrs\.?) [^,]+(?:, [^,]+)*,', '', c)   # 'Bapa and sponsors, Shri Mayurbhai and Shri Nimeshbhai, cut the ribbon'
    if JUNK.search(c):   # website link text that was crawled as a caption
        return ''
    c = re.sub(r'\b(a) (?=[aeiouAEIOU])', r'\1n ', c)                                           # 'in a illustrious mood'
    c = re.sub(r'\b(an) (?=[^aeiouAEIOU\W])', 'a ', c)
    c = re.sub(r"^(['\u2018\u201c].+?['\u2019\u201d])\s*[-\u2013\u2014:]\s*(?:Param Pujya |Pujya |HH )?(?:Pramukh|Mahant) Swami(?: Maharaj)?\s*$", r'\1', c)   # a quote of his: the card is already his
    c = re.sub(r'\s+([,;:])\s*', r'\1 ', c)   # 'Sharad Purnima ,Chants dhun'
    return re.sub(r'\s+', ' ', c).strip(' ,;:')


ING = {'performing': 'Performs', 'blessing': 'Blesses', 'greeting': 'Greets', 'reading': 'Reads', 'writing': 'Writes', 'playing': 'Plays',
       'singing': 'Sings', 'offering': 'Offers', 'listening': 'Listens', 'watching': 'Watches', 'meeting': 'Meets', 'inaugurating': 'Inaugurates',
       'sanctifying': 'Sanctifies', 'meditating': 'Meditates', 'walking': 'Walks', 'arriving': 'Arrives', 'departing': 'Departs', 'giving': 'Gives',
       'receiving': 'Receives', 'showering': 'Showers', 'applying': 'Applies', 'lighting': 'Lights', 'explaining': 'Explains', 'discoursing': 'Discourses',
       'talking': 'Talks', 'speaking': 'Speaks', 'addressing': 'Addresses', 'enjoying': 'Enjoys', 'observing': 'Observes', 'engaged': 'Engaged'}
DARSHAN = 'Darshan'   # the caption when the website gives only his name ('Param Pujya Mahant Swami Maharaj')
CAPTIONS = 'all'      # 'all': every card captioned; 'special': only one-off moments, no 'In a divine mood'; 'none': no captions (mockups, 20 Oct 2026)


EVERYDAY = re.compile(   # the everyday lines that say nothing about that particular day, left off in 'special' mode
    r"mood|divine|jovial|^darshan$|^bless\w*( (all|everyone|bhaktas|sadhus|the assembly|after the \w+))?$|"
    r"^during (the |his )?(morning |evening |daily )?(assembly|arti|puja|sabha|satsang sabha)$|^performs (the |his )?(morning |evening |daily )?(arti|puja)$|"
    r"^(meditates|engrossed|seated) in (his )?(daily |morning )?puja|sadhana mantra|daily prayer|^(does|doing|turns the) mala|^bids jai swaminarayan|"
    r"^greets (all|everyone|bhaktas|sadhus)$|folded hands|^observes prasad$|^engaged in (letter-writing|darshan|thought)|^(reads|reading) the shikshapatri|"
    r"^in thought|^seated$|^(has|having) (lunch|dinner|breakfast|his meal)$|^arrives|^departs|^listens attentively$|"
    r"^(honou?rs|honou?red|garlands|welcomes|meets|greets|receives|is honou?red|accepts|bless\w*)\b|with a (shawl|garland)|^honou?red", re.I)   # honouring, meeting or blessing someone is not special (Darpan, 20 Oct 2026)
GUEST = re.compile(r"(?i:^(honou?rs|honou?red|garlands|welcomes|meets|receives|is honou?red|accepts)\b|with a (shawl|garland)|"
                   r"\bmeets?\b|\bmeeting\b|calls on|courtesy (call|visit))|"   # Darpan, 24 Oct 2026: 'Pujya Devprasadji Maharaj meets Bapa' too, wherever the word comes
                   r"^Blesses (?:Shri |Smt\.? |Dr\.? |Mr\.? |Mrs\.? |H\.?E\.? )?[A-Z][a-z]+(?:bhai|ben|ji| [A-Z][a-z]+)")   # 'Blesses Shri Yashwantbhai Shah': a named guest   # guest photos lose when every year is a close up


# Darpan, 24 Oct 2026: "i dont like 'meeting other people' unless they are 'western' person, as bapa meets people all the time".
# A western guest is told by a title or a country (Mayor, Congressman, Mr Paul Mashatile, Australian Prime Minister), and never
# when the guest has an Indian name or post (Shri, Pujya, bhai, 'Consul General of India').
WESTERN = re.compile(r"\b(Mr|Mrs|Ms|Miss|Sir|Lady|Baroness|Baron|Rabbi|Rev|Reverend|Father|Bishop|Archbishop|Cardinal|Pope|Imam|Mayor|"
                     r"Senator|Congress(?:man|woman)|Ambassador|Consul|Councillor|Council\s?member|Sheriff|Prince|Princess|King|Queen|"
                     r"MP|MLA|Hon|Rt|Lord(?! (?:Swaminarayan|Harikrishna|Krishna|Rama?|Shiva|Ganesh|Hanuman))|"
                     r"American|British|English|Canadian|Australian|Israeli|European|French|German|Italian|Dutch|Swiss|Irish|Scottish|Welsh|Christian|Jewish|"
                     r"U\.?S\.? (?:Senator|Congress\w*)|(?:Prime Minister|President|Premier) of [A-Z]\w*)\b")
INDIAN = re.compile(r"\b(Shri|Smt|Pujya|P\.P\.|Sant|Swami\w*|Maharaj|Bapu|Muni|Mufti|Mahant|Acharya|Guru|Sadhus?|Kothari|"
                    r"of India|Indian|India's|Gujarat|Patel|Shah|Desai|Mehta|Kumar|Singh|Sharma|Kapoor|Joshi|Trivedi|Pandya|Amin|Modi|Gandhi|Nagarpalika|Panchayat|Samaj|Mandal|Sangh|Sabha)\b|"
                    r"\w+(bhai|ben|ji|das|lal|chand|nath|prasad|anand|aran)\b", re.I)


def western(c):
    """True when the caption is about meeting or honouring a western guest, which stays special (Darpan, 24 Oct 2026)."""
    c = re.sub(r'\s+', ' ', c or '').strip()
    return bool(GUEST.search(c) and WESTERN.search(c) and not INDIAN.search(re.sub(NAME, '', re.sub(r'\bBapa\b', '', c))))


def range_title(c):
    """An album's own heading that baps.org lists as a photo's caption ('Gondal 22 to 24 October 2007 -',
    'Bochasan21 to 29 July 2009 -', '1 to 9 November 2004 -'): returns its place ('' when it has none), or None
    for a real caption. Darpan, 22 Oct 2026: 'Gondal 22 to 24 October 2007 -' showed under a card saying MUMBAI."""
    m = re.fullmatch(rf'\s*([A-Za-z][A-Za-z .]*?)?\s*\d{{1,2}}(?:st|nd|rd|th)?(?: {MONTH})? (?:to|-|–) \d{{1,2}}(?:st|nd|rd|th)? {MONTH},? \d{{4}}\s*[-–]?\s*', c or '')
    return (m.group(1) or '').strip() if m else None


def caption(x):
    """The caption without the name repeated on every card: 'Swamishri blesses all' becomes 'Blesses all'.
    Where dropping the name wouldn't read well ('Swamishri's divine gestures', 'Sadhus honour Swamishri'),
    the name becomes 'Bapa'."""
    if range_title(x.get('c')) is not None:   # only the album's dates: the card is a darshan
        return DARSHAN
    c = tidy(re.sub(r'\s+', ' ', x.get('c') or '').strip())
    if not c or re.fullmatch(rf'(?:Pujya |Shri )?{NAME}(?: Maharaj)?', c):
        return DARSHAN if x.get('c') else ''
    c = about_bapa(c)
    m = re.match(rf'^{NAME}[\s,]+(.+)$', c)
    if m and not re.match(r"(and|with|along|together|'s|’s)\b", m.group(1), re.I):
        c = m.group(1)[0].upper() + m.group(1)[1:]
    c = re.sub(NAME, 'Bapa', c)
    w = c.split(' ', 1)
    if w[0].lower() in ING and len(w) > 1:   # 'Performing sanctifying rituals' reads like the other cards: 'Performs sanctifying rituals'
        c = ING[w[0].lower()] + ' ' + w[1]
    return c


