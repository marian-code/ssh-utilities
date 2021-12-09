"""Local connection os methods."""

import logging
import os
from typing import TYPE_CHECKING, List, Optional

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from ..abstract import OsABC
from ._os_path import OsPath

if TYPE_CHECKING:
    from ..typeshed import _PATH
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
        self._path = OsPath(connection)  # type: ignore

    @property
    def path(self) -> OsPath:
        return self._path

    def scandir(self, path: "_PATH"):
        return os.scandir(self.c._path2str(path))

    def chmod(self, path: "_PATH", mode: int, *, dir_fd: Optional[int] = None,
              follow_symlinks: bool = True):
        os.chmod(self.c._path2str(path), mode, dir_fd=dir_fd,
                 follow_symlinks=follow_symlinks)

    def lchmod(self, path: "_PATH", mode: int):
        os.lchmod(self.c._path2str(path), mode)

    def symlink(self, src: "_PATH", dst: "_PATH",
                target_is_directory: bool = False, *,
                dir_fd: Optional[int] = None):
        os.symlink(src, dst, target_is_directory=target_is_directory,
                   dir_fd=dir_fd)

    def remove(self, path: "_PATH", *, dir_fd: int = None):
        os.remove(path, dir_fd=dir_fd)

    def unlink(self, path: "_PATH", *, dir_fd: int = None):
        os.unlink(path, dir_fd=dir_fd)

    def rmdir(self, path: "_PATH", *, dir_fd: int = None):
        os.rmdir(path, dir_fd=dir_fd)

    def rename(self, src: "_PATH", dst: "_PATH", *,
               src_dir_fd: Optional[int] = None,
               dst_dir_fd: Optional[int] = None):
        os.rename(self.c._path2str(src), self.c._path2str(dst),
                  src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def replace(self, src: "_PATH", dst: "_PATH", *,
                src_dir_fd: Optional[int] = None,
                dst_dir_fd: Optional[int] = None):
        os.replace(self.c._path2str(src), self.c._path2str(dst),
                   src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    def makedirs(self, path: "_PATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
        os.makedirs(self.c._path2str(path), mode=mode, exist_ok=exist_ok)

    def mkdir(self, path: "_PATH", mode: int = 511, quiet: bool = True):
        self.makedirs(path, mode, exist_ok=False, parents=False, quiet=quiet)

    def listdir(self, path: "_PATH") -> List[str]:
        return os.listdir(self.c._path2str(path))

    def chdir(self, path: "_PATH"):
        os.chdir(self.c._path2str(path))

    def stat(self, path: "_PATH", *, dir_fd=None,
             follow_symlinks: bool = True) -> os.stat_result:
        return os.stat(self.c._path2str(path), dir_fd=dir_fd,
                       follow_symlinks=follow_symlinks)

    def lstat(self, path: "_PATH", *, dir_fd=None) -> os.stat_result:
        return os.lstat(self.c._path2str(path), dir_fd=dir_fd)

    @property
    def name(self) -> Literal["nt", "posix", "java"]:
        try:
            self._osname
        except AttributeError:
            self._osname = os.name  # type: ignore

        return self._osname

    def walk(self, top: "_PATH", topdown: bool = True,
             onerror=None, followlinks: bool = False) -> os.walk:
        return os.walk(top, topdown, onerror, followlinks)

    @staticmethod
    def supports_fd():
        return os.supports_fd()

    @staticmethod
    def supports_dir_fd():
        return os.supports_dir_fd()

    
