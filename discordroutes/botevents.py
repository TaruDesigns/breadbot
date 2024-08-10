import logging
import shlex

import discord
from loguru import logger

from db.models import (
    OrderBy,
    get_minmax_roundness_byuserid,
    get_minmax_roundness_leaderboard,
    select_user_info,
    upsert_message_discordinfo,
    upsert_user_info,
)
from discordroutes import bread as breadroute
from plots import plots

# This example requires the 'message_content' intent.
intents = discord.Intents.default()
intents.message_content = True
discord.utils.setup_logging(level=logging.INFO)
bot = discord.Client(intents=intents)


async def breadstats_handler(message: discord.Message, args: list[str]):
    """Main handler for $breadstats message.

    Args:
        message (discord.Message): Discord message
        args (list[str]): message content arguments
    """
    if len(args) < 2:
        await message.channel.send(content="Not enough arguments", reference=message)
    elif args[1] == "--history":
        ...
        plot_filepath = plots.plot_roundness_by_user(message.author.id)
        discord_file = discord.File(plot_filepath)
        reply_content = f"Here's your dumb graph"
        await message.channel.send(content=reply_content, reference=message, file=discord_file)

    elif args[1] == "--self":
        # Return results (top 1) for current user
        results_min = get_minmax_roundness_byuserid(message.author.id, orderby=OrderBy.ASC.value)
        min_roundness_percent = round(results_min["roundness"] * 100, 2) if results_min["roundness"] is not None else 0
        results_max = get_minmax_roundness_byuserid(message.author.id, orderby=OrderBy.DES.value)
        max_roundness_percent = round(results_max["roundness"] * 100, 2) if results_max["roundness"] is not None else 0
        reply_content = f"""
                            Hello {message.author.name}:
                            Min roundness:  {min_roundness_percent:.2f}% on message: {results_min["roundness_url"]},
                            Max roundness {max_roundness_percent:.2f}% on message: {results_max["roundness_url"]}
                            """
        await message.channel.send(content=reply_content, reference=message)
    elif args[1] == "--top":
        # Return "top X" for the server
        try:
            limit = int(args[2])
            append_to_limit = ""
            if limit > 10:
                limit = 10
                append_to_limit = f" (You're asking too much, nobody has seen a top {limit} ever)"
        except Exception as e:
            logger.warning(e)
            limit = 3
            append_to_limit = " (You didn't enter a valid number. Shame on you)"
        # Query DB and get results
        results_max = get_minmax_roundness_leaderboard(limit, orderby=OrderBy.DES.value)
        results_min = get_minmax_roundness_leaderboard(limit, orderby=OrderBy.ASC.value)
        # Generate message part for top X
        reply_content_max = f"Top {limit}{append_to_limit}:"
        for idx, val in enumerate(results_max):
            roundness_percent = round(val["roundness"] * 100, 2) if val["roundness"] is not None else 0
            user_info = select_user_info(val["author_id"])
            if user_info is None:
                user_info = {"author_name": "unknown"}
            reply_content_max = f"""{reply_content_max}\n #{idx + 1}: {user_info["author_name"]} with {roundness_percent:.2f}% on message {val["jump_url"]}"""
        # Generate message part for worst X
        reply_content_min = "Worst 3:"
        for idx, val in enumerate(results_min):
            user_info = select_user_info(val["author_id"])
            if user_info is None:
                user_info = {"author_name": "unknown"}
            roundness_percent = round(val["roundness"] * 100, 2) if val["roundness"] is not None else 0
            reply_content_min = f"""{reply_content_min}\n #{idx + 1}: {user_info["author_name"]} with {roundness_percent:.2f}% on message {val["jump_url"]}"""

        reply_content = f"{reply_content_max}\n{reply_content_min}"
        await message.channel.send(content=reply_content, reference=message)


async def hello_handler(message: discord.Message, args: list[str]):
    """Basic handler for hello message - just a health check

    Args:
        message (discord.Message): _description_
        args (list[str]): _description_
    """
    await message.channel.send(content="Hello!", reference=message)


async def breadinference_handler(message: discord.Message, args: list[str]):
    """Main bread inference handler, gets all the relevant data and inserts in DB

    Args:
        message (discord.Message): _description_
        args (list[str]): _description_
    """
    # Check Bread Candidate Message
    try:
        if await breadroute.check_bread_message(message=message):
            sentmessages = await breadroute.send_bread_message(message=message, overrideconfidence=False)
            # Store data in DB
            for sentmessage in sentmessages:
                upsert_message_discordinfo(
                    ogmessage_id=message.id,
                    replymessage_jump_url=sentmessage.jump_url,
                    replymessage_id=sentmessage.id,
                    author_id=message.author.id,
                    channel_id=message.channel.id,
                    guild_id=message.guild.id,
                )
        elif await breadroute.check_areyousure_message(message=message, botuser=bot.user):
            logger.debug("Are you sure message! Do everything again!")
            # Timeline is: User message with bread pic -> Bot reply -> User reply to bot reply ; Invert to get OG message
            ogmessageref = message.reference.resolved.reference
            # For some reason it won't automatically resolve all replies so I have to do it manually
            ogmessage = await get_message_by_id(
                guild_id=ogmessageref.guild_id,
                channel_id=ogmessageref.channel_id,
                message_id=ogmessageref.message_id,
            )
            # TODO double check that it the og message is a bread message?
            sentmessages = await breadroute.send_bread_message(message=ogmessage, overrideconfidence=True)
            # Store data in DB
            for sentmessage in sentmessages:
                upsert_message_discordinfo(
                    ogmessage_id=ogmessage.id,
                    replymessage_jump_url=sentmessage.jump_url,
                    replymessage_id=sentmessage.id,
                    author_id=message.author.id,
                    channel_id=message.channel.id,
                    guild_id=message.guild.id,
                )

    except Exception as e:
        logger.error(e)


async def help_handler(message: discord.Message, args: list[str]):
    help_message = """Available commands:
                    $breadstats --self : Get your roundness bread stats
                    $breadstats --top X : Get the server roundness breadstats (X is a number)
                    $breadstats --history : Get your roundness history
                    $help : you just used this
                    """
    await message.channel.send(content=help_message, reference=message)


mapping_functions = {
    "$breadstats": breadstats_handler,
    "$hello": hello_handler,
    "$bread": breadinference_handler,
    "$help": help_handler,
}


@bot.event
async def on_message(message: discord.Message):
    logger.debug("Received message!")
    # Cache the user info
    upsert_user_info(
        author_id=message.author.id,
        author_nickname=message.author.nick,
        author_name=message.author.name,
    )
    if message.author == bot.user:
        # This is just to avoid endlessly triggering itself
        return
    message_args = shlex.split(message.content.strip())
    func_args = (message, message_args)
    if message_args and message_args[0].startswith("$") and message_args[0] in mapping_functions.keys():
        await mapping_functions[message_args[0]](*func_args)
    else:
        # Default - assume it was a bread message and scan it anyway
        await breadinference_handler(message=message, args=message_args)


async def get_message_by_id(guild_id: int, channel_id: int, message_id: int):
    guild = bot.get_guild(guild_id)
    if guild is None:
        logger.error("Guild not found")
        raise ValueError("Guild not found")

    channel = guild.get_channel(channel_id)
    if channel is None:
        logger.info("Channel not found")
        raise ValueError("Channel not found")

    message = await channel.fetch_message(message_id)
    return message


async def get_user_by_id(user_id: int):
    user = await bot.fetch_use(user_id)
    return user


@bot.event
async def on_ready():
    logger.info(f"We have logged in as {bot.user}")
