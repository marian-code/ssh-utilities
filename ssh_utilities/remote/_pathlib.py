"""Module with pathlib functionality for SSHConnection."""

import logging
from typing import TYPE_CHECKING

from ..base import PathlibABC
from ._connection_wrapper import check_connections
from .path import SSHPath

if TYPE_CHECKING:
    from ..typeshed import _SPATH
    from .remote import SSHConnection

__all__ = ["Pathlib"]

log = logging.getLogger(__name__)


class Pathlib(PathlibABC):
    """Expose pathlib like API for remote hosts.

    See also
    --------
    :class:`ssh_utilities.local.Pathlib`
        local version of class with same API
    """

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    @check_connections()
    def Path(self, path: "_SPATH") -> SSHPath:
        """Provides API similar to pathlib.Path only for remote host.

        Only for Unix to Unix connections

        Parameters
        ----------
        path: _SPATH
            provide initial path

        Returns
        -------
        SSHPath
            object representing remote path
        """
        return SSHPath(self.c, self.c._path2str(path))
