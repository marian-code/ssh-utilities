"""Implements Path-like object for remote hosts."""

import logging
import stat
from collections import deque
from fnmatch import fnmatch
from functools import wraps
from os import fspath
from pathlib import Path, PurePosixPath, PureWindowsPath  # type: ignore
from typing import (TYPE_CHECKING, Any, Callable, Deque, Generator, Optional,
                    Union)

from ..utils import for_all_methods

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes
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
            if connection.os.osname == 'nt':
                cls._flavour = PureWindowsPath._flavour  # type: ignore
            else:
                cls._flavour = PurePosixPath._flavour  # type: ignore
        except AttributeError as e:
            log.exception(e)

        self = cls._from_parts(args, init=False)  # type: ignore
        self.c = connection
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
        return SSHPath(self.c, self.c.remote_home)

    def stat(self) -> "SFTPAttributes":
        """Get file or directory statistics, resolve symlinks alog the way.

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
        return self.c.os.stat(self._2str)

    def lstat(self):
        """Get file or directory statistics, do not resolve symlinks.

        Returns
        -------
        paramiko.sftp_attr.SFTPAttributes
            statistics objec similar to os.lstat output

        Raises
        ------
        FileNotFoundError
            if input path does not exist
        """
        if not self.is_file():
            raise FileNotFoundError("File doe not exist")
        return self.c.os.lstat(self._2str)

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
        NotImplementedError
            when non-relative pattern is passed in

        Warnings
        --------
        This method follows symlinks by default
        """
        if not self.is_dir():
            raise FileNotFoundError(f"Directory {self} does not exist.")
        if pattern.startswith("/"):
            raise NotImplementedError("Non-relative patterns are unsupported")

        # first count shell pattern symbols if more than two are present,
        # search must be recursive
        pattern_count = sum([
            pattern.count("*"),
            pattern.count("?"),
            min((pattern.count("["), pattern.count("]")))
        ])

        log.debug(f"pattern {pattern}")
        if pattern_count >= 2:
            recursive = True
        else:
            recursive = False

        log.debug(f"recursive: {recursive}")

        # split pattern to parts, so we can easily match at each subdir level
        parts: Deque[str] = deque(SSHPath(self.c, pattern).parts)
        log.debug(f"parts: {parts}")

        # append to origin path parts of pattern that do not contain any
        # wildcards, so we search as minimal number of sub-directories as
        # possible
        while True:
            p = parts.popleft()
            if "*" in p or "?" in p or ("[" in p and "]" in p):
                parts.appendleft(p)
                break
            else:
                self /= p

        # precompute number of origin path parts and pattern parts for speed
        origin_parts = len(self.parts)
        pattern_parts = len(parts) - 1
        for root, dirs, files in self.c.os.walk(self, followlinks=True):

            # compute number of actual root path parts
            root_parts = len(SSHPath(self.c, root).parts)
            # the difference determines which path of pattern to use, this is
            # because walk traverses directories "depth-first"
            idx = root_parts - origin_parts

            log.debug(f"root parts: {root_parts}, idx {idx}")

            # if we do not have the last part we are interested only in
            # directories because we need to get deeper in to the directory
            # structure
            if idx < pattern_parts:
                pattern = parts[idx]

                log.debug(f"actual level pattern: {pattern}")

                # now get directories that match the pattern and delete the
                # others, this takes advantage of list mutability - the next
                # seach paths will be built by walk based on already filtered
                # directories list
                indices = []
                for i, d in enumerate(dirs):
                    if not fnmatch(d, pattern):
                        indices.append(i)

                for index in sorted(indices, reverse=True):
                    del dirs[index]

                log.debug(f"actual dirs: {dirs}")

            elif idx >= pattern_parts:
                log.debug("now yielding the lasp path part")
                pattern = parts[-1]
                log.debug(f"end pattern {pattern}")
                r = SSHPath(self.c, root)
                for path in dirs + files:
                    log.debug(f"path {path}")
                    if fnmatch(path, pattern):
                        yield r / path

            if not recursive:
                break

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

    def is_dir(self) -> bool:
        """Check if path points to directory.

        Returns
        -------
        bool
            True if pointing to a directory
        """
        return self.c.os.isdir(self)

    def is_file(self) -> bool:
        """Check if path points to file.

        Returns
        -------
        bool
            True if pointing to a file
        """
        return self.c.os.isfile(self)

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
            for p in self.c.os.listdir(self):
                yield self / p

    def mkdir(self, mode: int = 511, parents: bool = False,
              exist_ok: bool = False):
        """Recursively create directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: "_SPATH"
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
        self.c.os.makedirs(self, mode=mode, exist_ok=exist_ok, parents=parents)

    def open(self, mode: str = "r", buffering: int = -1,  # type: ignore
             encoding: Optional[str] = "utf-8") -> "SFTPFile":
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
        self.c.builtins.open(self, mode=mode, bufsize=buffering,
                             encoding=encoding)

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
        with self.c.builtins.open(self, "rb") as f:
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
        with self.c.builtins.open(self, "r", encoding=encoding,
                                  errors=errors) as f:
            return f.read()

    def rename(self, target: "_SPATH") -> "SSHPath":  # type: ignore[override]
        """Rename directory or file.

        Parameters
        ----------
        target: _SPATH
            path name afer renaming

        Warnings
        --------
        Works only in posix
        """
        if self.c.os.name == "nt":
            raise NotImplementedError("Does not work on windows servers")

        self.c.sftp.posix_rename(self._2str, fspath(target))
        return self.replace(target)

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

    def resolve(self) -> "SSHPath":  # type: ignore[override]
        """Make the path absolute.

        Resolve all symlinks on the way and also normalize it.

        Returns
        -------
        "SSHPath"
            [description]
        """
        return SSHPath(self.c, self.c.sftp.normalize(self._2str))

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

        Warnings
        --------
        This method follows symlinks by default
        """
        return self.glob(f"**/{pattern}")

    def rmdir(self):
        """Remove directory, after point path to parent.

        Warnings
        --------
        This is recursive contrary to pathlib.Path implementation
        """
        self.c.rmtree(self)
        self.replace(self.parent)

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

    def write_bytes(self, data: Union[bytes, bytearray, memoryview]):
        """Write bytes to file.

        Parameters
        ----------
        data : Union[bytes, bytearray, memoryview]
            content to write to file
        """
        view = memoryview(data)
        with self.c.builtins.open(self, "wb") as f:
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

        with self.c.builtins.open(self, "w", encoding=encoding,
                                  errors=errors) as f:
            f.write(data)

    # ! NOT IMPLEMENTED
    def link_to(self, target):
        raise NotImplementedError

    def is_mount(self):
        raise NotImplementedError
