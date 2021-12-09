"""Template module for all shutil classes."""
import logging
from abc import ABC, abstractmethod
from typing import (IO, TYPE_CHECKING, Any, Callable, FrozenSet, List,
                    Optional, Sequence, Set, Union, overload)

try:
    from typing import Literal  # type: ignore - python >= 3.8
except ImportError:
    from typing_extensions import Literal  # python < 3.8

if TYPE_CHECKING:
    from paramiko.sftp_file import SFTPFile

    from ..typeshed import _CALLBACK, _DIRECTION, _GLOBPAT, _SPATH

__all__ = ["ShutilABC"]

logging.getLogger(__name__)


class ShutilABC(ABC):
    """`shutil` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def ignore_patterns(self, *paterns: Sequence[str]
                        ) -> Callable[[Any, Sequence[str]], Set[str]]:
        """Creates a callable for shutil.copytree function to ignore files.

        Parameters
        ----------
        *patterns: Sequence[str]
            a list of glob patterns that will ne used to exclude files

        Returns
        -------
        Callable[[Any, Sequence[str]], Set[str]]
            Callable the filters files, when called with a list of strings
            returns a subset that matches one oth the exclude patterns
        """
        raise NotImplementedError

    @overload
    @abstractmethod
    def copyfileobj(self, fsrc: "SFTPFile", fdst: IO, *,
                    direction: Literal["get"], length: Optional[int] = None):
        ...
    @overload
    @abstractmethod
    def copyfileobj(self, fsrc: IO, fdst: "SFTPFile", *,
                    direction: Literal["put"], length: Optional[int] = None):
        ...
    @abstractmethod
    def copyfileobj(self, fsrc: Union[IO, "SFTPFile"],
                    fdst: Union[IO, "SFTPFile"], *, direction: "_DIRECTION",
                    length: Optional[int] = None):
        """Copy the contents of one file-like object to another.

        Parameters
        ----------
        fsrc : Union[IO, SFTPFile]
            source file-like object must be local/remote based on direction parameter
        fdst : Union[IO, SFTPFile]
            source file-like object must be local/remote based on direction parameter
        direction : _DIRECTION
            either 'put' or 'get'
        length : int, optional
            [description], by default -1
        """
        raise NotImplementedError

    @abstractmethod
    def copyfile(self, src: "_SPATH", dst: "_SPATH", *,
                 direction: "_DIRECTION", follow_symlinks: bool = True,
                 callback: "_CALLBACK" = None, quiet: bool = True):
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        src: :const:`ssh_utilities.typeshed._SPATH`
            path to the file
        dst: :const:`ssh_utilities.typeshed._SPATH`
            path to copy into
        direction: :const:`ssh_utilities.typeshed._DIRECTION`
            'get' for download and 'put' for upload
        follow_symlinks: bool
            resolve symlinks when looking for file, by default True
        callback: :const:`ssh_utilities.typeshed._CALLBACK`
            callback function that recives two arguments: amount done and total
            amount to be copied
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        FileNotFoundError
            if `src` is not file
        IsADirectoryError
            if dst is a targer directory not full path
        ValueError
            if direction is not `put` or `get`
        """
        raise NotImplementedError

    @abstractmethod
    def copy(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
             follow_symlinks: bool = True, callback: "_CALLBACK" = None,
             quiet: bool = True):
        """Send files in the chosen direction local <-> remote.

        Parameters
        ----------
        src: :const:`ssh_utilities.typeshed._SPATH`
            path to the file
        dst: :const:`ssh_utilities.typeshed._SPATH`
            path to copy into
        direction: :const:`ssh_utilities.typeshed._DIRECTION`
            'get' for download and 'put' for upload
        follow_symlinks: bool
            resolve symlinks when looking for file, by default True
        callback: :const:`ssh_utilities.typeshed._CALLBACK`
            callback function that recives two arguments: amount done and total
            amount to be copied
        quiet: bool
            if True informative messages are suppresssed

        Warnings
        --------
        Unlike shutil this function cannot preserve file permissions (`copy`)
        or file metadata (`copy2`)

        Raises
        ------
        FileNotFoundError
            if `src` is not file
        ValueError
            if direction is not `put` or `get`
        """
        raise NotImplementedError

    @abstractmethod
    def copy2(self, src: "_SPATH", dst: "_SPATH", *, direction: "_DIRECTION",
              follow_symlinks: bool = True, callback: "_CALLBACK" = None,
              quiet: bool = True):
        raise NotImplementedError

    @abstractmethod
    def download_tree(self, remote_path: "_SPATH", local_path: "_SPATH",
                      include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                      remove_after: bool = True, quiet: bool = False):
        """Download directory tree from remote.

        Remote directory must exist otherwise exception is raised.

        Parameters
        ----------
        remote_path: :const:`ssh_utilities.typeshed._SPATH`
            path to directory which should be downloaded
        local_path: :const:`ssh_utilities.typeshed._SPATH`
            directory to copy to, must be full path!
        remove_after: bool
            remove remote copy after directory is uploaded
        include: :const:`ssh_utilities.typeshed._GLOBPAT`
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: :const:`ssh_utilities.typeshed._GLOBPAT`
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet:  Literal[True, False, "stats", "progress"]
            if `True` informative messages are suppresssed if `False` all is
            printed, if `stats` all statistics except progressbar are
            suppressed if `progress` only progressbar is suppressed

        Warnings
        --------
        both paths must be full: <some_remote_path>/my_directory ->
        <some_local_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when remote directory does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def upload_tree(self, local_path: "_SPATH", remote_path: "_SPATH",
                    include: "_GLOBPAT" = None, exclude: "_GLOBPAT" = None,
                    remove_after: bool = True, quiet: bool = False):
        """Upload directory tree to remote.

        Local path must exist otherwise, exception is raised.

        Parameters
        ----------
        local_path: :const:`ssh_utilities.typeshed._SPATH`
            path to directory which should be uploaded
        remote_path: :const:`ssh_utilities.typeshed._SPATH`
            directory to copy to, must be full path!
        remove_after: bool
            remove local copy after directory is uploaded
        include: :const:`ssh_utilities.typeshed._GLOBPAT`
            glob pattern of files to include in copy, can be used
            simultaneously with exclude, default is None = no filtering
        exclude: :const:`ssh_utilities.typeshed._GLOBPAT`
            glob pattern of files to exclude in copy, can be used
            simultaneously with include, default is None = no filtering
        quiet:  Literal[True, False, "stats", "progress"]
            if `True` informative messages are suppresssed if `False` all is
            printed, if `stats` all statistics except progressbar are
            suppressed if `progress` only progressbar is suppressed

        Warnings
        --------
        both paths must be full: <some_local_path>/my_directory ->
        <some_remote_path>/my_directory

        Raises
        ------
        FileNotFoundError
            when local directory does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def rmtree(self, path: "_SPATH", ignore_errors: bool = False,
               quiet: bool = True):
        """Recursively remove directory tree.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            directory to be recursively removed
        ignore_errors: bool
            if True only log warnings do not raise exception
        quiet: bool
            if True informative messages are suppresssed

        Raises
        ------
        FileNotFoundError
            if some part of deleting filed
        """
        raise NotImplementedError
