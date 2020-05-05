from subprocess import CalledProcessError

__all__ = ["CalledProcessError", "SFTPOpenError"]


class SFTPOpenError(Exception):
    """Raised when sftpf channel could not be opened."""
    pass
