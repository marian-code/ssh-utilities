"""Module collecting shutil-like local methods."""

import logging
import shutil
from pathlib import Path
from typing import (IO, TYPE_CHECKING, Any, Callable, List, Optional, Sequence,
                    Set)

from ..abstract import ShutilABC
from ..utils import context_timeit, deprecation_warning, file_filter

if TYPE_CHECKING:
    from ..typeshed import _CALLBACK, _DIRECTION, _GLOBPAT, _PATH
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

    def ignore_patterns(self, *paterns: Sequence[str]
                        ) -> Callable[[Any, Sequence[str]], Set[str]]:
        return shutil.ignore_patterns(*paterns)

    @staticmethod
    def copyfileobj(fsrc: IO, fdst: IO, *, direction: "_DIRECTION",
                    length: Optional[int] = None):

        if length:
            shutil.copyfileobj(fsrc, fdst, length)
        else:
            shutil.copyfileobj(fsrc, fdst)

    def copyfile(self, src: "_PATH", dst: "_PATH", *,
                 direction: "_DIRECTION", follow_symlinks: bool = True,
                 callback: "_CALLBACK" = None, quiet: bool = True):

        shutil.copyfile(self.c._path2str(src), self.c._path2str(dst),
                        follow_symlinks=follow_symlinks)

    def copy(self, src: "_PATH", dst: "_PATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):
        shutil.copy(self.c._path2str(src), self.c._path2str(dst),
                    follow_symlinks=follow_symlinks)

    def copy2(self, src: "_PATH", dst: "_PATH", *, direction: "_DIRECTION",
              follow_symlinks: bool = True, callback: "_CALLBACK" = None,
              quiet: bool = True):
        shutil.copy2(self.c._path2str(src), self.c._path2str(dst),
                     follow_symlinks=follow_symlinks)

    def download_tree(self, remote_path: "_PATH", local_path: "_PATH",
                      include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                      remove_after: bool = True, quiet: bool = False):

        def _cpy(src: str, dst: str):
            if src not in ignore_files("", src):
                shutil.copy2(src, dst)

        ignore_files = file_filter(include, exclude)

        remote_path = self.c._path2str(remote_path)
        local_path = self.c._path2str(local_path)

        if remove_after:
            shutil.move(remote_path, local_path, copy_function=_cpy)
        else:
            shutil.copytree(remote_path, local_path, copy_function=_cpy)

    def upload_tree(self, local_path: "_PATH", remote_path: "_PATH",
                    include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                    remove_after: bool = True, quiet: bool = False):

        self.download_tree(local_path, remote_path, include=include,
                           exclude=exclude, remove_after=remove_after,
                           quiet=quiet)

    def rmtree(self, path: "_PATH", ignore_errors: bool = False,
               quiet: bool = True):
        shutil.rmtree(self.c._path2str(path), ignore_errors=ignore_errors)
