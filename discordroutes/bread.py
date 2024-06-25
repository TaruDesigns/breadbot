import json
import os
from typing import Tuple

import discord
from dotenv import load_dotenv
from loguru import logger

from db.models import upsert_message_stats

load_dotenv()
download_directory = os.path.join(
    os.getcwd(), os.environ.get("DISCORD_DOWNLOAD_DIRECTORY")
)
discord_bread_channels = json.loads(os.environ.get("DISCORD_BREAD_CHANNELS"))
allowed_bread_groups = json.loads(os.environ.get("DISCORD_BREAD_ROLE"))


async def send_bread_message(
    message: discord.Message, overrideconfidence: bool = False
) -> Tuple[discord.Message, dict, int]:
    """Main "bread analyze" function -> calls the compute function and sends message based on results

    Args:
        message (_type_): _description_
    """

    # Download and process each attached picture
    for attachment in message.attachments:
        filename = os.path.join(download_directory, attachment.filename)
        if not os.path.exists(download_directory):
            os.makedirs(download_directory)
        await attachment.save(filename)
        logger.info(f"Saved {attachment.filename} to {download_directory}")
        async with message.channel.typing():
            # Compute: Get file (or None) and comment to be used
            discord_file, breadcomment = await compute_bread_message(
                filename=filename,
                overrideconfidence=overrideconfidence,
                ogmessage_id=message.id,
            )
            # Send the image back with the comment
            sentmessage = await message.channel.send(
                file=discord_file, content=breadcomment, reference=message
            )
            return sentmessage


async def compute_bread_message(
    filename: str, overrideconfidence: bool = False, ogmessage_id: int = 1
) -> Tuple[discord.File, str]:
    """Main "bread compute" function -> Does all the compute calls
    and returns the artifacts to be sent on the discord message

    Args:
        message (_type_): _description_
    """
    # Lazy import to make sure it's always updated
    from breadinfer.inference import inferhandler

    # Set confidences based on whether this was an "override" request or default
    if overrideconfidence:
        breadpic_confidence = float(os.environ.get("OVERRIDE_DETECTION_CONFIDENCE"))
        breadlabel_confidence = float(os.environ.get("MIN_BREAD_LABEL_CONFIDENCE"))
        breadseg_confidence = float(os.environ.get("MIN_BREAD_SEG_CONFIDENCE"))
    else:
        breadpic_confidence = float(os.environ.get("BREAD_DETECTION_CONFIDENCE"))
        breadlabel_confidence = float(os.environ.get("FILTER_BREAD_LABEL_CONFIDENCE"))
        breadseg_confidence = float(os.environ.get("FILTER_BREAD_SEG_CONFIDENCE"))
    # Compute labels, this also works as detection with confidence
    labels = await inferhandler.async_labels_from_imgpath(filename)
    # First we check if it is a bread picture at all
    if "bread" in labels.keys():
        # And then we check if it is good enough of a bread picture to do segmentation on it
        if labels["bread"] > breadpic_confidence:
            breadcomment = inferhandler.get_message_content_from_labels(
                predictions=labels, min_confidence=breadlabel_confidence
            )
            # We try to get the segmentation and roundness.
            try:
                (
                    out_img,
                    result,
                ) = await inferhandler.async_segmentation_from_imgpath(
                    input_img_path=filename, confidence=breadseg_confidence
                )
                # We get it here to use it later on and also save it on db
                roundness = inferhandler.estimate_roundness_from_mask(result)
                roundcomment = inferhandler.get_message_from_roundness(roundness)
                discord_file = discord.File(out_img)
                breadcomment = breadcomment + roundcomment
                try:
                    upsert_message_stats(
                        ogmessage_id=ogmessage_id,
                        roundness=roundness,
                        labels_json=labels,
                    )
                except Exception as e:
                    logger.error(
                        f" Couldn't upsert roundness+label data for {ogmessage_id}: {e}"
                    )
            # TODO get the proper exception(s)
            except Exception as e:
                logger.error(e)
                discord_file = discord.File(filename)
                breadcomment = (
                    breadcomment
                    + ". I couldn't find the shape dough. (Get it? Though - dough ehehehehe)"
                )
            # Send the image back with the comment
            file, content = discord_file, breadcomment
            return file, content
        else:
            # Bread was found but not confident enough
            file, content = (
                None,
                "This is only very mildly bread. Metaphysical bread even.",
            )
            return file, content
        ...
    else:
        # Bread label wasn't found at all
        file, content = None, "This isn't bread at all!"
        return file, content
        ...


async def check_bread_message(
    message, allowed_channels=discord_bread_channels, allowed_group=allowed_bread_groups
) -> None:
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


async def check_areyousure_message(message: discord.Message, botuser: str) -> None:
    """Check "Are you sure?" Message: User replies to message by bot and tells it to rerun the inference with lower confidence. Message can only be valid if it's a reply to a message done by the bot itself

    Args:
        message (DiscordMessage): DiscordMessage object
        botuser (str): bot user

    Returns:
        Bool: Whether it passes all checks or not
    """

    trigger_texts = ["are you sure", "fr no cap", "no way"]
    logger.debug("Checking message for areyousure content...")
    # Check if the message is a reply
    if not (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author == botuser
    ):
        return False
    # Check if message includes "are you sure or similar words"
    if not any(trigger in message.content.lower() for trigger in trigger_texts):
        return False
    return True
