"""Python builtins proxy."""

import logging
from typing import IO, TYPE_CHECKING, Optional

from ..abstract import BuiltinsABC

if TYPE_CHECKING:
    from ..typeshed import _PATH
    from .local import LocalConnection

__all__ = ["Builtins"]

logging.getLogger(__name__)


class Builtins(BuiltinsABC):
    """Local proxy for python builtins, mainly the open function.

    Supports same subset of API as remote version.

    See also
    --------
    :class:`ssh_utilities.remote.Builtins`
        remote version of class with same API
    """

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    def open(self, filename: "_PATH", mode: str = "r", buffering: int = -1,
             encoding: Optional[str] = None, errors: Optional[str] = None,
             newline: Optional[str] = None
             ) -> IO:
        encoding = encoding if encoding else "utf-8"
        errors = errors if errors else "strict"
        filename = self.c._path2str(filename)

        return open(filename, mode, encoding=encoding, errors=errors,
                    buffering=buffering, newline=newline)
