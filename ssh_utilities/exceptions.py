"""Module defining exceptions for ssh utilities."""

from subprocess import CalledProcessError

__all__ = ["CalledProcessError", "SFTPOpenError", "ConnectionError"]


class SFTPOpenError(Exception):
    """Raised when sftpf channel could not be opened."""

    pass


class ConnectionError(Exception):
    """Raised when connection to remote cannot be established."""

    pass
