import traceback
import typing

from jinbot import config


def remove_admin_prefix(text: str) -> str:
    """Remove admin prefix from text and return

    :param text: Admin command
    :type text: str
    :return: Changed admin command
    :rtype: str
    """
    return text[len(config.ADMIN_COMMAND_PREFIX) :]


def extract_params(command_and_text: str) -> typing.Tuple[str, str, str, int, int, int]:
    """Extract params from admin command

    :param command_and_text: String that contains command, params and text of message
    :type command_and_text: str
    :return: tuple of `command, text, message_filter, max_users, min_age, earlier` that parsed from given string
    :rtype: tuple
    """
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


def extract_users(conversations: list, min_age: int, now: float, earlier: int) -> list:
    """Returns list of users ids that match to given conditions

    :param conversations: List of conversations that contains user and last message information
    :type conversations: list
    :param min_age: Minimum age of users last message
    :type min_age: int
    :param now: Timestamp of command beginning
    :type now: float
    :param earlier: if `1` then keep only messages that are older than `min_age`, keep younger otherwise
    :type earlier: int
    :return: List of users ids that match to given conditions
    :rtype: list
    """
    try:
        if earlier:
            # Older than min age
            user_ids = [
                conversation.last_message.peer_id
                for conversation in conversations
                if getattr(conversation, "last_message", False)
                and ((now - conversation.last_message.date) > min_age)
            ]

        else:
            # Younger than min age
            user_ids = [
                conversation.last_message.peer_id
                for conversation in conversations
                if getattr(conversation, "last_message", False)
                and (now - conversation.last_message.date) < min_age
            ]

        return user_ids

    except AttributeError:
        traceback.print_exc()
        return []
