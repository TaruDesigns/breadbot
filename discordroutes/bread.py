import json
import os

import discord
from dotenv import load_dotenv
from loguru import logger

from breadinfer import infer

load_dotenv()
download_directory = os.path.join(
    os.getcwd(), os.environ.get("DISCORD_DOWNLOAD_DIRECTORY")
)
discord_bread_channels = json.loads(os.environ.get("DISCORD_BREAD_CHANNELS"))
allowed_bread_groups = json.loads(os.environ.get("DISCORD_BREAD_ROLE"))


async def send_bread_message(message):
    """Main "bread analyze" function -> Does all the compute
    and sends a reply

    Args:
        message (_type_): _description_
    """
    # Download and save each attached picture
    for attachment in message.attachments:
        filename = os.path.join(download_directory, attachment.filename)
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
        await attachment.save(filename)
        print(f"Saved {attachment.filename} to {download_directory}")
        labels = infer.labels_from_imgpath(filename)
        if "bread" in labels.keys():
            if labels["bread"] > float(os.environ.get("MIN_BREAD_CONFIDENCE")):
                breadcomment = infer.get_message_content_from_labels(labels=labels)
                out_img, result = infer.segmentation_from_imgpath(
                    input_img_path=filename
                )
                discord_file = discord.File(out_img)
                await message.channel.send(
                    file=discord_file,
                    content=breadcomment,
                    reference=message,
                )
            else:
                await message.channel.send(
                    content="This is only very mildly bread. Metaphysical bread even.",
                    reference=message,
                )
        else:
            await message.channel.send(
                content="This isn't bread at all!",
                reference=message,
            )


async def check_bread_message(
    message, allowed_channels=discord_bread_channels, allowed_group=allowed_bread_groups
):
    """Check Possible Bread Message: Message must be in one of the allowed channels
    made by a "Breadmancer" user
    and have attachments

    Args:
        message (DiscordMessage): DiscordMessage object
        allowed_channels (List): List of allowed channels for the message
        allowed_group (List): List of allowed roles for the user

    Returns:
        Bool: Whether it passes all checks or not
    """

    logger.debug("Checking message for bread content...")
    # Check if the message is in an allowed channel
    if message.channel.id not in allowed_channels:
        logger.debug("Message not in allowed channel")
        return False

    # Check if the author is from the specific group
    author = message.author
    author_role_ids = set([role.id for role in author.roles])
    allowed_role_ids = set(allowed_group)

    if not bool(author_role_ids.intersection(allowed_role_ids)):
        logger.debug("Message not from correct author in group")
        return False

    # Check if there are any embedded pictures
    if len(message.attachments) == 0:
        logger.debug("Message without attachments")
        return False
    logger.debug("Bread message candidate detected")
    return True
