"""Remote connection os methods."""

import errno
import logging
import os
from functools import wraps
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Iterator, List, Optional

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from ..abstract import DirEntryABC, OsABC
from ..constants import G, R
from ..exceptions import CalledProcessError, UnknownOsError
from ..utils import lprint
from ._connection_wrapper import check_connections
from ._os_path import OsPath

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes

    from ..typeshed import _SPATH, _WALK
    from .remote import SSHConnection

__all__ = ["Os"]

log = logging.getLogger(__name__)


def fd_error(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        for keyword, value in kwargs.items():
            if "dir_fd" in keyword and value is not None:
                raise NotImplementedError(
                    "dir_fd is not supported through ssh"
                )
        return func(self, *args, **kwargs)
    return wrapper



class DirEntryRemote(DirEntryABC):

    name: str
    path: str

    def __init__(self, connection: "SSHConnection", path: str,
                 attr_entry: "SFTPAttributes") -> None:
        self.c = connection
        self.name = attr_entry.filename
        self._attr_entry = attr_entry
        self.path = self.c.os.path.join(path, attr_entry.filename)

    def inode(self) -> int:
        return self._attr_entry.st_ino  # type: ignore

    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        if follow_symlinks:
            return S_ISDIR(
                self.c.os.stat(self.path, follow_symlinks=True).st_mode
            )
        else:
            return S_ISDIR(self._attr_entry.st_mode)

    def is_file(self, *, follow_symlinks: bool = False) -> bool:
        if follow_symlinks:
            return S_ISREG(
                self.c.os.stat(self.path, follow_symlinks=True).st_mode
            )
        else:
            return S_ISREG(self._attr_entry.st_mode)

    def is_symlink(self) -> bool:
        return S_ISLNK(self._attr_entry.st_mode)

    def stat(self, *, follow_symlinks: bool = False) -> "SFTPAttributes":
        if follow_symlinks:
            return self.c.os.stat(self.path, follow_symlinks=True)
        else:
            return self._attr_entry


class Os(OsABC):
    """Class gathering all remote methods similar to python os module.

    See also
    --------
    :class:`ssh_utilities.local.Os`
        local version of class with same API
    """

    _osname: Literal["nt", "posix"]

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection
        self._path = OsPath(connection)

    @property
    def path(self) -> OsPath:
        return self._path

    @check_connections
    def scandir(self, path: "_SPATH") -> Iterator[DirEntryRemote]:
        return ScandirIterator(self.c._path2str(path), self.c)

    @fd_error
    @check_connections(exclude_exceptions=FileNotFoundError)
    def chmod(self, path: "_SPATH", mode: int, *, dir_fd: Optional[int] = None,
              follow_symlinks: bool = True):
        path = self.c._path2str(path)

        if not self.path.exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )

        if follow_symlinks:
            path = self.c.sftp.normalize(path)

        self.c.sftp.chmod(path, mode)

    def lchmod(self, path: "_SPATH", mode: int):
        self.chmod(path, mode, follow_symlinks=False)

    @fd_error
    @check_connections
    def symlink(self, src: "_SPATH", dst: "_SPATH",
                target_is_directory: bool = False, *,
                dir_fd: Optional[int] = None):
        self.c.sftp.symlink(self.c._path2str(src), self.c._path2str(dst))

    @fd_error
    @check_connections(exclude_exceptions=(FileNotFoundError, IOError,
                                           IsADirectoryError))
    def remove(self, path: "_SPATH", *, dir_fd: int = None):
        path = self.c._path2str(path)

        if not self.path.exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )
        elif self.path.isdir(path):
            raise IsADirectoryError(
                errno.EISDIR, os.strerror(errno.EISDIR), path
            )
        else:
            self.c.sftp.unlink()

    unlink = remove

    @fd_error
    @check_connections(exclude_exceptions=OSError)
    def rmdir(self, path: "_SPATH", *, dir_fd: int = None):
        path = self.c._path2str(path)

        if not self.path.exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )
        elif any(self.scandir(path)):
            raise OSError(
                errno.ENOTEMPTY, os.strerror(errno.ENOTEMPTY), path
            )
        else:
            self.c.sftp.rmdir(path)

    @fd_error
    @check_connections(exclude_exceptions=(OSError, FileExistsError,
                                           NotADirectoryError, IOError))
    def rename(self, src: "_SPATH", dst: "_SPATH", *,
               src_dir_fd: Optional[int] = None,
               dst_dir_fd: Optional[int] = None):
        src = self.c._path2str(src)
        dst = self.c._path2str(dst)

        if self.name == "nt":
            if self.path.exists(dst):
                raise FileExistsError(
                    errno.EEXIST, os.strerror(errno.EEXIST), dst
                )
            self.c.sftp.rename(src, dst)
        else:
            if self.path.isfile(src) and self.path.isdir(dst):
                raise IsADirectoryError(
                    errno.EISDIR, os.strerror(errno.ENOENT), dst
                )
            elif self.path.isdir(src) and self.path.isfile(dst):
                raise NotADirectoryError(
                    errno.ENOTDIR, os.strerror(errno.ENOTDIR), dst
                )

            self.c.sftp.posix_rename(src, dst)

    @fd_error
    @check_connections(exclude_exceptions=IsADirectoryError)
    def replace(self, src: "_SPATH", dst: "_SPATH", *,
                src_dir_fd: Optional[int] = None,
                dst_dir_fd: Optional[int] = None):

        if self.path.isdir(dst):
            raise IsADirectoryError(
                errno.EISDIR, os.strerror(errno.ENOENT), dst
            )
        elif self.path.isfile(dst):
            self.remove(dst)

        self.rename(src, dst)

    @check_connections(exclude_exceptions=(FileExistsError, OSError))
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 quiet: bool = True):

        path = self.c._path2str(path)

        if self.path.isdir(path) and not exist_ok:
            raise FileExistsError(
                errno.EEXIST, os.strerror(errno.EEXIST), path
            )
        elif self.path.isdir(path) and exist_ok:
            return

        lprint(quiet)(f"{G}Creating directory:{R} "
                      f"{self.c.server_name}@{path}")

        to_make = []
        actual = path

        while True:
            # TODO this is not platform agnostic!
            if not self.path.isdir(actual):
                to_make.append(actual)
                actual = os.path.dirname(actual)
            else:
                break

        for tm in reversed(to_make):
            self.mkdir(tm, mode)

    @check_connections(exclude_exceptions=(FileExistsError, OSError))
    def mkdir(self, path: "_SPATH", mode: int = 511):

        try:
            self.c.sftp.mkdir(path, mode)
        except OSError as e:
            if self.path.isdir(path):
                raise FileExistsError(
                    errno.EEXIST, os.strerror(errno.EEXIST), path
                )
            else:
                raise OSError(f"Couldn't make dir {path}, probably permission "
                              f"error: {e}") from e

    @check_connections(exclude_exceptions=(NotADirectoryError,
                                           FileNotFoundError))
    def listdir(self, path: "_SPATH") -> List[str]:
        path = self.c._path2str(path)
        if not self.path.exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )
        elif not self.path.isdir(path):
            raise NotADirectoryError(
                errno.ENOTDIR, os.strerror(errno.ENOTDIR)
            )

        return self.c.sftp.listdir(self.c._path2str(path))

    @check_connections(exclude_exceptions=(FileNotFoundError, IOError,
                                           NotADirectoryError))
    def chdir(self, path: "_SPATH"):
        path = self.c._path2str(path)

        if not self.path.exists(path):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), path
            )
        elif not self.path.isdir(path):
            raise NotADirectoryError(
                errno.ENOTDIR, os.strerror(errno.ENOTDIR), path
            )

        self.c.sftp.chdir(path)

    @property
    def name(self) -> Literal["nt", "posix"]:

        try:
            self._osname
        except AttributeError:
            pass
        else:
            return self._osname

        error_count = 0

        # Try some common cmd strings
        for cmd in ('ver', 'command /c ver', 'cmd /c ver'):
            try:
                info = self.c.subprocess.run(
                    [cmd], suppress_out=True, quiet=True,
                    check=True, capture_output=True, encoding="utf-8",
                ).stdout
            except CalledProcessError as e:
                log.debug(f"Couldn't get os name: {e}")
                error_count += 1
            else:
                if "windows" in info.lower():
                    self._osname = "nt"
                    break
                else:
                    continue
        else:
            # no errors were thrown, but os name could not be identified from
            # the response strings
            if error_count == 0:
                raise UnknownOsError("Couldn't get os name")
            else:
                self._osname = "posix"

        return self._osname

    @fd_error
    @check_connections(exclude_exceptions=FileNotFoundError)
    def stat(self, path: "_SPATH", *, dir_fd: Optional[int] = None,
             follow_symlinks: bool = True) -> "SFTPAttributes":

        path = self.c._path2str(path)

        if follow_symlinks:
            stat = self.c.sftp.stat(self.c.sftp.normalize(path))
        else:
            stat = self.c.sftp.stat(path)

        return stat

    @fd_error
    def lstat(self, path: "_SPATH", *, dir_fd: Optional[int] = None,
              ) -> "SFTPAttributes":
        return self.stat(path, dir_fd=dir_fd, follow_symlinks=False)

    @check_connections()
    def walk(self, top: "_SPATH", topdown: bool = True,
             onerror=None, followlinks: bool = False) -> "_WALK":

        remote_path = self.c._path2str(top)
        files = []
        folders = []
        for f in self.c.sftp.listdir_attr(remote_path):
            try:
                # get file mode
                mode = f.st_mode
                if mode is None:
                    raise ValueError("Got None value for object mode")

                # check if flie is link and get mode of the real target
                if S_ISLNK(mode) and followlinks:
                    mode = self.c.os.stat(
                        self.path.join(remote_path, f.filename),
                        follow_symlinks=True
                    ).st_mode
                if mode is None:
                    raise ValueError("Got None value for object mode")

                # sort dirs and files
                if S_ISDIR(mode):
                    folders.append(f.filename)
                else:
                    files.append(f.filename)
            except OSError as e:
                if onerror is not None:
                    onerror(e)

        # TODO join might be wrong for some host systems
        if topdown:
            yield remote_path, folders, files
            sub_folders = [self.path.join(remote_path, f) for f in folders]
        else:
            sub_folders = [self.path.join(remote_path, f) for f in folders]
            yield remote_path, folders, files

        for sub_folder in sub_folders:
            for x in self.walk(sub_folder, topdown, onerror, followlinks):
                yield x

    @staticmethod
    def supports_fd():
        raise NotImplementedError

    @staticmethod
    def supports_dir_fd():
        raise NotImplementedError


class ScandirIterator(Iterator[DirEntryRemote]):
    """Reads directory contents and yields as DirEntry objects.

    These objects have subset of methods similar to `Path` object.
    """

    _iter_files: Iterator["SFTPAttributes"]

    def __init__(self, path: str, connection: "SSHConnection") -> None:
        self.c = connection
        self._path = path
        self._iter_files = self.c.sftp.listdir_iter(path)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        return DirEntryRemote(self.c, self._path, next(self._iter_files))

    def close(self):
        try:
            del self.c
            del self._path
            del self._files
        except Exception:
            pass
