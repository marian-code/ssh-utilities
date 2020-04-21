import math
import os
import sys
import time
import re
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import TypedDict

    ssh = TypedDict('ssh', {'address': str, 'rsa_key': int, 'name': str})

__all__ = ["FakeLog", "parse_ssh_config", "N_lines_up",
           "bytes_2_human_readable"]


class FakeLog:
    """ Fakes python logger methods and reroutes to print instead """

    @classmethod
    def debug(cls, msg):
        cls.__print__(msg)

    @classmethod
    def info(cls, msg):
        cls.__print__(msg)

    @classmethod
    def warning(cls, msg):
        cls.__print_err__(msg)

    @classmethod
    def error(cls, msg):
        cls.__print_err__(msg)

    @classmethod
    def exception(cls, msg):
        cls.__print_err__(msg)

    @classmethod
    def critical(cls, msg):
        cls.__print_err__(msg)

    @classmethod
    def __print__(cls, msg):
        print(str(msg))

    @classmethod
    def __print_err__(cls, msg):
        sys.stderr.write(f"{msg}\n")


def parse_ssh_config(config_file="~/.ssh/config") -> Dict[str, "ssh"]:

    def sp(string):
        return string.rsplit(" ", 1)[1]

    try:
        infile = open(os.path.expanduser(config_file), "r")
    except IOError as e:
        print("Couldn't read ssh config file, reverting to predefine values")
        return
    else:

        entries = infile.read().split("Host ")
        entries = [lines.splitlines() for lines in entries if lines]

        known_hosts = dict()

        for e in entries:
            host = e[0].strip()
            known_hosts[host] = dict()

            for line in e:
                if "HostName" in line:
                    known_hosts[host]["address"] = sp(line)
                if "IdentityFile" in line:
                    known_hosts[host]["rsa_key"] = sp(line)
                if "User" in line:
                    known_hosts[host]["name"] = sp(line)

        return known_hosts
    finally:
        infile.close()


# posunie kurzor o N riadkov nahor
def N_lines_up(N, quiet):
    if not quiet:
        sys.stdout.write(f"\033[{N}A")
        sys.stdout.write("\033[K ")
        print("\r", end="")


# konvertuje bytes na normalne jednotky
def bytes_2_human_readable(number_of_bytes, unit="b"):
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step_to_greater_unit = 1024.0

    number_of_bytes = float(number_of_bytes)
    unit = unit.casefold()
    units = ["b", "kb", "mb", "gb", "tb"]

    index = units.index(unit)

    if ((number_of_bytes / step_to_greater_unit) >= 1 and index == 0):
        number_of_bytes /= step_to_greater_unit
        unit = 'KB'

    if ((number_of_bytes / step_to_greater_unit) >= 1 and index > 0):
        number_of_bytes /= step_to_greater_unit
        unit = 'MB'

    if ((number_of_bytes / step_to_greater_unit) >= 1 and index > 1):
        number_of_bytes /= step_to_greater_unit
        unit = 'GB'

    if ((number_of_bytes / step_to_greater_unit) >= 1 and index > 2):
        number_of_bytes /= step_to_greater_unit
        unit = 'TB'

    precision = 1
    number_of_bytes = round(number_of_bytes, precision)

    return f"{number_of_bytes} {unit}"


# \033[<L>;<C>H # Move the cursor to line L, column C
# \033[<N>A     # Move the cursor up N lines
# \033[<N>B     # Move the cursor down N lines
# \033[<N>C     # Move the cursor forward N columns
# \033[<N>D     # Move the cursor backward N columns
# \033[2J       # Clear the screen, move to (0,0)
# \033[K        # Erase to end of line
