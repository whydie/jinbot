import json
import re
import time

import aiohttp
import requests
from akinator.async_aki import Akinator as AsyncAkinator

from jinbot import config

server_regex = re.compile(
    '[{"translated_theme_name":"[\s\S]*","urlWs":"https:\\\/\\\/srv[0-9]+\.akinator\.com:[0-9]+\\\/ws","subject_id":"[0-9]+"}]'
)
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


def auto_get_region(lang, theme):
    """Automatically get the uri and server from akinator.com for the specified language and theme"""

    uri = lang + ".akinator.com"

    response = requests.get("https://" + uri)
    match = server_regex.search(response.text)

    parsed = json.loads(match.group().split("'arrUrlThemesToPlay', ")[-1])

    if theme == "c":
        return {
            "uri": uri,
            "server": next((i for i in parsed if i["subject_id"] == "1"), None)[
                "urlWs"
            ],
        }

    elif theme == "a":
        return {
            "uri": uri,
            "server": next((i for i in parsed if i["subject_id"] == "14"), None)[
                "urlWs"
            ],
        }

    elif theme == "o":
        return {
            "uri": uri,
            "server": next((i for i in parsed if i["subject_id"] == "2"), None)[
                "urlWs"
            ],
        }


def raise_connection_error(response):
    if response == "KO - SERVER DOWN":
        return "AkiServerDown"

    elif response == "KO - TIMEOUT":
        return "AkiTimedOut"

    elif response == "KO - ELEM LIST IS EMPTY" or response == "WARN - NO QUESTION":
        return "AkiNoQuestions"

    else:
        return "AkiConnectionFailure"


region_info = auto_get_region("ru", "c")
uri, server = region_info["uri"], region_info["server"]
soft_constraint = "ETAT%3D%27EN%27" if config.AKINATOR_CHILD_MODE == "true" else ""
question_filter = "cat%3D1" if config.AKINATOR_CHILD_MODE == "false" else ""


class Akinator(AsyncAkinator):
    def __init__(self, is_defeated: int = 0, is_started: int = 1):
        super().__init__()
        self.is_defeated = is_defeated
        self.is_started = is_started

    async def _get_session_info(self):
        """Get uid and frontaddr from akinator.com/game"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://en.akinator.com/game") as w:
                match = info_regex.search(await w.text())

        self.uid, self.frontaddr = match.groups()[0], match.groups()[1]

    async def start_game(self):
        self.timestamp = time.time()

        await self._get_session_info()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                NEW_SESSION_URL.format(
                    uri,
                    self.timestamp,
                    server,
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
                    uri,
                    self.timestamp,
                    server,
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
                    server,
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
                    server,
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
            "is_defeated": self.is_defeated,
            "is_started": self.is_started,
        }

        if self.first_guess:
            dump["first_guess_name"] = self.first_guess["name"]
            dump["first_guess_description"] = self.first_guess["description"]
            dump["first_guess_absolute_picture_path"] = self.first_guess["absolute_picture_path"]
        else:
            dump["first_guess_name"] = ""
            dump["first_guess_description"] = ""
            dump["first_guess_absolute_picture_path"] = ""

        return dump

    def load_session(self, dump):
        self.is_defeated = dump["is_defeated"]
        self.timestamp = dump["timestamp"]
        self.session = dump["session"]
        self.signature = dump["signature"]
        self.step = int(dump["step"])
        self.frontaddr = dump["frontaddr"]

        if dump.get("first_guess_name"):
            self.first_guess = {
                "name": dump["first_guess_name"],
                "description": dump["first_guess_description"],
                "absolute_picture_path": dump["first_guess_absolute_picture_path"],
            }

        else:
            self.first_guess = None

        self.progression = float(dump["progression"])
        self.question = dump["question"]
        self.is_defeated = int(dump["is_defeated"])
        self.is_started = int(dump["is_started"])
