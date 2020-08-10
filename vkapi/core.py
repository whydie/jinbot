import typing
import time
import asyncio
import traceback

from vkbottle.utils.exceptions import VKError

from vkapi.utils import extract_params, extract_users
from jinbot import config


async def send_messages(
        bot,
        message: str,
        message_filter: str,
        min_age: int,
        max_users: typing.Union[int, float],
        earlier: int = 1,
):
    """
    Send message to a group of users

    :param bot: VK bot object
    :param message: Message text
    :type message: str
    :param message_filter: Message filter. e.g. `all`, `unread`, `important`, `unanswered`
    :type message_filter: str
    :param min_age: Minimal age of last message to consider user for sending
    :type min_age: int
    :param max_users: Maximal number of users
    :type max_users: int, float
    :param earlier: if 1, then send messages to users with earlier last_message, later otherwise
    :type earlier: int, optional
    """
    ended = False
    offset = 0
    now = time.time()

    while not ended:
        # noinspection PyBroadException
        try:
            conversations = await bot.api.messages.get_conversations(
                offset=offset,
                count=200,
                filter=message_filter,
                extended=0,
                group_id=bot.group_id,
            )

            if not conversations.items or offset >= max_users:
                # Either `max_users` limit reached, or got no new items
                ended = True

            else:
                await asyncio.sleep(config.ADMIN_TIMEOUT_NOTIFY)
                offset += 200

                user_ids = extract_users(conversations, min_age, now, earlier)
                first_id = max_users if max_users < len(user_ids) else 100

                if user_ids:
                    await bot.api.messages.send(
                        user_ids=user_ids[:first_id],
                        message=message,
                        random_id=bot.extension.random_id(),
                    )

                    if len(user_ids) > 100:
                        # Second part of users, if exist
                        await asyncio.sleep(config.ADMIN_TIMEOUT_NOTIFY)
                        await bot.api.messages.send(
                            user_ids=user_ids[first_id:],
                            message=message,
                            random_id=bot.extension.random_id(),
                        )

                await asyncio.sleep(config.ADMIN_TIMEOUT_NOTIFY)

        except (VKError, ValueError):
            # Some unexpected error while sending messages. Ignore
            await asyncio.sleep(config.ADMIN_TIMEOUT_API)
            traceback.print_exc()

        except:
            # Some exception while sending. Just ignore
            traceback.print_exc()


async def after_startup(bot):
    # Send `Reloading` message to everyone who was playing at the moment
    max_users = config.ADMIN_COMMAND_SEND_MESSAGE_RESTART_MAX_USERS
    min_age = config.ADMIN_COMMAND_SEND_MESSAGE_RESTART_MIN_AGE
    message_filter = config.ADMIN_COMMAND_SEND_MESSAGE_RESTART_FILTER
    message = config.ADMIN_COMMAND_SEND_MESSAGE_RESTART_ENDED_TEXT
    earlier = config.ADMIN_COMMAND_SEND_MESSAGE_RESTART_EARLIER

    await send_messages(
        bot=bot,
        message=message,
        message_filter=message_filter,
        min_age=min_age,
        max_users=max_users,
        earlier=earlier,
    )


async def handle_admin_redis(redis, command, msg):
    # Redis command
    try:
        response = await eval(command)

    except Exception as exc:
        response = exc

    await msg(response)


async def handle_admin_notify(bot, msg, command):
    command_and_text = command.split()

    if len(command_and_text) >= 2:
        # `command_and_text` should consist at least of 2 elements. Command and Text
        command, text, message_filter, max_users, min_age, earlier = extract_params(command_and_text)

        await msg(config.ADMIN_COMMAND_START_TEXT.format(command=command))

        await send_messages(
            bot=bot,
            message=text,
            message_filter=message_filter,
            min_age=min_age,
            max_users=max_users,
            earlier=earlier,
        )

        await msg(config.ADMIN_COMMAND_END_TEXT.format(command=command))
    else:
        await msg(config.ADMIN_UNKNOWN_COMMAND_TEXT)
