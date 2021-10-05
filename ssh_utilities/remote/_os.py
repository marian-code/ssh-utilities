"""Remote connection os methods."""

import logging
import os
from ntpath import join as njoin
from posixpath import join as pjoin
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Iterator, List, Optional

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

from ..abstract import DirEntryABC, OsABC, OsPathABC
from ..constants import G, R
from ..exceptions import CalledProcessError, UnknownOsError
from ..utils import lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes

    from ..typeshed import _SPATH, _WALK
    from .remote import SSHConnection

__all__ = ["Os"]

log = logging.getLogger(__name__)


# TODO get the follow_symlinks arguments working
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
        self._path = OsPathRemote(connection)

    @property
    def path(self) -> "OsPathRemote":
        return self._path

    def scandir(self, path: "_SPATH") -> "Scandir":
        return Scandir(self.c._path2str(path), self.c)

    @check_connections(exclude_exceptions=(OSError))
    def rename(self, src: "_SPATH", dst: "_SPATH", *,
               src_dir_fd: Optional[int] = None,
               dst_dir_fd: Optional[int] = None):
        if self.name == "nt":
            try:
                self.c.sftp.rename(self.c._path2str(src),
                                   self.c._path2str(dst))
            except IOError as e:
                raise OSError(str(e)) from e
        else:
            try:
                self.c.sftp.posix_rename(self.c._path2str(src),
                                         self.c._path2str(dst))
            except IOError as e:
                raise OSError(str(e)) from e

    @check_connections(exclude_exceptions=(FileExistsError, FileNotFoundError,
                                           OSError))
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):

        path = self.c._path2str(path)

        if self.path.isdir(path) and not exist_ok:
            raise FileExistsError(f"Directory already exists: "
                                  f"{self.c.server_name}@{path}")
        elif self.path.isdir(path) and exist_ok:
            return

        lprint(quiet)(f"{G}Creating directory:{R} "
                      f"{self.c.server_name}@{path}")

        if not parents:
            try:
                self.c.sftp.mkdir(path, mode)
            except Exception as e:
                raise FileNotFoundError(f"Error in creating directory: "
                                        f"{self.c.server_name}@{path}, "
                                        f"probably parent does not exist."
                                        f"\n{e}")

        to_make = []
        actual = path

        while True:
            # TODO this is not platform agnostic!
            actual = os.path.dirname(actual)
            if not self.path.isdir(actual):
                to_make.append(actual)
            else:
                break

        for tm in reversed(to_make):
            try:
                self.c.sftp.mkdir(tm, mode)
            except OSError as e:
                raise OSError(f"Couldn't make dir {tm},\n probably "
                              f"permission error: {e}")

        try:
            self.c.sftp.mkdir(path, mode)
        except OSError as e:
            raise OSError(f"Couldn't make dir {path}, probably permission "
                          f"error: {e}\nAlso check path formating")

    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        self.makedirs(path, mode, exist_ok=False, parents=False, quiet=quiet)

    @check_connections(exclude_exceptions=FileNotFoundError)
    def listdir(self, path: "_SPATH") -> List[str]:
        try:
            return self.c.sftp.listdir(self.c._path2str(path))
        except IOError as e:
            raise FileNotFoundError(f"Directory does not exist: {e}")

    @check_connections()
    def chdir(self, path: "_SPATH"):
        self.c.sftp.chdir(self.c._path2str(path))

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

    @check_connections(exclude_exceptions=FileNotFoundError)
    def stat(self, path: "_SPATH", *, dir_fd: Optional[int] = None,
             follow_symlinks: bool = True) -> "SFTPAttributes":

        try:
            spath = self.c._path2str(path)
            stat = self.c.sftp.stat(spath)

            # TODO do we need this? can links be chained?
            while True:
                if follow_symlinks and S_ISLNK(stat.st_mode):
                    spath = self.c.sftp.readlink(spath)
                    stat = self.c.sftp.stat(spath)
                else:
                    break
        except FileNotFoundError as e:
            raise FileNotFoundError(f"exception in stat: {e}, {path}")
        return stat

    def lstat(self, path: "_SPATH", *, dir_fd=None) -> "SFTPAttributes":
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
                    mode = self.c.os.stat(self.path.join(remote_path,
                                                         f.filename)).st_mode
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


# alternative to os.path module
class OsPathRemote(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    @check_connections(exclude_exceptions=IOError)
    def isfile(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISREG(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections(exclude_exceptions=IOError)
    def isdir(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISDIR(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections(exclude_exceptions=IOError)
    def islink(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.c.os.stat.__wrapped__
        try:
            return S_ISLNK(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    def realpath(self, path: "_SPATH") -> str:

        spath = self.c._path2str(path)
        stat = self.c.sftp.stat(spath)

        # TODO do we need this? can links be chained?
        while True:
            if S_ISLNK(stat.st_mode):
                spath = self.c.sftp.readlink(spath)
                stat = self.c.sftp.stat(spath)
            else:
                break

        return spath

    def getsize(self, path: "_SPATH") -> int:

        size = self.c.os.stat(path).st_size

        if size:
            return size
        else:
            raise OSError(f"Could not get size of file: {path}")

    def join(self, path: "_SPATH", *paths: "_SPATH") -> str:

        if self.c.os.name == "nt":
            return njoin(self.c._path2str(path),
                         *[self.c._path2str(p) for p in paths])
        else:
            return pjoin(self.c._path2str(path),
                         *[self.c._path2str(p) for p in paths])


class Scandir:
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
