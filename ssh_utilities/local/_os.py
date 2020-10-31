"""Local connection os methods."""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, List

from typing_extensions import Literal

from ..base import OsABC, OsPathABC

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .local import LocalConnection

__all__ = ["Os"]

logging.getLogger(__name__)


class Os(OsABC):
    """Class housing subset os module methods with same API as remote version.

    See also
    --------
    :class:`ssh_utilities.remote.Os`
        remote version of class with same API
    """

    _osname: Literal["nt", "posix", "java"]

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection
        self._path = OsPathLocal(connection)  # type: ignore

    @property
    def path(self) -> "OsPathLocal":
        return self._path

    @staticmethod
    def isfile(path: "_SPATH") -> bool:
        return os.path.isfile(path)

    @staticmethod
    def isdir(path: "_SPATH") -> bool:
        return os.path.isdir(path)

    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
        Path(self.c._path2str(path)).mkdir(mode=mode, parents=parents,
                                           exist_ok=exist_ok)

    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        self.makedirs(path, mode, exist_ok=False, parents=False, quiet=quiet)

    @staticmethod
    def listdir(path: "_SPATH") -> List[str]:
        return os.listdir(path)

    def stat(self, path: "_SPATH", *, dir_fd=None,
             follow_symlinks: bool = True) -> os.stat_result:
        return os.stat(self.c._path2str(path), dir_fd=dir_fd,
                       follow_symlinks=follow_symlinks)

    def lstat(self, path: "_SPATH", *, dir_fd=None) -> os.stat_result:
        return os.lstat(self.c._path2str(path), dir_fd=dir_fd)

    @property
    def name(self) -> Literal["nt", "posix", "java"]:
        try:
            self._osname
        except AttributeError:
            self._osname = os.name  # type: ignore
        finally:
            return self._osname

    osname = name


class OsPathLocal(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    def realpath(self, path: "_SPATH") -> str:
        return os.path.realpath(self.c._path2str(path))
