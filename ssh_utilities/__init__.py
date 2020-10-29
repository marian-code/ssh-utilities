"""SSH utilities module a thin wrapper of subset of paramiko functionality.

Exposes the most used paramiko methods in user friendly way
replicates subses of these APIs for remote hosts:
- os.path
- pathlib.path
- subprocess.run

Which should be enough for almost any file operations and some moderately
complex process running.
"""

import logging

from .connection import Connection
from .local import LocalConnection
from .remote._pathlib import SSHPath
from .remote._subprocess import PIPE, STDOUT, DEVNULL
from .remote.remote import SSHConnection
from .constants import GET, PUT

__all__ = ["SSHConnection", "Connection", "LocalConnection", "SSHPath", "PIPE",
           "STDOUT", "DEVNULL", "GET", "PUT"]

logging.getLogger(__name__)
