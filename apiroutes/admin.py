from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

from discordroutes.botevents import bot

router = APIRouter()


@router.get("/senddm")
async def send_dm(msg: str):  # API endpoint for sending a message to a discord's user
    user = await send_message(msg)
    return {"Message": f"'{msg}' sent to {user}"}


@router.get("/status")
async def pingpong():  # Status check
    return {"status": "ok"}


async def send_message(message, user_id: str = 206734328879775746) -> str:
    # This is just a test function

    user = await bot.fetch_user(user_id)
    await user.send(message)
    return {
        "user": user,
        "message": message,
    }
