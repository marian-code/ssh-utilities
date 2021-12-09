"""Module implementing local connection functionality.

Has the same API as remote version.
"""

import logging
from socket import gethostname
from typing import TYPE_CHECKING, Dict, Optional, Union

from ..abstract import ConnectionABC
from ..constants import G, Y
from ..remote.path import SSHPath
from ..utils import lprint
from . import Builtins, Os, Pathlib, Shutil, Subprocess

if TYPE_CHECKING:
    from pathlib import Path

    from ..abstract import (_BUILTINS_LOCAL, _OS_LOCAL, _PATHLIB_LOCAL,
                            _SHUTIL_LOCAL, _SUBPROCESS_LOCAL)
    from ..typeshed import _PATH

__all__ = ["LocalConnection"]

logging.getLogger(__name__)


class LocalConnection(ConnectionABC):
    """Emulates SSHConnection class on local PC."""

    def __init__(self, address: Optional[str], username: str,
                 password: Optional[str] = None,
                 pkey_file: Optional[Union[str, "Path"]] = None,
                 line_rewrite: bool = True, server_name: Optional[str] = None,
                 quiet: bool = False, thread_safe: bool = False,
                 allow_agent: Optional[bool] = False) -> None:

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.pkey_file = pkey_file
        self.allow_agent = allow_agent

        self.server_name = server_name if server_name else gethostname()
        self.server_name = self.server_name.upper()

        self.local = True

        # init submodules
        self._builtins = Builtins(self)  # type: ignore
        self._os = Os(self)  # type: ignore
        self._pathlib = Pathlib(self)  # type: ignore
        self._shutil = Shutil(self)  # type: ignore
        self._subprocess = Subprocess(self)  # type: ignore

    @property
    def builtins(self) -> "_BUILTINS_LOCAL":
        """Inner class providing access to substitutions for python builtins.

        :type: .remote.Builtins
        """
        return self._builtins

    @property
    def os(self) -> "_OS_LOCAL":
        """Inner class providing access to substitutions for python os module.

        :type: .remote.Os
        """
        return self._os

    @property
    def pathlib(self) -> "_PATHLIB_LOCAL":
        """Inner class providing access to substitutions for pathlib module.

        :type: .remote.Pathlib
        """
        return self._pathlib

    @property
    def shutil(self) -> "_SHUTIL_LOCAL":
        """Inner class providing access to substitutions for shutil module.

        :type: .remote.Shutil
        """
        return self._shutil

    @property
    def subprocess(self) -> "_SUBPROCESS_LOCAL":
        """Inner class providing access to substitutions for subprocess module.

        :type: .remote.Subprocess
        """
        return self._subprocess

    def __str__(self) -> str:
        return self._to_str("LocalConnection", self.server_name, None,
                            self.username, None, True, False)

    def to_dict(self) -> Dict[str, Optional[Union[str, bool, int]]]:
        return self._to_dict("LocalConnection", self.server_name, None,
                             self.username, None, True, False)

    @staticmethod
    def close(*, quiet: bool = True):
        """Close emulated local connection."""
        lprint(quiet)(f"{G}Closing local connection")

    @staticmethod
    def ssh_log(log_file="paramiko.log", level="WARN"):
        lprint()(f"{Y}Local sessions are not logged!")

    def _path2str(self, path: Optional["_PATH"]) -> str:
        if isinstance(path, SSHPath):
            raise TypeError(
                "LocalConnection does not accept 'SSHPath' as input"
            )
        else:
            return super()._path2str(path)
