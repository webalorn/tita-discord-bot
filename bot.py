import random, re, os, json, copy
import asyncio
import aiohttp
import discord
from discord import Game
from discord.ext.commands import Bot

BOT_PREFIX = ("!")
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

##### COMMANDS #####

# Music

@client.command(name='add-music',
                brief="Add music",
                description="Add a music from youtube url",
                aliases=['add'],
                pass_context=True)
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

@client.command(name='play-music',
                brief="Play music",
                description="Play a music added with add-music command",
                aliases=['play'],
                pass_context=True)
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

@client.command(name='image')
async def sendImage(url):
    image = discord.Embed(colour=0xFF0000)
    image.set_image(url=url)
    await client.say(embed=image)

# Keywords

@client.command(name='add-keyword', aliases=['match'])
async def addKeyword(keyword, command):
    keyword = str(keyword)
    if keyword in config['aliases']:
        return await client.say("Je le sais déjà, stupide humain")
    if not keyword in config['keywords']:
        config['keywords'][keyword] = []

    if command[:1] != '!':
        command = '!' + command

    config['keywords'][keyword].append(command)
    save_config()
    await client.say('Je serais bientot plus reactif a tout les {0}'.format(keyword))

@client.command(name='add-alias', aliases=['alias'])
async def addAlias(keyword, aliasOf):
    keyword = str(keyword)
    if keyword in config['keywords'] or keyword in config['aliases']:
        return await client.say("Pauvre humain, ne sait tu pas que sous mon règne absolu, {0} a déjà un pouvoir ?".format(keyword))
    
    config['aliases'][keyword] = aliasOf
    save_config()
    await client.say('Ainsi {0} signifira dorénavant {1} pour tous, parceque je le veux'.format(keyword, aliasOf))

##### EVENTS #####

async def useKeyword(message, key):
    if key in config['keywords']:
        for cmd in config['keywords'][key]:
            fakeMessage = copy.deepcopy(message)
            fakeMessage.content = cmd
            await client.process_commands(fakeMessage)

@client.event
async def on_ready():
    await client.change_presence(game=Game(name="to rule human world"))
    print("Logged in as " + client.user.name)

@client.event
async def on_message(message):
    global musicChannel, musicPlayer

    if musicChannel and not musicPlayer:
        await musicChannel.disconnect()
        musicChannel = None

    msg_text = message.clean_content.lower()

    if msg_text[:1] in BOT_PREFIX:
        await client.process_commands(message)
    elif message.author != client.user:
        for key in config['keywords']:
            if key in msg_text:
                await useKeyword(message, key)
        for key in config['aliases']:
            if key in msg_text:
                await useKeyword(message, config['aliases'][key])

                


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

print("CONFIG: ", config)

client.loop.create_task(list_servers())
client.run(input())