import random, re, os, json, copy, time
import asyncio
import aiohttp
import discord
from discord import Game
from discord.ext.commands import Bot

BOT_PREFIX = ("!")
keywords_delay = 0.5
everyone_admin = False

client = Bot(command_prefix=BOT_PREFIX)

config_file = 'config.json'
config = {}

musicChannel = None
musicPlayer = None


##### FUNCTIONS #####

def youtube_url_validation(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        return True
    return False

def save_config():
    with open(config_file, 'w') as f:
        json.dump(config, f)

def stopMusicPlayer():
    global musicPlayer
    if musicPlayer:
        musicPlayer.stop()
    musicPlayer = None

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
            musicPlayer = await musicChannel.create_ytdl_player(url, after=stopMusicPlayer)
            musicPlayer.start()

def commandAdmin(*p, **pn):
    pn['pass_context'] = True
    def decorated(func):
        async def wrapper(context, *args, **kwargs):
            if not context.message.author.id in config['admins'] and not everyone_admin:
                return False
            return await func(context, *args, **kwargs)
        return client.command(*p, **pn)(wrapper)
    return decorated

def getRandomSentence(category):
    if category in config['random'] and len(config['random'][category]):
        return random.choice(config['random'][category])
    return "J'en reste sans voix :-*"

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

@commandAdmin(name='stop-music', aliases=['stop'], brief="[ADMIN]")
async def stopMusic(context):
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
    l = [
        "Tu as perdu, {0}",
        "You lost THE GAME, {0}",
        "{0}: PERDU ! Hahaha !",
    ]
    await client.say(random.choice(l).format(context.message.author.mention))

# Keywords

@client.command(name='add-keyword', aliases=['match'])
async def addKeyword(keyword, command):
    keyword = str(keyword).lower()
    if keyword in config['aliases']:
        return await client.say("Je le sais déjà, stupide humain")
    if not keyword in config['keywords']:
        config['keywords'][keyword] = []

    if command[:1] != '!':
        command = '!' + command

    config['keywords'][keyword].append(command)
    save_config()
    await client.say('Je serais bientot plus reactif a tout les {0}'.format(keyword))

@client.command(name='list-keywords')
async def listKeywords():
    await client.say('Je connais le sens absolu de: {0}'.format(", ".join("**{0}**".format(m) for m in config['keywords'].keys())))

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

@client.command(name='random')
async def randomSaySenetence(category):
    await client.say(getRandomSentence(category))

@client.command(name='list-random')
async def getRandomCategoryList():
    await client.say('Je suis imprévisible, quand on parle de: {0}'.format(", ".join("**{0}**".format(m) for m in config['random'].keys())))

@commandAdmin(name='rm-random', brief="[ADMIN]")
async def removeRandomCategory(context, category):
    del config['random'][category]
    save_config()
    await client.say('Finalement, je ne dirait plus rien de {0}'.format(category))

##### EVENTS #####

lastUsedWord = {}
async def useKeyword(message, key):
    if key in config['keywords']:
        if key in lastUsedWord and time.time() - lastUsedWord[key] < keywords_delay:
            return
        lastUsedWord[key] = time.time()
        for cmd in config['keywords'][key]:
            fakeMessage = copy.deepcopy(message)
            fakeMessage.content = cmd
            await client.process_commands(fakeMessage)

async def sayItsMe(message):
    l = [
        "C'est moi !",
        "Votre maitre répond a l'appel",
        "Je suis celle dont vous parlez",
        "Oui, être insignifiant"
    ]
    await client.send_message(message.channel, random.choice(l))

@client.event
async def on_ready():
    await client.change_presence(game=Game(name="to rule human world"))
    print("Logged in as " + client.user.name)

@client.event
async def on_message(message):
    global musicChannel, musicPlayer

    msg_text = message.clean_content.lower()

    if msg_text[:1] in BOT_PREFIX:
        await client.process_commands(message)
    elif message.author != client.user:
        for key in config['keywords']:
            if key.lower() in msg_text:
                await useKeyword(message, key)
        for key in config['aliases']:
            if key.lower() in msg_text:
                await useKeyword(message, config['aliases'][key])

        if client.user.id in message.raw_mentions:
            await sayItsMe(message)

    if musicChannel and not musicPlayer:
        await musicChannel.disconnect()
        musicChannel = None

async def list_servers():
    await client.wait_until_ready()
    while not client.is_closed:
        print("Current servers:")
        for server in client.servers:
            print(server.name)
        await asyncio.sleep(600)

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
    if not 'admins' in config:
        config['admins'] = ['211191341533757440']

client.loop.create_task(list_servers())
client.run(input())