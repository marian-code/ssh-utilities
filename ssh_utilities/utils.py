"""Helper function and classes for ssh_utilities module."""

import re
import sys
import time
from types import MethodType
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, List, Optional, Union, Sequence

from colorama import Back

from .exceptions import CalledProcessError

__all__ = ["ProgressBar", "N_lines_up", "bytes_2_human_readable",
           "CompletedProcess", "lprint", "for_all_methods", "glob2re"]


class CompletedProcess:
    """Completed remote process, mimics subprocess.CompletedProcess API."""

    def __init__(self):

        self.args: List[str] = []
        self.returncode: Optional[int] = None
        self.stdout: str = ""
        self.stderr: str = ""

    def __str__(self):
        return (f"<CompletedProcess>(\n"
                f"stdout: {self.stdout}\nstderr: {self.stderr}\n"
                f"returncode: {self.returncode}\nargs: {self.args})")

    def check_returncode(self):
        """Check if remote process return code was 0, if not raise exception.

        Raises
        ------
        CalledProcessError
            if return code was non-zero
        """
        if self.returncode != 0:
            raise CalledProcessError(self.returncode, self.args, self.stdout,
                                     self.stderr)


class ProgressBar:
    """Measure file copy speed and disply progressbar."""

    def __init__(self, total: int = 0) -> None:
        self._average_speed = 0.0
        self._total = total
        self._done = 0

    def start(self, total_size: int):
        """Start timer.

        Parameters
        ----------
        total_size : int
            total size of files to copy in bytes.
        """
        self._average_speed = 0.0
        self.total = total_size
        self._done = 0

    @contextmanager
    def update(self, size: int, quiet: bool):
        """Update copying progressbar.

        Parameters
        ----------
        size : int
            actual copied size
        quiet : bool
            if true print of message is suppressed
        """
        t_start = time.time()
        yield
        cp_time = time.time() - t_start

        self._average_speed = (self._average_speed + (size / cp_time)) / 2
        self._done += size

        percent_done = int(100 * (self._done / self._total))

        if percent_done < 10:
            progress_bar = f"{' ' * 49}{percent_done}%{' ' * 49}"
        elif percent_done == 100:
            progress_bar = f"{' ' * 47}{percent_done}%{' ' * 49}"
        else:
            progress_bar = f"{' ' * 48}{percent_done}%{' ' * 49}"

        progress_bar_1 = progress_bar[:percent_done]
        progress_bar_2 = progress_bar[percent_done:]

        if not quiet:
            print(f"|{Back.LIGHTGREEN_EX}{progress_bar_1}{Back.RESET}"
                  f"{progress_bar_2}| "
                  f"{bytes_2_human_readable(self._average_speed)}/s", quiet)


def lprint(text: Any, quiet: bool = False):
    """Function that limits print output.

    Paremeters
    ----------
    text: Any
        content to print
    quiet: bool
        if true, do not print and return imediatelly
    """
    if quiet:
        pass
    else:
        print(text)


def for_all_methods(decorator: Callable, exclude: Sequence[str] = [],
                    subclasses: bool = False):
    """Decorate all methods in class.

    Parameters
    ----------
    decorator: Callable
        callable to be used to decorate class methods
    exclude: List[str]
        list of method names to exclude
    subclasses:
        if true decorate also all subclasses methods

    Warnings
    --------
    This decorator should be used on class only.

    Static and class methods must be excluded or they will not work

    Use subclasses=True with great care! it will decorate methods for all
    instances of class in your module
    """
    def decorate(cls):
        if subclasses:
            try:
                classes = cls.__mro__
            except AttributeError:
                classes = [cls]
        else:
            classes = [cls]
        for c in classes:
            for attr in c.__dict__:
                if callable(getattr(c, attr)) and attr not in exclude:
                    try:
                        setattr(c, attr, decorator(getattr(c, attr)))
                    except TypeError:
                        pass
        return cls
    return decorate


def N_lines_up(N, quiet: bool):
    """Move cursor N lines up.

    Parameters
    ----------
    quiet: bool
        if true print of message is suppressed
    """
    if not quiet:
        sys.stdout.write(f"\033[{N}A")
        sys.stdout.write("\033[K ")
        print("\r", end="")


def glob2re(patern):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.

    Parameters
    ----------
    pattern: str
        shell glob pattern

    References
    ----------
    https://stackoverflow.com/questions/27726545/python-glob-but-against-a-list-of-strings-rather-than-the-filesystem
    """
    i, n = 0, len(patern)
    res = ''
    while i < n:
        c = patern[i]
        i += 1
        if c == '*':
            res = res + '.*'
            # res += '[^/]*'
        elif c == '?':
            res = res + '.'
            # res +='[^/]'
        elif c == '[':
            j = i
            if j < n and patern[j] == '!':
                j += 1
            if j < n and patern[j] == ']':
                j += 1
            while j < n and patern[j] != ']':
                j += 1
            if j >= n:
                res += '\\['
            else:
                stuff = patern[i:j].replace('\\', '\\\\')
                i = j + 1
                if stuff[0] == '!':
                    stuff = '^' + stuff[1:]
                elif stuff[0] == '^':
                    stuff = '\\' + stuff
                res = '%s[%s]' % (res, stuff)
        else:
            res = res + re.escape(c)
    return res + '\Z(?ms)'


def bytes_2_human_readable(number_of_bytes: Union[int, float],
                           unit: str = "b") -> str:
    """Convert bytes to human readable format.

    Parameters
    ----------
    number_of_bytes : int
        number to convert
    unit : str
        units of the passed in size, by default "b"

    Returns
    -------
    str
        filesize in best suitable format

    Raises
    ------
    ValueError
        if number of bytes is less than 0
    """
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
