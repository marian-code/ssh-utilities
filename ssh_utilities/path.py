"""Implements Path-like object for remote hosts."""

import re
from os import fspath
from os.path import join
from pathlib import Path, _posix_flavour
from typing import TYPE_CHECKING, Generator, Union, Callable, Optional
from functools import wraps
import stat
from paramiko.file import BufferedFile

from .utils import for_all_methods, glob2re

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes
    from paramiko.sftp_file import SFTPFile
    SPath = Union[str, Path, "SSHPath"]
    from .remote import SSHConnection

__all__ = ["SSHPath"]

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

        """
        # If it was not SSHPath instance before don't cast to SSHPath
        # wrapper is not needed, return imediatelly
        if not isinstance(self, SSHPath):
            return function(self, *args, **kwargs)

        # get function name
        name = function.__name__

        # get connection attribute before it is destroyed by running the method
        # methods __new__  and _init must be excluded because the connection
        # is not yet initialized when they are called
        if name not in ("__new__", "_init"):
            connection = self._c

        # run the method and capture output
        output = function(self, *args, **kwargs)

        # if result is path instance, which is wrong, cast to SSHPath
        # we do not care for other return types and leave those unchanged
        if isinstance(output, Path):
            if name not in ("__new__", "_init"):
                return SSHPath(connection, output)
            else:
                return output
        else:
            return output
        """

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
    Not all methods are implemented!

    Cannot connect to servers with different operating systems simultaneously

    Only works with posix servers

    Raises
    ------
    NotImplementedError when on some methods that have not been implemented.
    """

    _flavour = _posix_flavour
    _c: "SSHConnection"

    def __new__(cls, connection: "SSHConnection", *args, **kwargs):
        """Copied from pathlib."""

        # TODO check if server is posix

        self = cls._from_parts(args, init=False)
        self._c = connection
        if not self._flavour.is_supported:
            raise NotImplementedError("cannot instantiate %r on your system"
                                      % (cls.__name__,))
        self._init()
        return self

    @property
    def _2str(self):
        return fspath(self)

    def cwd(self) -> "SSHPath":
        return SSHPath(self._c, self._c.sftp.normalize("."))

    def home(self) -> "SSHPath":
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
        if not self.is_file():
            raise FileNotFoundError("File doe not exist")
        return self._c.sftp.stat(self._2str)

    def chmod(self, mode):
        self._c.sftp.chmod(self._2str, mode)

    def exists(self) -> bool:
        return any((self.is_dir(), self.is_file()))

    def glob(self, pattern: str):

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
        return self._c.isdir(self)

    def is_file(self) -> bool:
        return self._c.isfile(self)

    def is_symlink(self):
        return stat.S_ISLNK(self.stat.st_mode)

    def is_socket(self):
        return stat.S_ISSOCK(self.stat.st_mode)

    def is_fifo(self):
        return stat.S_ISFIFO(self.stat.st_mode)

    def is_block_device(self):
        return stat.S_ISBLK(self.stat.st_mode)

    def is_char_device(self):
        return stat.S_ISCHR(self.stat.st_mode)

    def iterdir(self) -> Generator["SSHPath", None, None]:

        if not self.is_dir():
            raise FileNotFoundError(f"Directory {self} does not exist.")

        if self.is_dir():
            for p in self._c.listdir(self):
                yield self / p

    def mkdir(self, mode: int = 511, parents: bool = False,
              exist_ok: bool = False):
        self._c.mkdir(self, mode=mode, exist_ok=exist_ok, parents=parents)

    def open(self, mode: str = "r", buffering: int = -1,
             encoding: Optional[str] = "utf-8") -> "SFTPFile":
        self._c.open(self, mode=mode, bufsize=buffering, encoding=encoding)

    def read_bytes(self) -> bytes:
        if not self.is_file():
            raise FileNotFoundError("Cannot open file.")
        with self._c.open(self, "rb") as f:
            return f.read()

    def read_text(self):
        if not self.is_file():
            raise FileNotFoundError("Cannot open file.")
        with self._c.open(self, "r") as f:
            return f.read()

    def rename(self, target):
        """Remove directory or file.

        Warnings
        --------
        Works only in posix
        """
        self._c.sftp.posix_rename(self._2str, fspath(target))
        return self.replace(target)

    def replace(self, target):
        self = SSHPath(self._c, target)
        return self

    def resolve(self) -> Path:
        return Path(self._c.sftp.normalize(self._2str))

    def rglob(self, pattern):
        return self.glob(f"**/{pattern}")

    def rmdir(self):
        """Remove directory, after point path to parent.

        Warnings
        --------
        This is recursive contrary to pathlib.Path implementation
        """
        self._c.rmtree(self)
        self.replace(self.parent)

    def symlink_to(self, target):
        self._c.sftp.symlink(self._2str, fspath(target))

    def touch(self, mode=0o666, exist_ok: bool = True):
        """Create empty file.

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
        if not self.exists() and not missing_ok:
            raise FileNotFoundError("Cannot unlink file/dir does not exist")
        elif self.is_dir():
            raise TypeError("Path is a directory use rmdir instead")
        elif self.is_file():
            self._c.sftp.unlink(self._2str)

    def write_bytes(self, data):
        with self._c.open(self, "wb") as f:
            f.write(data.encode())

    def write_text(self, data, encoding="utf-8"):
        with self._c.open(self, "w") as f:
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
