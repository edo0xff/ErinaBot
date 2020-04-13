# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import time
import discord

import ErinaBot as erina

from datetime import datetime
from discord.ext import tasks
from unidecode import unidecode


ACCESS_TOKEN = ""

client = discord.Client()

erina.conversation.load_dictionary("intentions.yml")
erina.conversation.load_dictionary("dialogs.yml")

@erina.intention
async def help(ctx, args):
    '''
        **Hola, mi nombre es Erina!**

        Solo soy un robot y no se hacer muchas cosas :robot: pero trataré de hacerlo lo mejor que pueda.

        No entiendo del todo el lenguaje de los humanos, pero puedes tratar de hablarme de forma natural. :sweat_smile:

        Aquí algunas del las cosas que se hacer:
    '''
    pass

@erina.intention
async def list_downloaded_songs(ctx, message):
    '''
        **Listar las canciones descargadas**

        Para listar las canciones que he descargado simplemente di algo como:

        :black_small_square: ¿Eri qué canciones has descargado?
        :black_small_square: Eri lista de canciones descargadas

        De la lista que aparezca puedes pedir una canción:

        :black_small_square: Eri pon la 3
        :black_small_square: quiero escuchar la 5 eri
    '''
    songs = erina.music.list_downloaded_songs()

    string = "".join("**%s** - %s\n" %(i, songs[i]) for i in range(len(songs)))

    embed = discord.Embed(title="%i Canciones descargadas" %(len(songs)),
                            description=string,
                            color=discord.Color.purple())

    await ctx.channel.send(embed=embed)

    erina.conversation.set_context_var(ctx, "downloaded_songs", songs)
    erina.conversation.set_context_var(ctx, "yt_search_result", '')

@erina.intention
async def yt_search(ctx, args):
    '''
        **Buscar canciones**

        Para buscar canciones dime algo así:

        :black_small_square: Eri busca "Ghost - Rats"
        :black_small_square: Eri busca esta cancion "Tusa"
        :black_small_square: Eri busca canciones de "Metallica"

        Se desplegara una lista numerada, para poner una cancion puedes decir:

        :black_small_square: Eri quiero escuchar la numero 4
        :black_small_square: Eri pon la 2
        :black_small_square: Eri agrega la 3
    '''
    if not args.string:
        await ctx.channel.send("¿Qué busco? :thinking:")
        return

    await ctx.channel.send("Buscando **%s** :face_with_monocle:" %(args.string))

    async with ctx.channel.typing():
        videos = erina.music.search_yt_video(args.string)

    if len(videos) == 0:
        await ctx.channel.send("Lo siento tuve problemas con la busqueda :sweat_smile:")
        return

    erina.conversation.set_context_var(ctx, "yt_search_result", videos)

    string = "".join("%i.- [%s](%s)\n" %(i, videos[i]['name'], videos[i]['url']) for i in range(len(videos)))
    embed =  discord.Embed(title=args.string, description=string, color=discord.Color.purple())

    await ctx.channel.send(embed=embed)

@erina.intention
async def play_music(ctx, args):
    '''
        **Poner música**

        Si quieres escuchar una canción solo dime:

        :black_small_square: Eri pon "Metallica - One"
        :black_small_square: Eri quiero escuchar "Ghost Monstrance Clock"

        O algo así. Solo recuerda poner el nombre de la canción entre comillas.

        Trata de ser especifico ya que pondré el primer resultado que encuentre en youtube. :sweat_smile:

        También puedes simplemente indicarme el enlace a YouTube:

        :black_small_square: Eri reproduce http://youtube.com/...
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("Conectate a un canal de voz :rolling_eyes:")
        return

    video_url = None
    song_path = None
    song_metadata = None

    if args.yt_url:
        video_url = args.yt_url

    elif args.string:
        if "tusa" in args.string:
            await ctx.channel.send("Weyyy nooooo! la cancion! :sob::ok_hand::ok_hand::ok_hand:")

        async with ctx.channel.typing():
            search_results = erina.music.search_yt_video(args.string)

        if len(search_results) == 0:
            await ctx.channel.send("Lo siento no pude encontrar tu rolita :C")
            return

        video_url = search_results[0]['url']

    elif args.number != None:
        songs = erina.conversation.get_context_var(ctx, "downloaded_songs")
        videos = erina.conversation.get_context_var(ctx, "yt_search_result")

        if videos:
            video_url = videos[args.number]['url']

        elif songs:
            song_path = "songs/%s" %(songs[args.number])

        else:
            await ctx.channel.send("Primero realiza una busqueda :thinking:")
            return

    else:
        await ctx.channel.send("¿Qué canción quieres?")
        return

    if video_url:
        async with ctx.channel.typing():
            await ctx.channel.send("Dame un segundo, necesito descargarla...")
            song_path, song_title, song_thumbnail = erina.music.download_yt_video(video_url)

            song_metadata = {
                "path": song_path,
                "title": song_title,
                "thumbnail": song_thumbnail,
                "url": video_url,
                "requested_by": ctx.author.mention
            }

            erina.db.songs.insert_one(song_metadata)

    if not song_path:
        await ctx.add_reaction("😢")
        await ctx.channel.send("Los siento no pude encontrarla :C")
        return

    if not song_metadata:
        song_metadata = erina.db.songs.find_one({"path": song_path})

    erina.music.play(client, ctx, voice_channel, song_metadata)

    queue_info = erina.music.get_queue_info(voice_channel)

    if not queue_info:
        return

    string = "".join(":black_small_square: %s\n" %(song["metadata"]["title"]) for song in queue_info)

    embed = discord.Embed(title="%i canciones en la playlist" %(len(queue_info)),
                            description=string,
                            color=discord.Color.purple())

    await ctx.channel.send(embed=embed)

@erina.intention
async def pause_music(ctx, args):
    '''
        **Pausar música**

        Si estás escuchando música y quieres que ponga pausa solo di algo como:

        :black_small_square: Pausa la musica eri
        :black_small_square: Eri pausar música
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("No estoy conectada a ningun canal de voz :rolling_eyes:")
        return

    if not voice_channel.is_playing():
        await ctx.channel.send("No se esta reproduciendo nada :thinking:")
        return

    await ctx.add_reaction("⏸")
    voice_channel.pause()

@erina.intention
async def resume_music(ctx, args):
    '''
        **Quitar pausa**

        Si pausaste la música y quieres reanudar la reproducción di:

        :black_small_square: Eri play
        :black_small_square: Eri quita la pausa
        :black_small_square: ponle play eri
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("No estoy conectada a ningun canal de voz :rolling_eyes:")
        return

    if not voice_channel.is_paused():
        await ctx.channel.send("No música en pausa :thinking:")
        return

    await ctx.add_reaction("▶️")
    await ctx.channel.send("Fierro :cowboy: :ok_hand:")
    voice_channel.resume()

@erina.intention
async def skip_song(ctx, args):
    '''
        **Saltar canción**

        Si tienes más de una canción en lista puedes pedirme que la adelante:

        :black_small_square: adelanta la cancion eri
        :black_small_square: Eri siguiente canción
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("No estoy conectada a ningun canal de voz :rolling_eyes:")
        return

    if not voice_channel.is_playing():
        await ctx.channel.send("No se esta reproduciendo nada :thinking:")
        return

    await ctx.add_reaction("⏭")
    voice_channel.stop()

@erina.intention
async def set_player_volume(ctx, args):
    '''
        **Cambiar volumen de la música**

        Si el volumen esta muy alto o muy bajo, pide que lo ajuste:

        :black_small_square: Eri volumen al 50
        :black_small_square: pon el volumen al 10 eri
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("No estoy conectada a ningun canal de voz :rolling_eyes:")
        return

    if not voice_channel.source:
        await ctx.channel.send("No se esta reproduciendo nada :rolling_eyes:")
        return

    if not args.number:
        await ctx.channel.send("¿En cuánto pongo el volumen?")
        return

    volume = args.number / 100

    if volume < 0:
        volume = 0

    elif volume > 1:
        volume = 1

    erina.music.set_volume(voice_channel, volume)
    await ctx.channel.send("Volumen: **%i** :loud_sound:" %(args.number))

@erina.intention
async def leave_voice_channel(ctx, args):
    '''
        **Salir del canal de voz**

        Si ya no estas escuchando música o ya no quieres escucharla solo dime que deje  el canal de voz:

        :black_small_square: sal de la llamada eri
        :black_small_square: Eri abandona el canal de voz

        De todas formas si nadie pide una canción en 3 minutos de que terminó la última yo saldré automaticamente. :kissing_closed_eyes:
    '''
    voice_channel = await erina.music.get_voice_channel(client, ctx.author)

    if not voice_channel:
        await ctx.channel.send("No estoy conectada a ningun canal de voz :rolling_eyes:")
        return

    erina.music.remove_queue(voice_channel)

    await ctx.add_reaction("☹️")
    await ctx.channel.send("Ay :c al fin que ni queria hablar con ustedes :'v :broken_heart:")

    await voice_channel.disconnect()

@erina.intention
async def covid_statistics(ctx, args):
    '''
        **Estadisticas del COVID-19**

        ¿Te interesa saber las cifras más actuales de esta pandemia para tu país?

        :black_small_square: Eri ¿Cual es la situación del covid en "México"?

        No olvides indicar entre comillas el nombre de tu país.
    '''
    if not args.string:
        await ctx.channel.send("¿De qué país?")
        return

    await ctx.channel.send("Voy, dame un segundo...")

    async with ctx.channel.typing():
        covid_cases = erina.utils.covid_cases(args.string)

    embed = discord.Embed(title="Casos de covid en %s" %(args.string),
                            description=covid_cases,
                            color=discord.Color.purple())

    await ctx.channel.send(embed=embed)

@erina.intention
async def send_nudes(ctx, args):
    '''
        **Send Nudes**

        Jaja ¿Es necesario que lo explique? :flushed::face_with_hand_over_mouth:
    '''
    await ctx.add_reaction("🤣")
    await ctx.channel.send("Pinshi puerco... espera 7u7r")

    async with ctx.channel.typing():
        url, thumbnail = erina.utils.get_nudes()

    embed = (discord.Embed(title=":smiling_imp:",
                            description="[Ver Imagen Completa](%s)" %(url),
                            color=discord.Color.purple())
                            .set_image(url=thumbnail))

    await ctx.channel.send(embed=embed)

@erina.intention
async def create_reminder(ctx, args):
    '''
        **Crear recordatorio**

        ¿Quieres que te recuerde algo?

        :black_small_square: Eri programa un recordatorio "Comprar leche" en 10 minutos.
        :black_small_square: recuerdame "Hacer algo productivo" en 2 días eri

        Indica el contenido del recordatorio entre comillas y en cuanto tiempo quieres que te lo recuerde, siendo el tiempo en minutos, horas o días.
    '''
    if not args.string:
        await ctx.channel.send("¿Qué quieres que te recuerde?")
        return

    if not args.number:
        await ctx.channel.send("¿En cuanto tiempo?")
        return

    expiration = args.number

    if "dia" in unidecode(ctx.clean_content):
        expiration = expiration * 24 * 60 * 60
        type = "días"

    elif "hora" in ctx.clean_content:
        expiration = expiration * 60 * 60
        type = "horas"

    else:
        expiration = expiration * 60
        type = "minutos"

    creation_date = "%s %s" %(args.number, type)

    expiration += time.time()
    notification = {
        'expiration': expiration,
        'message': args.string,
        'author': ctx.author.mention,
        'channel': ctx.channel.id,
        'creation_date': creation_date
    }

    erina.db.notifications.insert_one(notification)

    await ctx.add_reaction("👍")
    await ctx.channel.send("Vale yo te aviso :sunglasses:")

    date = datetime.utcfromtimestamp(expiration-18000).strftime('%Y-%m-%d %H:%M')
    embed = (discord.Embed(title="Recordatorio programado",
                            description=args.string,
                            color=discord.Color.purple())
                            .add_field(name="Fecha", value=date)
                            .add_field(name="Autor", value=ctx.author.mention))

    await ctx.channel.send(embed=embed)

@erina.intention
async def send_meme(ctx, args):
    '''
        **Memes**

        Puedo mandarte algunos memes, pero no garantizo que sean graciosos :sob:

        :black_small_square: Eri manda un meme
    '''
    await ctx.channel.send("Deja busco uno que este bueno :'3 ...")

    async with ctx.channel.typing():
        await ctx.channel.send(erina.utils.get_meme())

@erina.intention
async def send_joke(ctx, args):
    '''
        **Chistes**

        Me se algunos chistes :laughing:

        :black_small_square: Cuenta un chiste eri
    '''
    await ctx.channel.send("Mmm ...")

    async with ctx.channel.typing():
        await ctx.channel.send(erina.utils.get_joke())

@tasks.loop(seconds=30.0)
async def cronjob():
    '''
        Revisa la base de datos cada 30s y si encuentra una notificacion
        que haya expirado la envia al canal donde la crearon.
    '''
    notifications = erina.db.notifications.find()
    unix_time = time.time()

    for notification in notifications:
        if notification['expiration'] <= unix_time:
            erina.db.notifications.delete_one({'_id': notification['_id']})

            channel_id = notification['channel']
            channel = client.get_channel(channel_id)

            author = notification['author']
            message = notification['message']
            creation_date = notification['creation_date']

            embed = (discord.Embed(title="Recodatorio", description=message, color=discord.Color.purple())
                    .add_field(name="Hace", value=creation_date)
                    .add_field(name="Autor", value=author))

            await channel.send(embed=embed)

@client.event
async def on_ready():
    print("Erina-san is ready!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Hentai!")
    await client.change_presence(status=discord.Status.online, activity=activity)

    cronjob.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if (not client.user in message.mentions)\
        and (not message.mention_everyone)\
        and (not erina.conversation.talking_to_me(message.content)):
        return

    await erina.conversation.recognize(message)

client.run(ACCESS_TOKEN)
