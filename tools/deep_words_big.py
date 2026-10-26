"""The wide word list (Darpan, 26 Oct 2026: "type in anything": grass, blue flowers, plane, football found nothing).
Short prompts, the way photos are described on the web, which the SigLIP 2 model scores most reliably.
Website only; tools/deep_tags.py checks each word's bar before it is used (BIG_KEEP in tools/deep_words.py).
"""

def a(x):
    return f'a photo of {x}'

GROUPS = {
    'nature': ['grass', 'green grass lawn', 'trees', 'palm trees', 'a big banyan tree', 'leaves', 'flowers', 'sky', 'blue sky',
               'clouds', 'sunset', 'sunrise', 'the moon', 'stars at night', 'the sea', 'a beach', 'waves', 'a river', 'a lake',
               'a pond', 'a waterfall', 'mountains', 'hills', 'snow', 'ice', 'a desert', 'sand', 'a forest', 'farm fields',
               'crops', 'rain', 'fog', 'a rainbow', 'rocks', 'a cave', 'an island', 'a garden', 'a park', 'bushes', 'bamboo'],
    'flowers': ['red flowers', 'blue flowers', 'yellow flowers', 'white flowers', 'pink flowers', 'purple flowers',
                'orange flowers', 'marigolds', 'roses', 'red roses', 'lotus flowers', 'sunflowers', 'jasmine', 'orchids',
                'tulips', 'lilies', 'a bouquet of flowers', 'flower petals', 'a flower garland', 'a flower carpet',
                'a flower decoration', 'a vase of flowers', 'a flower rangoli'],
    'animals': ['animals', 'a cow', 'a bull', 'a calf', 'an elephant', 'a horse', 'a camel', 'a dog', 'a puppy', 'a cat',
                'a monkey', 'a peacock', 'a parrot', 'pigeons', 'birds', 'a swan', 'ducks', 'a deer', 'a lion', 'a tiger',
                'fish', 'a butterfly', 'a goat', 'sheep', 'a donkey', 'a snake', 'a squirrel', 'a rabbit', 'a tortoise',
                'a giraffe', 'a zebra', 'a kangaroo', 'a crocodile', 'a bear', 'a hen'],
    'vehicles': ['a plane', 'an aeroplane cabin', 'an airport', 'a helicopter', 'a car', 'a bus', 'a train', 'a railway station',
                 'a boat', 'a ship', 'a bicycle', 'a motorbike', 'a scooter', 'an auto rickshaw', 'a tractor', 'a truck',
                 'a golf cart', 'a bullock cart', 'a horse carriage', 'a chariot', 'a decorated float', 'a jeep',
                 'a van', 'a wheelchair', 'a traffic road', 'a hot air balloon'],
    'sports': ['football', 'a football match', 'cricket', 'a cricket bat', 'volleyball', 'basketball', 'badminton',
               'table tennis', 'tennis', 'kabaddi', 'a running race', 'swimming', 'a swimming pool', 'yoga', 'exercise',
               'a gym', 'a sports stadium', 'a trophy', 'medals', 'a tug of war', 'skating', 'chess', 'kho kho',
               'children playing games', 'a playground', 'a ball'],
    'objects': ['a microphone', 'a book', 'books', 'a pen', 'a letter', 'spectacles', 'an umbrella', 'a flag', 'flags',
                'balloons', 'a kite', 'a lamp', 'candles', 'oil lamps', 'a cake', 'a clock', 'a mobile phone', 'a laptop',
                'a computer', 'a camera', 'a television', 'a big screen', 'a projector', 'a chair', 'a sofa', 'a throne',
                'a swing', 'a bed', 'a table', 'a cushion', 'a crown', 'a shawl', 'a turban', 'a prayer mala',
                'a conch shell', 'a bell', 'drums', 'a harmonium', 'a tabla', 'a sitar', 'a flute', 'a guitar',
                'a keyboard piano', 'a certificate', 'a map', 'a globe', 'a model of a building', 'a painting',
                'a photo frame', 'a poster', 'a banner', 'a statue', 'a fountain', 'a chandelier', 'curtains', 'a carpet',
                'a red carpet', 'a rangoli', 'a clay pot', 'a coconut', 'a basket', 'a gift box', 'a ribbon', 'scissors',
                'a plaque', 'a foundation stone', 'a shovel', 'bricks', 'a crane', 'a ladder', 'a rope', 'a fan',
                'an air conditioner', 'a mirror', 'a door', 'a window', 'a gate', 'an arch', 'pillars', 'a dome',
                'a staircase', 'a balcony', 'a railing', 'a tent', 'a canopy', 'lights', 'fairy lights', 'fireworks',
                'a bonfire', 'a sacred fire', 'smoke', 'water', 'a water bottle', 'a glass of water', 'a cup of tea',
                'a plate', 'a bowl', 'a spoon', 'a tray', 'a silver plate', 'a gold ornament', 'jewellery', 'a necklace',
                'a watch', 'a bag', 'a suitcase', 'a newspaper', 'a magazine', 'a calendar', 'a sign board', 'a name board',
                'a stethoscope', 'medicine', 'a hospital bed', 'a walking stick', 'a fan of peacock feathers', 'a chamar fan',
                'an idol', 'a small murti', 'murtis in a shrine', 'a footprint', 'a tilak mark', 'a sandalwood paste',
                'a scroll', 'a manuscript', 'a pot of water', 'a kalash', 'a lamp stand', 'incense sticks'],
    'food': ['food', 'Indian food', 'a thali meal', 'sweets', 'Indian sweets', 'laddoos', 'fruit', 'mangoes', 'bananas',
             'apples', 'grapes', 'oranges', 'a pineapple', 'a watermelon', 'vegetables', 'rice', 'chapati bread', 'samosas',
             'snacks', 'ice cream', 'a birthday cake', 'milk', 'tea', 'juice', 'nuts', 'dry fruits', 'chocolates',
             'biscuits', 'a food offering', 'cooking', 'a kitchen', 'people serving food', 'people eating a meal'],
    'places': ['an airport', 'a hospital', 'a school', 'a classroom', 'a college', 'a university', 'a stadium',
               'an auditorium', 'an office', 'a meeting room', 'a library', 'a museum', 'an exhibition', 'a street',
               'a market', 'a shop', 'a village', 'a city', 'a city skyline', 'skyscrapers', 'a bridge', 'a temple',
               'a Hindu temple', 'a temple at night', 'the inside of a temple', 'a temple shrine', 'a courtyard',
               'a marble floor', 'a rooftop', 'a terrace', 'a construction site', 'a factory', 'a farm', 'a house',
               'a hut', 'a palace', 'a fort', 'a church', 'a mosque', 'a parliament building', 'a government building',
               'a hotel', 'a restaurant', 'a big hall', 'a stage', 'a decorated stage', 'a big tent', 'a parking lot',
               'a corridor', 'a lift', 'a garden path', 'a monument', 'a tower', 'a statue on a pedestal'],
    'people': ['children', 'a baby', 'young boys', 'young men', 'teenagers', 'women', 'girls', 'an old man', 'a family',
               'a crowd', 'a huge crowd', 'an audience', 'monks', 'saints in saffron robes', 'volunteers', 'police',
               'soldiers', 'a doctor', 'nurses', 'musicians', 'singers', 'dancers', 'actors', 'students', 'a politician',
               'a man in a suit', 'foreign visitors', 'western visitors', 'a group photo', 'people in white clothes',
               'people wearing turbans', 'people wearing masks', 'people in traditional costumes'],
    'actions': ['smiling', 'laughing', 'walking', 'sitting', 'standing', 'sleeping', 'eating', 'drinking', 'reading',
                'writing', 'speaking', 'giving a speech', 'praying', 'clapping', 'waving', 'blessing', 'hugging',
                'dancing', 'singing', 'playing music', 'playing', 'cooking', 'serving food', 'cutting a cake',
                'cutting a ribbon', 'lighting a lamp', 'pouring water', 'throwing flowers', 'putting a garland',
                'bowing', 'touching feet', 'shaking hands', 'taking a photo', 'signing a document', 'looking at a map',
                'looking through a window', 'pointing', 'thinking', 'listening', 'meditating', 'crying', 'celebrating',
                'greeting with folded hands', 'giving a gift', 'receiving a gift', 'climbing stairs', 'getting into a car',
                'getting off a plane', 'riding', 'swimming', 'running', 'jumping', 'marching', 'a procession',
                'a parade', 'a ceremony', 'a wedding', 'a birthday celebration', 'a meeting', 'a discussion',
                'an interview', 'a press conference', 'a rally', 'a gathering', 'a celebration'],
    'colours': ['red', 'blue', 'green', 'yellow', 'pink', 'purple', 'white', 'black', 'golden', 'silver', 'orange',
                'colourful', 'black and white', 'saffron'],
    'time': ['night', 'evening', 'morning', 'daytime', 'indoors', 'outdoors', 'lit up at night', 'in the dark',
             'a sunny day', 'a rainy day', 'winter', 'summer'],
}

BIG = {}
for g, xs in GROUPS.items():
    for x in xs:
        word = x
        for art in ('a ', 'an ', 'the '):
            if word.startswith(art):
                word = word[len(art):]
        if g == 'colours':
            prompt = f'a photo where the main colour is {x}'
        elif g in ('actions',):
            prompt = f'a photo of people {x}' if not x.startswith('a ') else a(x)
        else:
            prompt = a(x)
        BIG.setdefault(word, prompt)
