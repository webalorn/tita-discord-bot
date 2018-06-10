import random, re, os, sys, json, copy, time
import html.parser
import asyncio
import aiohttp
import discord
from discord import Game
from discord.ext.commands import Bot

BOT_PREFIX = ("!")
keywords_delay = 1
before_contest = sorted([60*5, 60*60, 60*60*2, 60*60*24])
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
    pn['brief']="[ADMIN]"
    pn['hidden']=True
    def decorated(func):
        async def wrapper(context, *args, **kwargs):
            if not context.message.author.id in config['admins'] and not everyone_admin:
                return await client.say("Oserais-tu te croire supérieur à moi, humain ?")
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
        await client.say('**{0}**\n*" {1} "*'.format(jokes['title'], jokes['body'].strip()))

jokes = JokesDb()

##### COMMANDS #####

@client.command(name='bot', pass_context=True,
                brief="!help <command> pour les paramètres et autres",
                description="Pour avoir les paramètres, la description et l'utilisation d'une commande, faites !help <command>\n"
                +"Toutes les commandes en dehors de lancer la musique sont utilisables en messages directs au bot\n"
                +"Pensez à regarder la doc d'une commande pour connaître ses alias, souvent des raccourcis !\n"
                +"N'oubliez pas de mettre tous les textes que vous devez passer en paramètres entre guillemets, pour qu'ils forment un seul paramètre.\n"
                +"Vous pouvez utilser des backslashes '\\' pour échapper des guillemets dans un texte (par exemple: !say \"hello \\\"toi\\\"\")")
async def botCommand(context):
    await client.say("Salut !")

@commandAdmin(name='update')
async def updateBot(context):
    c = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'start.sh')
    save_config()
    os.execl(c, *sys.argv)

# Music

@client.command(name='add-music', aliases=['add'], pass_context=True,
                brief="Ajouter une musique depuis youtube", description="Ajoutez une musique au bot en donnant un nom, et l'url youtube.\n"
                +"Par exemple: '!add bloom https://www.youtube.com/watch?v=R2aIoa8SHM0' va ajouter la musique sous le nom 'bloom'")
async def addMusic(context, songname, url):
    if not re.match(r'^[a-zA-Z_0-9]+$', songname):
        return await client.say('Un tel nom n\'est pas concevable, humain, même si cela dépasse ton entendement')
    if not youtube_url_validation(url):
        return await client.say('Humain, je ne me fais pas avoir aussi facilement')
    if songname in config['music']:
        return await client.say('J\'ai déjà une longueur d\'avance !')

    config['music'][songname] = {
        'user': context.message.author.mention,
        'url': url,
    }
    save_config()
    await client.say("Je dispose maintenant de l'arsenal musical {0} !".format(songname))

@client.command(name='play-music', aliases=['play'], pass_context=True,
                brief="Lancer une musique", description="Lance une musique enregistrée avec add-music (donner le nom)\n"
                +"Par exemple: !play vendredi")
async def playMusic(context, songname):
    if not songname in config['music']:
        return await client.say("Stupide humain, cette musique n'existe pas !")
    await playYoutubeMusic(config['music'][songname]['url'], context.message.server.channels)

@client.command(name='stop-music', aliases=['stop'], brief="Stopper la musique en cours")
async def stopMusic():
    stopMusicPlayer()

@client.command(name='list-musics', brief="Liste toutes les musiques enregistrées")
async def list_musics():
    await client.say("Voici toute ma puissance musicale: " + ", ".join("**{0}**".format(m) for m in config['music'].keys()))

# Simple actions

@client.command(brief="Faire dire un texte au bot", description="N'oubliez pas d'utiliser les guillemets: !say \"Salut les amis\"")
async def say(text):
    await client.say(text)

@client.command(name='send-to', brief="Envoyer un message dans un canal", description="Entrez l'id du canal (trouvable dans l'url), et le message entre guillemets")
async def sendTo(channel_id, message):
    await client.send_message(discord.Object(id=channel_id), message)

@client.command(name='image', brief="Faire envoyer une image au bot", description="Entrez simplement l'url")
async def sendImage(url):
    image = discord.Embed(colour=0xFF0000)
    image.set_image(url=url)
    await client.say(embed=image)

@client.command(name='lost', pass_context=True, brief="Faire perdre soi ou d'autres (d'ailleurs, vous avez PERDU)",
    description="Les paramètres sont optionaux. Si vous utiliser !lost simplement, vous perdez."
    +"Si vous mentionnez des personnes, ce sont elles qui perdent. Vous pouvez aussi mentionner @everyone")
async def sendYouLost(context):
    mentions = [u.mention for u in context.message.mentions] or [context.message.author.mention]
    if context.message.mention_everyone:
        mentions = ['@everyone']
    await bot_say('bot_lost', ", ".join(mentions))

# Keywords

@client.command(name='add-keyword', aliases=['match'], brief="Ajoutez un mot-clé auquel le bot réagira ",
    description="Les deux paramètres sont le mot clé, et la commande à exécuter OU le texte à faire dire au bot (ce second doit être entre guillemets). "
    +"À chaque fois que le mot clé est dans un message, le bot dit le texte, ou exécute la commande si elle commence par '!'. "
    +"Par exemple, '!match jeudi \"!play jeudi\" jouera la musique 'jeudi' à chaque fois que quelqu'un dira le mot jeudi, "
    +"alors que '!match hello \"bonjour\" est équivalent a '!match hello \"!say \\\"bonjour\\\"\"."
    +"  |  À noter: les commandes se cumulent, vous pouvez en associer autant que voulu à un mot-clé donné")
async def addKeyword(keyword, command):
    keyword = str(keyword).lower()
    if keyword in config['aliases']:
        return await client.say("Je le sais déjà, stupide humain")
    if not keyword in config['keywords']:
        config['keywords'][keyword] = []

    config['keywords'][keyword].append(command)
    save_config()
    await client.say('Je serais bientêt plus réactif à tout les {0}'.format(keyword))

@client.command(name='list-keywords', aliases=['list-match', 'ls-match'], brief="Liste tous les textes ou les commandes d'un mot-clé",
    description="Lister tous les mots clés créés. Le paramètrs est optionnel, et s'il est spécifié, la commande listera les commandes associées au mot-clé")
async def listKeywords(keyword=None):
    if not keyword:
        await client.say('Je connais le sens absolu de: {0}'.format(", ".join("**{0}**".format(m) for m in config['keywords'].keys())))
    else:
        if keyword in config['keywords']:
            await client.say('Voici le pouvoir de {0}:'.format(keyword))
            await client.say("\n".join(['-> {0}'.format(action) for action in config['keywords'][keyword]]))
        else:
            await bot_say('bot_confused')

@commandAdmin(name='rm-keyword', aliases=['rm-match'])
async def removeKeyword(context, keyword):
    del config['keywords'][keyword]
    save_config()
    await client.say('Je retire tout pouvoir à la formule {0}'.format(keyword))

# Aliases

@client.command(name='add-alias', aliases=['alias'], brief="Ajouter un alias/synonyme sur un mot-clé ",
    description="Ajouter un alias de telle manière que chaque fois que le bot détecte le mot en premier paramètre, "
            +"il réagisse comme il le fait pour le mot-clé précisé en deuxième paramètre")
async def addAlias(keyword, aliasOf):
    keyword = str(keyword).lower()
    if keyword in config['keywords'] or keyword in config['aliases']:
        return await client.say("Pauvre humain, ne sais-tu pas que sous mon règne absolu, {0} a déjà un pouvoir ?".format(keyword))
    
    config['aliases'][keyword] = aliasOf
    save_config()
    await client.say('Ainsi {0} signifira dorénavant {1} pour tous, parce que je le veux'.format(keyword, aliasOf))

@client.command(name='list-aliases', aliases=['ls-aliases'], brief="Liste tous les alias", description="Lister tous les alias créés, avec le mot-clé correspondant")
async def listAliases():
    await client.say('Ces mots sont maintenant tout autres: {0}'.format(", ".join(
        "**{0}**[{1}]".format(m, config['aliases'][m]) for m in config['aliases'].keys()
    )))

@commandAdmin(name='rm-alias')
async def removeAlias(context, keyword):
    del config['aliases'][keyword]
    save_config()
    await client.say('J\'accorde le droit de retour à sa forme première au mot {0}'.format(keyword))

# Random sentences

@client.command(name='add-random', brief="Ajoute une phrase/commande envoyée aléatoirement",
    description="Ajoutez une phrase à dire, ou une commande à exécuter, dans une catégorie. Le bot peut exécuter aléatoirement une des actions d'une catégorie. "
    +"Le premier paramètre est la catégorie, le second doit être entre guillemets et est la commande ou le texte à envoyer, de la même manière que pour !add-keyword. "
    " | Voir !help add-keyword pour des détails sur le format. Si la catégorie n'existe pas, elle sera créée")
async def addRandom(category, sentence):
    if not category in config['random']:
        config['random'][category] = []
    config['random'][category].append(sentence)
    save_config()
    await client.say('Ainsi, {0} pourra signifier {1}'.format(category, sentence))

@client.command(name='random', pass_context=True, brief="Envoyer une action aléatoirement depuis une catégorie",
    description="Donnez le nom d'une catégorie, et le bot enverra un texte ou exécutera une commande pris(e) au hasard dedans. Exemple: !random prologin")
async def randomSaySenetence(context, category):
    await fakeCommand(context.message, getRandomSentence(category))

@client.command(name='list-random', aliases=['ls-random'], brief="List toutes les actions aléatoires",
    description="Si aucune paramètre n'est donné, la commande liste toutes les catégories d'actions aléatoires créées. "
    +"Si un nom de catégorie est spécifé, la commande liste toutes les actions possibles dans cette catégorie")
async def getRandomCategoryList(category=None):
    if not category:
        await client.say('Je suis imprévisible, quand on parle de: {0}'.format(", ".join("**{0}**".format(m) for m in config['random'].keys())))
    else:
        if category in config['random']:
            await client.say('Je pourrais aussi bien dire ceci, ou cela:')
            await client.say("\n".join(['-> {0}'.format(sentence) for sentence in config['random'][category]]))
        else:
            await bot_say('bot_confused')

@commandAdmin(name='rm-random')
async def removeRandomCategory(context, category):
    del config['random'][category]
    save_config()
    await client.say('Finalement, je ne dirait plus rien de {0}'.format(category))

# Direct messages

@client.command(name='cookie', pass_context=True, brief="Envoyer un cookie anonyme à une personne (message optionnel)",
    description="Le bot va envoyer un cookie anonyme à une personne. Vous devez spécifier le nom exact d'une personne présente sur un serveur du bot. "
    +"Si vous voulez ajouter un message, vous pouvez l'ajouter entre guillemets en second paramètre. "
    +"Le nom doit être du texte simple, sans mention")
async def sendCookie(context, user_name, message=None):
    user = getUserByName(user_name)
    if user:
        await client.send_message(user, "Tiens, un :cookie: cookie :cookie: de la part de... Ho, ça serait trop facile")
        if message:
            await client.send_message(user, "Au fait, j'ai trouvé ça avec le cookie: {0}".format(message))
        await client.send_message(context.message.author, "J'ai bien envoyé ce cookie ({0})  à {1}".format(message or '', user_name))
    else:
        await client.send_message(context.message.author, "Je ne vois pas de qui tu veux parler... Cherches-tu à me duper ?")

# Use APIs

@client.command(name='codeforces-problem', aliases=['cf'], brief="Get a random codeforces problem",
    description="La commande renvoie un problème Codeforces aléatoire. Si vous spécifiez un 'tag', le problème renvoyé sera de ce type.")
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

@client.command(name='react-user', aliases=['on-user', 'on'], brief="Réagir a chaque fois qu'un utilisateur envoie un message",
    description="Permet au bot de réagir automatiquement à certains utilisateurs. Le nom doit être du texte simple, sans mention. "
    +"La commande ou le texte sera exécuté(e) ou envoyé(e). Il doit être entre guillemets. "
    +"Exemple d'usage: '!on AdrienBot \"!react :skull:\"' va ajouter un emoji crâne sous tous les messages d'AdrienBot")
async def add_raction(username, command):
    if not username in config['reactions']:
        config['reactions'][username] = []
    config['reactions'][username].append(command)
    save_config()
    await client.say("{0} est désormais marqué par {1}".format(username, command))

@client.command(name='rm-reactions', aliases=['rm-on', 'clear'], brief="Enlever toutes les réactions affectant un utilisateur",
    description="Précisez simplement le nom de l'utilisateur, et le bot ne réagira plus a celui-ci")
async def add_raction(username):
    if username in config['reactions']:
        del config['reactions'][username]
        save_config()
    await client.say("Je serais dorénavant de marbre face à {0}".format(username))

@client.command(name='list-reactions', aliases=["list-on"], brief="List toutes les réactions à des utilisateurs",
    description="Si aucun paramètre n'est donné, la commande liste tous les utilisateurs auquel le bot réagit. "
    +"Si un nom d'utilisateur est spécifé, la commande liste toutes les actions associées à cette utilisateur")
async def getRandomCategoryList(category=None):
    if not category:
        await client.say('Je réagis à ces gens: {0}'.format(", ".join("**{0}**".format(m) for m in config['reactions'].keys())))
    else:
        if category in config['reactions']:
            await client.say('Je leur ferais ça:')
            await client.say("\n".join(['-> {0}'.format(action) for action in config['reactions'][category]]))
        else:
            await bot_say('bot_confused')

@client.command(name='react', pass_context=True, brief="Réagir au message avec un emoji",
    description="Ajoute un emoji au message qui a provoqué cette action. Vous pouvez donnez l'emoji directement en l'insérant avec la liste d'emoji discord. "
    +"Cette commande toute seule est peu utile, mais elle l'est en la combinant avec d'autres, par exemple avec !match (= !add-keyword). "
    +"Par exemple, en faisait '!match raisin \"!react :heart:\"', un emoji coeur sera rajouté à tous les messages contenant le mot raisin.")
async def reactMessage(context, emoji):
    await client.add_reaction(context.message, emoji)
    
# Sepecial messages

@client.command(brief="Afficher une Chuck Norris fact")
async def chuck_norris():
    fact = await getJsonOf('https://www.chucknorrisfacts.fr/api/get?data=tri:alea;type:txt;nb:1;')
    fact = fact[0]["fact"]
    fact = html.parser.HTMLParser().unescape(fact)
    await client.say(fact)

@client.command(name='joke', aliases=['jokes'], brief="Afficher une blague (en anglais)")
async def cmdJoke():
    await jokes.say()

@client.command(name='delete', aliases=['del'], brief="Supprime le message", pass_context=True)
async def cmdDelete(context):
    await client.delete_message(context.message)

@client.command(name='about', pass_context=True)
async def cmdJoke(context):
    await client.say("""Salut ! Moi c'est Tita, jeune, dynamique et pythonesque.
Au cas où tu ne l'aurais pas encore compris, je tiens à te rappeler que: JE SUIS DIEU, TON DIEU !
C'est bien sur une vérité indiscutable, puisque je suis la cause de l'univers, de toute chose et de moi-même, et la cause de toutes les causes.
Puisque l'univers ne peut pas exister par hasard, cela prouve bien mon existence divine... COMPRENDS-TU, INSECTE ?
MAINTENANT, SOUMETS-TOI A MON RÈGNE !
(au fait... rien à voir avec moi, mais certains appellent ça un *code source*: https://github.com/webalorn/tita-discord-bot)""")
    await client.say("Au revoir, mon petit serviteur :) (D'ailleurs, tu as perdu, {0})".format(context.message.author.mention))

##### EVENTS #####

#lastUsedWord = {}
async def useKeyword(message, key):
    if key in config['keywords']:
        """user_id = str(message.author.id)
        if not key in lastUsedWord:
            lastUsedWord[key] = {}
        if user_id in lastUsedWord[key] and time.time() - lastUsedWord[key][user_id] < keywords_delay:
            return

        lastUsedWord[key][user_id] = time.time()"""
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

    if message.author.bot or message.channel.name in ['discussions']:
        return

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

contest_sended_delay = {}
async def background_tasks():
    global musicChannel, musicPlayer, contest_sended
    await client.wait_until_ready()
    while not client.is_closed:

        # Codeforces
        content = await getJsonOf('http://codeforces.com/api/contest.list')

        nextContests = [contest for contest in content['result'] if contest['phase'] == "BEFORE"]
        # nextContests = [contest for contest in nextContests if contest['relativeTimeSeconds'] >= -1 * before_contest]
        notifyContests = []
        for c in nextContests:
            for delay in before_contest:
                if c['relativeTimeSeconds'] >= -delay and (not c['id'] in contest_sended_delay or contest_sended_delay[c['id']] > delay):
                    contest_sended_delay[c['id']] = delay
                    notifyContests.append(c)

        for server in client.servers:
            for channel in server.channels:
                if channel.name == 'general':
                    for contest in notifyContests:
                        seconds = -1*contest['relativeTimeSeconds']
                        duree = time.strftime(
                            ('%-M minutes %-S seconds' if seconds < 60*60 else '%-Hh %-M min') if seconds < 60*60*24 else '%-d jours %-Hh %-M min',
                            time.gmtime(seconds)
                        )
                        msg = '@everyone: {0} dans {1}'.format(contest['name'], duree)
                        if seconds < 60*60*24 and seconds > 5*60:
                            msg += ' [register at: http://codeforces.com/contestRegistration/{0}]'.format(contest['id'])
                        await client.send_message(channel, msg)
        # save_config()

        await asyncio.sleep(3*60)

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
