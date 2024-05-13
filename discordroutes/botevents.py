import logging

import discord
from loguru import logger

from discordroutes import bread as breadroute

# Discord Init
# This example requires the 'message_content' intent.
intents = discord.Intents.default()
intents.message_content = True
discord.utils.setup_logging(level=logging.INFO)
bot = discord.Client(intents=intents)


@bot.event
async def on_message(message):
    logger.debug("Received message!")
    if message.author == bot.user:
        # This is just to avoid endlessly triggering itself
        return
    if message.content.startswith("$hello"):
        # Just a test/health check function
        await message.channel.send(content="Hello!", reference=message)

    # Check Bread Candidate Message
    try:
        if await breadroute.check_bread_message(message=message):
            await breadroute.send_bread_message(
                message=message, overrideconfidence=False
            )
        elif await breadroute.check_areyousure_message(
            message=message, botuser=bot.user
        ):
            logger.debug("Are you sure message! Do everything again!")
            ogmessageref = message.reference.resolved.reference
            ogmessage = await get_message_by_id(
                guild_id=ogmessageref.guild_id,
                channel_id=ogmessageref.channel_id,
                message_id=ogmessageref.message_id,
            )
            if True or await breadroute.check_bread_message(message=ogmessage):
                await breadroute.send_bread_message(
                    message=ogmessage, overrideconfidence=True
                )

    except Exception as e:
        logger.error(e)
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
