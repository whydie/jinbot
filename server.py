import os
import traceback

import aioredis
from vkbottle import Bot, Message, PhotoUploader
from vkbottle.framework.framework.rule import ChatActionRule
from vkbottle.types import GroupJoin
from vkbottle.utils.exceptions import VKError

from jinbot import config
from jinbot.core import Game
from jinbot.managers import VKStrategy

from vkapi.utils import remove_admin_prefix
from vkapi.rules import CommandFromAdmin
from vkapi.core import handle_admin_notify, handle_admin_redis, after_startup


bot = Bot(os.getenv("VK_KEY"), debug=config.DEBUG)
redis = bot.loop.run_until_complete(aioredis.create_redis_pool("redis://localhost", password=os.getenv("REDIS_KEY")))
uploader = PhotoUploader(bot.api, generate_attachment_strings=True)
setattr(bot, "uploader", uploader)

# Get admin list
get_members = bot.loop.run_until_complete(bot.api.groups.get_members(group_id=bot.group_id, filter="managers"))
admin_list = [user.id for user in get_members.items]


@bot.on.message_handler(CommandFromAdmin(admin_list=admin_list))
async def handle_admin_command(msg: Message):
    command = remove_admin_prefix(text=msg.text)

    if command.startswith("redis"):
        await handle_admin_redis(redis=redis, msg=msg, command=command)

    elif command.startswith("notify"):
        await handle_admin_notify(bot=bot, msg=msg, command=command)

    else:
        await msg(config.ADMIN_UNKNOWN_COMMAND_TEXT)


@bot.on.event.group_join()
async def handle_join(event: GroupJoin):
    try:
        await bot.api.messages.send(
            peer_id=event.user_id,
            message=config.TEXT_JOINED,
            random_id=bot.extension.random_id(),
        )

    except VKError as exc:
        # If dont have dialog with user, then ignore
        if exc.error_code != 901:
            traceback.print_exc()


@bot.on.event.group_leave()
async def handle_leave(event: GroupJoin):
    try:
        await bot.api.messages.send(
            peer_id=event.user_id,
            message=config.TEXT_LEFT,
            random_id=bot.extension.random_id(),
        )

    except VKError as exc:
        # If dont have dialog with user, then ignore
        if exc.error_code != 901:
            traceback.print_exc()


@bot.on.message_handler(ChatActionRule("chat_invite_user"))
async def handle_invite(msg: Message):
    await VKStrategy.send_message(
        bot=bot,
        msg=msg,
        text=config.TEXT_CHAT_INVITE.format(group_id=config.VK_GROUP_ID),
    )


@bot.on.message_handler(text=config.ANSWER_BACK)
async def handle_back(msg: Message):
    game = await Game.factory_game(
        bot=bot, manager=VKStrategy, msg=msg, redis=redis, chat_id=str(msg.chat_id)
    )
    if game:
        await game.handle_back()
    else:
        await msg(config.TEXT_SERVER_DOWN)


@bot.on.message_handler(text=config.ANSWER_CONTINUE)
async def handle_continue(msg: Message):
    game = await Game.factory_game(
        bot=bot, manager=VKStrategy, msg=msg, redis=redis, chat_id=str(msg.chat_id)
    )
    if game:
        await game.handle_continue()

    else:
        await msg(config.TEXT_SERVER_DOWN)


@bot.on.message_handler(text=config.ANSWER_RESTART)
async def handle_restart(msg: Message):
    await Game.handle_restart(
        bot=bot, manager=VKStrategy, msg=msg, redis=redis, chat_id=str(msg.chat_id)
    )


@bot.on.message_handler()
async def handle_answer(msg: Message):
    answer = config.ANSWERS.get(msg.text, None)
    if answer:
        # Known answer
        game = await Game.factory_game(
            bot=bot, manager=VKStrategy, msg=msg, redis=redis, chat_id=str(msg.chat_id)
        )

        if game:
            await game.handle_answer(answer=answer)

        else:
            await msg(config.TEXT_SERVER_DOWN)

    else:
        # Unknown answer
        await VKStrategy.send_message(bot=bot, msg=msg, text=config.TEXT_UNKNOWN_COMMAND)


if __name__ == "__main__":
    # Initialize akinator global vars
    config.init_akinator()

    if config.DEBUG:
        bot.run_polling()

    else:
        bot.loop.create_task(after_startup(bot=bot))
        bot.run_polling()
