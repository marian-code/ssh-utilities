"""Module collecting shutil-like local methods."""

import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List

from ..base import ShutilABC
from ..utils import context_timeit, file_filter

if TYPE_CHECKING:
    from ..typeshed import _CALLBACK, _DIRECTION, _GLOBPAT, _SPATH
    from .local import LocalConnection

__all__ = ["Shutil"]

logging.getLogger(__name__)


class Shutil(ShutilABC):
    """Local version of shutil supporting same subset of API as remote version.

    See also
    --------
    :class:`ssh_utilities.remote.Shutil`
        remote version of class with same API
    """

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    @staticmethod
    def copy_files(files: List[str], remote_path: "_SPATH",
                   local_path: "_SPATH", *, direction: "_DIRECTION",
                   follow_symlinks: bool = True, quiet: bool = False):

        with context_timeit(quiet):
            for f in files:
                file_remote = Path(remote_path) / f
                file_local = Path(local_path) / f

                if direction == "get":
                    shutil.copy2(file_remote, file_local,
                                 follow_symlinks=follow_symlinks)
                elif direction == "put":
                    shutil.copy2(file_local, file_remote,
                                 follow_symlinks=follow_symlinks)
                else:
                    raise ValueError(f"{direction} is not valid direction. "
                                     f"Choose 'put' or 'get'")

    def copyfile(self, src: "_SPATH", dst: "_SPATH", *,
                 direction: "_DIRECTION", follow_symlinks: bool = True,
                 callback: "_CALLBACK" = None, quiet: bool = True):

        shutil.copyfile(self.c._path2str(src), self.c._path2str(dst),
                        follow_symlinks=follow_symlinks)

    def copy(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):
        shutil.copy(self.c._path2str(src), self.c._path2str(dst),
                    follow_symlinks=follow_symlinks)

    def copy2(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
              follow_symlinks: bool = True, callback: "_CALLBACK" = None,
              quiet: bool = True):
        shutil.copy2(self.c._path2str(src), self.c._path2str(dst),
                     follow_symlinks=follow_symlinks)

    def download_tree(self, remote_path: "_SPATH", local_path: "_SPATH",
                      include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                      remove_after: bool = True, quiet: bool = False):

        def _cpy(src: str, dst: str):
            if allow_file(src):
                shutil.copy2(src, dst)

        allow_file = file_filter(include, exclude)

        remote_path = self.c._path2str(remote_path)
        local_path = self.c._path2str(local_path)

        if remove_after:
            shutil.move(remote_path, local_path, copy_function=_cpy)
        else:
            shutil.copytree(remote_path, local_path, copy_function=_cpy)

    def upload_tree(self, local_path: "_SPATH", remote_path: "_SPATH",
                    include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                    remove_after: bool = True, quiet: bool = False):

        self.download_tree(local_path, remote_path, include=include,
                           exclude=exclude, remove_after=remove_after,
                           quiet=quiet)

    @staticmethod
    def rmtree(path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):
        shutil.rmtree(path, ignore_errors=ignore_errors)
