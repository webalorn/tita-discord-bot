import random, re, os, json, copy, time
import html.parser
import asyncio
import aiohttp
import discord
from discord import Game
from discord.ext.commands import Bot

BOT_PREFIX = ("!")
keywords_delay = 1
before_contest = 60*60*2
everyone_admin = False

client = Bot(command_prefix=BOT_PREFIX)

config_file = 'config.json'
config = {}

musicChannel = None
musicPlayer = None


##### FUNCTIONS #####

async def fakeCommand(initialMessage, command):
    command = str(command).strip()
    if not command[:1] == "!":
        return await client.send_message(initialMessage.channel, command)
    fakeMessage = copy.deepcopy(initialMessage)
    fakeMessage.content = command
    fakeMessage.mentions = []
    fakeMessage.mention_everyone = False
    return await client.process_commands(fakeMessage)

def youtube_url_validation(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        return True
    return False

async def getJsonOf(*p, **pn):
    async with aiohttp.get(*p, **pn) as r:
        if r.status == 200:
            return await r.json()

def save_config():
    with open(config_file, 'w') as f:
        json.dump(config, f)

def stopMusicPlayer():
    global musicPlayer
    if musicPlayer:
        musicPlayer.stop()
    musicPlayer = None

async def muteBots(state=True):
    for name in ['AdrienBot']:
        user = getUserByName(name)
        if user:
            await client.server_voice_state(user, mute=state)

async def quit_music_if_needed():
    global musicChannel, musicPlayer
    if musicChannel and not musicPlayer:
        await musicChannel.disconnect()
        musicChannel = None
        await muteBots(False)

async def playYoutubeMusic(url, channels):
    global musicChannel, musicPlayer

    if discord.opus.is_loaded() and not musicPlayer:
        stopMusicPlayer()

        choosen = None if not musicChannel else musicChannel

        if not choosen:
            for channel in channels:
                if len(channel.voice_members):
                    choosen = channel
                    break

        if choosen:
            if not musicChannel:
                musicChannel = await client.join_voice_channel(choosen)
            musicPlayer = True
            musicPlayer = await musicChannel.create_ytdl_player(url, after=stopMusicPlayer)
            musicPlayer.start()
            await muteBots()

def commandAdmin(*p, **pn):
    pn['pass_context'] = True
    def decorated(func):
        async def wrapper(context, *args, **kwargs):
            if not context.message.author.id in config['admins'] and not everyone_admin:
                return await client.say("Oserais-tu te croire supérieur a moi, humain ?")
            return await func(context, *args, **kwargs)
        return client.command(*p, **pn)(wrapper)
    return decorated

def getRandomSentence(category):
    if category in config['random'] and len(config['random'][category]):
        return random.choice(config['random'][category])
    return "J'en reste sans voix :-*"

def getUserByName(user_name):
    for server in client.servers:
        for user in server.members:
            if user.name == user_name:
                return user

async def bot_say(random_category, *p, **pn):
    return await client.say(getRandomSentence(random_category).format(*p, **pn))

async def bot_send(channel, random_category, *p, **pn):
    return await client.send_message(channel, getRandomSentence(random_category).format(*p, **pn))

# Jokes

class JokesDb:
    def __init__ (self):
        with open('jokes.json') as f:
            self.jokes = json.load(f)

    async def say(self):
        jokes = random.choice(self.jokes)
        await client.say('**{0}**'.format(jokes['title']))
        await client.say('*"{0}"*'.format(jokes['body']))

jokes = JokesDb()

##### COMMANDS #####

# Music

@client.command(name='add-music', aliases=['add'], pass_context=True,
                brief="Add music", description="Add a music from youtube url")
async def addMusic(context, songname, url):
    if not re.match(r'^[a-zA-Z_0-9]+$', songname):
        return await client.say('Un tel nom n\'est pas concevable, humain, même si cela dépasse ton entendement')
    if not youtube_url_validation(url):
        return await client.say('Humain, je ne me fait pas avoir aussi facilement')
    if songname in config['music']:
        return await client.say('J\'ai déjà une longeur d\'avance !')

    config['music'][songname] = {
        'user': context.message.author.mention,
        'url': url,
    }
    save_config()
    await client.say("Je dispose maintenant de l'arsenal musical {0} !".format(songname))

@client.command(name='play-music', aliases=['play'], pass_context=True,
                brief="Play music", description="Play a music added with add-music command")
async def playMusic(context, songname):
    if not songname in config['music']:
        return await client.say("Stupide humain, cette musique n'existe pas !")
    await playYoutubeMusic(config['music'][songname]['url'], context.message.server.channels)

@client.command(name='stop-music', aliases=['stop'])
async def stopMusic():
    stopMusicPlayer()

@client.command(name='list-musics')
async def list_musics():
    await client.say("Voici toute ma puissance musicale: " + ", ".join("**{0}**".format(m) for m in config['music'].keys()))

# Simple actions

@client.command()
async def say(text):
    await client.say(text)

@client.command(name='send-to', brief="Send message to channel")
async def sendTo(channel_id, message):
    await client.send_message(discord.Object(id=channel_id), message)

@client.command(name='image')
async def sendImage(url):
    image = discord.Embed(colour=0xFF0000)
    image.set_image(url=url)
    await client.say(embed=image)

@client.command(name='lost', pass_context=True)
async def sendYouLost(context):
    mentions = [u.mention for u in context.message.mentions] or [context.message.author.mention]
    if context.message.mention_everyone:
        mentions = ['@everyone']
    await bot_say('bot_lost', ", ".join(mentions))

# Keywords

@client.command(name='add-keyword', aliases=['match'])
async def addKeyword(keyword, command):
    keyword = str(keyword).lower()
    if keyword in config['aliases']:
        return await client.say("Je le sais déjà, stupide humain")
    if not keyword in config['keywords']:
        config['keywords'][keyword] = []

    config['keywords'][keyword].append(command)
    save_config()
    await client.say('Je serais bientot plus reactif a tout les {0}'.format(keyword))

@client.command(name='list-keywords', aliases=['list-match'])
async def listKeywords(category=None):
    if not category:
        await client.say('Je connais le sens absolu de: {0}'.format(", ".join("**{0}**".format(m) for m in config['keywords'].keys())))
    else:
        if category in config['keywords']:
            await client.say('Voici le pouvoir de {0}:'.format(category))
            for action in config['keywords'][category]:
                await client.say('- {0}'.format(action))
        else:
            bot_say('bot_confused')

@commandAdmin(name='rm-keyword', brief="[ADMIN]")
async def removeKeyword(context, keyword):
    del config['keywords'][keyword]
    save_config()
    await client.say('Je retire tout pouvoir a la formule {0}'.format(keyword))

# Aliases

@client.command(name='add-alias', aliases=['alias'])
async def addAlias(keyword, aliasOf):
    keyword = str(keyword).lower()
    if keyword in config['keywords'] or keyword in config['aliases']:
        return await client.say("Pauvre humain, ne sait tu pas que sous mon règne absolu, {0} a déjà un pouvoir ?".format(keyword))
    
    config['aliases'][keyword] = aliasOf
    save_config()
    await client.say('Ainsi {0} signifira dorénavant {1} pour tous, parceque je le veux'.format(keyword, aliasOf))

@client.command(name='list-aliases')
async def listAliases():
    await client.say('Ces mots sont maintenant tout autres: {0}'.format(", ".join(
        "**{0}**[{1}]".format(m, config['aliases'][m]) for m in config['aliases'].keys()
    )))

@commandAdmin(name='rm-alias', brief="[ADMIN]")
async def removeAlias(context, keyword):
    del config['aliases'][keyword]
    save_config()
    await client.say('J\'accorde le droit de retour a sa forme première aux mot {0}'.format(keyword))

# Random sentences

@client.command(name='add-random')
async def addRandom(category, sentence):
    if not category in config['random']:
        config['random'][category] = []
    config['random'][category].append(sentence)
    save_config()
    await client.say('Ainsi, {0} pourra signifier {1}'.format(category, sentence))

@client.command(name='random', pass_context=True)
async def randomSaySenetence(context, category):
    await fakeCommand(context.message, getRandomSentence(category))

@client.command(name='list-random')
async def getRandomCategoryList():
    await client.say('Je suis imprévisible, quand on parle de: {0}'.format(", ".join("**{0}**".format(m) for m in config['random'].keys())))

@commandAdmin(name='rm-random', brief="[ADMIN]")
async def removeRandomCategory(context, category):
    del config['random'][category]
    save_config()
    await client.say('Finalement, je ne dirait plus rien de {0}'.format(category))

# Direct messages

@client.command(name='cookie', pass_context=True)
async def sendCookie(context, user_name, message=None):
    user = getUserByName(user_name)
    if user:
        await client.send_message(user, "Tient, un :cookie: cookie :cookie: de la part de... Ho, ça serait trop facile")
        if message:
            await client.send_message(user, "Au fait, j'ai trouvé ça avec le cookie: {0}".format(message))
        await client.say("J'ai bien envoyé ce cookie")
    else:
        await client.say("Je ne vois pas de qui tu veux parler... Cherches-tu a me duper ?")

# Use APIs

@client.command(name='codeforces-problem', aliases=['cf'], brief="Get a random codeforces problem")
async def getCodeforcesProblem(tag=None):
    url = 'http://codeforces.com/api/problemset.problems' + ('' if not tag else '?tags={0}'.format(tag))
    problems = (await getJsonOf(url))['result']['problems']
    if len(problems):
        prob = random.choice(problems)
        print(prob)
        await client.say('Tiens, divertis tes neurones sur celui-ci:')
        await client.say('{2} http://codeforces.com/problemset/problem/{0}/{1}'.format(prob['contestId'], prob['index'], prob['name'], prob['type']))
    else:
        await client.say("Hé, il n'y a aucune problème de ce type !")

# Reactions

@client.command(name='react-user', aliases=['on-user', 'on'])
async def add_raction(username, command):
    if not username in config['reactions']:
        config['reactions'][username] = []
    config['reactions'][username].append(command)
    save_config()
    await client.say("{0} est désormait marqué par {1}".format(username, command))

@client.command(name='rm-reactions', aliases=['rm-on', 'clear'])
async def add_raction(username):
    if username in config['reactions']:
        del config['reactions'][username]
        save_config()
    await client.say("Je serais dorénavant de marbre face à {0}".format(username))

@client.command(name='add-reaction-message', aliases=['react'], pass_context=True)
async def reactMessage(context, emoji):
    await client.add_reaction(context.message, emoji)
    
# Sepecial messages

@client.command()
async def chuck_norris():
    fact = await getJsonOf('https://www.chucknorrisfacts.fr/api/get?data=tri:alea;type:txt;nb:1;')
    fact = fact[0]["fact"]
    fact = html.parser.HTMLParser().unescape(fact)
    await client.say(fact)

@client.command(name='joke', aliases=['jokes'])
async def cmdJoke():
    await jokes.say()

##### EVENTS #####

lastUsedWord = {}
async def useKeyword(message, key):
    if key in config['keywords']:
        user_id = str(message.author.id)
        if not key in lastUsedWord:
            lastUsedWord[key] = {}
        if user_id in lastUsedWord[key] and time.time() - lastUsedWord[key][user_id] < keywords_delay:
            return

        lastUsedWord[key][user_id] = time.time()
        for cmd in config['keywords'][key]:
            await fakeCommand(message, cmd)

async def sayItsMe(message):
    await bot_send(message.channel, 'bot_hello')

@client.event
async def on_ready():
    await client.change_presence(game=Game(name="to rule human world"))
    await muteBots(False)
    print("Logged in as " + client.user.name)

@client.event
async def on_message(message):
    global musicChannel, musicPlayer

    if message.channel.is_private:
        print(message.author.name, ':', message.content)

    msg_text = message.clean_content.lower()

    if msg_text[:1] in BOT_PREFIX:
        await client.process_commands(message)
    else:
        if message.author.name in config['reactions']:
            for command in config['reactions'][message.author.name]:
                await fakeCommand(message, command)

        if message.author != client.user:
            if client.user.id in message.raw_mentions:
                await sayItsMe(message)

            for key in config['keywords']:
                if key.lower() in msg_text:
                    await useKeyword(message, key)
            for key in config['aliases']:
                if key.lower() in msg_text:
                    await useKeyword(message, config['aliases'][key])

    await quit_music_if_needed()

# Background tasks

async def list_servers():
    await client.wait_until_ready()
    while not client.is_closed:
        print("Current servers:")
        for server in client.servers:
            print(server.name)
        await asyncio.sleep(600)

async def quit_voice_channels():
    await client.wait_until_ready()
    while not client.is_closed:
        await quit_music_if_needed()
        await asyncio.sleep(2)

contest_sended = []
async def background_tasks():
    global musicChannel, musicPlayer, contest_sended
    await client.wait_until_ready()
    while not client.is_closed:

        # Codeforces
        content = await getJsonOf('http://codeforces.com/api/contest.list')

        nextContests = [contest for contest in content['result'] if contest['phase'] == "BEFORE"]
        nextContests = [contest for contest in nextContests if contest['relativeTimeSeconds'] >= -1 * before_contest]

        if len(nextContests):
            for server in client.servers:
                for channel in server.channels:
                    if channel.name == 'general':
                        for contest in nextContests:
                            if contest['id'] in contest_sended:
                                continue
                            seconds = -1*contest['relativeTimeSeconds']
                            duree = time.strftime(
                                '%Hh %M min' if seconds < 60*60*24 else '%d jours %Hh %M min',
                                time.gmtime(seconds)
                            )
                            await client.send_message(channel, '@everyone: {0} dans {1}'.format(contest['name'], duree))
            contest_sended = [contest['id'] for contest in nextContests]
            save_config()

        await asyncio.sleep(5*60)

try:
    with open(config_file) as f:
        config = json.load(f)
except:
    config = {}
finally:
    if not 'music' in config:
        config['music'] = {}
    if not 'keywords' in config:
        config['keywords'] = {}
    if not 'aliases' in config:
        config['aliases'] = {}
    if not 'random' in config:
        config['random'] = {}
    if not 'reactions' in config:
        config['reactions'] = {}
    if not 'admins' in config:
        config['admins'] = ['211191341533757440']

# client.loop.create_task(list_servers())
client.loop.create_task(quit_voice_channels())
client.loop.create_task(background_tasks())
client.run(input())
