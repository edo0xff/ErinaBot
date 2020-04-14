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

import re
import yaml
import time
import string
import random
import unidecode
import Levenshtein

from discord import Embed, Color

intention_callbacks = {}
intentions_help = []


class Arguments():
    '''
    This class is used to represent arguments (strings, numbers and urls)
    inside messages content.

    .. note::
        *String* is anything inside quotes.

    .. attribute:: string(str)
        An string in the given message content.

    .. attribute:: number(int)
        A number in the given message content.

    .. attribute:: yt_url(str)
        A YouTube url in the given message content.

    You will receive an intance object of this class in your intention handlers.
    If there is no arguments in the message content class attributes will be *None*.

    Quick example of reading arguments:

    .. code-block:: python

        # ...

        @erina.intention
        async def some_nice_intention(ctx, args):
            if args.string:
                await ctx.channel.send("String argument: %s" %(args.string))

            if args.number:
                await ctx.channel.send("Numeric argument: %i" %(args.number))

            if args.yt_url:
                await ctx.channel.send("YouTube url: %s" %(args.yt_url))
    '''
    def __init__(self, content):
        '''
        Search for arguments in the given string.

        Args:
            content (str): Message content.
        '''
        self.string = None
        self.number = None
        self.yt_url = None

        regex1 = re.search(r'(\'|\")(.*)(\'|\")', content)
        regex2 = re.search(r'([0-9]+)', content)
        regex3 = re.search(
            r'(https?://)?(www\.)?'
            '(youtube|youtu|youtube-nocookie)\.(com|be)/'
            '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})', content)

        if regex1:
            self.string = regex1.group(2)

        if regex2:
            self.number = int(regex2.group(1))

        if regex3:
            self.yt_url = "http://www.youtube.com/watch?v=%s" %(regex2.group(6))


class Conversation():
    '''
    This class handle the received messages and process them to recognize the
    message intention based on the levenshtein distance between input message
    and loaded intentions.

    .. important::
        You will use this class throw **ErinaBot.conversation** instance.
    '''
    def __init__(self):
        '''Initializes dictionary and context vars.
        '''
        self.dictionary = []
        self.context = {}

    def __clear_string(self, text):
        '''Removes strings between quotes also removes punctuations
        and non ascii characters and also removes bot's name (eri) and
        youtube url's in order to increase recognition accurate.

        Args:
            text (str): String to clear.
        '''
        text = text.lower()
        text = unidecode.unidecode(text)
        text = re.sub(r'(\"|\')(.+)(\"|\')', "", text)
        text = re.sub(r'([0-9]+)', "", text)
        text = re.sub(r'(^e+r+i+\s+)|(\s+e+r+i+$)|(\s+e+r+i+\s+)', "", text)
        text = re.sub(
                r'(https?://)?(www\.)?'
                '(youtube|youtu|youtube-nocookie)\.(com|be)/'
                '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})', "", text)

        text = ''.join([word for word in text if word not in string.punctuation])

        return text

    def get_context(self, ctx):
        '''Gets the context value for the especified context.

        Args:
            ctx (discord.Message): Context.

        Returns:
            str: The context value.
        '''
        key = "%s" %(ctx.channel.id)
        if key in self.context.keys():
            return self.context[key]

        else:
            return ''

    def set_context(self, ctx, value):
        '''Sets the context value for the especified context.

        Args:
            ctx (discord.Message): Context.
            value (str): Context value.
        '''
        key = "%s" %(ctx.channel.id)
        self.context[key] = value

    def clear_context(self, ctx):
        '''Clears the context value for the especified context.

        Args:
            ctx (discord.Message): Context.
        '''
        key = "%s" %(ctx.channel.id)
        self.context[key] = ''

    def set_context_var(self, ctx, var, val):
        '''Creates a context var for the especified context.

        Args:
            ctx (discord.Message): Context.
            var (str): Var name.
            val (mixed): Var value, it could be whatever you want.
        '''
        key = "%s.%s" %(ctx.channel.id, var)
        self.context[key] = val

    def get_context_var(self, ctx, var):
        '''Gets the value of the especified context var.

        Args:
            ctx (discord.Message): Context.
            var (str): Var name.

        Returns:
            mixed: Var value.
        '''
        key = "%s.%s" %(ctx.channel.id, var)
        if key in self.context.keys():
            return self.context[key]

        else:
            return ''

    def load_dictionary(self, file):
        '''Loads a dictionary of intentions or dialogs. Must be a .yml file.
        see *intentions.yml* and *dialogs.yml* for reference.

        Args:
            file(str): Intentions or Dialogs disctionary path.
        '''
        file = open(file)
        content = file.read()
        file.close()

        loaded = yaml.load(content)

        for question, answer in loaded:
            if isinstance(question, list):
                for sub_question in question:
                    self.dictionary.append([self.__clear_string(sub_question), answer])
            else:
                self.dictionary.append([self.__clear_string(question), answer])

    def talking_to_me(self, text):
        '''Look for the bot's name (eri) in the given string.

        Args:
            text (str): String to search in.

        Returns:
            boolean: True if the bot's name is in the given string.
        '''
        text = text.lower()
        regex = re.search(r'(^e+r+i+\s+)|(\s+e+r+i+$)|(\s+e+r+i+\s+)', text)

        if regex:
            return True

        return False

    async def recognize(self, msg):
        '''Reconize the intention of the given string and call the appropriate
        intention handler. If the recognition result is a dialog not and intention
        it will send the dialog answer.

        .. note::
            If the intention handler is not defined will not throw an error it will
            just log an alert.

        *How to use it:*

        .. code-block:: python

            # Bot initialization, intention dictionary load
            # and intention definition here

            @client.event
            async def on_message(message):
                if message.author == client.user:
                    return

                if (not client.user in message.mentions)\\
                    and (not message.mention_everyone)\\
                    and (not erina.conversation.talking_to_me(message.content)):
                    return

                # recognize the incoming message
                await erina.conversation.recognize(message)

            client.run(ACCESS_TOKEN)

        Args:
            msg (discord.Message): Message to recognize.
        '''
        min_distance = 9999
        index = 0

        text = self.__clear_string(msg.content)

        for i in range(len(self.dictionary)):
            question = self.dictionary[i][0]
            distance = Levenshtein.distance(question, text)

            if distance < min_distance:
                min_distance = distance
                index =  i

        intention = self.dictionary[index][1]

        if intention == 'help':
            for help in intentions_help:
                embed = Embed(description=help,
                                color=Color.purple())

                await msg.channel.send(embed=embed)
                time.sleep(1)

            return

        if isinstance(intention, list):
            answer = random.choice(intention)
            await msg.channel.send(answer)

        else:
            if not intention in intention_callbacks.keys():
                print("ConversationError: recognized intention '%s' is not implemented" %(intention))
                return

            print("Recognized intention: %s" %(intention))
            await intention_callbacks[intention](msg, Arguments(msg.clean_content))


def handle_intention(func):
    '''Decorator for intention handler declaration.
    '''
    intention_callbacks[func.__name__] = func
    if func.__doc__:
        intentions_help.append(func.__doc__)

    return func

if __name__ == "__main__":
    conversation = Conversation()

    conversation.load_dictionary("intentions.yml")
    conversation.load_dictionary("dialogs.yml")

    while True:
        text = input("Di algo: ")
        answer = conversation.recognize(text)

        print("Prediction: %s" %(answer))
