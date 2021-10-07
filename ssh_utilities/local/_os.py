"""Local connection os methods."""

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from ..abstract import OsABC, OsPathABC

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

    def scandir(self, path: "_SPATH"):
        return os.scandir(self.c._path2str(path))

    def chmod(self, path: "_SPATH", mode: int, *, dir_fd: Optional[int] = None,
              follow_symlinks: bool = True):
        os.chmod(self.c._path2str(path), mode, dir_fd=dir_fd,
                 follow_symlinks=follow_symlinks)

    def lchmod(self, path: "_SPATH", mode: int):
        os.lchmod(self.c._path2str(path), mode)

    def symlink(self, src: "_SPATH", dst: "_SPATH",
                target_is_directory: bool = False, *,
                dir_fd: Optional[int] = None):
        os.symlink(src, dst, target_is_directory=target_is_directory,
                   dir_fd=dir_fd)

    def remove(self, path: "_SPATH", *, dir_fd: int = None):
        os.remove(path, dir_fd=dir_fd)

    def unlink(self, path: "_SPATH", *, dir_fd: int = None):
        os.unlink(path, dir_fd=dir_fd)

    def rmdir(self, path: "_SPATH", *, dir_fd: int = None):
        os.rmdir(path, dir_fd=dir_fd)

    def rename(self, src: "_SPATH", dst: "_SPATH", *,
               src_dir_fd: Optional[int] = None,
               dst_dir_fd: Optional[int] = None):
        os.rename(self.c._path2str(src), self.c._path2str(dst),
                  src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def replace(self, src: "_SPATH", dst: "_SPATH", *,
                src_dir_fd: Optional[int] = None,
                dst_dir_fd: Optional[int] = None):
        os.replace(self.c._path2str(src), self.c._path2str(dst),
                   src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
        Path(self.c._path2str(path)).mkdir(mode=mode, parents=parents,
                                           exist_ok=exist_ok)

    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        self.makedirs(path, mode, exist_ok=False, parents=False, quiet=quiet)

    @staticmethod
    def listdir(path: "_SPATH") -> List[str]:
        return os.listdir(path)

    def chdir(self, path: "_SPATH"):
        os.chdir(self.c._path2str(path))

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

        return self._osname

    def walk(self, top: "_SPATH", topdown: bool = True,
             onerror=None, followlinks: bool = False) -> os.walk:
        return os.walk(top, topdown, onerror, followlinks)


class OsPathLocal(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    def isfile(self, path: "_SPATH") -> bool:
        return os.path.isfile(self.c._path2str(path))

    def isdir(self, path: "_SPATH") -> bool:
        return os.path.isdir(self.c._path2str(path))

    def exists(self, path: "_SPATH") -> bool:
        return os.path.exists(self.c._path2str(path))

    def islink(self, path: "_SPATH") -> bool:
        return os.path.islink(self.c._path2str(path))

    def realpath(self, path: "_SPATH") -> str:
        return os.path.realpath(self.c._path2str(path))

    def getsize(self, path: "_SPATH") -> int:
        return os.path.getsize(self.c._path2str(path))

    def join(self, path: "_SPATH", *paths: "_SPATH") -> str:
        return os.path.join(self.c._path2str(path),
                            *[self.c._path2str(p) for p in paths])
