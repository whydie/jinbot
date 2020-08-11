import json
import time
import re

import aiohttp
from akinator.async_aki import Akinator as AsyncAkinator

from jinbot import config


info_regex = re.compile("var uid_ext_session = '(.*)'\\;\\n.*var frontaddr = '(.*)'\\;")
soft_constraint = "ETAT%3D%27EN%27" if config.AKINATOR_CHILD_MODE == "true" else ""
question_filter = "cat%3D1" if config.AKINATOR_CHILD_MODE == "false" else ""


def raise_connection_error(response):
    """Match game API status codes to local status codes"""
    if response == "KO - SERVER DOWN":
        return "AkiServerDown"

    if response in ("KO - TIMEOUT", "KO - UNAUTHORIZED"):
        return "AkiTimedOut"

    if response in ("KO - ELEM LIST IS EMPTY", "WARN - NO QUESTION"):
        return "AkiNoQuestions"

    return "AkiConnectionFailure"


class Akinator(AsyncAkinator):
    """Custom Akinator class that was changed for performance needs

    :param is_ended: Flag that used for conditional cases
    :type is_ended: int, optional
    :param last_guess: Name of last guess
    :type last_guess: str, optional
    """
    def __init__(self, is_ended: int = 0, last_guess: str = ""):
        super().__init__()
        self.is_ended = is_ended
        self.last_guess = last_guess

    async def _get_session_info(self):
        """Get uid and frontaddr from akinator.com/game"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://en.akinator.com/game") as w:
                match = info_regex.search(await w.text())

        self.uid, self.frontaddr = match.groups()[0], match.groups()[1]

    def _parse_response(self, response):
        """Parse the JSON response and turn it into a Python object"""
        if "KO - UNAUTHORIZED" in response:
            return {"completion": "KO - UNAUTHORIZED"}

        return json.loads(",".join(response.split("(")[1::])[:-1])

    async def start_game(self, **kwargs):
        """Get session info from game API"""
        self.timestamp = time.time()
        await self._get_session_info()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    config.NEW_SESSION_URL.format(
                        config.uri,
                        self.timestamp,
                        config.server,
                        config.AKINATOR_CHILD_MODE,
                        self.uid,
                        self.frontaddr,
                        soft_constraint,
                        question_filter,
                    ),
                    headers=config.HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp, True)

            return resp["completion"]

        return raise_connection_error(resp["completion"])

    async def answer(self, ans):
        """Send `answer` request to game API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                config.ANSWER_URL.format(
                    config.uri,
                    self.timestamp,
                    config.server,
                    config.AKINATOR_CHILD_MODE,
                    self.session,
                    self.signature,
                    self.step,
                    ans,
                    self.frontaddr,
                    question_filter,
                ),
                headers=config.HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp)

            return resp["completion"]

        return raise_connection_error(resp["completion"])

    async def back(self):
        """Send `back` request to game API"""
        if self.step == 0:
            return "CantGoBackAnyFurther"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                config.BACK_URL.format(
                    config.server,
                    self.timestamp,
                    config.AKINATOR_CHILD_MODE,
                    self.session,
                    self.signature,
                    self.step,
                    question_filter,
                ),
                headers=config.HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp)

            return resp["completion"]

        return raise_connection_error(resp["completion"])

    async def win(self):
        """Send `win` request to game API"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                config.WIN_URL.format(
                    config.server,
                    self.timestamp,
                    config.AKINATOR_CHILD_MODE,
                    self.session,
                    self.signature,
                    self.step,
                ),
                headers=config.HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self.first_guess = resp["parameters"]["elements"][0]["element"]

            return resp["completion"]

        return raise_connection_error(resp["completion"])

    def dump_session(self):
        """Serialize session information to JSON

        :return: JSON formatted string that contains session information
        :rtype: str
        """
        dump = {
            "timestamp": self.timestamp,
            "session": self.session,
            "signature": self.signature,
            "step": self.step,
            "frontaddr": self.frontaddr,
            "progression": self.progression,
            "question": self.question,
            "is_ended": self.is_ended,
            "last_guess": self.last_guess,
        }

        if self.first_guess:
            dump["first_guess_name"] = self.first_guess.get("name", "")
            dump["first_guess_description"] = self.first_guess.get("description", "")
            dump["first_guess_absolute_picture_path"] = self.first_guess.get("absolute_picture_path", "")

        else:
            dump["first_guess_name"] = ""
            dump["first_guess_description"] = ""
            dump["first_guess_absolute_picture_path"] = ""

        return json.dumps(dump)

    def load_session(self, dump):
        """Load session information from json dump

        :param dump: JSON serialized information that used to fill session object
        :type dump: str
        """
        loaded = json.loads(dump)

        self.timestamp = loaded["timestamp"]
        self.session = loaded["session"]
        self.signature = loaded["signature"]
        self.step = int(loaded["step"])
        self.frontaddr = loaded["frontaddr"]

        if loaded.get("first_guess_name"):
            self.first_guess = {
                "name": loaded["first_guess_name"],
                "description": loaded["first_guess_description"],
                "absolute_picture_path": loaded["first_guess_absolute_picture_path"],
            }

        else:
            self.first_guess = None

        self.progression = float(loaded["progression"])
        self.question = loaded["question"]
        self.is_ended = int(loaded["is_ended"])
        self.last_guess = loaded["last_guess"]
