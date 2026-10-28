"""Who was with Bapa (Darpan, 26 Oct 2026: "search by people's names, do it"). Finds the people named in the baps.org
photo captions, so the search bar can find a swami, a leader or a devotee by name, with a forgiving spelling.

    python tools/search_people.py --db bapas.db --out search/data/people.json

No AI: the names are read from the captions with a few plain rules.
  swamis      "Pujya Viveksagar Swami", "Sadguru Ishwarcharandas Swami"  ->  Viveksagar Swami, Ishwarcharan Swami
  with a title "Shri Vijaybhai Rupani", "Dr. APJ Abdul Kalam", "Prime Minister Justin Trudeau", "HE Paul Mashatile"
  bhai names  "Bhupendrabhai Patel"
Bhagwan, the gurus, the murtis, the paramhansas of Shriji Maharaj's time and the names of mandirs, festivals and halls
are not people here. Spellings of one person are joined (Raghabhai Bharvad, Ragha Bharwad, Raghu Bharwad;
Ishwarcharandas Swami, Ishwarcharan Swami; Dr. Kalam, Dr. APJ Abdul Kalam) and every spelling is kept, so each one
finds the photos.

Writes [[name, kind, [spellings, lower case], photos with Bapa, days with Bapa, first day, last day], ...], the most
photos first. kind: s a swami, p anyone else. Used by site/search-people.js.
"""
import argparse, collections, json, re, sqlite3

TITLE = (r"Shri|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Hon\.?|Honourable|Honorable|Smt\.?|Prof\.?|Sheikh|H\.\s?E\.|HE|HH|Sir|Lady|Dame|Justice"
         r"|Prime Minister|Chief Minister|Deputy Chief Minister|Minister|Governor|President|Vice President|Mayor|Ambassador"
         r"|High Commissioner|Senator|Congressman|Congresswoman|Assemblyman|Premier|King|Queen|Prince|Princess|Pujya|Mahant|Acharya")
WORD = r"(?:[A-Z]\.\s?){1,3}|[A-Z][a-zA-Z'\-]+"
TITLED = re.compile(rf"\b((?:{TITLE})\s+)((?:(?:{WORD})\s){{0,4}}(?:{WORD}))")
BHAI = re.compile(r"\b([A-Z][a-z]+bhai(?:\s[A-Z][a-z]{2,})?)\b")
SWAMI = re.compile(r"\b([A-Z][a-z]{2,})\s+(?:Swami|Sawmi|Swamy)(?:ji)?\b(?!\s+Maharaj|narayan)")
HONOUR = {'pujya', 'param', 'sadguru', 'shri', 'brahmaswarup', 'pragat', 'his', 'holiness', 'hh', 'aksharbrahma', 'aksharbrahman',
          'aksharmukta', 'and', 'the', 'with', 'by', 'of', 'senior', 'other', 'all', 'hon', 'honourable', 'honorable', 'dr', 'mr', 'mrs',
          'ms', 'smt', 'prof', 'sheikh', 'he', 'h.e', 'sir', 'justice', 'prime', 'chief', 'deputy', 'minister', 'governor', 'president',
          'vice', 'mayor', 'ambassador', 'high', 'commissioner', 'senator', 'congressman', 'congresswoman', 'assemblyman', 'premier',
          'king', 'queen', 'prince', 'princess', 'lady', 'dame', 'acharya', 'mahant', 'former', 'union', 'state', 'consul', 'general',
          'mp', 'mla', 'leader', 'rt', 'judge'}

# not a person: Bhagwan and the murtis, the gurus, places, events and things
NOT = set('''mandir mandirs dev devji bhagwan varni varninath dharmakul parampara guru smruti jayanti celebration celebrations mahayaag mahayag
mahayagna yagna yagya vidyamandir sukhshaiya shaiya deri dham charitra nagar sarovar tower akshardham haveli dwar janmotsav janmashtami
mahadev abhishek murti murtis mandap prarthana ceremony hall school college university hospital sabha assembly festival day din bhavan
road airport centre center complex kendra sanstha trust society award awards book granth utsav mahotsav parayan katha pujan samaiyo
shibir satsang vachanamrut swaminarayan harikrishna ghanshyam gunatitanand gopalanand nilkanth nilkanthvarni radha krishna radhaji sitaji
sita ram rama ramji hanumanji hanuman ganeshji ganapatiji ganesh shiva shiv shankar parvati parvatiji lakshmi laxmi laxminarayan
lakshminarayan gopinath gopinathji govind radharaman jagannath jagannathji jaganath venkateshwar balaji ayyappaji padmavatiji subhadraji
balbhadraji kartikeyaji lakshmanji shrinivas suryanarayan sarveshwar siddheshwar jabreshwar ranchhodrai dharmadev bhaktimata vasudevnarayan
sahajanand shriji bhagatji shastriji yogiji pramukh mahant swamishri maharaj's swami's thakorji akshar purushottam akshar-purushottam
mahavirswami gurus samadhi nagar' street park stadium ground grounds city state county district village temple church mosque museum
house palace office parliament senate council committee department ministry government foundation institute library hotel conference
summit expo exhibition gallery pavilion gate shikhar dome kalash prasad annakut diwali holi navratri uttarayan pratishtha shilanyas
murti-pratishtha mahapuja puja arti aarti kirtan bhajan ghat kund lake river sea beach island mount hill hills temple-like vishwashanti
vishwa shanti swaminarayan's mandir's yagnapurush jayanti's tapomurti nilkanthvarni bhagwan's balprakash bal yuva mahila seva sevak
sevaks volunteers karyakar karyakars devotees youths children balaks balikas kishores kishoris saints sadhus swamis parva
ministers leaders guests dignitaries officials members trustees chowk bethak samaj radhikaji ganpatiji lakshmiji harikrishana
harirkishna harirkrishna jabareshwar upasana puraskar sansthan gaushala jinalay bhaktaratno swaminaryan iskcon mataji vitthal-rukmaniji
ranchhodji vasudevji vasudev dharmadevji gopalanandji bhagatiji maha shree
'''.split())
# people of Shriji Maharaj's time (paintings and murtis), not people who met Bapa
OLD = {'jiva khachar', 'dada khachar', 'mukund brahmachari', 'mulji brahmachari', 'jaga bhakta', 'pragji bhakta', 'popat bhabha',
       'lalji maharaj', 'raghuvirji maharaj', 'ayodhyaprasadji maharaj', 'haka bapu', 'diwan saheb', 'bapu gokhale', 'jaga swami',
       'gunatitanand swami', 'gopalanand swami', 'muktanand swami', 'brahmanand swami', 'premanand swami', 'nishkulanand swami',
       'nityanand swami', 'swayamprakashanand swami', 'bhumanand swami', 'vyapkanand swami', 'devanand swami', 'sahajanand swami',
       'ramanand swami', 'mahant swami', 'pramukh swami', 'yogi swami', 'shastri swami', 'krishna swami', 'bhagatji swami',
       'balmukund swami'}
# one person, written in ways the rules cannot join: spelling -> the name they are shown by
SAME = {'prime minister modi': 'Narendra Modi', 'narendrabhai modi': 'Narendra Modi', 'charles iii': 'King Charles',
        'raghabhai': 'Ragha Bharwad', 'raghu bharwad': 'Ragha Bharwad', 'lalkrishna advani': 'L.K. Advani', 'sheikh nahayan': 'Nahyan Mabarak Al Nahyan',
        'c.p. radhakrishnan': 'C.P. Radhakrishna', 'pierre poilievre leader': 'Pierre Poilievre', 'sharad arvind bobade': 'Sharad Arvind Bobde',
        'henry j. hyde': 'Henry Hyde', 'atmarpit nemiji': 'Atmaprit Nemiji', 'harirkishna maharaj': None}
# swamis known by a title, kept as they are
TITLED_SWAMI = {'doctor', 'kothari', 'jeer', 'jeeyar', 'chinna'}


def sound(s):
    """A spelling key, so Bharwad and Bharvad, Vinubhai and Vinu, Tyagvallabhdas and Tyagvallabh look alike."""
    s = re.sub(r"[^a-z]", '', s.lower())
    for a, b in (('w', 'v'), ('ph', 'f'), ('sh', 's'), ('kh', 'k'), ('gh', 'g'), ('th', 't'), ('dh', 'd'), ('bh', 'b'), ('ch', 'c'),
                 ('jh', 'j'), ('ee', 'i'), ('oo', 'u'), ('aa', 'a'), ('y', 'i'), ('z', 'j'), ('q', 'k')):
        s = s.replace(a, b)
    return re.sub(r'(.)\1+', r'\1', s)


def near(a, b):
    """at most one letter different (left out, added or changed)"""
    if abs(len(a) - len(b)) > 1:
        return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return a[i + 1:] == b[i + 1:] or a[i + 1:] == b[i:] or a[i:] == b[i + 1:]


def clean(name):
    name = re.sub(r"'s$", '', name.strip(" .,'"))
    name = re.sub(r"\b([A-Z])\.\s?(?=[A-Z]\b|[A-Z]\.)", r'\1.', name)    # L. K. Advani -> L.K. Advani
    words = name.split()
    while words and words[0].lower().strip('.') in HONOUR:
        words.pop(0)
    while words and words[-1].lower() in HONOUR:
        words.pop()
    return ' '.join(words)


def is_person(name):
    words = name.split()
    if not words or any(w.lower().strip(".'") in NOT for w in words) or name.lower() in OLD:
        return False
    if any(p in NOT for w in words for p in w.lower().split('-')):
        return False
    return not all(len(w.strip('.')) <= 1 for w in words)


def names_in(cap):
    """(name, kind) for each person a caption names"""
    out = []
    for m in SWAMI.finditer(cap):
        stem = m.group(1)
        if stem.lower() in HONOUR or stem.lower() in NOT or stem.endswith('anand') and stem.lower() not in TITLED_SWAMI:
            continue
        if stem.endswith('das') and len(stem) > 6:
            stem = stem[:-3]
        name = stem + ' Swami'
        if name.lower() not in OLD:
            out.append((name, 's'))
    for m in TITLED.finditer(cap):
        name = clean(m.group(2))
        if {'Swami', 'Swamiji', 'Sawmi', 'Swamy'} & set(name.split()) or not is_person(name):
            continue
        if len(name.split()) == 1 and not name.endswith(('ji', 'bhai')):
            # one word after a title: keep the title, so it reads as it does in the caption (Prince Charles, Dr. Kalam)
            title = clean_title(m.group(0)[:m.start(2) - m.start(0)])
            if not title:
                continue
            name = title + ' ' + name
        out.append((name, 'p'))
    for m in BHAI.finditer(cap):
        name = clean(m.group(1))
        if is_person(name):
            out.append((name, 'p'))
    return list(dict.fromkeys(out))


def clean_title(t):
    """the last title before a one word name: 'Hon. Prime Minister ' -> 'Prime Minister'"""
    t = ' '.join(t.split())
    m = re.search(r"(Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Prof\.?|Sheikh|Sir|Lady|Prime Minister|Chief Minister|President|Governor|Mayor|Senator|"
                  r"Premier|King|Queen|Prince|Princess|Ambassador)$", t)
    if not m:
        return ''
    t = m.group(1)
    return t + '.' if t in ('Dr', 'Mr', 'Mrs', 'Ms', 'Prof') else t


def key_words(name):
    """sound keys of a name's words, without the bhai, ji and das endings and without titles"""
    ws = []
    for w in name.replace('-', ' ').split():
        if w.lower().strip('.') in HONOUR or w.lower() in ('swami', 'maharaj'):
            continue
        w = re.sub(r'(bhai|ben|ji|das)$', '', w) if len(w) > 6 else w
        if w:
            ws.append(sound(w))
    return ws


def join(counts, kind):
    """join the spellings of one person; the most used spelling names them"""
    groups = []   # [names, keys, kind]
    singles = []
    for name, n in sorted(counts.items(), key=lambda x: (-len(key_words(x[0])), -x[1])):
        k = key_words(name)
        if not k:
            continue
        home = None
        for g in groups:
            gk = g[1]
            if g[2] != kind[name]:
                continue
            if k == gk:
                home = g
            elif len(k) == len(gk) > 1 and k[-1] == gk[-1] and len(k[-1]) >= 5 and all(a == b or (len(a) >= 5 and near(a, b)) for a, b in zip(k, gk)):
                home = g       # Ragha Bharvad, Raghu Bharwad
            elif len(k) < len(gk) and len(k) >= 2 and (k == gk[-len(k):] or k == gk[:len(k)]):
                home = g       # Abdul Kalam -> APJ Abdul Kalam, Dhirubhai Nanji -> Dhirubhai Nanji Mehta
            elif len(k) == len(gk) == 1 and len(k[0]) >= 7 and near(k[0], gk[0]):
                home = g       # Viveksagar, Vieksagar
            if home:
                break
        if home:
            home[0].append(name)
        elif len(k) == 1 and kind[name] == 'p':
            singles.append((name, k[0]))
        else:
            groups.append([[name], k, kind[name]])
    # one word only (Dr. Kalam, Raghabhai): joined to the one full name it can belong to, by surname or by first name
    for name, k in singles:
        fits = [g for g in groups if g[2] == 'p' and len(g[1]) > 1 and g[1][0 if name.endswith('bhai') else -1] == k]
        if len(fits) == 1 and len(k) >= 4:
            fits[0][0].append(name)
        else:
            groups.append([[name], [k], 'p'])
    groups = [g[0] for g in groups]
    for spelling, to in SAME.items():
        a = next((g for g in groups if any(n.lower() == spelling for n in g)), None)
        b = next((g for g in groups if any(n.lower() == (to or '').lower() for n in g)), None)
        if a and b and a is not b:
            b += a
            groups.remove(a)
        elif a and to and not b:
            a.append(to)
    return groups


def spellings(names, kind):
    out = set()
    for n in names:
        low = n.lower()
        out.add(low)
        if ' ' in low:
            out.add(re.sub(r'\b(\w{3,}?)bhai\b', r'\1', low))                  # Narendrabhai Modi -> narendra modi
        if kind == 's':
            stem = low[:-6]
            out.add(stem + 'das swami')
        else:
            out.add(re.sub(r'^(dr\.|mr\.|mrs\.|ms\.|prof\.|sheikh|sir|prime minister|chief minister|president|governor|mayor) ', '', low))
    return sorted(s for s in out if len(s) >= 4)


def people(db):
    rows = [(d, bapa, names_in(cap)) for d, cap, bapa in
            db.execute("SELECT coalesce(date, date_from), caption, is_bapa FROM photos WHERE caption != ''")]
    counts, kind = collections.Counter(), {}
    for d, bapa, found in rows:
        for name, k in found:
            counts[name] += 1
            kind[name] = k
    group = {}
    groups = join(counts, kind)
    for i, names in enumerate(groups):
        for n in names:
            group[n] = i
    photos, days = collections.Counter(), collections.defaultdict(set)
    for d, bapa, found in rows:
        if bapa == 1 and d:
            for i in {group[n] for n, k in found if n in group}:
                photos[i] += 1
                days[i].add(d)
    people = []
    for i, names in enumerate(groups):
        if not photos[i]:
            continue
        shown = [SAME[n.lower()] for n in names if SAME.get(n.lower())]
        name = shown[0] if shown else max(names, key=lambda x: (counts[x], len(x)))
        k = kind.get(name, 'p')
        people.append([name, k, spellings(names, k), photos[i], len(days[i]), min(days[i]), max(days[i])])
    # a spelling two people share, or a lone word that is part of another person's name (Modi: Narendra Modi and
    # Purnesh Modi), finds neither of them
    seen = collections.Counter(sp for p in people for sp in set(p[2]))
    words = collections.Counter(w for p in people for sp in set(p[2]) if ' ' in sp for w in set(sp.split()))
    for p in people:
        own = {w for sp in p[2] if ' ' in sp for w in sp.split()}
        p[2] = [sp for sp in p[2] if seen[sp] == 1 and (' ' in sp or words[sp] == (1 if sp in own else 0))] or p[2][:1]
    people.sort(key=lambda p: (-p[3], p[0]))
    return people


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default='bapas.db')
    ap.add_argument('--out', default='search/data/people.json')
    a = ap.parse_args()
    found = people(sqlite3.connect(a.db))
    with open(a.out, 'w', encoding='utf-8') as f:
        json.dump(found, f, ensure_ascii=False, separators=(',', ':'))
    print(len(found), 'people ->', a.out)


if __name__ == '__main__':
    main()
