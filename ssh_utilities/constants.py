from colorama import Back, Fore, init
from pathlib import Path

__all__ = ["G", "LG", "R", "RED", "C", "Y", "CONFIG_PATH"]

init(autoreset=True)
G = Fore.GREEN
LG = Fore.LIGHTGREEN_EX
R = Fore.RESET
RED = Fore.RED
C = Fore.LIGHTCYAN_EX
Y = Fore.YELLOW

CONFIG_PATH = Path("~/.ssh/config").expanduser()