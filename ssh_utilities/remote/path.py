"""Implements Path-like object for remote hosts."""

import errno
import logging
import os
from functools import wraps
from os.path import samestat
from pathlib import Path, PurePosixPath, PureWindowsPath  # type: ignore
from sys import version_info as python_version
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..utils import for_all_methods

if TYPE_CHECKING:
    from paramiko.sftp_file import SFTPFile

    from ..typeshed import _SPATH
    from .remote import SSHConnection

__all__ = ["SSHPath"]

log = logging.getLogger(__name__)

DEC_EXCLUDE = ("_parse_args", "_from_parts", "_from_parsed_parts",
               "_format_parsed_parts", "cwd", "home")


def _to_ssh_path(function: Callable):
    """A to cast all return types to SSHPath where applicable.

    Parameters
    ----------
    function: Callable
        function to check for right return type
    """
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        """Take care to preserve order of commands it is crucial!.

        See also
        --------
        :class:`SSHPath`
        """
        # get function name
        name = function.__name__
        log.debug(f"wrapping: {name}, instance is: {type(self)}")

        # If it was not SSHPath instance before don't cast to SSHPath
        # wrapper is not needed, return imediatelly
        #
        # methods __new__  and _init must be excluded because the connection
        # is not yet initialized when they are called
        if not isinstance(self, SSHPath) or name in ("__new__", "_init"):
            return function(self, *args, **kwargs)

        # get connection attribute before it is destroyed by running the method
        connection = self.c

        # run the method and capture output
        output = function(self, *args, **kwargs)

        # if result is path instance, which is wrong, cast to SSHPath
        # we do not care for other return types and leave those unchanged
        if isinstance(output, Path):
            return SSHPath(connection, output)
        else:
            return output

    return wrapper


class _SSHAccessor:

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    def mkdir(self, *args, **kwargs):
        self.c.os.makedirs(*args, **kwargs)

    def rmdir(self, *args, **kwargs):
        self.c.os.rmdir(*args, **kwargs)

    def chmod(self, *args, **kwargs):
        self.c.os.chmod(*args, **kwargs)

    def lchmod(self, *args, **kwargs):
        self.c.os.lchmod(*args, **kwargs)

    def unlink(self, *args, **kwargs):
        self.c.os.unlink(*args, **kwargs)

    def symlink(self, *args, **kwargs):
        self.c.os.symlink(*args, **kwargs)

    if python_version >= (3, 10):
        def open(self, *args, **kwargs):
            self.c.builtins.open(*args, **kwargs)
    else:
        # This will not work, we have no way to emulate os.open function which
        # is called in this method chain by Path._opener Only in version 3.10
        # this changes from os.open --> io.open
        pass

    def stat(self, *args, **kwargs):
        return self.c.os.stat(*args, **kwargs)

    def lstat(self, *args, **kwargs):
        return self.c.os.lstat(*args, **kwargs)

    def scandir(self, *args, **kwargs):
        return self.c.os.scandir(*args, **kwargs)

    def listdir(self, *args, **kwargs):
        return self.c.os.listdir(*args, **kwargs)

    def rename(self, *args, **kwargs):
        return self.c.os.rename(*args, **kwargs)

    def replace(self, *args, **kwargs):
        return self.c.os.replace(*args, **kwargs)


class _Template:

    def __init__(self, accessor: _SSHAccessor) -> None:
        self._accessor = accessor


@for_all_methods(_to_ssh_path, subclasses=True, exclude=DEC_EXCLUDE)
class SSHPath(Path):
    """Object providing similar API to Pathlib.Path but for remote server.

    The for all methods wrapper will wrap whole pathlib library and thus will
    always try to cast every path to SSHPath, so logic must be emplyed in
    wrapper to prevent this.

    Parameters
    ----------
    connection: Connection
        instance of `ssh_utilities.Connection` to server
    path: _SPATH
        initial path

    Warnings
    --------
    Some methods have changed signature from classmethod -> instancemethod
    since old approach was not vaiable in this application. These are:
    home() and cwd().
    """

    _flavour = Any
    _accessor: _SSHAccessor
    c: "SSHConnection"

    def __new__(cls, connection: "SSHConnection", *args, **kwargs):
        """Remote Path class construtor.

        Copied and adddapted from pathlib.
        """
        try:
            if connection.os.name == 'nt':
                cls._flavour = PureWindowsPath._flavour  # type: ignore
            else:
                cls._flavour = PurePosixPath._flavour  # type: ignore
        except AttributeError as e:
            log.exception(e)

        self = cls._from_parts(args, init=False)  # type: ignore
        self.c = connection
        self._init(template=_Template(_SSHAccessor(connection)))
        return self

    @property
    def connection(self) -> "SSHConnection":
        return self.c

    @property
    def _2str(self):
        return os.fspath(self)

    def cwd(self) -> "SSHPath":  # type: ignore
        """Returns current working directory.

        Warnings
        --------
        This is no longer a class method!
        Sometimes return value can be empty string for unknown reasons.

        Returns
        -------
        SSHPath
            path to current directory
        """
        d = self.c.sftp.getcwd()
        if d:
            return SSHPath(self.c, d)
        else:
            return SSHPath(self.c, self.c.sftp.normalize("."))

    def home(self) -> "SSHPath":  # type: ignore
        """Get home dir on remote server for logged in user.

        Warnings
        --------
        This is no longer a class method!

        Returns
        -------
        Path
            path to remote home
        """
        if not self.c._sftp_open:
            self.c.sftp
        return SSHPath(self.c, self.c._remote_home)

    def group(self) -> str:
        """Return file group.

        Returns
        -------
        str
            string with group name

        Raises
        ------
        NotImplementedError
            when used on windows host
        """
        if self.c.os.name == "nt":
            raise NotImplementedError("This is implemented only for posix "
                                      "type systems")
        else:
            cmd = ["stat", "-c", "'%G'", str(self)]
            group = self.c.subprocess.run(cmd, suppress_out=True, quiet=True,
                                          capture_output=True,
                                          encoding="utf-8").stdout

            return group

    if python_version < (3, 10):
        def open(self, mode: str = "r", buffering: int = -1,  # type: ignore
                 encoding: Optional[str] = "utf-8", errors: Optional[str] = None,
                 newline: Optional[str] = None) -> "SFTPFile":
            """Opens remote file, works as pathlib.Path open function.

            Can be used both as a function or a decorator.

            Parameters
            ----------
            filename: _SPATH
                path to file to be opened
            mode: str
                select mode to open file. Same as python open modes
            encoding: str
                encoding type to decode file bytes stream
            errors: Optional[str]
                define error handling when decoding raw stream
            newline: Optional[str]
                define how newline symbols are handled
            buffering: int
                buffer size, 0 turns off buffering, 1 uses line buffering, and any
                number greater than 1 (>1) uses that specific buffer size

            Raises
            ------
            FileNotFoundError
                when mode is 'r' and file does not exist
            """
            return self.c.builtins.open(self, mode=mode, buffering=buffering,
                                        encoding=encoding, errors=errors,
                                        newline=newline)

    def owner(self):
        """Return file owner.

        Returns
        -------
        str
            string with owner name

        Raises
        ------
        NotImplementedError
            when used on windows host
        """
        if self.c.os.name == "nt":
            raise NotImplementedError("This is implemented only for posix "
                                      "type systems")
        else:
            cmd = ["getent", "passwd", self.stat().st_uid, "|", "cut", "-d:", "-f1"]
            owner = self.c.subprocess.run(cmd, suppress_out=True, quiet=True,
                                          capture_output=True,
                                          encoding="utf-8").stdout

            return owner

    if python_version < (3, 9):
        # in version bellow 3.9 there is a call to os.stat instead of
        # _accessor.stat so we have to override
        def samefile(self, other_path: "_SPATH"):
            """Return whether other_path is the same or not as this file.

            As returned by os.path.samefile())
            """
            st = self.stat()
            try:
                other_st = other_path.stat()  # type: ignore
            except AttributeError:
                other_st = self._accessor.stat(other_path)
            return samestat(st, other_st)

    def touch(self, mode: int = 0o666, exist_ok: bool = True):
        """Create this file with the given access mode, if it doesn't exist.

        The permissions are unix-style and identical to those used by
        Python’s os.chmod function.

        Parameters
        ----------
        mode : int
            integer number of the desired mode
        exist_ok: bool
            do not raise an exception when file already exists

        Raises
        ------
        FileExistsError
            when file or directory with same name already exists
        """
        if self.exists() and not exist_ok:
            raise FileExistsError(
                errno.ENOENT, os.strerror(errno.ENOENT), self._2str
            )
        else:
            with self.c.builtins.open(self, "w") as f:
                f.write("")

            self.chmod(mode=mode)

    def absolute(self):
        """Return an absolute version of this path.

        This function works even if the path doesn't point to anything.

        No normalization is done, i.e. all '.' and '..' will be kept along.
        Use resolve() to get the canonical path to a file.
        """
        # XXX untested yet!
        if self._closed:
            self._raise_closed()
        if self.is_absolute():
            return self
        # because of this we must override, pathlib uses os.getcwd
        # method and does not go through accessor
        obj = self._from_parts([self.cwd()._2str] + self._parts, init=False)
        obj._init(template=self)
        return obj

    def expanduser(self):
        """Return a new path with expanded ~ and ~user constructs.

        As returned by os.path.expanduser
        """
        if (not (self._drv or self._root) and
            self._parts and self._parts[0][:1] == '~'):
            homedir = self.home()._2str
            return self._from_parts([homedir] + self._parts[1:])

        return self
