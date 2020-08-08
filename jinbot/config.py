ANSWER_YES_TEXT = "Да"
ANSWER_YES_TEXT_LOWER = ANSWER_YES_TEXT.lower()
ANSWER_YES_NUM = "1"

ANSWER_NO_TEXT = "Нет"
ANSWER_NO_TEXT_LOWER = ANSWER_NO_TEXT.lower()
ANSWER_NO_NUM = "2"

ANSWER_DONT_KNOW_TEXT = "Не знаю"
ANSWER_DONT_KNOW_TEXT_LOWER = ANSWER_DONT_KNOW_TEXT.lower()
ANSWER_DONT_KNOW_NUM = "3"

ANSWER_PROBABLY_YES_TEXT = "Возможно, частично"
ANSWER_PROBABLY_YES_TEXT_LOWER = ANSWER_PROBABLY_YES_TEXT.lower()
ANSWER_PROBABLY_YES_NUM = "4"

ANSWER_PROBABLY_NO_TEXT = "Скорее нет, не совсем"
ANSWER_PROBABLY_NO_TEXT_LOWER = ANSWER_PROBABLY_NO_TEXT.lower()
ANSWER_PROBABLY_NO_NUM = "5"

ANSWER_BACK_TEXT = "Назад"
ANSWER_BACK_TEXT_LOWER = ANSWER_BACK_TEXT.lower()
ANSWER_BACK_NUM = "6"
ANSWER_BACK = [ANSWER_BACK_TEXT, ANSWER_BACK_TEXT_LOWER, ANSWER_BACK_NUM]

ANSWER_RESTART_TEXT = "Начать заново"
ANSWER_RESTART_TEXT_LOWER = ANSWER_RESTART_TEXT.lower()
ANSWER_RESTART_NUM = "7"
ANSWER_RESTART = [ANSWER_RESTART_TEXT, ANSWER_RESTART_TEXT_LOWER, ANSWER_RESTART_NUM]

ANSWER_CONTINUE_TEXT = "Продолжить"
ANSWER_CONTINUE_NUM = "8"

ANSWER_START_TEXT = "Начать"
ANSWER_START_UPPER = [ANSWER_START_TEXT, "Играть", "Давай", "Привет", "Го", "Гоу", "Поехали", ANSWER_CONTINUE_TEXT]
ANSWER_START_LOWER = [item.lower() for item in ANSWER_START_UPPER]
ANSWER_START_OTHER = [ANSWER_CONTINUE_NUM]

# List of answers to start
ANSWER_START = ANSWER_START_UPPER + ANSWER_START_LOWER + ANSWER_START_OTHER

ANSWERS = {
    ANSWER_YES_TEXT: "0",
    ANSWER_YES_TEXT_LOWER: "0",
    ANSWER_YES_NUM: "0",

    ANSWER_NO_TEXT: "1",
    ANSWER_NO_TEXT_LOWER: "1",
    ANSWER_NO_NUM: "1",

    ANSWER_DONT_KNOW_TEXT: "2",
    ANSWER_DONT_KNOW_TEXT_LOWER: "2",
    ANSWER_DONT_KNOW_NUM: "2",

    ANSWER_PROBABLY_YES_TEXT: "3",
    ANSWER_PROBABLY_YES_TEXT_LOWER: "3",
    ANSWER_PROBABLY_YES_NUM: "3",

    ANSWER_PROBABLY_NO_TEXT: "4",
    ANSWER_PROBABLY_NO_TEXT_LOWER: "4",
    ANSWER_PROBABLY_NO_NUM: "4",
}

MESSAGE_INTERFACE = f"1) {ANSWER_YES_TEXT}\n" \
                    f"2) {ANSWER_NO_TEXT}\n" \
                    f"3) {ANSWER_DONT_KNOW_TEXT}\n" \
                    f"4) {ANSWER_PROBABLY_YES_TEXT}\n" \
                    f"5) {ANSWER_PROBABLY_NO_TEXT}\n\n" \
                    f"6) {ANSWER_BACK_TEXT}\n" \
                    f"7) {ANSWER_RESTART_TEXT}"

VK_GROUP_ID = "bot_jin"

TEXT_VICTORY = "Я думаю... Это:\n" \
               "{name} ({description})\n" \
               " Хочешь сыграть ещё?"

TEXT_QUESTION = "Вопрос №{step}\n" \
                "Прогресс: {progression}\n" \
                "➖➖➖➖➖\n" \
                "{question}\n" \
                "➖➖➖➖➖\n" \
                + MESSAGE_INTERFACE

TEXT_UNKNOWN_COMMAND = f"Неизвестная команда\n" \
                       f"Чтобы начать, напишите \"{ANSWER_START_TEXT}\""

TEXT_JOINED = "Ну что, начнём? 😏"
TEXT_CHAT_INVITE = TEXT_JOINED + "\nОбращайтесь ко мне через @{group_id}"
TEXT_LEFT = "Уже уходишь? 😢"
TEXT_DEFEATED = f"Ты победил, я принимаю поражение 🤕\n" \
                f"7) {ANSWER_RESTART_TEXT}"

TEXT_DEFEATED_CONTINUE = f"{TEXT_DEFEATED}\n" \
                         f"8) {ANSWER_CONTINUE_TEXT}"

TEXT_SESSION_EXPIRED = "Тебя слишком долго не было, и я забыл твои ответы 😞\n"
TEXT_SERVER_DOWN = "Бот приболел и ему нужно немного отдохнуть 🤒\n"

DEBUG = False

AKINATOR_CHILD_MODE = "false"

ADMIN_COMMAND_PREFIX = "//"
ADMIN_UNKNOWN_COMMAND_TEXT = "Команда должна начинаться с redis или notify\n\n" \
                             "Например:\n\n" \
                             "Очистить БД\n" \
                             "//redis.flushall()\n\n" \
                             "Получить количество записей в БД\n" \
                             "//redis.dbsize()\n\n" \
                             "Разослать сообщение\n" \
                             "//notify-{filter}-{max_users}-{min_age}-{earlier} Сообщение\n" \
                             "filter - all, unread, unanswered, important\n\n" \
                             "max_users - Количество пользователей, которым отправится сообщение\n\n" \
                             "min_age - Минимальная давность последнего сообщения пользователя в секундах\n\n" \
                             "earlier - Если 1, то отправить только тем у кого последнее собщение старше min_age. Если 0, то моложе"

ADMIN_COMMAND_START_TEXT = "Команда \"{command}\" запущена..."
ADMIN_COMMAND_END_TEXT = "Команда \"{command}\" завершена"
ADMIN_TIMEOUT_NOTIFY = 2  # Seconds
ADMIN_TIMEOUT_API = 10  # Seconds

ADMIN_COMMAND_SEND_MESSAGE_MIN_AGE_DEFAULT = 60 * 60 * 24 * 2  # 1 Day
ADMIN_COMMAND_SEND_MESSAGE_FILTER_DEFAULT = "all"
ADMIN_COMMAND_SEND_MESSAGE_EARLIER_DEFAULT = 1  # 1 True, 0 False

ADMIN_COMMAND_SEND_MESSAGE_RESTART_MAX_USERS = 200
ADMIN_COMMAND_SEND_MESSAGE_RESTART_FILTER = "all"
ADMIN_COMMAND_SEND_MESSAGE_RESTART_MIN_AGE = 60 * 2  # 2 Minutes
ADMIN_COMMAND_SEND_MESSAGE_RESTART_ENDED_TEXT = "Бот перезапустился, ещё пару секунд и будет готов 🥳"

SESSION_PROGRESS_UNSURE_VICTORY = 85
SESSION_PROGRESS_SURE_VICTORY = 90
SESSION_PROGRESS_MIN_STEP_UNSURE_VICTORY = 25
SESSION_PROGRESS_DEFEAT = 60
SESSION_MAX_STEPS_FIRST = 40
SESSION_MAX_STEPS_SECOND = 60
