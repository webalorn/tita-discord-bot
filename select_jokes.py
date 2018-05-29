import random, json

wrongWords = ['sex', 'dick', 'fuck', 'ass', 'ejacul', 'porn', 'nsfw', 'anus', 'felch', 'cum', 'cunt', 'tit', 'gay', 'lesbian', 'homosex', 'heterosex',
'**', 'blowjob', 'condom', 'abortion', 'mistress', 'monogamy', 'lgbt', 'pedo', 'pee', 'butt', 'sbake', 'pants', '69', 'strip', 'lick', 'shit', 'bitch', 'manhoob']
max_jokes = 2000

with open('jokes_all.json') as f:
    jokes = json.load(f)

jokes = list(filter(lambda b: len([w for w in wrongWords if (w in b['title'].lower() or w in b['body'].lower())]) == 0, jokes))

print(jokes[0])
random.shuffle(jokes)
print(jokes[0])

jokes = jokes[:max_jokes]

with open('jokes.json', 'w') as f:
    json.dump(jokes, f)