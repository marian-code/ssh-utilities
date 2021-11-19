"""Local connection os.path methods."""

import logging
import os
from typing import TYPE_CHECKING

from ..abstract import OsPathABC

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .local import LocalConnection

__all__ = ["OsPath"]

logging.getLogger(__name__)


class OsPath(OsPathABC):
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
