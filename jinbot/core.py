import asyncio
import typing
from json import JSONDecodeError

from aiohttp.client_exceptions import ClientConnectionError
from aioredis.commands import Redis
from vkbottle import Message

from jinbot import config
from jinbot.akinator import Akinator
from jinbot.managers import AbstractManager
from jinbot.utils import (
    save_session,
    create_and_save_session,
    get_or_create_session,
    get_object_key,
    update_region,
)


class Game:
    """
    Common Class that aggregates all necessary objects of game

    :param bot: Bot object that contains API-methods of specific interface
    :param manager: Message Manager object
    :type manager: Type[AbstractManager]
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
        manager: typing.Type[AbstractManager],
        session_created: bool,
        session: Akinator,
        msg,
        redis: Redis,
        session_id: str,
    ):
        self.bot = bot
        self.manager = manager
        self.msg = msg
        self.session_id = session_id
        self.session_created, self.session = session_created, session
        self.redis = redis

    def can_continue(self):
        # Akinator counting starts with 0, so minus 1 from max steps
        return (self.session.step < config.AKINATOR_MAX_STEPS - 1) \
               and self.session.progression < config.SESSION_PROGRESS_SURE_VICTORY

    def are_guesses_left(self):
        """There is no other guesses when we already have guessed something and progression is more than maximum progression"""
        return not(self.session.last_guess and not self.can_continue())

    def is_victory(self):
        """
        It's victory either when `self.session.progression` is more or equal than needed for sure victory
        or if `self.session.step` is more or equal than minimal needed for unsure victory,
           and `self.session.progression` is more or equal than needed for unsure victory
        """

        is_sure_victory = (
            self.session.progression >= config.SESSION_PROGRESS_SURE_VICTORY
        )
        is_unsure_victory = (
            self.session.progression >= config.SESSION_PROGRESS_UNSURE_VICTORY
            and self.session.step >= config.SESSION_PROGRESS_MIN_STEP_UNSURE_VICTORY
        )

        return is_sure_victory or is_unsure_victory

    def is_defeat(self) -> int:
        """
        Bot is defeated either when we encountered one of the checkpoints or got `self.is_bad_guess` case

        :return: 1 if bot cant guess, 0 otherwise
        :rtype: int
        """
        return int(
            (
                self.session.step == config.SESSION_MAX_STEPS_FIRST
                or self.session.step == config.SESSION_MAX_STEPS_SECOND
            )
            and self.session.progression < config.SESSION_PROGRESS_DEFEAT
        )

    async def create_and_start(self, prefix_text: str = ""):
        """Create new session, save it to DB and send steps"""
        _, self.session = await create_and_save_session(
            session_id=self.session_id, redis=self.redis
        )
        if self.session:
            await self.send_step(prefix_text=prefix_text)

        else:
            await self.manager.send_message(
                bot=self.bot, msg=self.msg, text=config.TEXT_SERVER_DOWN
            )

    async def send_step(self, prefix_text: str = ""):
        """Send step information to user"""
        await self.manager.send_message(
            bot=self.bot,
            msg=self.msg,
            text=prefix_text
            + config.TEXT_QUESTION.format(
                step=self.session.step + 1,
                progression=f"{self.session.progression:.2f}%",
                question=self.session.question,
            ),
        )

    async def send_victory_message(self, guess: dict, can_continue: bool = True):
        """Send victory message and image of guess"""
        if can_continue:
            message = config.TEXT_VICTORY

        else:
            message = config.TEXT_VICTORY_WO_CONTINUE

        if guess.get("absolute_picture_path", None):
            # Guess without image
            await self.manager.send_image(
                bot=self.bot,
                msg=self.msg,
                url=guess["absolute_picture_path"],
                text=message.format(
                    name=guess["name"], description=guess["description"]
                ),
            )

        else:
            # Guess with image
            await self.manager.send_message(
                bot=self.bot,
                msg=self.msg,
                text=message.format(
                    name=guess["name"], description=guess["description"]
                ),
            )

    async def send_defeated_message(self, can_continue: bool = True):
        await self.manager.send_message(
            bot=self.bot,
            msg=self.msg,
            text=config.TEXT_DEFEATED_CONTINUE
            if can_continue
            else config.TEXT_DEFEATED,
        )

    async def handle_exception(self, status_code: str) -> bool:
        if status_code == "AkiTimedOut":
            # Session expired. Restart game
            _, self.session = await create_and_save_session(
                session_id=self.session_id, redis=self.redis
            )

            if self.session:
                await self.manager.send_message(
                    bot=self.bot, msg=self.msg, text=config.TEXT_SESSION_EXPIRED
                )
                await self.send_step()

            return True

        if status_code == "CantGoBackAnyFurther":
            await self.send_step()

            return True

        if status_code == "AkiNoQuestions":
            # Question limit reached. Send defeat message and restart game
            await self.send_defeated_message(can_continue=False)

            return True

        if status_code == "AkiServerDown":
            # Akinator server is down. Try to update region and Send message
            update_region()
            await self.manager.send_message(
                bot=self.bot, msg=self.msg, text=config.TEXT_SERVER_DOWN
            )

            return True

        return False

    async def handle_guessed(self):
        """Handle possible victory case

        If guess is not repeating, then send victory message.
        If guess is repeating, then if there is other possible guesses send next step, send defeat message otherwise.
        """
        status_code = await self.session.win()
        caught_exception = await self.handle_exception(status_code=status_code)

        if not caught_exception:
            # No Exception after winning
            is_repeating = (
                self.session.first_guess.get("name") == self.session.last_guess
            )
            if is_repeating:
                # Repeated guess
                if not self.are_guesses_left():
                    # Repeated guess got maximum progress, so most probably there is no other guesses
                    self.session.is_ended = 1
                    await save_session(
                        session_id=self.session_id,
                        session=self.session,
                        redis=self.redis,
                    )
                    await self.send_defeated_message(can_continue=False)

                else:
                    # Repeated guess, but there can be other guesses. Continue game
                    await save_session(
                        session_id=self.session_id,
                        session=self.session,
                        redis=self.redis,
                    )
                    await self.send_step()

            else:
                self.session.is_ended = 1
                self.session.last_guess = self.session.first_guess["name"]
                await save_session(
                    session_id=self.session_id, session=self.session, redis=self.redis,
                )
                await self.send_victory_message(self.session.first_guess, can_continue=self.can_continue())

    async def continue_game(self, answer: str, first_try: bool = True):
        """
        Not completed. Continue to play

        :param answer: Text of users answer
        :type answer: str
        :param first_try: If True, then in case of error run `self.continue_game` again, restart game otherwise
        :type first_try: bool, optional
        """
        try:
            # Continue. Not defeated game
            status_code = await self.session.answer(answer)
            caught_exception = await self.handle_exception(status_code=status_code)

            if not caught_exception:
                if self.is_victory():
                    # Victory case. Could be repeating
                    await self.handle_guessed()

                else:
                    self.session.is_ended = self.is_defeat()
                    if self.session.is_ended:
                        # Defeated game
                        await self.send_defeated_message(
                            can_continue=self.can_continue()
                        )

                    else:
                        # Not guessed yet. Send next question to user
                        await self.send_step()

                    # Save session in DB after user answered to question
                    await save_session(
                        session_id=self.session_id,
                        session=self.session,
                        redis=self.redis,
                    )

        except (ValueError, JSONDecodeError, ClientConnectionError):
            if first_try:
                # Wait a little, try again
                await asyncio.sleep(0.5)
                await self.continue_game(answer=answer, first_try=False)

            else:
                # Error occurred. Create and send step with error message
                await self.create_and_start(prefix_text=config.TEXT_ANSWER_ERROR)

    async def handle_answer(self, answer: str):
        # Known answer
        if not self.session_created:
            # Session already existed
            if self.session.is_ended:
                # Ended game. Start new one
                await self.create_and_start()

            else:
                # Not ended game. Continue
                await self.continue_game(answer=answer)

        else:
            # Just created game. Send steps
            await self.send_step()

    async def handle_back(self):
        # Ongoing game
        status_code = await self.session.back()
        caught_exception = await self.handle_exception(status_code=status_code)

        if not caught_exception:
            if self.session.is_ended:
                # Game was ended. Start it, so player could continue
                self.session.is_ended = 0

            await save_session(
                session_id=self.session_id, session=self.session, redis=self.redis,
            )
            await self.send_step()

    async def handle_continue(self):
        if not self.session_created:
            # Existed game
            if self.session.is_ended:
                # There is other guesses
                if self.can_continue():
                    # There is other questions
                    if self.is_victory() or self.is_defeat():
                        # Continue wrong guess or defeated game
                        self.session.is_ended = 0
                        await save_session(
                            session_id=self.session_id,
                            session=self.session,
                            redis=self.redis,
                        )
                        await self.send_step()

                else:
                    # Cant be continued
                    await self.create_and_start()

            else:
                # Not ended. Continue
                await self.send_step()
        else:
            # Created game. Send steps
            await self.send_step()

    @staticmethod
    async def handle_restart(
        bot,
        manager: typing.Type[AbstractManager],
        msg: Message,
        redis: Redis,
        chat_id: str,
    ):
        """Restart game. Create new session, save it to DB and send steps"""
        _, session = await create_and_save_session(
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

        else:
            await manager.send_message(bot=bot, msg=msg, text=config.TEXT_SERVER_DOWN)

    @staticmethod
    async def factory_game(
        bot,
        manager: typing.Type[AbstractManager],
        msg: Message,
        redis: Redis,
        chat_id: str,
    ):
        """
        Factory method that returns Game object

        :param bot: Bot object that contains API-methods of specific interface
        :param manager: Message Manager object
        :type manager: AbstractManager
        :param msg: Users Message object
        :type msg: Message
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

        return None
