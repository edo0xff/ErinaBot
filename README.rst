ErinaBot
========

I know there is a lot of bots for discord that do a lot of nice stuff but I want a bot who I can talk naturally so thats why I'm developing this.

First of all I'm not using neural networks for Natural Language Processing yet because I'm still developing a good architecture that works acceptable.  Instead of Neural Networks Erina just calculates the `Levenshtein distance <https://dzone.com/articles/the-levenshtein-algorithm-1>`_ between the input message and its related intention phrases, then chooses the intention with the lowest distance. And that's it. It is very simple but it works.

This bot works with two important concepts: *intentions* and *dialogs*, the first ones refers to actions that the bot can execute like *play_music*, *send_meme* and we define this intentions in a file called *intentions.yml* (so you must be familiarized with yaml syntax) like this:

*intentions.yml*

.. code-block:: none

    -
        -
            - send some memes
            - i want to see a meme
            - send me a meme
        - send_meme
	-
	    -
	        - what time is it
	        - show time
	        - system time
	    - show_time

As you can notice the yaml intentions file is an array of arrays where the first value is an array (yes I like arrays) containing some phrases related to the intention which is the second value of the array. So the bot will look at this phrases searching the most similar to the input message and executing the intention related to it.

So, now what? How do I send dank memes when the bot find that the input message is related to *send_meme* intention? That's a good question. Look at
`ErinaBot.intention <https://erinabot.readthedocs.io/en/latest/#erinabot>`_ documentation.

Also I said the bot works with *dialogs* too. That's a yaml file called *dialogs.yml* but it's kinda different:

*dialogs.yml*

.. code-block:: none

    -
        -
            - hi
            - hello
            - hi how are you
            - whats up
        -
            - Hello!
            - Hey!
            - Sup boy!
    -
        -
            - whats your name
            - who are you
        -
            - I'm a robot!
            - I'm your master B)
            - I don't know :(

Both of the array values are arrays containing *questions* -> *answers* so when the bot determines that the input message is similar to any question a random answer is choosed and send it to the channel where the message came from.

Example
~~~~~~~

To handle those *intentions* and *dialogs* your bot code should looks like this:

.. code-block:: python

  import time
  import discord
  import ErinaBot as erina
  from datetime import datetime

  ACCESS_TOKEN = "your_atoken_here"

  client = discord.Client()

  erina.conversation.load_dictionary("intentions.yml")
  erina.conversation.load_dictionary("dialogs.yml")

  @erina.intention
  async def show_time(ctx, args):
    """
      **Show system time**

      You can ask me for show system time :smiley:
    """
    date = datetime.utcfromtimestamp(time.time())
    date = date.strftime('%Y-%m-%d %H:%M')

    await ctx.channel.send("Server time: %s" %(date))

  @erina.intention
  async def send_meme(ctx, args):
    """
      **Sending nice meme**

      You can ask me for some memes B)
    """
    img_url = "https://imgur.com/a/5ybu9TO"

    embed = (discord.Embed(title="Dank meme", description="I found 	this meme for you <3")
              .set_image(img_url))

    await ctx.channel.send(embed=embed)

  @client.event
  async def on_ready():
    print("Erina-san is ready!")
    activity = discord.Activity(type=discord.ActivityType.watching, name="Movies!")
    await client.change_presence(status=discord.Status.online, activity=activity)

  @client.event
  async def on_message(message):
    if message.author == client.user:
      return

    if (not client.user in message.mentions)\
      and (not message.mention_everyone)\
      and (not erina.conversation.talking_to_me(message.content)):
      return

    # recognize the incoming message
    await erina.conversation.recognize(message)

  client.run(ACCESS_TOKEN)

By the way, I already made a complete example in *main.py* which has some dialogs to stablish conversations and do things like play music also it searches youtube videos and download them as mp3, it sends memes, it tracks lastest COVID statistics by country. (note. I'm spanish speaker so that example is in spanish).

So if you run that example you can ask to the bot things like:

.. code-block:: none

  you: Hola eri!
  bot: Hola :)!
  you: Eri quiero escuchar "Ghost - rats"
  bot: *plays ghost - rats*

Installation
~~~~~~~~~~~~

.. note::

  These installation instructions and commands are for linux-debian based systems.

Clone the repository:

.. code-block:: none

    $ git clone https://github.com/0oeduardoo0/ErinaBot.git

`ErinaBot.db <https://erinabot.readthedocs.io/en/latest/#erinabot>`_ is an Mongo database, so you need to install mongo db:

.. code-block:: none

    $ sudo apt install mongodb

Install the required modules:

.. code-block:: none

    $ pip3 install -r requirements.txt

Set your bot access token `here <https://github.com/0oeduardoo0/ErinaBot/blob/master/main.py#L15>`_

Run example *main.py*:

.. code-block:: none

  $ python3 main.py

To run it in background:

.. code-block:: none

    $ sudo chmod +x start
    $ ./start

And to stop it:

.. code-block:: none

    $ sudo chmod +x stop
    $ ./stop

Once the bot is running invite him to your discord server then say hello (the only name
that the bot recognize is *eri* and she speak only spanish for now. See. #TODO):

.. code-block:: none

   Hola eri!

Or you can just tag the bot in the message:

.. code-block:: none

   @Botname help

Or send a message like this (only spanish for now):

.. code-block:: none

   Hola eri ¿Qué puedes hacer?

TODO
====

- Record a demo video to show how the bot works.
- Make an english example.
- Implements suffle and loop `_music_player.py <https://github.com/0oeduardoo0/ErinaBot/blob/master/ErinaBot/_music_player.py>`_.
- Parse more kind of arguments `_conversation.py <https://github.com/0oeduardoo0/ErinaBot/blob/master/ErinaBot/_conversation.py#L78>`_.
- Make this function works with different bot names `_conversation.py <https://github.com/0oeduardoo0/ErinaBot/blob/master/ErinaBot/_conversation.py#L226>`_.
- Implements Logger.
- Implements Neural Networks for intent recognition (I'm testing Convolutional-Neural-Network and Recurrent-Neural-Network (LSTM) but I'm not getting better results than Levenshtein distance).

- Add more functionalities to the bot.

  - Roleplay
  - Send gifs
  - Games

Links
=====

- `API Reference documentation <https://erinabot.readthedocs.io/en/latest>`_
- `Discord Server <https://discord.gg/96aCQtv>`_
- `How to get bot tokens: guide step by step <https://www.writebots.com/discord-bot-token/>`_

CONTRIB
=======

Enter to discord server and let's talk about what we have to do!
