import logging

import discord
from loguru import logger

from db.models import get_minmax_roundness_byuserid, upsert_message_discordinfo
from discordroutes import bread as breadroute

# Discord Init
# This example requires the 'message_content' intent.
intents = discord.Intents.default()
intents.message_content = True
discord.utils.setup_logging(level=logging.INFO)
bot = discord.Client(intents=intents)


@bot.event
async def on_message(message: discord.Message):
    logger.debug("Received message!")
    if message.author == bot.user:
        # This is just to avoid endlessly triggering itself
        return
    if message.content.startswith("$hello"):
        # Just a test/health check function
        await message.channel.send(content="Hello!", reference=message)
    if message.content.startswith("$breadstats --self"):
        results = get_minmax_roundness_byuserid(message.author.id)
        reply_content = f""""
                            Hello {message.author.name}:
                            Min roundness:  {results["min_roundness"]} on message: {results["min_roundness_url"]},
                            Max roundness {results["max_roundness"]} on message: {results["max_roundness_url"]}
                            """
        await message.channel.send(content=reply_content, reference=message)
    if message.content.startswith("$breadstats --top"):
        await message.channel.send(content="Not yet", reference=message)

    # Check Bread Candidate Message
    try:
        if await breadroute.check_bread_message(message=message):
            sentmessage = await breadroute.send_bread_message(
                message=message, overrideconfidence=False
            )
            # Store data in DB
            upsert_message_discordinfo(
                ogmessage_id=message.id,
                replymessage_jump_url=sentmessage.jump_url,
                replymessage_id=sentmessage.id,
                author_id=message.author.id,
                channel_id=message.channel.id,
                guild_id=message.guild.id,
            )
        elif await breadroute.check_areyousure_message(
            message=message, botuser=bot.user
        ):
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
            sentmessage = await breadroute.send_bread_message(
                message=ogmessage, overrideconfidence=True
            )
            # Store data in DB
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


async def get_message_by_id(guild_id: int, channel_id: int, message_id: int):
    guild = bot.get_guild(guild_id)
    if guild is None:
        logger.error("Guild not found")
        raise ValueError("Guild not found")

    channel = guild.get_channel(channel_id)
    if channel is None:
        print("Channel not found")
        raise ValueError("Channel not found")

    message = await channel.fetch_message(message_id)
    return message


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
