import asyncio
import traceback
import typing
from json import JSONDecodeError

from aioredis.commands import Redis

from jinbot import config
from jinbot.akinator import Akinator
from jinbot.managers import AbstractManager
from jinbot.utils import (
    save_session,
    create_and_save_session,
    get_or_create_session,
    get_object_key,
)


class Game:
    """
    Common Class that aggregates all necessary objects of game

    :param bot: Bot object that contains API-methods of specific interface
    :param manager: Message Manager object
    :type manager: AbstractManager
    :param session_created: True If session was created, False if already existed
    :type session_created: bool
    :param session: Session object
    :type session: Akinator
    :param msg: Users Message object
    :param redis: Connection to DB object
    :type redis: Redis
    :param session_id: Key of session object in DB
    :type session_id: str
    """

    def __init__(
        self,
        bot,
        manager: AbstractManager,
        session_created: bool,
        session: Akinator,
        msg,
        redis: Redis,
        session_id: str,
    ):
        """Initializes game object with session, creates and save if didnt exist"""
        self.bot = bot
        self.manager = manager
        self.msg = msg
        self.session_id = session_id
        self.session_created, self.session = session_created, session
        self.redis = redis

    async def handle_guessed(self):
        # Guessed. Send answer
        status_code = await self.session.win()
        is_handled = await self.handle_exception(status_code=status_code)

        if not is_handled:
            # No Exception after winning
            self.session.is_ended = 1
            await save_session(
                session_id=self.session_id,
                session=self.session,
                redis=self.redis,
            )
            await self.send_victory_message(self.session.first_guess)

    def can_continue(self):
        return self.session.step < config.AKINATOR_MAX_STEPS

    async def handle_exception(self, status_code) -> bool:
        if status_code == "AkiTimedOut":
            # Session expired. Restart game
            created, self.session = await create_and_save_session(
                session_id=self.session_id, redis=self.redis
            )
            if self.session:
                await self.manager.send_message(
                    bot=self.bot, msg=self.msg, text=config.TEXT_SESSION_EXPIRED
                )
                await self.send_step()

            return True

        elif status_code == "CantGoBackAnyFurther":
            await self.send_step()

            return True

        elif status_code == "AkiNoQuestions":
            # Question limit reached. Send defeat message and restart game
            await self.create_and_start()
            await self.send_defeated_message()

            return True

        elif status_code == "AkiServerDown":
            # Akinator server is down. Send message
            await self.manager.send_message(
                bot=self.bot, msg=self.msg, text=config.TEXT_SERVER_DOWN
            )

            return True

        return False

    def is_victory(self):
        """
            It's victory either when `session.progression` is more or equal than needed for sure victory
            or if `session.step` is more than minimal needed for unsure victory,
                and `session.progression` is more or equal than needed for unsure victory
        """

        is_sure_victory = self.session.progression >= config.SESSION_PROGRESS_SURE_VICTORY
        is_unsure_victory = (
            self.session.progression >= config.SESSION_PROGRESS_UNSURE_VICTORY
            and self.session.step >= config.SESSION_PROGRESS_MIN_STEP_UNSURE_VICTORY
        )

        return is_sure_victory or is_unsure_victory

    def is_defeated(self) -> int:
        """
        Check if bot is defeated

        :return: True if bot cant guess, False otherwise
        :rtype: bool
        """
        return int(
            (
                self.session.step == config.SESSION_MAX_STEPS_FIRST
                or self.session.step == config.SESSION_MAX_STEPS_SECOND
            )
            and self.session.progression < config.SESSION_PROGRESS_DEFEAT
        )

    async def send_step(self):
        """
        Send step information to user
        """
        await self.manager.send_message(
            bot=self.bot,
            msg=self.msg,
            text=config.TEXT_QUESTION.format(
                step=self.session.step + 1,
                progression=f"{self.session.progression:.2f}%",
                question=self.session.question,
            ),
        )

    async def send_victory_message(self, guess):
        """Send victory message and image of guess"""
        if guess.get("absolute_picture_path", None):
            await self.manager.send_image(
                bot=self.bot,
                msg=self.msg,
                url=guess["absolute_picture_path"],
                text=config.TEXT_VICTORY.format(
                    name=guess["name"], description=guess["description"]
                )
            )
        else:
            await self.manager.send_message(
                bot=self.bot,
                msg=self.msg,
                text=config.TEXT_VICTORY.format(
                    name=guess["name"], description=guess["description"]
                ),
            )

    async def send_defeated_message(self):
        """
        Send defeat message
        """
        # Cant guess anymore
        await self.manager.send_message(
            bot=self.bot,
            msg=self.msg,
            text=config.TEXT_DEFEATED_CONTINUE if self.can_continue() else config.TEXT_DEFEATED,
        )

    async def create_and_start(self):
        """Create new session, save it to DB and send steps"""
        created, self.session = await create_and_save_session(
            session_id=self.session_id, redis=self.redis
        )
        if self.session:
            await self.send_step()

    async def continue_game(self, answer: str, first_try: bool = True):
        """
        Not completed. Continue to play

        :param answer: Text of users answer
        :type answer: str
        :param first_try: If True, then in case of error run `continue_game` again, restart game otherwise
        :type first_try: bool, optional
        """
        try:
            # Continue. Not defeated game
            status_code = await self.session.answer(answer)
            is_handled = await self.handle_exception(status_code=status_code)

            if not is_handled:
                # No Exception

                if self.is_victory():
                    await self.handle_guessed()

                else:
                    self.session.is_ended = self.is_defeated()
                    if self.session.is_ended:
                        await self.send_defeated_message()

                    else:
                        # Not guessed yet. Send next question to user
                        await self.send_step()

                    # Save session in DB after user answered to question
                    await save_session(
                        session_id=self.session_id,
                        session=self.session,
                        redis=self.redis,
                    )

        except (ValueError, JSONDecodeError):
            if first_try:
                # Wait a little, try again
                await asyncio.sleep(0.5)
                await self.continue_game(answer=answer, first_try=False)

            else:
                await self.create_and_start()

    async def handle_answer(self, answer: str):
        # Known answer
        if not self.session_created:
            # Session already existed
            if self.session.is_ended:
                # Completed game. Start new one
                await self.create_and_start()

            else:
                # Not completed game. Continue
                await self.continue_game(answer=answer)
        else:
            # Just created game. Send steps
            await self.send_step()

    async def handle_back(self):
        # Ongoing game
        status_code = await self.session.back()
        is_handled = await self.handle_exception(status_code=status_code)

        if not is_handled:
            self.session.is_ended = 0
            await save_session(
                session_id=self.session_id, session=self.session, redis=self.redis,
            )
            await self.send_step()

    async def handle_start(self):
        if not self.session_created:
            # Existed game
            if self.session.is_ended:
                if self.is_defeated():
                    if self.can_continue():
                        self.session.is_ended = 0
                        await save_session(
                            session_id=self.session_id,
                            session=self.session,
                            redis=self.redis,
                        )
                        await self.send_step()
                    else:
                        await self.create_and_start()

                elif self.is_victory():
                    self.session.is_ended = 0
                    await save_session(
                        session_id=self.session_id,
                        session=self.session,
                        redis=self.redis,
                    )
                    await self.send_step()

            else:
                await self.send_step()
        else:
            # Just created game. Send steps
            await self.send_step()

    @staticmethod
    async def handle_restart(bot, manager, msg, redis, chat_id):
        """Restart game. Create new session, save it to DB and send steps"""
        created, session = await create_and_save_session(
            session_id=get_object_key(manager, "session", chat_id), redis=redis
        )
        if session:
            await manager.send_message(
                bot=bot,
                msg=msg,
                text=config.TEXT_QUESTION.format(
                    step=session.step + 1,
                    progression=f"{session.progression:.2f}%",
                    question=session.question,
                ),
            )

    @staticmethod
    async def factory_game(
        bot, manager: typing.Type[AbstractManager], msg, redis: Redis, chat_id: str
    ):
        """
        Factory method that returns Game object

        :param bot: Bot object that contains API-methods of specific interface
        :param manager: Message Manager object
        :type manager: AbstractManager
        :param msg: Users Message object
        :param redis: Connection to DB object
        :type redis: Redis
        :param chat_id: Unique id of chat
        :return: Game object or None if some error occurred
        :rtype: Game, None
        """
        session_id = get_object_key(manager, "session", chat_id)
        created, session = await get_or_create_session(
            session_id=session_id, redis=redis
        )
        if session:
            game = Game(
                bot=bot,
                manager=manager,
                msg=msg,
                session_created=created,
                session=session,
                redis=redis,
                session_id=session_id,
            )
            return game

        else:
            return None
