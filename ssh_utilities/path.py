"""Implements Path-like object for remote hosts."""

import logging
import re
import stat
from functools import wraps
from os import fspath
from os.path import join
from pathlib import Path, PurePosixPath, PureWindowsPath  # type: ignore
from typing import TYPE_CHECKING, Any, Callable, Generator, Optional, Union

from .utils import for_all_methods, glob2re

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes
    from paramiko.sftp_file import SFTPFile
    SPath = Union[str, Path, "SSHPath"]
    from .remote import SSHConnection

__all__ = ["SSHPath"]

logging.getLogger(__name__)

DEC_EXCLUDE = ("_parse_args", "_from_parts", "_from_parsed_parts",
               "_format_parsed_parts", "cwd", "home")


def to_ssh_path(function: Callable):
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

        # If it was not SSHPath instance before don't cast to SSHPath
        # wrapper is not needed, return imediatelly
        #
        # methods __new__  and _init must be excluded because the connection
        # is not yet initialized when they are called
        if not isinstance(self, SSHPath) or name in ("__new__", "_init"):
            return function(self, *args, **kwargs)

        # get connection attribute before it is destroyed by running the method
        connection = self._c

        # run the method and capture output
        output = function(self, *args, **kwargs)

        # if result is path instance, which is wrong, cast to SSHPath
        # we do not care for other return types and leave those unchanged
        if isinstance(output, Path):
            return SSHPath(connection, output)
        else:
            return output

    return wrapper


@for_all_methods(to_ssh_path, subclasses=True, exclude=DEC_EXCLUDE)
class SSHPath(Path):
    """Object porviding similar API to Pathlib.Path but for remote server.

    The for all methods wrapper will wrap whole pathlib library and thus will
    always try to cas every path to SSHPath, so logic must be emplyed in
    wrapper to prevent this.

    Parameters
    ----------
    connection: Connection
        instance of `ssh_utilities.Connection` to server
    path: SPath
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
    _c: "SSHConnection"

    def __new__(cls, connection: "SSHConnection", *args, **kwargs):
        """Remote Path class construtor.

        Copied and adddapted from pathlib.
        """
        if connection.osname == 'nt':
            cls._flavour = PureWindowsPath._flavour  # type: ignore
        else:
            cls._flavour = PurePosixPath._flavour  # type: ignore

        self = cls._from_parts(args, init=False)  # type: ignore
        self._c = connection
        self._init()
        return self

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
        d = self._c.sftp.getcwd()
        if d:
            return SSHPath(self._c, d)
        else:
            return SSHPath(self._c, self._c.sftp.normalize("."))

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
        if not self._c._sftp_open:
            self._c.sftp
        return SSHPath(self._c, self._c.remote_home)

    @property
    def stat(self) -> "SFTPAttributes":
        """Get file or directory statistics.

        Returns
        -------
        paramiko.sftp_attr.SFTPAttributes
            statistics objec similar to os.stat output

        Raises
        ------
        FileNotFoundError
            if input path does not exist
        """
        if not self.is_file():
            raise FileNotFoundError("File doe not exist")
        return self._c.sftp.stat(self._2str)

    def chmod(self, mode: int):
        """Change the mode/permissions of a file.

        The permissions are unix-style and identical to those used by
        Python’s os.chmod function.

        Parameters
        ----------
        mode : int
            integer number of the desired mode
        """
        self._c.sftp.chmod(self._2str, mode)

    def exists(self) -> bool:
        """Check if path exists.

        This is constrained by the subset of implemented
        pathlib.Path functionality.
        """
        return any((self.is_dir(), self.is_file(), self.is_symlink(),
                    self.is_socket(), self.is_fifo(), self.is_block_device(),
                    self.is_char_device()))

    def glob(self, pattern: str) -> Generator["SSHPath", None, None]:
        """Glob the given relative pattern in directory given by this path.

        Parameters
        ----------
        pattern : str
            glob pattern to ue for filtering

        Yields
        ------
        SSHPath
            yields all matching files (of any kind):

        Raises
        ------
        FileNotFoundError
            if current path does not point to directory
        """
        if not self.is_dir():
            raise FileNotFoundError(f"Directory {self} does not exist.")

        if pattern.startswith("**"):
            recursive = True
        else:
            recursive = False

        pattern = glob2re(pattern)

        for root, dirs, files in self._c._sftp_walk(self):

            for path in dirs + files:
                path = join(root, path)
                if re.search(pattern, f"/{path}", re.I):
                    yield SSHPath(self._c, path)

            if not recursive:
                break

    def is_dir(self) -> bool:
        """Check if path points to directory.

        Returns
        -------
        bool
            True if pointing to a directory
        """
        return self._c.isdir(self)

    def is_file(self) -> bool:
        """Check if path points to file.

        Returns
        -------
        bool
            True if pointing to a file
        """
        return self._c.isfile(self)

    def is_symlink(self):
        """Check if path points to symlink.

        Returns
        -------
        bool
            True if pointing to a symlink
        """
        return stat.S_ISLNK(self.stat.st_mode)

    def is_socket(self):
        """Check if path points to socket.

        Returns
        -------
        bool
            True if pointing to a socket
        """
        return stat.S_ISSOCK(self.stat.st_mode)

    def is_fifo(self):
        """Check if path points to FIFO pipe.

        Returns
        -------
        bool
            True if pointing to a FIFO pipe
        """
        return stat.S_ISFIFO(self.stat.st_mode)

    def is_block_device(self):
        """Check if path points to block device.

        Returns
        -------
        bool
            True if pointing to a block device
        """
        return stat.S_ISBLK(self.stat.st_mode)

    def is_char_device(self):
        """Check if path points to character device.

        Returns
        -------
        bool
            True if pointing to a character device
        """
        return stat.S_ISCHR(self.stat.st_mode)

    def iterdir(self) -> Generator["SSHPath", None, None]:
        """Iterate files in current directory.

        Yields
        ------
        SSHPath
            yields paths in current dir

        Raises
        ------
        FileNotFoundError
            if this path is not a directory and thus cannot be iterated
        """
        if not self.is_dir():
            raise FileNotFoundError(f"Directory {self} does not exist.")
        else:
            for p in self._c.listdir(self):
                yield self / p

    def mkdir(self, mode: int = 511, parents: bool = False,
              exist_ok: bool = False):
        """Recursively create directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: "SPath"
            path to directory which should be created
        mode: int
            create directory with mode, default is 511
        exist_ok: bool
            if true and directory exists, exception is silently passed when dir
            already exists
        parents: bool
            if true any missing parent dirs are automatically created, else
            exception is raised on missing parent

        Raises
        ------
        OSError
            if directory could not be created
        FileNotFoundError
            when parent directory is missing and parents=False
        FileExistsError
            when directory already exists and exist_ok=False
        """
        self._c.mkdir(self, mode=mode, exist_ok=exist_ok, parents=parents)

    def open(self, mode: str = "r", buffering: int = -1,  # type: ignore
             encoding: Optional[str] = "utf-8") -> "SFTPFile":
        """Opens remote file, works as pathlib.Path open function.

        Can be used both as a function or a decorator.

        Parameters
        ----------
        filename: SPath
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
        self._c.open(self, mode=mode, bufsize=buffering, encoding=encoding)

    def read_bytes(self) -> bytes:
        """Read contents of a file as bytes.

        Returns
        -------
        bytes
            file contents encoded as bytes

        Raises
        ------
        FileNotFoundError
            if path does not point to a file
        """
        if not self.is_file():
            raise FileNotFoundError("Cannot open file.")
        with self._c.open(self, "rb") as f:
            return f.read()

    def read_text(self, encoding: Optional[str] = None,
                  errors: Optional[str] = None) -> str:
        """Read whole file to string.

        Parameters
        ----------
        encoding : Optional[str], optional
            file encoding, by default None - means uft-8
        errors : Optional[str], optional
            error handling for the decoder, by default None - `strict` handling

        Returns
        -------
        str
            whole file read to string

        Raises
        ------
        FileNotFoundError
            if file does not exist
        """
        if not self.is_file():
            raise FileNotFoundError("Cannot open file.")
        with self._c.open(self, "r", encoding=encoding, errors=errors) as f:
            return f.read()

    def rename(self, target: "SPath") -> "SSHPath":  # type: ignore[override]
        """Rename directory or file.

        Parameters
        ----------
        target: SPath
            path name afer renaming

        Warnings
        --------
        Works only in posix
        """
        if self._c.osname == "nt":
            raise NotImplementedError("Does not work on windows servers")

        self._c.sftp.posix_rename(self._2str, fspath(target))
        return self.replace(target)

    def replace(self, target: "SPath") -> "SSHPath":  # type: ignore[override]
        """Rename this path to the given path.

        Parameters
        ----------
        target : SPath
            target path

        Returns
        -------
        SSHPath
            New Path instance pointing to the given path.
        """
        self = SSHPath(self._c, fspath(target))
        self._c.change_dir(target)
        return self

    def resolve(self) -> "SSHPath":  # type: ignore[override]
        """Make the path absolute.

        Resolve all symlinks on the way and also normalize it.

        Returns
        -------
        "SSHPath"
            [description]
        """
        return SSHPath(self._c.sftp.normalize(self._2str))

    def rglob(self, pattern: str) -> Generator["SSHPath", None, None]:
        """Glob the given relative pattern in directory given by this path.

        Convenience function for glob.

        Parameters
        ----------
        pattern : str
            glob pattern to ue for filtering

        Yields
        ------
        SSHPath
            yields all matching files (of any kind)

        Raises
        ------
        FileNotFoundError
            if current path does not point to directory
        """
        return self.glob(f"**/{pattern}")

    def rmdir(self):
        """Remove directory, after point path to parent.

        Warnings
        --------
        This is recursive contrary to pathlib.Path implementation
        """
        self._c.rmtree(self)
        self.replace(self.parent)

    def symlink_to(self, target: "SPath"):  # type: ignore[override]
        """Make this path a symlink pointing to the given path.

        Parameters
        ----------
        target : SPath
            target path to which symlink will point
        """
        self._c.sftp.symlink(self._2str, fspath(target))

    def touch(self, mode=0o666, exist_ok: bool = True):
        """Create this file with the given access mode, if it doesn't exist.

        Warnings
        --------
        mode argument is not used

        Raises
        ------
        FileExistsError
            when file exists
        """
        if self.exists() and not exist_ok:
            raise FileExistsError(f"{self} is a file or dir, "
                                  f"cannot create new file")
        else:
            with self._c.open(self, "w") as f:
                f.write("")

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
            self._c.sftp.unlink(self._2str)

    def write_bytes(self, data: Union[bytes, bytearray, memoryview]):
        """Write bytes to file.

        Parameters
        ----------
        data : Union[bytes, bytearray, memoryview]
            content to write to file
        """
        view = memoryview(data)
        with self._c.open(self, "wb") as f:
            f.write(view)
            # f.write(data.encode())

    def write_text(self, data, encoding: Optional[str] = None,
                   errors: Optional[str] = None):
        """Write whole string to file.

        Parameters
        ----------
        data : str
            string to write to file
        encoding : Optional[str], optional
            file encoding, by default None - means uft-8
        errors : Optional[str], optional
            error handling for the decoder, by default None - `strict` handling

        Raises
        ------
        TypeError
            if data is not string type
        """
        if not isinstance(data, str):
            raise TypeError(f"data must be str, not {data.__class__.__name__}")

        with self._c.open(self, "w", encoding=encoding, errors=errors) as f:
            f.write(data)

    # ! NOT IMPLEMENTED
    def group(self):
        raise NotImplementedError

    def link_to(self, target):
        raise NotImplementedError

    def lstat(self):
        raise NotImplementedError

    def owner(self):
        raise NotImplementedError

    def is_mount(self):
        raise NotImplementedError
