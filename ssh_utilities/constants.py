"""Module housing ssh-utilities constants."""

import logging
from pathlib import Path

from colorama import Fore, init

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

__all__ = ["G", "LG", "R", "RED", "C", "Y", "CONFIG_PATH", "GET", "PUT"]

logging.getLogger(__name__)

init(autoreset=True)
G = Fore.GREEN  #: used to higlight important messages in CLI mode
#: used to highlight important messages, when copying files
LG = Fore.LIGHTGREEN_EX
R = Fore.RESET  #: resets the foreground color to default
RED = Fore.RED  #: used to highlight errors
#: used to highlight important messages, on command execution
C = Fore.LIGHTCYAN_EX
Y = Fore.YELLOW  #: used to highlight important messages, on command execution
#: used to specify copy direction sever -> local
GET: Literal["get"] = "get"
#: used to specify copy direction local -> sever
PUT: Literal["put"] = "put"
#: default path to ssh configuration file
CONFIG_PATH = Path("~/.ssh/config").expanduser()
