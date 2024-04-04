import asyncio
import json
import os
import sys

import discord
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from loguru import logger

from discordroutes import bread as breadroute

load_dotenv()


app = FastAPI()
# Discord Init
# This example requires the 'message_content' intent.
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)

# Logger
logger.remove()  # remove the old handler. Else, the old one will work along with the new one you've added below'
logger.add(sys.stdout, level="DEBUG")


@app.on_event("startup")
async def startup_event():  # this fucntion will run before the main API starts
    asyncio.create_task(bot.start(os.environ.get("DISCORD_TOKEN")))
    await asyncio.sleep(4)  # optional sleep for established connection with discord
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")


@app.get("/")
async def root(msg: str):  # API endpoint for sending a message to a discord's user
    user = await send_message(msg)
    return {"Message": f"'{msg}' sent to {user}"}


async def send_message(message):
    # This is just a test function
    user = await bot.fetch_user("206734328879775746")
    await user.send(message)
    return user  # for optional log in the response of endpoint


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
    if await breadroute.check_bread_message(message=message):
        await breadroute.send_bread_message(message=message)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5987)
