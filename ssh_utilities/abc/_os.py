"""Template module for all os classes."""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, FrozenSet, TypeVar

if TYPE_CHECKING:
    from ..typeshed import _SPATH, _ONERROR

__all__ = ["OsPathABC", "OsABC"]

logging.getLogger(__name__)

# Python does not yet support higher order generics so this is devised to
# circumvent the problem, we must always define Generic with all possible
# return types
# problem discussion: https://github.com/python/typing/issues/548
# potentially use returns in the future github.com/dry-python/returns
_Os1 = TypeVar("_Os1")  # bool
_Os2 = TypeVar("_Os2")  # List[str]
_Os3 = TypeVar("_Os3")  # "_ATTRIBUTES"
_Os4 = TypeVar("_Os4")  # Literal["nt", "posix", "java"]
_Os5 = TypeVar("_Os5")  # OsPathABC
_Os6 = TypeVar("_Os6")  # "_WALK"


class OsPathABC(ABC):
    """`os.path` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    def realpath(self, path: "_SPATH") -> str:
        """Return the canonical path of the specified filename.

        Eliminates any symbolic links encountered in the path.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path to resolve

        Returns
        -------
        str
            string representation of the resolved path
        """
        raise NotImplementedError


class OsABC(ABC, Generic[_Os1, _Os2, _Os3, _Os4, _Os5, _Os6]):
    """`os` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def isfile(self, path: "_SPATH") -> _Os1:
        """Check if path points to a file.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Raises
        ------
        IOError
            if file could not be accessed
        """
        raise NotImplementedError

    @abstractmethod
    def isdir(self, path: "_SPATH") -> _Os1:
        """Check if path points to directory.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Raises
        ------
        IOError
            if dir could not be accessed
        """
        raise NotImplementedError

    @abstractmethod
    def makedirs(self, path: "_SPATH", mode: int = 511, exist_ok: bool = True,
                 parents: bool = True, quiet: bool = True):
        """Recursively create directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
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
        raise NotImplementedError

    @abstractmethod
    def mkdir(self, path: "_SPATH", mode: int = 511, quiet: bool = True):
        """Create single directory.

        If it already exists, show warning and return.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to directory which should be created
        mode: int
            create directory with mode, default is 511
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
        raise NotImplementedError

    @abstractmethod
    def listdir(self, path: "_SPATH") -> _Os2:
        """Lists contents of specified directory.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
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
        raise NotImplementedError

    @abstractmethod
    def chdir(self, path: "_SPATH"):
        raise NotImplementedError

    @abstractmethod
    def stat(self, path: "_SPATH", *, dir_fd=None,
             follow_symlinks: bool = True) -> _Os3:
        """Replacement for os.stat function.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
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
        raise NotImplementedError

    @abstractmethod
    def lstat(self, path: "_SPATH", *, dir_fd=None) -> _Os3:
        """Similar to stat only this does not resolve symlinks.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to file whose stats are desired
        dir_fd: Any
            not implemented in remote version

        Returns
        -------
        SFTPAttributes
            stat object similar to one returned by `os.lstat`

        Warnings
        --------
        `dir_fd` parameter has no effect, it is present only so the signature
        is compatible with `os.lstat`
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> _Os4:
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
        raise NotImplementedError

    osname = name

    @property  # type: ignore
    @abstractmethod
    def path(self) -> _Os5:
        raise NotImplementedError

    @path.setter  # type: ignore
    @abstractmethod
    def path(self, path: _Os5):
        raise NotImplementedError

    def walk(self, top: "_SPATH", topdown: bool = True,
             onerror: "_ONERROR" = None, followlinks: bool = False) -> _Os6:
        """Recursive directory listing.

        Parameters
        ----------
        top : :const:`ssh_utilities.typeshed._SPATH`
            directory to start from
        topdown : bool, optional
            if true or not specified, the triple for a directory is generated
            before the triples for any of its subdirectories (directories are
            generated top-down). This enables you to modify the subdirectories
            list in place befor iteration continues. If topdown is False, the
            triple for a directory is generated after the triples for all of
            its subdirectories, by default True
        onerror : :const:`ssh_utilities.typeshed._ONERROR`, optional
            Callable acception one argument of type exception which decides
            how to handle that exception, by default None
        followlinks : bool, optional
            follow symbolic links if true, by default False

        Returns
        -------
        :const:`ssh_utilities.typeshed._WALK`
            iterator of 3 tuples containing current dir, subdirs and files
        """
        raise NotImplementedError
