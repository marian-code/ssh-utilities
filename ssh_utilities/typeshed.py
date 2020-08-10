from typing import IO, TYPE_CHECKING, Any, Mapping, Optional, Sequence, Union

if TYPE_CHECKING:
    from os import PathLike
    from pathlib import Path
    from .path import SSHPath

    AnyPath = Union[str, bytes, PathLike[str], PathLike[bytes]]

    _FILE = Union[None, int, IO[Any]]
    _TXT = Union[bytes, str]
    # Python 3.6 does't support _CMD being a single PathLike.
    # See: https://bugs.python.org/issue31961
    _CMD = Union[_TXT, Sequence[AnyPath]]
    _ENV = Union[Mapping[bytes, _TXT], Mapping[str, _TXT]]

    _GLOBPAT = Optional[str]
    _SPATH = Union[str, Path, SSHPath]

__all__ = ["_FILE", "_CMD", "_ENV", "_GLOBPAT", "_SPATH"]