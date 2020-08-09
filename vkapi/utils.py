from jinbot import config

import traceback


def remove_admin_prefix(text: str) -> str:
    """
    Remove admin prefix from text and return

    :param text: Admin command
    :type text: str
    :return: Changed admin command
    :rtype: str
    """
    return text[len(config.ADMIN_COMMAND_PREFIX):]


def extract_params(command_and_text):
    command_and_params = command_and_text[0].split("-")
    command = command_and_params[0]
    text = " ".join(command_and_text[1:])

    message_filter = (
        command_and_params[1]
        if len(command_and_params) >= 2
        else config.ADMIN_COMMAND_SEND_MESSAGE_FILTER_DEFAULT
    )
    max_users = (
        int(command_and_params[2])
        if len(command_and_params) >= 3
        else float("inf")  # All users
    )
    min_age = (
        int(command_and_params[3])
        if len(command_and_params) >= 4
        else config.ADMIN_COMMAND_SEND_MESSAGE_MIN_AGE_DEFAULT
    )
    earlier = (
        int(command_and_params[4])
        if len(command_and_params) >= 5
        else config.ADMIN_COMMAND_SEND_MESSAGE_EARLIER_DEFAULT
    )

    return command, text, message_filter, max_users, min_age, earlier


def extract_users(conversations, min_age, now, earlier):
    try:
        if earlier:
            # Older than min age
            user_ids = [
                conversation.last_message.peer_id
                for conversation in conversations.items
                if (now - conversation.last_message.date) > min_age
            ]

        else:
            # Younger than min age
            user_ids = [
                conversation.last_message.peer_id
                for conversation in conversations.items
                if (now - conversation.last_message.date) < min_age
            ]

        return user_ids
    except AttributeError:
        traceback.print_exc()
        return []
