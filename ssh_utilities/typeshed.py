"""Module containing typing aliases for ssh-utilities."""

from typing import (IO, TYPE_CHECKING, Any, Callable, Iterator, List, Mapping,
                    Optional, Sequence, Tuple, Union, Type)

from typing_extensions import Literal

if TYPE_CHECKING:
    from os import PathLike
    from pathlib import Path

    from .remote.path import SSHPath

    AnyPath = Union[str, bytes, PathLike[str], PathLike[bytes]]

    _FILE = Union[None, int, IO[Any]]
    _TXT = Union[bytes, str]
    # Python 3.6 does't support _CMD being a single PathLike.
    # See: https://bugs.python.org/issue31961
    _CMD = Union[_TXT, Sequence[AnyPath]]
    _ENV = Union[Mapping[bytes, _TXT], Mapping[str, _TXT]]

    _GLOBPAT = Optional[str]
    _SPATH = Union[str, Path, SSHPath]
    _DIRECTION = Literal["get", "put"]
    _CALLBACK = Optional[Callable[[float, float], Any]]
    _WALK = Iterator[Tuple[str, List[str], List[str]]]
    _EXCTYPE = Union[Type[Exception], Tuple[Type[Exception], ...]]


__all__ = ["_FILE", "_CMD", "_ENV", "_GLOBPAT", "_SPATH", "_DIRECTION",
           "_CALLBACK", "_WALK", "_EXCTYPE"]
