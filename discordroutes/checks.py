from loguru import logger


async def check_bread_message(message, allowed_channels, allowed_group):
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
