"""Remote connection os methods."""

import logging
import os
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, List

from typing_extensions import Literal

from ..abc import OsABC, OsPathABC
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

    @check_connections(exclude_exceptions=IOError)
    def isfile(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.stat.__wrapped__
        try:
            return S_ISREG(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections(exclude_exceptions=IOError)
    def isdir(self, path: "_SPATH") -> bool:
        # have to call without decorators, otherwise FileNotFoundError
        # does not propagate
        unwrap = self.stat.__wrapped__
        try:
            return S_ISDIR(unwrap(self, self.c._path2str(path)).st_mode)
        except FileNotFoundError:
            return False

    @check_connections(exclude_exceptions=(FileExistsError, FileNotFoundError,
                                           OSError))
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):

        path = self.c._path2str(path)

        if self.isdir(path) and not exist_ok:
            raise FileExistsError(f"Directory already exists: "
                                  f"{self.c.server_name}@{path}")
        elif self.isdir(path) and exist_ok:
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
            if not self.isdir(actual):
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

    change_dir = chdir

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

    osname = name

    @check_connections()
    def stat(self, path: "_SPATH", *, dir_fd=None,
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
                mode = f.st_mode
                if S_ISLNK(mode) and followlinks:
                    mode = self.c.os.stat(os.path.join(remote_path,
                                                       f.filename)).st_mode

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
            sub_folders = [os.path.join(remote_path, f) for f in folders]
        else:
            sub_folders = [os.path.join(remote_path, f) for f in folders]
            yield remote_path, folders, files

        for sub_folder in sub_folders:
            for x in self.walk(sub_folder, topdown, onerror, followlinks):
                yield x


# alternative to os.path module
class OsPathRemote(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

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
