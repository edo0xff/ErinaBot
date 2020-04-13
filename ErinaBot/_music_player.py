# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2020 edo0xff

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import os
import re
import hashlib
import discord
import asyncio
import itertools
import unidecode
import youtube_dl

from requests import get
from bs4 import BeautifulSoup
from async_timeout import timeout


class MusicQueue():
    '''
    This class is used for MusicPlayer to manage songs queues for the music
    play feature. This class uses asyncio Queues.

    .. attribute:: queue(asyncio.Queue(maxsize=50))
        Songs queue

    .. attribute:: text_channel(discord.TextChannel)
        Queue text channel (user requested songs from this text channel)

    .. attribute:: voice_channel(discord.VoiceClient)
        Queue voice channel (user who requested songs is in this voice channel)

    .. attribute:: volume(float)
        Volume for the queue songs (float from 0.0 to 1.0, 1.0 by default)
    '''
    def __init__(self, text_channel, voice_channel, loop):
        '''
        Initializes the Music Queue.

        Args:
            text_channel(discord.TextChannel): Text channel for the queue (when
                                                a song starts it sends song's info
                                                to this channel).
            voice_channel(discord.VoiceClient): Songs will be played here.
            loop(asyncio.AbstractEventLoop): We need this to create tasks (we get
                                                it from client.loop).
        '''
        self.queue = asyncio.Queue(maxsize=50)
        self.next = asyncio.Event()
        self.text_channel = text_channel
        self.voice_channel = voice_channel
        self.loop = loop
        self.task = self.loop.create_task(self.__queue_worker())
        self.active = True
        self.volume = 1.0

    async def __destroy(self):
        '''
        Disconnects voice channel and stops task loop.
        '''
        await self.voice_channel.disconnect()
        self.active = False
        self.task.cancel()

    async def __queue_worker(self):
        '''
        Queue worker waits for songs in the queue and plays them in voice channel.
        When a song is putted to the queue it plays it and also sends a embed
        message with song info.

        It waits 3 minutes for songs. If there is no songs putted in those 3 minutes
        automatically leaves the voice_channel and stop the queue task.
        '''
        while self.active:
            self.next.clear()

            try:
                # wait for 3 minutes for songs
                async with timeout(180):
                    song = await self.queue.get()

            except asyncio.TimeoutError:
                await self.text_channel.send("Nadie esta escuchando musica, salgo del canal de voz :pleading_face:")
                await self.__destroy()
                continue

            if not self.voice_channel.is_connected():
                await self.__destroy()
                continue

            source = song['source']
            metadata = song['metadata']

            embed = (discord.Embed(title=":headphones: Ahora suena", description=metadata["title"], color=discord.Color.purple())
                    .set_thumbnail(url=metadata['thumbnail'])
                    .add_field(name="Requested By", value=metadata['requested_by'])
                    .add_field(name="Enlaces", value="[YouTube](%s)" %(metadata['url'])))

            await self.text_channel.send(embed=embed)

            source.volume = self.volume

            self.voice_channel.play(source, after=lambda _: self.loop.call_soon_threadsafe(self.next.set))
            self.voice_channel.is_playing()

            await self.next.wait()

            source.cleanup()


class MusicPlayer():
    '''
    Music utilities like download search and play. You will use this class throw
    ErinaBot.music object.

    .. attribute:: queues(dict)
        Dictionary that contains *channel* -> *music queue*.
    '''
    def __init__(self):
        self.queues = {}

    async def get_voice_channel(self, client, author):
        '''
        Gets the voice channel for the given user (who sends a message requesting
        a song).

        Args:
            client(discord.Client): Discord client, we gonna search the voice_channel here.
            author(discord.User): User who requested the song.

        Returns:
            discord.VoiceClient: Voice channel (False if user is no connected to a voice channel).
        '''
        voice_channel = discord.utils.get(client.voice_clients, guild=author.guild)

        if not voice_channel or not voice_channel.is_connected():
            if not author.voice:
                return False

            voice_channel = await author.voice.channel.connect()

        return voice_channel

    def get_queue(self, text_channel, voice_channel, loop):
        '''
        Gets the music queue for the given voice_channel. If the given voice_channel
        doesn't have a music queue it creates one.

        Args:
            text_channel(discord.TextChannel): text_channel for the queue (if
                                                queue needs to be created).
            voice_channel(discord.VoiceClient): voice_channel for the queue.
            loop(asyncio.AbstractEventLoop): we get this from *client.loop*

        Returns:
            ErinaBot.MusicQueue: Music queue for the given voice_channel.
        '''
        queue = None

        if voice_channel.guild.id in self.queues.keys():
            queue = self.queues[voice_channel.guild.id]

        if not queue or not queue.active:
            queue = MusicQueue(text_channel, voice_channel, loop)
            self.queues[voice_channel.guild.id] = queue

        return queue

    def remove_queue(self, voice_channel):
        '''
        Removes queue for the given voice_channel.

        Args:
            voice_channel(discord.VoiceClient): It will removes the queue for this channel.
        '''
        if voice_channel.guild.id in self.queues.keys():
            del self.queues[voice_channel.guild.id]

    def set_volume(self, voice_channel, volume):
        '''
        Sets the music volume for the given channel (if it is playing music).

        Args:
            voice_channel(discord.VoiceClient): Set the volumen for this channel.
            volume(float): Volume from 0.0 to 1.0.
        '''
        if voice_channel.guild.id in self.queues.keys():
            queue = self.queues[voice_channel.guild.id]

        else:
            return

        queue.volume = volume
        voice_channel.source.volume = volume

    def get_queue_info(self, voice_channel):
        '''
        Gets the queued songs for the given voice_channel.

        Args:
            voice_channel(discord.VoiceClient): Gets the queued songs of this channel.

        Returns:
            array[dict]: Array of dictionaries (each dictionary contains: ['source'] and ['metadata'] keys).
        '''
        if voice_channel.guild.id in self.queues.keys():
            queue = self.queues[voice_channel.guild.id]

        else:
            return None

        if queue.queue.empty():
            return None

        upcoming = list(itertools.islice(queue.queue._queue, 0, 5))
        return upcoming

    def search_yt_video(self, query):
        '''
        Search for songs (any video actually) for the given search query.

        .. note::
            Results are limited to 10.

        Args:
            query(str): Search for videos of this in YouTube.

        Returns:
            array[dict]: Array dictionaries of the results (each dictionary contains ['url'] and ['name'] keys)
        '''
        response = get("https://www.youtube.com/results?search_query=%s" %(query))

        soup = BeautifulSoup(response.text, 'lxml')

        videos = []
        for vid in soup.find_all(attrs={'class':'yt-uix-tile-link'}, limit=10):
            url = 'https://www.youtube.com' + vid['href']
            name = vid['title']

            if not "user" in url and not "channel" in url and not "playlist" in url:
                videos.append({'url':url, 'name':name})

        return videos

    def download_yt_video(self, url):
        '''
        Downloads a YouTube video.

        Args:
            url(str): Url for the video to download.

        Returns:
            tuple(song_path, song_title, song_thumbnail): each value will be False if the download fails.
        '''
        if "user" in url or "channel" in url or "playlist" in url:
            return False, False, False

        response = get(url)
        soup = BeautifulSoup(response.text, 'lxml')
        song_title = soup.find("meta", attrs={'property':'og:title'})['content']
        song_thumbnail = soup.find("meta", attrs={'property':'og:image'})['content']

        song_path = "songs/%s.mp3" %(song_title)

        if not os.path.exists(song_path):
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'songs/' + song_title + '.%(ext)s'
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        if not os.path.exists(song_path):
            return False, False, False

        return song_path, song_title, song_thumbnail

    def list_downloaded_songs(self):
        '''
        Get a list of the downloaded songs.

        Returns:
            array[str]: Names of the donwloaded songs (only name not full path).
        '''
        entries = os.scandir("songs/")
        songs = []
        for entry in entries:
            if entry.is_file():
                songs.append(entry.name)

        return songs

    def play(self, client, ctx, voice_channel, metadata):
        '''
        Enqueue a song for the given voice_channel.

        Song metadata must be a dictionary like this:

        .. code-block:: python

            metadata = {
                'path':'song/file/path.mp3',
                'title':'song title',
                'thumbnail':'song thumbnail url',
                'url':'yt url',
                'requested_by': ctx.author.mention
            }

        .. note::
            You get those parameters (path, title, thumbnail) from ErinaBot.download_yt_video()

        Args:
            client(discord.Client): Needed to create the queue if it doesn't exists.
            ctx(discord.Message): Needed to create the queue if it doesn't exists.
            voice_channel(discord.VoiceClient): The song will be played here.
            metadata(dict): Song metadata.
        '''
        queue = self.get_queue(ctx.channel, voice_channel, client.loop)

        source = discord.FFmpegPCMAudio(metadata['path'])
        source = discord.PCMVolumeTransformer(source)

        song = {
            "source": source,
            "metadata": metadata
        }

        queue.queue.put_nowait(song)
