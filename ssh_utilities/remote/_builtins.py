"""Python builtins remote version."""

import logging
from types import MethodType
from typing import TYPE_CHECKING, Optional

from ..base import BuiltinsABC
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient
    from paramiko.sftp_file import SFTPFile

    from ..typeshed import _SPATH
    from .remote import SSHConnection

__all__ = ["Builtins"]

log = logging.getLogger(__name__)


class Builtins(BuiltinsABC):
    """Remote replacement for python builtins, mainly the open function.

    See also
    --------
    :class:`ssh_utilities.local.Builtins`
        local version of class with same API
    """

    sftp: "SFTPClient"

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    @check_connections(exclude_exceptions=FileNotFoundError)
    def open(self, filename: "_SPATH", mode: str = "r",
             encoding: Optional[str] = None,
             bufsize: int = -1, errors: Optional[str] = None
             ) -> "SFTPFile":
        """Opens remote file, works as python open function.

        Can be used both as a function or a decorator.

        Parameters
        ----------
        filename: _SPATH
            path to file to be opened
        mode: str
            select mode to open file. Same as python open modes
        encoding: Optional[str]
            encoding type to decode file bytes stream
        bufsize: int
            buffer size, 0 turns off buffering, 1 uses line buffering, and any
            number greater than 1 (>1) uses that specific buffer size
        errors: Optional[str]
            string that specifies how encoding and decoding errors are to be
            handled, see builtin function
            `open <https://docs.python.org/3/library/functions.html#open>`_
            documentation for more details

        Raises
        ------
        FileNotFoundError
            when mode is 'r' and file does not exist
        """
        path = self.c._path2str(filename)
        encoding = encoding if encoding else "utf-8"
        errors = errors if errors else "strict"

        if not self.c.os.isfile(path) and "r" in mode:
            raise FileNotFoundError(f"Cannot open {path} for reading, "
                                    f"it does not exist.")

        def read_decode(self, size=None):
            data = self.paramiko_read(size=size)

            if isinstance(data, bytes) and "b" not in mode and encoding:
                data = data.decode(encoding=encoding, errors=errors)

            return data

        # open file
        try:
            file_obj = self.c.sftp.open(path, mode=mode, bufsize=bufsize)
        except IOError as e:
            log.exception(f"Error while opening file {filename}: {e}")
            raise e
        else:
            # rename the read method so i is not overwritten
            setattr(file_obj, "paramiko_read", getattr(file_obj, "read"))

            # repalce read with new method that automatically decodes
            file_obj.read = MethodType(read_decode, file_obj)

        return file_obj
