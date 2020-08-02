"""Helper function and classes for ssh_utilities module."""

import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Union

from paramiko.config import SSHConfig
from tqdm import tqdm
from tqdm.utils import _term_move_up

from .exceptions import CalledProcessError

__all__ = ["ProgressBar", "N_lines_up", "bytes_2_human_readable",
           "CompletedProcess", "lprint", "for_all_methods", "glob2re",
           "file_filter", "config_parser", "context_timeit"]


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


class _DummyTqdmWrapper:

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    def update_bar(self, *args, **kwargs):
        pass

    def write(self, *args, **kwargs):
        pass


class _TqdmWrapper(tqdm):

    _prefix = _term_move_up() + '\r'

    def __init__(self, *args, **kwargs) -> None:

        # write_up is not a tqdm natice argument, it determines how many lines
        # will be written above the progressbar
        self._prefix = self._prefix * kwargs.pop("write_up")

        super().__init__(*args, **kwargs)

        self._last_transfered = 0

    def update_bar(self, transfered: int, total_file_size: int):
        part = transfered - self._last_transfered
        if part < 0:
            part = transfered
        self._last_transfered = transfered
        self.update(part)  # update pbar with increment

    def write(self, s, _file=None, end="\n", nolock=False):
        super().write(self._prefix + s, file=_file, end=end, nolock=nolock)


def ProgressBar(total: Optional[float] = None, unit: str = 'b',
                unit_scale: bool = True, miniters: int = 1, ncols: int = 100,
                unit_divisor: int = 1024, write_up=2,
                quiet: bool = True, *args, **kwargs
                ) -> Union[_DummyTqdmWrapper, _TqdmWrapper]:
    """Progress Bar factory return tqdm subclass or dummy replacement.

    Parameters
    ----------
    total : Optional[int]
        total number to transfer, units are set with unit parameter
    unit : str
        units in which total is input, by default 'b'
    unit_scale : bool
        whether toscale units
    miniters : int
        minimum number of iterations after which update takes place
    ncols : int
        progressbar length
    unit_divisor : int
        scale factor for units
    write_up : int
        number of lines that are written above progressbar
    quiet : bool
        if True progressbar is not shown

    Returns
    -------
    Union[_DummyTqdmWrapper, _TqdmWrapper]
        which is returned is decided based on value of quiet argument
    """
    if quiet:
        return _DummyTqdmWrapper(total=total, unit=unit, unit_scale=unit_scale,
                                 miniters=miniters, ncols=ncols,
                                 unit_divisor=unit_divisor, write_up=write_up,
                                 *args, **kwargs)
    else:
        return _TqdmWrapper(total=total, unit=unit, unit_scale=unit_scale,
                            miniters=miniters, ncols=ncols,
                            unit_divisor=unit_divisor, write_up=write_up,
                            *args, **kwargs)


class lprint:
    """Callable class that limits print output.

    Parameters
    ----------
    text: Any
        content to print
    quiet: bool
        if true, do not print and return imediatelly
    """

    line_rewrite = True

    def __init__(self, quiet: bool = False):
        self._quiet = quiet
        self._first_print = True

    def __call__(self, text: Any, *, up=None):

        if self._first_print or not self.line_rewrite:
            prefix = ""
        else:
            prefix = (_term_move_up() + "\r") * up

        if not self._quiet:
            print(f"{prefix}{text}")


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

    Use `subclasses=True` with great care! it will decorate methods for all
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


# ! DEPRECATED
class N_lines_up:
    """Move cursor N lines up.

    Warnings
    --------
    function is deprecated !

    Parameters
    ----------
    quiet: bool
        if true print of message is suppressed
    """

    line_rewrite = True

    def __init__(self, *, quiet: bool) -> None:
        self._print = all([not quiet, self.line_rewrite])

    def __call__(self, N: int):
        if self._print:
            sys.stdout.write(f"\033[{N}A")
            sys.stdout.write("\033[K ")
            print("\r", end="")


class file_filter:
    """Discriminate files to copy by passed in glob patterns.

    This is a callable class and works much in a same way as
    operator.itemgetter

    Parameters
    ----------
    include: Optional[str]
        pattern of files to include
    exclude: Optional[str]
        patttern if files to exclude
    """

    def __init__(self, include: Optional[str], exclude: Optional[str]) -> None:

        if include and exclude:
            self._inc = re.compile(glob2re(include))
            self._exc = re.compile(glob2re(exclude))
            self.match = self._match_both
        elif include and not exclude:
            self._inc = re.compile(glob2re(include))
            self.match = self._match_inc
        elif not include and exclude:
            self._exc = re.compile(glob2re(exclude))
            self.match = self._match_exc
        elif not include and not exclude:
            self.match = self._match_none

    def _match_none(self, filename: str) -> bool:
        return True

    def _match_inc(self, filename: str) -> bool:
        if not self._inc.search(filename):
            return False
        else:
            return True

    def _match_exc(self, filename: str) -> bool:
        if self._exc.search(filename):
            return False
        else:
            return True

    def _match_both(self, filename: str) -> bool:
        return self._match_exc(filename) and self._match_inc(filename)

    def __call__(self, filename: str) -> bool:
        return self.match(filename)


def glob2re(patern):
    """Translate a shell PATTERN to a regular expression.

    There is no way to quote meta-characters.

    Parameters
    ----------
    patern: str
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
    return '(?ms)' + res + '\Z'


def config_parser(config_path: Union["Path", str]) -> SSHConfig:
    """Parses ssh config file.

    Parameters
    ----------
    config_path : Path
        path to config file

    Returns
    -------
    SSHConfig
        paramiko SSHConfig object that parses config file
    """
    if isinstance(config_path, str):
        config_path = Path(config_path).expanduser()

    config = SSHConfig()
    config.parse(config_path.open())

    return config


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


@contextmanager
def context_timeit(quiet: bool = False):
    """Context manager which timme the code executed in its scope.

    Simple stats about CPU time are printed on context exit.

    Parameters
    ----------
    quiet : bool, optional
        If true no statistics are printed on context exit, by default False
    """
    start = time.time()
    yield
    end = time.time()
    if not quiet:
        print(f"CPU time: {(end - start):.2f}s")
    else:
        pass


# \033[<L>;<C>H # Move the cursor to line L, column C
# \033[<N>A     # Move the cursor up N lines
# \033[<N>B     # Move the cursor down N lines
# \033[<N>C     # Move the cursor forward N columns
# \033[<N>D     # Move the cursor backward N columns
# \033[2J       # Clear the screen, move to (0,0)
# \033[K        # Erase to end of line
