"""Module housing ssh-utilities constants."""

import logging
from pathlib import Path

from colorama import Fore, init
from typing_extensions import Literal

__all__ = ["G", "LG", "R", "RED", "C", "Y", "CONFIG_PATH"]

logging.getLogger(__name__)

init(autoreset=True)
G = Fore.GREEN
LG = Fore.LIGHTGREEN_EX
R = Fore.RESET
RED = Fore.RED
C = Fore.LIGHTCYAN_EX
Y = Fore.YELLOW
GET: Literal["get"] = "get"
PUT: Literal["put"] = "put"

CONFIG_PATH = Path("~/.ssh/config").expanduser()
