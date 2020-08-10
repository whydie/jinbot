import json
import re
import time

import aiohttp
from akinator.async_aki import Akinator as AsyncAkinator

from jinbot import config


info_regex = re.compile("var uid_ext_session = '(.*)'\\;\\n.*var frontaddr = '(.*)'\\;")

# URLs for the API requests
NEW_SESSION_URL = "https://{}/new_session?callback=jQuery331023608747682107778_{}&urlApiWs={}&partner=1&childMod={}&player=website-desktop&uid_ext_session={}&frontaddr={}&constraint=ETAT<>'AV'&soft_constraint={}&question_filter={}"
ANSWER_URL = "https://{}/answer_api?callback=jQuery331023608747682107778_{}&urlApiWs={}&childMod={}&session={}&signature={}&step={}&answer={}&frontaddr={}&question_filter={}"
BACK_URL = "{}/cancel_answer?callback=jQuery331023608747682107778_{}&childMod={}&session={}&signature={}&step={}&answer=-1&question_filter={}"
WIN_URL = "{}/list?callback=jQuery331023608747682107778_{}&childMod={}&session={}&signature={}&step={}"

# HTTP headers to use for the requests
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) snap"
        " Chromium/81.0.4044.92 Chrome/81.0.4044.92 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
}


def raise_connection_error(response):
    if response == "KO - SERVER DOWN":
        return "AkiServerDown"

    elif response == "KO - TIMEOUT" or response == "KO - UNAUTHORIZED":
        return "AkiTimedOut"

    elif response == "KO - ELEM LIST IS EMPTY" or response == "WARN - NO QUESTION":
        return "AkiNoQuestions"

    else:
        return "AkiConnectionFailure"


soft_constraint = "ETAT%3D%27EN%27" if config.AKINATOR_CHILD_MODE == "true" else ""
question_filter = "cat%3D1" if config.AKINATOR_CHILD_MODE == "false" else ""


class Akinator(AsyncAkinator):
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
        self.timestamp = time.time()
        await self._get_session_info()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                NEW_SESSION_URL.format(
                    config.uri,
                    self.timestamp,
                    config.server,
                    config.AKINATOR_CHILD_MODE,
                    self.uid,
                    self.frontaddr,
                    soft_constraint,
                    question_filter,
                ),
                headers=HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp, True)

            return resp["completion"]

        else:
            return raise_connection_error(resp["completion"])

    async def answer(self, ans):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ANSWER_URL.format(
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
                headers=HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp)

            return resp["completion"]

        else:
            return raise_connection_error(resp["completion"])

    async def back(self):
        if self.step == 0:
            return "CantGoBackAnyFurther"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                BACK_URL.format(
                    config.server,
                    self.timestamp,
                    config.AKINATOR_CHILD_MODE,
                    self.session,
                    self.signature,
                    self.step,
                    question_filter,
                ),
                headers=HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self._update(resp)

            return resp["completion"]

        else:
            return raise_connection_error(resp["completion"])

    async def win(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                WIN_URL.format(
                    config.server,
                    self.timestamp,
                    config.AKINATOR_CHILD_MODE,
                    self.session,
                    self.signature,
                    self.step,
                ),
                headers=HEADERS,
            ) as w:
                resp = self._parse_response(await w.text())

        if resp["completion"] == "OK":
            self.first_guess = resp["parameters"]["elements"][0]["element"]

            return resp["completion"]

        else:
            return raise_connection_error(resp["completion"])

    def dump_session(self):
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
