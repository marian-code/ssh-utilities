"""Helper function and classes for ssh_utilities module."""

import fnmatch
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import (TYPE_CHECKING, Any, Callable, Generic, List, Optional,
                    Sequence, Set, TypeVar, Union)
from warnings import warn

from paramiko.config import SSHConfig
from tqdm import tqdm
from tqdm.utils import _term_move_up

from .exceptions import CalledProcessError

if TYPE_CHECKING:
    from .remote.path import SSHPath
    from .typeshed import _CMD, _SPATH

__all__ = ["ProgressBar", "bytes_2_human_readable", "CompletedProcess",
           "lprint", "for_all_methods", "file_filter", "config_parser",
           "context_timeit", "NullContext", "path_wildcard_expand"]


_CompletedProcess = TypeVar("_CompletedProcess", str, bytes)


class CompletedProcess(Generic[_CompletedProcess]):
    """Completed remote process, mimics subprocess.CompletedProcess API.

    Parameters
    ----------
    bytes_out: bool
        is true set stderr and stdout to bytes
    """

    stdout: _CompletedProcess
    stderr: _CompletedProcess

    def __init__(self, initial: _CompletedProcess):

        self.args: "_CMD" = []
        self.returncode: Optional[int] = None

        self.stdout = initial
        self.stderr = initial

    def __str__(self):
        return (f"<CompletedProcess>(\n"
                f"stdout: {self.stdout}\nstderr: {self.stderr}\n"
                f"returncode: {self.returncode}\nargs: {self.args})")

    @property
    def cmd(self) -> "_CMD":
        return self.args

    @property
    def output(self) -> _CompletedProcess:
        return self.stdout

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
    """Dummy wrapper mirroring tqdm wrapper.

    All methods do nothing, used when no output is to be printed.
    """

    def __init__(self, *args, **kwargs) -> None:  # NOSONAR
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):  # NOSONAR
        pass

    def update_bar(self, *args, **kwargs):  # NOSONAR
        pass

    def write(self, *args, **kwargs):  # NOSONAR
        pass


class _TqdmWrapper(tqdm):

    _prefix = _term_move_up() + '\r'

    def __init__(self, *args, **kwargs) -> None:

        # write_up is not a tqdm natice argument, it determines how many lines
        # will be written above the progressbar
        self._prefix = self._prefix * kwargs.pop("write_up")

        super().__init__(*args, **kwargs)

        self._last_transfered = 0

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return super().__exit__(exc_type, exc_value, traceback)

    def update_bar(self, transfered: int, total_file_size: int):
        part = transfered - self._last_transfered
        if part < 0:
            part = transfered
        self._last_transfered = transfered
        self.update(part)  # update pbar with increment

    def write(self, s, _file=None, end="\n", nolock=False):
        super().write(self._prefix + s, file=_file, end=end, nolock=nolock)


def ProgressBar(total: Optional[float] = None, unit: str = 'b',  # NOSONAR
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
            for attr_str in c.__dict__:

                attr = getattr(c, attr_str)

                if callable(attr) and attr_str not in exclude:
                    try:
                        setattr(c, attr_str, decorator(attr))
                    except TypeError:
                        pass
                elif isinstance(attr, property):
                    new_property = property(decorator(attr.__get__),
                                            attr.__set__, attr.__delattr__)
                    setattr(c, attr_str, new_property)
        return cls
    return decorate


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

    def __init__(self, include: Optional[Union[str, Sequence[str]]],
                 exclude: Optional[Union[str, Sequence[str]]]) -> None:

        if isinstance(include, str):
            include = [include]
        if isinstance(exclude, str):
            exclude = [exclude]

        self._inc_pattern = include
        self._exc_pattern = exclude

        if include and exclude:
            self.match = self._match_both
        elif include and not exclude:
            self.match = self._match_inc
        elif not include and exclude:
            self.match = self._match_exc
        elif not include and not exclude:
            self.match = self._match_none

    def _match_none(self, path: "_SPATH", filenames: Sequence[str]) -> Set[str]:
        return set()

    def _match_inc(self, path: "_SPATH", filenames: Sequence[str]) -> Set[str]:

        files = []
        for pattern in self._inc_pattern:  # type: ignore
            files.extend(fnmatch.filter(filenames, pattern))

        return set([f for f in filenames if f not in files])

    def _match_exc(self, path: "_SPATH", filenames: Sequence[str]) -> Set[str]:

        files = []
        for pattern in self._exc_pattern:  # type: ignore
            files.extend(fnmatch.filter(filenames, pattern))

        return set(files)

    def _match_both(self, path: "_SPATH", filenames: Sequence[str]) -> Set[str]:
        return self._match_exc(path, filenames).union(self._match_inc(path, filenames))

    def __call__(self, path: "_SPATH", filenames: Sequence[str]) -> Set[str]:
        return self.match(path, filenames)


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
    try:
        config.parse(config_path.open())
    except FileNotFoundError:
        pass

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


class NullContext:
    """Replacement for contextlib.nullcontext for python 3.6."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        """Replacement for arbitrrary context that does nothing."""
        pass


def deprecation_warning(replacement: str, additional_msg: str = "") -> Callable:
    """Wrap callable and show deprecation warning before execution.

    Parameters
    ----------
    replacement : str
        suggested replacement callable for the one that emits warning
    additional_msg : str, optional
        additionaly message to display at the end

    Returns
    -------
    Callable
        same callable as passed in only now it emits deprecation warning.
    """

    def decorator(function: Callable) -> Callable:

        @wraps
        def warn_decorator(*args, **kwargs):

            warn(f"{function.__name__} is deprecated and will be removed/made "
                 f"private in future release. Please use {replacement} "
                 f"instead. {additional_msg}")

            return function(*args, **kwargs)

        return warn_decorator
    return decorator


def path_wildcard_expand(*paths: "SSHPath") -> List["SSHPath"]:

    files = []

    for remote_path in paths:
        remote_pattern = str(remote_path.relative_to(remote_path.root))
        remote_root = remote_path.connection.pathlib.Path(remote_path.root)
        remote_files = list(remote_root.glob(remote_pattern))
        files.extend(remote_files)

    return files
        