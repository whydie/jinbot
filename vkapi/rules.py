from vkbottle import Message
from vkbottle.framework.framework.rule import AbstractMessageRule

from jinbot import config


class CommandFromAdmin(AbstractMessageRule):
    def __init__(self, admin_list: list):
        self.admin_list = admin_list

    async def check(self, message: Message) -> bool:
        if (message.from_id in self.admin_list) \
                and message.text.startswith(config.ADMIN_COMMAND_PREFIX):
            return True
