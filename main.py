import asyncio
import json
import logging
import os
import sys

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger

from apiroutes import api_router
from db.models import create_db
from discordroutes.botevents import bot

load_dotenv()

app = FastAPI()
app.include_router(api_router)


# Logger
logger.remove()  # remove the old handler. Else, the old one will work along with the new one you've added below'
logger.add(sys.stdout, level="DEBUG")


@app.on_event("startup")
async def startup_event():  # this function will run before the main API starts
    asyncio.create_task(bot.start(os.environ.get("DISCORD_TOKEN")))
    await asyncio.sleep(4)  # optional sleep for established connection with discord
    logger.info(f"{bot.user} has connected to Discord!")
    create_db()
    logger.info("Started DB")


@app.get("/")
async def docs_redirect():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5987)
