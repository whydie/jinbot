import asyncio
import typing
from concurrent import futures
from json.decoder import JSONDecodeError

from aiohttp import ClientConnectionError
from aioredis.commands import Redis

from jinbot.akinator import Akinator
from jinbot import config


def update_region():
    """Update region related `uri` and `server` """
    region_info = config.auto_get_region()
    config.uri, config.server = region_info["uri"], region_info["server"]


def get_object_key(manager, *object_path: str) -> str:
    """Create key for object in DB

    :param manager: Message Manager object
    :type manager: AbstractManager
    :param object_path: Unique ID of object
    :type object_path: str
    :return: Unique key for object
    """
    return "||".join([manager.prefix, *object_path])


async def create_session(
    first_try: bool = True, is_ended: int = 0
) -> typing.Optional[Akinator]:
    """Create session object and start it

    :param first_try: if True, then in case of Error try again, dont try otherwise
    :type first_try: bool, optional
    :param is_ended: if True, then cant continue game
    :type is_ended: int, optional
    :return: Session object
    :rtype: Akinator, optional
    """
    try:
        session = Akinator(is_ended=is_ended)
        status_code = await session.start_game()

        if status_code != "OK":
            # Server error. Try to update region
            update_region()

            return None

        return session

    except (JSONDecodeError, AttributeError, ClientConnectionError, futures.TimeoutError):
        if first_try:
            # Some problem with Akinator API. Wait a little and try again
            await asyncio.sleep(0.5)

            return await create_session(first_try=False)

        return None


async def save_session(session_id: str, session: Akinator, redis: Redis) -> Akinator:
    """Dump session object and save it in DB

    :param session_id: Unique ID that used as a key for Session object in DB
    :type session_id: str
    :param session: Session object
    :type session: Akinator
    :param redis: Connection to DB object
    :type redis: Redis
    :return: Session object
    :rtype: Akinator
    """
    session_dump = session.dump_session()
    await redis.set(session_id, session_dump, expire=config.SESSION_EXPIRE_TIME)

    return session


async def create_and_save_session(
    session_id: str, redis: Redis, is_ended: int = 0
) -> typing.Tuple[bool, typing.Optional[Akinator]]:
    """Remove session and create new one

    :param session_id: Unique ID that used as a key for Session object in DB
    :type session_id: str
    :param redis: Connection to DB object
    :type redis: Redis
    :param is_ended: if True, then then cant continue game
    :type is_ended: int, optional
    :return: True if created, False if existed and Session object
    :rtype: tuple(bool, Akinator)
    """
    session = await create_session(is_ended=is_ended)
    if session:
        await save_session(session_id=session_id, session=session, redis=redis)

        return True, session

    return False, None


async def get_or_create_session(
    session_id: str, redis: Redis
) -> typing.Tuple[bool, typing.Optional[Akinator]]:
    """Find Session object in DB, create if not founded

    :param session_id: Unique ID that used as a key for Session object in DB
    :type session_id: str
    :param redis: Connection to DB object
    :type redis: Redis
    :return: `True` if created, `False` if existed and Session object
    :rtype: tuple(bool, Akinator)
    """
    session_dump = await redis.get(session_id, encoding="utf-8")

    if session_dump:
        # Founded. Load object
        session = Akinator()
        session.load_session(session_dump)

        return False, session

    # Not founded. Create
    session = await create_session()
    if session:
        await save_session(session_id=session_id, session=session, redis=redis)

        return True, session

    return False, None
