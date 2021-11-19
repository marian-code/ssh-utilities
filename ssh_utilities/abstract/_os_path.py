"""Template module for all os.path classes and methods."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, FrozenSet

if TYPE_CHECKING:
    from ..typeshed import _SPATH

__all__ = ["OsPathABC"]

logging.getLogger(__name__)


class OsPathABC(ABC):
    """`os.path` module drop-in replacement base."""

    __name__: str
    __abstractmethods__: FrozenSet[str]

    @abstractmethod
    def isfile(self, path: "_SPATH") -> bool:
        """Check if path points to a file.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Returns
        -------
        bool
            check result

        Raises
        ------
        IOError
            if file could not be accessed
        """
        raise NotImplementedError

    @abstractmethod
    def isdir(self, path: "_SPATH") -> bool:
        """Check if path points to directory.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Returns
        -------
        bool
            check result

        Raises
        ------
        IOError
            if dir could not be accessed
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, path: "_SPATH") -> bool:
        """Check if path exists in filesystem.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Returns
        -------
        bool
            check result
        """
        raise NotImplementedError

    @abstractmethod
    def islink(self, path: "_SPATH") -> bool:
        """Check if path points to symbolic link.

        Parameters
        ----------
        path: :const:`ssh_utilities.typeshed._SPATH`
            path to check

        Returns
        -------
        bool
            check result

        Raises
        ------
        IOError
            if dir could not be accessed
        """
        raise NotImplementedError

    @abstractmethod
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

    @abstractmethod
    def getsize(self, path: "_SPATH") -> int:
        """Return the size of path in bytes.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            path to file/directory

        Returns
        -------
        int
            size in bytes

        Raises
        ------
        OsError
            if the file does not exist or is inaccessible
        """
        raise NotImplementedError

    @abstractmethod
    def join(self, path: "_SPATH", *paths: "_SPATH") -> str:
        """Join one or more path components intelligently.

        The return value is the concatenation of path and any members of
        *paths with exactly one directory separator following each non-empty
        part except the last, meaning that the result will only end
        in a separator if the last part is empty. If a component is
        an absolute path, all previous components are thrown away and
        joining continues from the absolute path component. On Windows,
        the drive letter is not reset when an absolute path component
        (e.g., 'foo') is encountered. If a component contains a drive letter,
        all previous components are thrown away and the drive letter is reset.
        Note that since there is a current directory for each drive,
        os.path.join("c:", "foo") represents a path relative to the current
        directory on drive C: (c:foo), not c:/foo.

        Parameters
        ----------
        path : :const:`ssh_utilities.typeshed._SPATH`
            the starting path part
        *paths : :const:`ssh_utilities.typeshed._SPATH`
            path parts to join to the first one

        Returns
        -------
        str
            joined path parts
        """
        raise NotImplementedError
