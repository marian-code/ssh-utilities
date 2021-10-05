"""Implements Path-like object for remote hosts."""

import logging
from functools import wraps
from os import fspath
from os.path import samestat
from pathlib import Path, PurePosixPath, PureWindowsPath  # type: ignore
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
        self.c.shutil.rmtree(*args, **kwargs)

    # ! This will not work we have no way to emulate os.open function which
    # ! is called in this method chain by Path._opener
    # def open(self, *args, **kwargs):
    #     self.c.builtins.open(*args, **kwargs)

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


class _Template:

    def __init__(self, accessor: _SSHAccessor) -> None:
        self._accessor = accessor


@for_all_methods(_to_ssh_path, subclasses=True, exclude=DEC_EXCLUDE)
class SSHPath(Path):
    """Object porviding similar API to Pathlib.Path but for remote server.

    The for all methods wrapper will wrap whole pathlib library and thus will
    always try to cas every path to SSHPath, so logic must be emplyed in
    wrapper to prevent this.

    Parameters
    ----------
    connection: Connection
        instance of `ssh_utilities.Connection` to server
    path: _SPATH
        initial path

    Warnings
    --------
    Not all methods are implemented! Some rather obscure had to be left out
    due to the nature of ssh and lazyness of the author

    Some methods have changed signature from classmethod -> instancemethod
    since old approach was not vaiable in this application. Most notably:
    home() and cwd().

    Raises
    ------
    NotImplementedError when on some methods that have not been implemented.
    """

    _flavour = Any
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
        return fspath(self)

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
        For this to work correctly sftp channel must be open

        Returns
        -------
        Path
            path to remote home
        """
        if not self.c._sftp_open:
            self.c.sftp
        return SSHPath(self.c, self.c._remote_home)

    def chmod(self, mode: int):
        """Change the mode/permissions of a file.

        The permissions are unix-style and identical to those used by
        Python’s os.chmod function.

        Parameters
        ----------
        mode : int
            integer number of the desired mode
        """
        self.c.sftp.chmod(self._2str, mode)

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

    def replace(self, target: "_SPATH") -> "SSHPath":  # type: ignore[override]
        """Rename this path to the given path.

        Parameters
        ----------
        target : _SPATH
            target path

        Returns
        -------
        SSHPath
            New Path instance pointing to the given path.
        """
        self = SSHPath(self.c, fspath(target))
        self.c.os.chdir(target)
        return self

    # TODO this method could also run through accessor,
    # TODO need to implement replace in os
    def resolve(self) -> "SSHPath":  # type: ignore[override]
        """Make the path absolute.

        Resolve all symlinks on the way and also normalize it.

        Returns
        -------
        "SSHPath"
            [description]
        """
        return SSHPath(self.c, self.c.sftp.normalize(self._2str))

    def samefile(self, other_path: "_SPATH"):
        """Return whether other_path is the same or not as this file
        (as returned by os.path.samefile()).
        """
        st = self.stat()
        try:
            other_st = other_path.stat()  # type: ignore
        except AttributeError:
            other_st = self.c.os.stat(other_path)
        return samestat(st, other_st)

    def symlink_to(self, target: "_SPATH", target_is_directory: bool = False):
        """Make this path a symlink pointing to the given path.

        Parameters
        ----------
        target : _SPATH
            target path to which symlink will point
        target_is_directory: bool
            this parameter is ignored

        Warnings
        --------
        `target_is_directory` parameter is ignored
        """
        self.c.sftp.symlink(self._2str, fspath(target))

    def touch(self, mode: int = 0o666, exist_ok: bool = True):
        """Create this file with the given access mode, if it doesn't exist.

        The permissions are unix-style and identical to those used by
        Python’s os.chmod function.

        Parameters
        ----------
        mode : int
            integer number of the desired mode
        exist_ok: bool
            do not raise an exception when fiel already exists

        Raises
        ------
        FileExistsError
            when file or directory with same name already exists
        """
        if self.exists() and not exist_ok:
            raise FileExistsError(f"{self} is a file or dir, "
                                  f"cannot create new file")
        else:
            with self.c.builtins.open(self, "w") as f:
                f.write("")

            self.chmod(mode=mode)

    def unlink(self, missing_ok: bool = False):
        """Delete file or symbolic link.

        Parameters
        ----------
        missing_ok : bool, optional
            If False and file does not exist raise exception, by default False

        Raises
        ------
        FileNotFoundError
            if missing_ok is false and file does not exist
        IsADirectoryError
            if trying to unlink a directory
        """
        if not self.exists() and not missing_ok:
            raise FileNotFoundError("Cannot unlink file/dir does not exist")
        elif self.is_dir():
            raise IsADirectoryError("Path is a directory use rmdir instead")
        elif self.is_file():
            self.c.sftp.unlink(self._2str)

    # ! NOT IMPLEMENTED
    def link_to(self, target):
        raise NotImplementedError

    def lchmod(self, mode):
        raise NotImplementedError

    def absolute(self):
        raise NotImplementedError
