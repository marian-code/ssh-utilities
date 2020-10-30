"""Module implementing local connection functionality.

Has the same API as remote version.
"""

import logging
from pathlib import Path
from socket import gethostname
from typing import Optional, Union

from ..constants import G, Y
from ..utils import lprint
from ._builtins import Builtins
from ._os import Os
from ._pathlib import Pathlib
from ._shutil import Shutil
from ._subprocess import Subprocess

__all__ = ["LocalConnection"]

logging.getLogger(__name__)


class LocalConnection(Builtins, Shutil, Os, Subprocess, Pathlib):
    """Emulates SSHConnection class on local PC."""

    def __init__(self, address: Optional[str], username: str,
                 password: Optional[str] = None,
                 rsa_key_file: Optional[Union[str, Path]] = None,
                 line_rewrite: bool = True, server_name: Optional[str] = None,
                 quiet: bool = False, share_connection: int = 10) -> None:

        # set login credentials
        self.password = password
        self.address = address
        self.username = username
        self.rsa_key_file = rsa_key_file

        self.server_name = server_name if server_name else gethostname()
        self.server_name = self.server_name.upper()

        self.local = True

        # init subclasses
        Builtins.__init__(self, self)
        Shutil.__init__(self, self)
        Os.__init__(self, self)
        Pathlib.__init__(self, self)
        Subprocess.__init__(self, self)

    def __str__(self) -> str:
        return self.to_str("LocalConnection", self.server_name, None,
                           self.username, None)

    @staticmethod
    def close(*, quiet: bool = True):
        """Close emulated local connection."""
        lprint(quiet)(f"{G}Closing local connection")

    @staticmethod
    def ssh_log(log_file="paramiko.log", level="WARN"):
        lprint()(f"{Y}Local sessions are not logged!")
