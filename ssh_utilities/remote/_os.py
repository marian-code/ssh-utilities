"""Remote connection os methods."""

import logging
import os
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, List

from typing_extensions import Literal

from ..base import OsPathABC, OsABC
from ..constants import G, R
from ..exceptions import CalledProcessError, UnknownOsError
from ..utils import lprint
from ._connection_wrapper import check_connections

if TYPE_CHECKING:
    from paramiko.sftp_attr import SFTPAttributes

    from ..typeshed import _SPATH
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
        self._path = OsPathRemote(connection)  # type: ignore

    @property
    def path(self) -> "OsPathRemote":
        return self._path

    @check_connections()
    def isfile(self, path: "_SPATH") -> bool:
        """Check if path points to a file.

        Parameters
        ----------
        path: "_SPATH"
            path to check

        Raises
        ------
        IOError
            if file could not be accessed
        """
        try:
            return S_ISREG(self.c.sftp.stat(self.c._path2str(path)).st_mode)
        except IOError:
            return False

    @check_connections()
    def isdir(self, path: "_SPATH") -> bool:
        """Check if path points to directory.

        Parameters
        ----------
        path: "_SPATH"
            path to check

        Raises
        ------
        IOError
            if dir could not be accessed
        """
        _path = self.c._path2str(path)
        try:
            s = self.c.sftp.stat(_path)

            if S_ISLNK(s.st_mode):
                s = self.c.sftp.stat(self.c.sftp.readlink(_path))

            return S_ISDIR(s.st_mode)
        except IOError:
            return False

    @check_connections(exclude_exceptions=(FileExistsError, FileNotFoundError,
                                           OSError))
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
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
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        OSError
            if directory could not be created
        FileNotFoundError
            when parent directory is missing and parents=False
        FileExistsError
            when directory already exists and exist_ok=False
        """
        path = self.c._path2str(path)

        if not self.isdir(path):
            lprint(quiet)(f"{G}Creating directory:{R} "
                          f"{self.c.server_name}@{path}")

            if not parents:
                try:
                    self.c.sftp.mkdir(path, mode)
                except Exception as e:
                    raise FileNotFoundError(f"Error in creating directory: "
                                            f"{self.c.server_name}@{path}, "
                                            f"probably parent does not exist.")

            to_make = []
            actual = path

            while True:
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
                raise OSError(f"Couldn't make dir {path}, probably "
                              f"permission error: {e}\n"
                              f"Also check path formating")
        elif not exist_ok:
            raise FileExistsError(f"Directory already exists: "
                                  f"{self.c.server_name}@{path}")

    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        self.makedirs(path, mode, exist_ok=False, parents=False, quiet=quiet)

    @check_connections(exclude_exceptions=FileNotFoundError)
    def listdir(self, path: "_SPATH") -> List[str]:
        """Lists contents of specified directory.

        Parameters
        ----------
        path: "_SPATH"
            directory path

        Returns
        -------
        List[str]
            list  of files, dirs, symlinks ...

        Raises
        ------
        FileNotFoundError
            if directory does not exist
        """
        try:
            return self.c.sftp.listdir(self.c._path2str(path))
        except IOError as e:
            raise FileNotFoundError(f"Directory does not exist: {e}")

    @check_connections()
    def chdir(self, path: "_SPATH"):
        """Change sftp working directory.

        Parameters
        ----------
        path: "_SPATH"
            new directory path
        """
        self.c.sftp.chdir(self.c._path2str(path))

    change_dir = chdir

    @property
    def name(self) -> Literal["nt", "posix"]:
        """Try to get remote os name same as `os.name` function.

        Warnings
        --------
        Due to the complexity of the check, this method only checks is remote
        server is windows by trying to run `ver` command. If that fails the
        remote is automatically assumed to be POSIX which should hold true
        in most cases.
        If absolute certianty is required you should do your own checks.

        Note
        ----
        This methods main purpose is to help choose the right flavour when
        instantiating `ssh_utilities.path.SSHPath`. For its use the provided
        accuracy should be sufficient.

        Returns
        -------
        Literal["nt", "posix"]
            remote server os name

        Raises
        ------
        UnknownOsError
            if remote server os name could not be determined
        """
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
        """Replacement for os.stat function.

        Parameters
        ----------
        path: _SPATH
            path to file whose stats are desired
        dir_fd: Any
            not implemented
        follow_symlinks: bool
            whether to resolve symbolic links along the way

        Returns
        -------
        SFTPAttributes
            stat object similar to one returned by `os.stat`

        Warnings
        --------
        `dir_fd` parameter has no effect, it is present only so the signature
        is compatible with `os.stat`
        """
        spath = self.c._path2str(path)
        stat = self.c.sftp.stat(spath)

        # TODO do we need this? can links be chained?
        while True:
            if follow_symlinks and S_ISLNK(stat.st_mode):
                spath = self.c.sftp.readlink(spath)
                stat = self.c.sftp.stat(spath)
            else:
                break

        return stat

    def lstat(self, path: "_SPATH", *, dir_fd=None) -> "SFTPAttributes":
        """Similar to stat only this does not resolve symlinks.

        Parameters
        ----------
        path: _SPATH
            path to file whose stats are desired
        dir_fd: Any
            not implemented

        Returns
        -------
        SFTPAttributes
            stat object similar to one returned by `os.lstat`

        Warnings
        --------
        `dir_fd` parameter has no effect, it is present only so the signature
        is compatible with `os.lstat`
        """
        return self.stat(path, dir_fd=dir_fd, follow_symlinks=False)


# alternative to os.path module
class OsPathRemote(OsPathABC):
    """Drop in replacement for `os.path` module."""

    def __init__(self, connection: "SSHConnection") -> None:
        self.c = connection

    def realpath(self, path: "_SPATH") -> str:
        """Return the canonical path of the specified filename.

        Eliminates any symbolic links encountered in the path.

        Parameters
        ----------
        path : _SPATH
            path to resolve

        Returns
        -------
        str
            string representation of the resolved path
        """
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
