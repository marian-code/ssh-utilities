"""Template module for all connection classes."""

from ._builtins import BuiltinsABC
from ._connection import ConnectionABC
from ._os import OsABC, DirEntryABC
from ._os_path import OsPathABC
from ._pathlib import PathlibABC
from ._shutil import ShutilABC
from ._subprocess import SubprocessABC

from typing import TYPE_CHECKING, Iterator, Union, List, IO

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

if TYPE_CHECKING:
    from os import stat_result, DirEntry

    from paramiko.sftp_attr import SFTPAttributes
    from paramiko.sftp_file import SFTPFile
    from subprocess import CompletedProcess as sCP
    from ..utils import CompletedProcess as CP

    from pathlib import Path
    from ..typeshed import _WALK
    from ..remote.path import SSHPath

    _ATTRIBUTES = Union[SFTPAttributes, stat_result]
    #: iterator that scans through directory and return DirEntry objects
    _SCANDIR = Iterator[Union["DirEntry", "DirEntryABC"]]

    # Because python typing system does not support higher kinded types we must
    # resort to this soulution of the problem and pass in all the prepared
    # return types to the Generic class which is ugly and more error prone than
    # would be ideal
    # problem discussion: https://github.com/python/typing/issues/548
    # potentially use returns in the future github.com/dry-python/returns
    # * multi types
    _BUILTINS_MULTI = BuiltinsABC[Iterator[Union[IO, SFTPFile]]]
    _OS_MULTI = OsABC[
        Iterator[_SCANDIR],
        Iterator[List[str]],
        Iterator[_ATTRIBUTES],
        Iterator[Literal["nt", "posix", "java"]],
        Iterator[OsPathABC],
        Iterator[_WALK],
    ]
    _PATHLIB_MULTI = PathlibABC[Iterator[Union[Path, SSHPath]]]
    _SHUTIL_MULTI = ShutilABC
    _SUBPROCESS_MULTI = SubprocessABC[Iterator[Union[CP, sCP]]]

    # * remote types
    _BUILTINS_REMOTE = BuiltinsABC["SFTPFile"]
    _OS_REMOTE = OsABC[
        _SCANDIR,
        List[str],
        "SFTPAttributes",
        Literal["nt", "posix"],
        OsPathABC,
        "_WALK",
    ]
    _PATHLIB_REMOTE = PathlibABC["SSHPath"]
    _SHUTIL_REMOTE = ShutilABC
    _SUBPROCESS_REMOTE = SubprocessABC[Union[CP, sCP]]

    # * local types
    _BUILTINS_LOCAL = BuiltinsABC[IO]
    _OS_LOCAL = OsABC[
        _SCANDIR,
        List[str],
        "stat_result",
        Literal["nt", "posix", "java"],
        OsPathABC,
        _WALK,
    ]
    _PATHLIB_LOCAL = PathlibABC[Path]
    _SHUTIL_LOCAL = ShutilABC
    _SUBPROCESS_LOCAL = SubprocessABC[Union[CP, sCP]]


__all__ = [
    "ConnectionABC",
    "OsPathABC",
    "BuiltinsABC",
    "OsABC",
    "ShutilABC",
    "SubprocessABC",
    "PathlibABC",
    "DirEntryABC",
]
