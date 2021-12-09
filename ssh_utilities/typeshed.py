"""Module containing typing aliases for ssh-utilities."""

from typing import (IO, TYPE_CHECKING, Any, Callable, Iterator, List, Mapping,
                    Optional, Sequence, Tuple, Union, Type)

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

if TYPE_CHECKING:
    from os import PathLike
    from pathlib import Path

    from .remote.path import SSHPath

    AnyPath = Union[str, bytes, PathLike[str], PathLike[bytes]]

#: opened file object or int file descriptor
_FILE = Union[None, int, IO[Any]]
#: string or bytes variable
_TXT = Union[bytes, str]
# Python 3.6 does't support _CMD being a single PathLike.
# See: https://bugs.python.org/issue31961
#: command to exectute for subprocess run, can be str, bytes or sefuence of
#: these
_CMD = Union[_TXT, Sequence["AnyPath"]]
#: mapping of environment varibles names
_ENV = Optional[Union[Mapping[bytes, _TXT], Mapping[str, _TXT]]]
#: srting glob pattern
_GLOBPAT = Optional[str]
#: accepted path types by ssh_utilities - str, Path or SSHPath
#: for remote connection
_SPATH = Union[str, "Path", "SSHPath"]
#: accepted path types by ssh_utilities - str, Path or SSHPath
#: for local connection
_PATH = Union[str, "Path", "SSHPath"]
#: alias for file send direction - put or get
_DIRECTION = Literal["get", "put"]
#: copy callback function - callable that accepts two floats first reperesents
#: done part and second total amount
_CALLBACK = Optional[Callable[[float, float], Any]]
#: walk iterator yield typle exactly same as os.walk
_WALK = Iterator[Tuple[str, List[str], List[str]]]
#: alias for exception of tuple of exceptions
_EXCTYPE = Union[Type[Exception], Tuple[Type[Exception], ...]]
#: callble that accept one argument which is of exception type
_ONERROR = Optional[Callable[[Exception], Any]]

__all__ = ["_FILE", "_CMD", "_ENV", "_GLOBPAT", "_SPATH", "_PATH",
           "_DIRECTION", "_CALLBACK", "_WALK", "_EXCTYPE", "_ONERROR"]
