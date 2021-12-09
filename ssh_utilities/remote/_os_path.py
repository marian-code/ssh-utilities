"""Remote connection os.path methods."""

import errno
import logging
import os
from ntpath import join as njoin
from posixpath import join as pjoin
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING

from ..abstract import OsPathABC
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .remote import SSHConnection


__all__ = ["OsPath"]

log = logging.getLogger(__name__)


# alternative to os.path module
class OsPath(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    @check_connections(exclude_exceptions=IOError)
    def isfile(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISREG(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections(exclude_exceptions=IOError)
    def isdir(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISDIR(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections
    def exists(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            unwrap(self, self.c._path2str(path))
        except FileNotFoundError:
            return False
        else:
            return True

    @check_connections(exclude_exceptions=IOError)
    def islink(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISLNK(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections
    def realpath(self, path: "_SPATH") -> str:
        return self.c.sftp.normalize(self.c._path2str(path))

    def getsize(self, path: "_SPATH") -> int:

        size = self.c.os.stat(path).st_size

        if size:
            return size
        else:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )

    @check_connections
    def join(self, path: "_SPATH", *paths: "_SPATH") -> str:

        if self.c.os.name == "nt":
            return njoin(self.c._path2str(path),
                         *[self.c._path2str(p) for p in paths])
        else:
            return pjoin(self.c._path2str(path),
                         *[self.c._path2str(p) for p in paths])
