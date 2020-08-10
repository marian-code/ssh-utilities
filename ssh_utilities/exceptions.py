"""Module defining exceptions for ssh-utilities."""

import logging
from subprocess import CalledProcessError, TimeoutExpired

__all__ = ["CalledProcessError", "SFTPOpenError", "ConnectionError",
           "TimeoutExpired"]

logging.getLogger(__name__)

logging.getLogger(__name__)


class SFTPOpenError(Exception):
    """Raised when sftp channel could not be opened."""

    pass


class ConnectionError(Exception):
    """Raised when connection to remote cannot be established."""

    pass


class UnknownOsError(Exception):
    """Raised when remote server os could not be determined."""

    pass
