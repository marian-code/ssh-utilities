"""Python builtins proxy."""

import logging
from typing import TYPE_CHECKING, Optional, IO

from ..base import ConnectionABC

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .local import LocalConnection

__all__ = ["Builtins"]

logging.getLogger(__name__)


class Builtins(ConnectionABC):
    """Local proxy for python builtins, mainly the open function.

    Supports same subset of API as remote version.
    """

    def __init__(self, connection: "LocalConnection") -> None:
        pass

    @staticmethod
    def open(filename: "_SPATH", mode: str = "r",
             encoding: Optional[str] = None,
             bufsize: int = -1, errors: Optional[str] = None
             ) -> IO:
        encoding = encoding if encoding else "utf-8"
        errors = errors if errors else "strict"

        return open(filename, mode, encoding=encoding, errors=errors)
