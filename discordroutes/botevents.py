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
            await breadroute.send_bread_message(message=message)
    except Exception as e:
        logger.error(e)
        logger.error(e)


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
