"""
Конфигурация приложения
"""

from os import path, getenv
from dotenv import load_dotenv

from loguru import logger

# State
DEFAULT_STATE_DIR = path.join(path.dirname(path.abspath(__file__)), "../state")
DEFAULT_DOTENV_FILE = path.join(DEFAULT_STATE_DIR, "config.env")
DEFAULT_COOKIES_FILE = path.join(DEFAULT_STATE_DIR, "cookies.txt")


load_dotenv(DEFAULT_DOTENV_FILE)

# VK config
VK_GROUP_ID = getenv("VK_GROUP_ID")
VK_BOT_TOKEN = getenv("VK_BOT_TOKEN")
VK_USER_TOKEN = getenv("VK_USER_TOKEN")


# Misc config
PUSH_LOGS = True


logger.add(path.join(DEFAULT_STATE_DIR, "bot.log"), rotation="5 MB")

if not PUSH_LOGS:
    logger.remove()
