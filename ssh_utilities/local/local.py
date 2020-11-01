"""Module implementing local connection functionality.

Has the same API as remote version.
"""

import logging
from pathlib import Path
from socket import gethostname
from typing import Optional, Union

from ..constants import G, Y
from ..utils import lprint
from ..base import ConnectionABC
from . import Builtins, Os, Pathlib, Shutil, Subprocess

__all__ = ["LocalConnection"]

logging.getLogger(__name__)


class LocalConnection(ConnectionABC):
    """Emulates SSHConnection class on local PC."""

    def __init__(self, address: Optional[str], username: str,
                 password: Optional[str] = None,
                 rsa_key_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, server_name: Optional[str] = None,
                 quiet: bool = False, thread_safe: bool = False) -> None:

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.rsa_key_file = rsa_key_file

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
    def builtins(self) -> Builtins:
        return self._builtins

    @property
    def os(self) -> Os:
        return self._os

    @property
    def pathlib(self) -> Pathlib:
        return self._pathlib

    @property
    def shutil(self) -> Shutil:
        return self._shutil

    @property
    def subprocess(self) -> Subprocess:
        return self._subprocess

    def __str__(self) -> str:
        return self.to_str("LocalConnection", self.server_name, None,
                           self.username, None, True)

    @staticmethod
    def close(*, quiet: bool = True):
        """Close emulated local connection."""
        lprint(quiet)(f"{G}Closing local connection")

    @staticmethod
    def ssh_log(log_file="paramiko.log", level="WARN"):
        lprint()(f"{Y}Local sessions are not logged!")
