"""Local proxy to pathlib library."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..base import PathlibABC

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .local import LocalConnection

__all__ = ["Pathlib"]

logging.getLogger(__name__)


class Pathlib(PathlibABC):
    """Proxy for `pathlib.Path` object with same API as remote version."""

    def __init__(self, connection: "LocalConnection") -> None:
        self.c = connection

    def Path(self, path: "_SPATH") -> Path:
        return Path(self.c._path2str(path))
