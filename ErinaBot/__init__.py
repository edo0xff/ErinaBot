# -*- coding: utf-8 -*-

"""
ErinaBot
~~~~~~~~

Discord bot with Natural Language Processing and other basic stuff.

:copyright: 2020 - Eduardo B.R. `edo0xff <https://edo0xff.me>`_
:license: MIT, see LICENSE for more details.

.. tip::
    I already coded a nice bot example so check the
    `github repo <https://github.com/0oeduardoo0/ErinaBot>`_
    out!

"""

__title__ = 'ErinaBot'
__author__ = 'Eduardo <edo0xff>'
__license__ = 'MIT'
__version__ = '0.1'
__copyright__ = 'Copyright 2020 edo0xff'

from . import utils
from ._music_player import MusicPlayer, MusicQueue
from ._conversation import Conversation, Arguments, handle_intention

from pymongo import MongoClient

mongo = MongoClient("mongodb://localhost:27017/")

#: ErinaBot.Conversation instance.
conversation = Conversation()

#: ErinaBot.MusicPlayer instance.
music = MusicPlayer()

#: Mongo database instance.
db = mongo.ErinaBot

intention = handle_intention
'''
    Use this decorator to declarate intention handlers. The intention handler
    function name must be the same as intention defined in intentions.yml
    by example:

    *intentions.yml*

    .. code-block:: none

        -
            -
                - what time is it
                - show time
                - system time
            - show_time

    Your intention handler for *show_time* should looks like:

    .. code-block:: python

        import time
        import ErinaBot as erina
        from datetime import datetime

        ACCESS_TOKEN = "your_atoken_here"

        client = discord.Client()

        erina.conversation.load_dictionary("intentions.yml")

        @erina.intention
        async def show_time(ctx, args):
            """
                **Show system time**

                You can ask me for show system time :smiley:
            """
            date = datetime.utcfromtimestamp(time.time())
            date = date.strftime('%Y-%m-%d %H:%M')

            await ctx.channel.send("Server time: %s" %(date))

    .. tip::
        As you can notice you can document your intention handler in *python like doc*
        and it will be showed as help when bot receive a *help* command.

    Intention handlers will receive two parameters **ctx** which is a
    `discord.Message <https://discordpy.readthedocs.io/en/latest/api.html#message>`_
    instance and **args** that is an `ErinaBot.Arguments <#arguments>`_ instance
    which contains arguments (string, numbers, url's) in received messages.

'''
