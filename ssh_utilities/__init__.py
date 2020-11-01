"""SSH utilities module a thin wrapper of subset of paramiko functionality.

Exposes the most used paramiko methods in user friendly way
replicates subses of these APIs for remote hosts:
- os.path
- pathlib.path
- subprocess.run

Which should be enough for almost any file operations and some moderately
complex process running.
"""

from warnings import warn

warn("The old API is deprecated, please refer to the docs for changes: "
     "https://ssh-utilities.readthedocs.io/en/latest/", DeprecationWarning)

import logging

from .connection import Connection
from .local import LocalConnection
from .remote.path import SSHPath
from .remote import SSHConnection, PIPE, STDOUT, DEVNULL
from .constants import GET, PUT
from .utils import config_parser

__all__ = ["SSHConnection", "Connection", "LocalConnection", "SSHPath", "PIPE",
           "STDOUT", "DEVNULL", "GET", "PUT", "config_parser"]

logging.getLogger(__name__)
